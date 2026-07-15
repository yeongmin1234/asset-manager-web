import logging
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.database import engine
from app.models.inventory_job_run import InventoryJobRun
from app.models.inventory_schedule import InventorySchedule
from app.models.inventory_snapshot import InventorySnapshot
from app.services.inventory_service import InventoryError, InventoryService, MAX_RESULT_LIMIT


logger = logging.getLogger(__name__)
_fallback_locks = set()
_fallback_locks_guard = threading.Lock()
ADVISORY_LOCK_NAMESPACE = 73150


class InventorySnapshotNotFoundError(Exception):
    pass


class PostgresAdvisoryLock:
    def __init__(self, database_engine: Engine = engine):
        self.engine = database_engine

    @contextmanager
    def acquire(self, schedule_id: int):
        lock_key = ADVISORY_LOCK_NAMESPACE * 1000000 + int(schedule_id)
        if self.engine.dialect.name == "postgresql":
            connection = self.engine.connect()
            acquired = bool(connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"), {"lock_key": lock_key},
            ).scalar())
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": lock_key},
                    )
                connection.close()
            return

        with _fallback_locks_guard:
            acquired = lock_key not in _fallback_locks
            if acquired:
                _fallback_locks.add(lock_key)
        try:
            yield acquired
        finally:
            if acquired:
                with _fallback_locks_guard:
                    _fallback_locks.discard(lock_key)


class InventorySnapshotService:
    def __init__(
        self,
        inventory_service: Optional[InventoryService] = None,
        config: Settings = settings,
        lock_manager: Optional[PostgresAdvisoryLock] = None,
        sleep_func=time.sleep,
    ):
        self.inventory_service = inventory_service or InventoryService(config=config)
        self.config = config
        self.lock_manager = lock_manager or PostgresAdvisoryLock()
        self.sleep = sleep_func

    def run_schedule(
        self, db: Session, schedule_id: int, allow_inactive: bool = False,
    ) -> InventoryJobRun:
        schedule = db.get(InventorySchedule, schedule_id)
        if schedule is None:
            raise InventorySnapshotNotFoundError("재고 조회 일정을 찾을 수 없습니다.")
        if not schedule.is_active and not allow_inactive:
            return self._record_skipped(db, schedule.id, "inactive_schedule", "비활성 일정은 실행하지 않습니다.")

        with self.lock_manager.acquire(schedule.id) as acquired:
            if not acquired:
                return self._record_skipped(
                    db, schedule.id, "duplicate_run", "동일한 재고 조회 작업이 이미 실행 중입니다.",
                )
            return self._run_locked(db, schedule)

    def _run_locked(self, db: Session, schedule: InventorySchedule) -> InventoryJobRun:
        now = datetime.now(timezone.utc)
        expected_requested = (
            len(self._normalize_codes(schedule.target_item_codes))
            if schedule.target_mode == "selected_items" else 0
        )
        run = InventoryJobRun(schedule_id=schedule.id, started_at=now, status="running")
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            items, requested_count, failures = self._collect(schedule)
            if not items:
                code, message = failures[0] if failures else ("no_inventory", "저장할 재고 데이터가 없습니다.")
                return self._finish_failed(db, run, requested_count, len(failures), code, message)

            snapshot_at = datetime.now(timezone.utc)
            group_id = str(uuid.uuid4())
            snapshot_count = self._store_snapshots(db, schedule.id, group_id, snapshot_at, items)
            run.snapshot_group_id = group_id
            run.finished_at = datetime.now(timezone.utc)
            run.requested_item_count = requested_count
            run.success_count = len(items)
            run.failed_count = len(failures)
            run.snapshot_count = snapshot_count
            run.status = "partial_success" if failures else "success"
            if failures:
                run.error_code = failures[0][0][:64]
                run.safe_error_message = self._summarize_failures(failures)
            schedule.last_run_at = run.finished_at
            db.commit()
            db.refresh(run)
            # Snapshot persistence is the transaction boundary. Alert evaluation runs
            # only after a successful save and never makes the snapshot job fail.
            try:
                from app.services.inventory_alert_service import InventoryAlertService
                InventoryAlertService.detect_for_snapshot_group(
                    db, group_id, partial_result=bool(failures)
                )
                db.commit()
            except Exception as alert_exc:
                db.rollback()
                logger.error(
                    "Inventory alert detection failed schedule_id=%s error_type=%s",
                    schedule.id, type(alert_exc).__name__,
                )
            return run
        except InventoryError as exc:
            return self._finish_failed(db, run, expected_requested, 1, exc.kind, exc.message)
        except ValueError as exc:
            return self._finish_failed(db, run, expected_requested, 1, "validation", str(exc))
        except Exception as exc:
            logger.error(
                "Inventory snapshot job failed schedule_id=%s error_type=%s",
                schedule.id, type(exc).__name__,
            )
            return self._finish_failed(
                db, run, expected_requested, 1, "internal_error", "재고 스냅샷 저장 중 오류가 발생했습니다.",
            )

    def _collect(self, schedule: InventorySchedule) -> Tuple[List[Dict[str, Any]], int, List[Tuple[str, str]]]:
        limit = min(MAX_RESULT_LIMIT, max(1, int(self.config.inventory_snapshot_max_items)))
        if schedule.target_mode == "all_supported_items":
            products = self.inventory_service.search_products(limit=limit)
            locations = self._call_with_412_backoff(
                lambda: self.inventory_service.get_inventory_by_location(limit=limit)
            )
            grouped = self._group_locations(locations)
            return [
                self.inventory_service._aggregate_inventory(product, grouped.get(product["item_code"], []))
                for product in products
            ], len(products), []

        codes = self._normalize_codes(schedule.target_item_codes)
        if not codes:
            raise ValueError("선택 품목 일정에는 하나 이상의 품목코드가 필요합니다.")
        matches = self.inventory_service.search_products_for_keywords(codes, limit_per_keyword=1)
        items = []
        failures = []
        for index, code in enumerate(codes):
            found = matches.get(code) or []
            if not found or found[0]["item_code"] != code:
                failures.append(("item_not_found", "품목코드 {}을(를) 찾지 못했습니다.".format(code)))
                continue
            if index > 0 and self.config.inventory_snapshot_request_interval > 0:
                self.sleep(self.config.inventory_snapshot_request_interval)
            try:
                locations = self._call_with_412_backoff(
                    lambda code=code: self.inventory_service.get_inventory_by_location(
                        item_code=code, limit=MAX_RESULT_LIMIT,
                    )
                )
                items.append(self.inventory_service._aggregate_inventory(found[0], locations))
            except InventoryError as exc:
                failures.append((exc.kind, exc.message))
                if exc.http_status == 412:
                    remaining = len(codes) - index - 1
                    failures.extend([
                        ("rate_limited", "호출 제한으로 조회하지 못한 품목이 있습니다.")
                        for _ in range(remaining)
                    ])
                    break
        return items, len(codes), failures

    def _call_with_412_backoff(self, operation):
        retries = max(0, min(5, int(self.config.inventory_snapshot_412_max_retries)))
        for attempt in range(retries + 1):
            try:
                return operation()
            except InventoryError as exc:
                if exc.http_status != 412 or attempt >= retries:
                    raise
                delay = max(0.1, float(self.config.inventory_snapshot_request_interval)) * (2 ** attempt)
                logger.warning("ECOUNT snapshot rate limited http_status=412 retry=%s", attempt + 1)
                self.sleep(delay)
        raise RuntimeError("unreachable")

    @staticmethod
    def _group_locations(locations):
        grouped = {}
        for location in locations:
            grouped.setdefault(location["item_code"], []).append(location)
        return grouped

    @staticmethod
    def _normalize_codes(values):
        return list(dict.fromkeys(
            str(value).strip().upper() for value in (values or []) if str(value).strip()
        ))[:10]

    @staticmethod
    def _store_snapshots(db, schedule_id, group_id, snapshot_at, items):
        count = 0
        for item in items:
            total = Decimal(str(item["total_quantity"]))
            db.add(InventorySnapshot(
                snapshot_group_id=group_id, schedule_id=schedule_id, snapshot_at=snapshot_at,
                row_type="total", item_code=item["item_code"], item_name=item.get("item_name"),
                unit=item.get("unit"), warehouse_code="", warehouse_name=None,
                quantity=total, total_quantity=total,
            ))
            count += 1
            for index, warehouse in enumerate(item.get("warehouses") or [], 1):
                warehouse_code = warehouse.get("warehouse_code") or "__UNKNOWN_{}".format(index)
                db.add(InventorySnapshot(
                    snapshot_group_id=group_id, schedule_id=schedule_id, snapshot_at=snapshot_at,
                    row_type="warehouse", item_code=item["item_code"], item_name=item.get("item_name"),
                    unit=item.get("unit"), warehouse_code=warehouse_code,
                    warehouse_name=warehouse.get("warehouse_name"),
                    quantity=Decimal(str(warehouse["quantity"])), total_quantity=total,
                ))
                count += 1
        db.flush()
        return count

    @staticmethod
    def _record_skipped(db, schedule_id, code, message):
        now = datetime.now(timezone.utc)
        run = InventoryJobRun(
            schedule_id=schedule_id, started_at=now, finished_at=now, status="skipped",
            error_code=code, safe_error_message=message,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def _finish_failed(db, run, requested, failed, code, message):
        db.rollback()
        run = db.get(InventoryJobRun, run.id)
        run.finished_at = datetime.now(timezone.utc)
        run.status = "failed"
        run.requested_item_count = requested
        run.failed_count = failed
        run.error_code = str(code or "failed")[:64]
        run.safe_error_message = str(message or "재고 조회에 실패했습니다.")[:500]
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def _summarize_failures(failures):
        unique_messages = list(dict.fromkeys(message for _, message in failures))
        return " / ".join(unique_messages)[:500]


def list_active_inventory_schedules(db: Session) -> List[InventorySchedule]:
    return list(db.scalars(
        select(InventorySchedule).where(InventorySchedule.is_active.is_(True)).order_by(InventorySchedule.id)
    ))
