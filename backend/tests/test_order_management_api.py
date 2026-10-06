import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.order_management import router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.online_order_channel import OnlineOrderChannel


class OrderManagementApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        MenuVisibilitySetting.__table__.create(self.engine)
        OnlineOrderChannel.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.app = FastAPI()
        self.app.include_router(router)
        self.user = SimpleNamespace(id=1, role="user", menu_permissions=["online_order"])
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_read_routes_and_admin_placeholders(self):
        for path in ("dashboard", "preview", "result/1", "mappings", "history", "settings"):
            response = self.client.get(f"/online/orders/{path}")
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.json()["status"], "ready")
            if path == "dashboard":
                self.assertEqual(response.json()["today_count"], 0)
                self.assertEqual(response.json()["mapping_required_count"], 0)
            if path in ("preview", "mappings", "history"):
                self.assertEqual(response.json()["items"], [])
                self.assertEqual(response.json()["total"], 0)
        self.assertEqual(self.client.post("/online/orders/process").status_code, 403)
        self.user.role = "admin"
        for path in ("upload", "process", "mappings"):
            self.assertEqual(self.client.post(f"/online/orders/{path}").status_code, 501, path)

    def test_permission_and_visibility_are_enforced(self):
        self.user.menu_permissions = []
        self.assertEqual(self.client.get("/online/orders/dashboard").status_code, 403)
        self.user.menu_permissions = ["online_order"]
        self.db.add(MenuVisibilitySetting(menu_key="online_order", visible=False))
        self.db.commit()
        self.assertEqual(self.client.get("/online/orders/dashboard").status_code, 403)
        self.user.role = "admin"
        self.assertEqual(self.client.get("/online/orders/dashboard").status_code, 403)

    def test_anonymous_request_requires_jwt(self):
        del self.app.dependency_overrides[get_current_user]
        self.assertEqual(self.client.get("/online/orders/dashboard").status_code, 401)

    def test_routes_register_once_in_application(self):
        from app.main import app

        for path in ("dashboard", "preview", "upload", "process", "result/{result_id}", "history", "settings"):
            full_path = f"/online/orders/{path}"
            self.assertEqual(sum(route.path == full_path for route in app.routes), 1, full_path)
        mapping_routes = [route for route in app.routes if route.path == "/online/orders/mappings"]
        self.assertEqual(len(mapping_routes), 2)
        self.assertEqual(set().union(*(route.methods for route in mapping_routes)), {"GET", "POST"})

    def test_channel_management_and_process_catalog(self):
        base = "/online/orders/channels"
        self.db.add(OnlineOrderChannel(name="스마트스토어", code="smartstore", description="네이버 스마트스토어", is_default=True))
        self.db.commit()
        initial = self.client.get(base)
        self.assertEqual(initial.status_code, 200)
        self.assertFalse(initial.json()[0]["processing_supported"])
        self.assertEqual(self.client.post(base, json={"name": "쿠팡", "code": "coupang"}).status_code, 403)

        self.user.role = "admin"
        created = self.client.post(base, json={"name": "쿠팡", "code": "coupang", "description": "쿠팡", "is_default": True})
        self.assertEqual(created.status_code, 201)
        channel = created.json()
        self.assertFalse(channel["processing_supported"])
        self.assertEqual(self.client.post(base, json={"name": "중복", "code": "coupang"}).status_code, 409)
        self.assertEqual(self.client.post(base, json={"name": "잘못된 코드", "code": "Bad-Code"}).status_code, 422)
        self.assertEqual(self.client.post(base, json={"name": "미사용 기본", "code": "inactive", "is_active": False, "is_default": True}).status_code, 422)
        self.assertEqual(sum(row["is_default"] for row in self.client.get(base).json()), 1)
        self.assertEqual(next(row for row in self.client.get(base).json() if row["code"] == "smartstore")["is_default"], False)

        channel_id = channel["id"]
        immutable = self.client.put(f"{base}/{channel_id}", json={"name": "쿠팡", "code": "changed", "description": "", "is_active": True, "is_default": False})
        self.assertEqual(immutable.status_code, 422)
        updated = self.client.put(f"{base}/{channel_id}", json={"name": "쿠팡 수정", "description": "변경", "is_active": False, "is_default": False})
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()["is_active"])
        self.assertEqual([row["code"] for row in self.client.get(f"{base}?active_only=true").json()], ["smartstore"])
        self.assertEqual([row["code"] for row in self.client.get(base).json() if row["is_default"]], ["smartstore"])
        self.assertEqual(self.client.post("/online/orders/process").status_code, 501)

        self.user.role = "user"
        self.assertEqual(self.client.get(base).status_code, 200)
        self.assertEqual(self.client.put(f"{base}/{channel_id}", json={"name": "차단", "description": "", "is_active": True, "is_default": False}).status_code, 403)
        self.user.menu_permissions = []
        self.assertEqual(self.client.get(base).status_code, 403)


if __name__ == "__main__":
    unittest.main()
