import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers import scm_activity
from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.base import Base
from app.models.scm_activity_log import ScmActivityLog
from app.models.user import User


class ScmActivityTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[User.__table__, ScmActivityLog.__table__])
        self.db = Session(self.engine)
        self.user = User(id=1, username="staff", name="담당자", password_hash="-", role="user", menu_permissions=["scm_app"], is_active=True)
        self.db.add(self.user)
        self.db.commit()
        app = FastAPI()
        app.include_router(scm_activity.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_registration_and_status_change_appear_newest_first(self):
        first = self.client.post("/scm/activity", json={"module": "consultation", "action": "create"})
        second = self.client.post("/scm/activity", json={"module": "sales", "action": "status_change"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        activities = self.client.get("/scm/dashboard").json()["recent_activity"]
        self.assertEqual([item["id"] for item in activities], [second.json()["id"], first.json()["id"]])
        self.assertEqual(activities[0]["user_name"], "담당자")
        self.assertEqual(activities[0]["message"], "판매 상태 변경 (미리보기)")

    def test_filters_and_message_cannot_contain_client_data(self):
        self.client.post("/scm/activity", json={"module": "as", "action": "create"})
        self.client.post("/scm/activity", json={"module": "sales", "action": "create"})
        result = self.client.get("/scm/activity", params={"module": "as", "action": "create", "user": "담당", "keyword": "A/S"}).json()
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["message"], "A/S 등록 (미리보기)")
        self.assertEqual(self.client.post("/scm/activity", json={"module": "as", "action": "create", "message": "고객 전화번호"}).status_code, 422)

    def test_update_and_delete_actions_are_recorded(self):
        for action in ("update", "delete"):
            response = self.client.post("/scm/activity", json={"module": "store", "action": action})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["action"], action)
        self.assertEqual(self.client.get("/scm/activity", params={"module": "store"}).json()["total"], 2)

    def test_permission_and_invalid_action(self):
        self.user.menu_permissions = []
        self.assertEqual(self.client.get("/scm/dashboard").status_code, 403)
        self.assertEqual(self.client.get("/scm/activity").status_code, 403)
        self.assertEqual(self.client.post("/scm/activity", json={"module": "sales", "action": "create"}).status_code, 403)
        self.user.menu_permissions = ["scm_app"]
        self.assertEqual(self.client.post("/scm/activity", json={"module": "as", "action": "delete"}).status_code, 422)

    def test_admin_is_recorded_too(self):
        self.user.role = "admin"
        self.user.menu_permissions = []
        response = self.client.post("/scm/activity", json={"module": "store", "action": "update"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user_name"], "담당자")

    def test_anonymous_is_rejected(self):
        self.app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.client.get("/scm/dashboard").status_code, 401)
        self.assertEqual(self.client.get("/scm/activity").status_code, 401)
        self.assertEqual(self.client.post("/scm/activity", json={"module": "store", "action": "create"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
