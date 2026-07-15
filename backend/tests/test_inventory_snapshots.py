from contextlib import contextmanager
from datetime import datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.db.database import get_db
from app.main import app
from app.models.inventory_job_run import InventoryJobRun
from app.models.inventory_schedule import InventorySchedule
from app.models.inventory_snapshot import InventorySnapshot
from app.models.user import User
from app.services.inventory_scheduler_service import InventorySchedulerService, calculate_next_run_at
from app.services.inventory_service import InventoryConnectionError, InventoryService
from app.services.inventory_snapshot_query_service import compare_latest_snapshots, get_latest_snapshot
from app.services.inventory_snapshot_service import InventorySnapshotService


def config(**overrides):
    values = {
        "inventory_snapshot_max_items": 200,
        "inventory_snapshot_request_interval": 0,
        "inventory_snapshot_412_max_retries": 2,
        "inventory_scheduler_enabled": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def product(code, name):
    return {"item_code": code, "item_name": name, "size": None, "unit": "EA"}


def location(code, quantity, warehouse_code="001", warehouse_name="본사"):
    return {
        "item_code": code, "item_name": code, "product_size_description": None,
        "warehouse_code": warehouse_code, "warehouse_name": warehouse_name,
        "quantity": Decimal(str(quantity)),
    }


class FakeInventoryService:
    _aggregate_inventory = staticmethod(InventoryService._aggregate_inventory)

    def __init__(self, products=None, locations=None, failures=None):
        self.products = products or []
        self.locations = locations or []
        self.failures = failures or {}
        self.product_calls = 0
        self.location_calls = 0

    def search_products(self, limit=200):
        self.product_calls += 1
        failure = self.failures.get("products")
        if failure:
            raise failure
        return self.products[:limit]

    def search_products_for_keywords(self, keywords, limit_per_keyword=1):
        self.product_calls += 1
        return {
            code: [item for item in self.products if item["item_code"] == code][:limit_per_keyword]
            for code in keywords
        }

    def get_inventory_by_location(self, item_code=None, limit=200):
        self.location_calls += 1
        failure = self.failures.get(item_code or "all")
        if isinstance(failure, list) and failure:
            error = failure.pop(0)
            if error:
                raise error
        elif failure:
            raise failure
        rows = self.locations if not item_code else [row for row in self.locations if row["item_code"] == item_code]
        return rows[:limit]


class FakeLock:
    def __init__(self, acquired=True):
        self.acquired = acquired

    @contextmanager
    def acquire(self, schedule_id):
        yield self.acquired


class FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.running = False

    def start(self, paused=False):
        self.running = True

    def resume(self):
        pass

    def shutdown(self, wait=False):
        self.running = False

    def get_jobs(self):
        return list(self.jobs)

    def remove_job(self, job_id):
        self.jobs = [job for job in self.jobs if job.id != job_id]

    def add_job(self, function, trigger, args, id, **kwargs):
        job = SimpleNamespace(
            id=id,
            next_run_time=trigger.get_next_fire_time(None, datetime.now(timezone.utc)),
        )
        self.jobs.append(job)
        return job


class InventorySnapshotTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        InventorySchedule.__table__.create(self.engine)
        InventoryJobRun.__table__.create(self.engine)
        InventorySnapshot.__table__.create(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_schedule(self, active=True, mode="selected_items", codes=None, run_time=time(8, 0)):
        schedule = InventorySchedule(
            name="오전 재고", run_time=run_time, timezone="Asia/Seoul", is_active=active,
            target_mode=mode, target_item_codes=codes or [],
        )
        self.db.add(schedule)
        self.db.commit()
        return schedule

    def make_service(self, fake, acquired=True, **config_overrides):
        return InventorySnapshotService(
            inventory_service=fake, config=config(**config_overrides),
            lock_manager=FakeLock(acquired), sleep_func=lambda seconds: None,
        )

    def test_snapshot_stores_decimal_negative_total_and_warehouses(self):
        schedule = self.add_schedule(codes=["A"])
        fake = FakeInventoryService(
            [product("A", "상품 A")],
            [location("A", "1.1234567890"), location("A", "-2.0000000000", "002", "RMA")],
        )
        run = self.make_service(fake).run_schedule(self.db, schedule.id)
        rows = list(self.db.scalars(select(InventorySnapshot).order_by(InventorySnapshot.row_type)))
        self.assertEqual(run.status, "success")
        self.assertEqual(run.snapshot_count, 3)
        total = next(row for row in rows if row.row_type == "total")
        self.assertEqual(total.total_quantity, Decimal("-0.8765432110"))
        self.assertEqual([row.quantity for row in rows if row.row_type == "warehouse"], [
            Decimal("1.1234567890"), Decimal("-2.0000000000"),
        ])

    def test_partial_failure_saves_successful_item(self):
        schedule = self.add_schedule(codes=["A", "B"])
        error = InventoryConnectionError("connection_failed", "안전한 연결 오류")
        fake = FakeInventoryService(
            [product("A", "상품 A"), product("B", "상품 B")], [location("A", "3")],
            failures={"B": error},
        )
        run = self.make_service(fake).run_schedule(self.db, schedule.id)
        self.assertEqual((run.status, run.success_count, run.failed_count), ("partial_success", 1, 1))
        self.assertGreater(run.snapshot_count, 0)

    def test_total_failure_is_recorded_without_sensitive_values(self):
        schedule = self.add_schedule(mode="all_supported_items")
        fake = FakeInventoryService(failures={
            "products": InventoryConnectionError("connection_failed", "이카운트 연결에 실패했습니다."),
        })
        run = self.make_service(fake).run_schedule(self.db, schedule.id)
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.error_code, "connection_failed")
        self.assertNotIn("SESSION_ID", repr(run.safe_error_message))
        self.assertNotIn("API_CERT_KEY", repr(run.safe_error_message))

    def test_412_has_bounded_backoff(self):
        schedule = self.add_schedule(codes=["A"])
        limited = InventoryConnectionError("http_error", "호출 제한", 412)
        fake = FakeInventoryService(
            [product("A", "상품 A")], [location("A", "1")],
            failures={"A": [limited, limited, None]},
        )
        sleeps = []
        service = InventorySnapshotService(
            inventory_service=fake,
            config=config(inventory_snapshot_request_interval=1, inventory_snapshot_412_max_retries=2),
            lock_manager=FakeLock(), sleep_func=sleeps.append,
        )
        run = service.run_schedule(self.db, schedule.id)
        self.assertEqual(run.status, "success")
        self.assertEqual(fake.location_calls, 3)
        self.assertEqual(sleeps, [1.0, 2.0])

    def test_duplicate_lock_and_inactive_schedule_are_skipped(self):
        active = self.add_schedule(codes=["A"])
        inactive = self.add_schedule(active=False, codes=["A"])
        fake = FakeInventoryService([product("A", "A")], [location("A", "1")])
        duplicate = self.make_service(fake, acquired=False).run_schedule(self.db, active.id)
        inactive_run = self.make_service(fake).run_schedule(self.db, inactive.id)
        self.assertEqual((duplicate.status, duplicate.error_code), ("skipped", "duplicate_run"))
        self.assertEqual((inactive_run.status, inactive_run.error_code), ("skipped", "inactive_schedule"))
        self.assertEqual(fake.location_calls, 0)

    def test_latest_and_compare_queries(self):
        schedule = self.add_schedule(codes=["A"])
        fake = FakeInventoryService([product("A", "상품 A")], [location("A", "1")])
        self.make_service(fake).run_schedule(self.db, schedule.id)
        fake.locations = [location("A", "3")]
        self.make_service(fake).run_schedule(self.db, schedule.id)
        latest = get_latest_snapshot(self.db, item_code="A")
        compared = compare_latest_snapshots(self.db, item_code="A")
        self.assertEqual(latest["items"][0]["total_quantity"], Decimal("3.0000000000"))
        self.assertEqual(compared["items"][0]["difference"], Decimal("2.0000000000"))

    def test_scheduler_loads_only_active_schedule_in_korea_timezone(self):
        active = self.add_schedule(codes=["A"], run_time=time(8, 0))
        self.add_schedule(active=False, codes=["B"])
        fake_scheduler = FakeScheduler()
        service = InventorySchedulerService(
            config=config(), scheduler=fake_scheduler, session_factory=self.Session,
        )
        service.start()
        try:
            run_jobs = [job.id for job in fake_scheduler.jobs if job.id.startswith("inventory-schedule-")]
            self.assertEqual(run_jobs, ["inventory-schedule-{}".format(active.id)])
            self.assertIn("inventory-schedules-sync", [job.id for job in fake_scheduler.jobs])
            next_run = calculate_next_run_at(active, datetime(2026, 7, 14, 22, 0, tzinfo=timezone.utc))
            self.assertEqual((next_run.hour, next_run.minute), (8, 0))
            self.assertEqual(str(next_run.tzinfo), "Asia/Seoul")
        finally:
            service.shutdown()


class InventorySnapshotRouteTest(unittest.TestCase):
    def test_openapi_contains_admin_and_user_snapshot_paths(self):
        paths = app.openapi()["paths"]
        expected = {
            "/admin/integrations/ecount/inventory/schedules",
            "/admin/integrations/ecount/inventory/schedules/{schedule_id}/active",
            "/admin/integrations/ecount/inventory/schedules/{schedule_id}/run",
            "/admin/integrations/ecount/inventory/job-runs",
            "/admin/integrations/ecount/inventory/snapshots",
            "/inventory/snapshots/latest",
            "/inventory/snapshots/history",
            "/inventory/snapshots/compare",
        }
        self.assertTrue(expected.issubset(paths))

    def test_normal_user_gets_403_for_admin_schedule_api(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=2, username="user", name="일반", password_hash="-", role="user",
        )
        try:
            response = TestClient(app).get("/admin/integrations/ecount/inventory/schedules")
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_gets_401(self):
        response = TestClient(app).get("/inventory/snapshots/latest")
        self.assertEqual(response.status_code, 401)

    def test_admin_can_manually_run_schedule(self):
        now = datetime.now(timezone.utc)
        safe_run = SimpleNamespace(
            id=1, schedule_id=7, snapshot_group_id="safe-group", started_at=now,
            finished_at=now, status="success", requested_item_count=1, success_count=1,
            failed_count=0, snapshot_count=2, error_code=None, safe_error_message=None,
            created_at=now,
        )
        app.dependency_overrides[get_current_user] = lambda: User(
            id=1, username="admin", name="관리자", password_hash="-", role="admin",
        )
        app.dependency_overrides[get_db] = lambda: object()
        try:
            with patch("app.api.routers.ecount_integration.InventorySnapshotService") as service:
                service.return_value.run_schedule.return_value = safe_run
                response = TestClient(app).post(
                    "/admin/integrations/ecount/inventory/schedules/7/run"
                )
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_duplicate_manual_run_returns_409(self):
        now = datetime.now(timezone.utc)
        skipped = SimpleNamespace(
            id=2, schedule_id=7, snapshot_group_id=None, started_at=now, finished_at=now,
            status="skipped", requested_item_count=0, success_count=0, failed_count=0,
            snapshot_count=0, error_code="duplicate_run",
            safe_error_message="동일한 재고 조회 작업이 이미 실행 중입니다.", created_at=now,
        )
        app.dependency_overrides[get_current_user] = lambda: User(
            id=1, username="admin", name="관리자", password_hash="-", role="admin",
        )
        app.dependency_overrides[get_db] = lambda: object()
        try:
            with patch("app.api.routers.ecount_integration.InventorySnapshotService") as service:
                service.return_value.run_schedule.return_value = skipped
                response = TestClient(app).post(
                    "/admin/integrations/ecount/inventory/schedules/7/run"
                )
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
