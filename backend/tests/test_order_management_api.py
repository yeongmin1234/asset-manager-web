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


class OrderManagementApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        MenuVisibilitySetting.__table__.create(self.engine)
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
        for path in ("dashboard", "result/1", "mappings", "history", "settings"):
            response = self.client.get(f"/online/orders/{path}")
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.json()["status"], "ready")
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

        for path in ("dashboard", "upload", "process", "result/{result_id}", "history", "settings"):
            full_path = f"/online/orders/{path}"
            self.assertEqual(sum(route.path == full_path for route in app.routes), 1, full_path)
        mapping_routes = [route for route in app.routes if route.path == "/online/orders/mappings"]
        self.assertEqual(len(mapping_routes), 2)
        self.assertEqual(set().union(*(route.methods for route in mapping_routes)), {"GET", "POST"})


if __name__ == "__main__":
    unittest.main()
