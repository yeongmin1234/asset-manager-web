import unittest

from app.main import app


class CrudOpenApiRegressionTest(unittest.TestCase):
    def test_major_crud_routes_and_methods_exist(self):
        expected = {
            "/assets": {"get", "post"}, "/assets/{asset_id}": {"get", "put", "delete"},
            "/assets/{asset_id}/dispose": {"patch"},
            "/software": {"get", "post"}, "/software/{software_id}": {"put", "delete"},
            "/vehicles": {"get", "post"}, "/vehicles/{vehicle_id}": {"put", "delete"},
            "/vehicles/{vehicle_id}/insurance-histories": {"get", "post"},
            "/vehicles/insurance-histories/{history_id}": {"put", "delete"},
            "/expiration-schedules": {"get", "post"}, "/expiration-schedules/{schedule_id}": {"get", "put", "delete"},
            "/expiration-schedules/{schedule_id}/complete": {"patch"},
            "/hr/accounts": {"get", "post"}, "/hr/accounts/{account_id}": {"put", "delete"},
            "/hr/accounts/import": {"post"}, "/users": {"get", "post"}, "/users/{user_id}": {"put", "delete"},
            "/work-manuals": {"get", "post"}, "/work-manuals/{manual_id}": {"get", "put", "delete"},
            "/vendor-contacts": {"get", "post"}, "/vendor-contacts/{contact_id}": {"put", "delete"},
            "/install-files": {"get", "post"}, "/install-files/{file_id}": {"get", "put", "delete"},
            "/admin/audit-logs": {"get"},
        }
        paths = app.openapi()["paths"]
        for path, methods in expected.items():
            self.assertIn(path, paths, path)
            self.assertTrue(methods.issubset(paths[path]), "{}: {}".format(path, methods - set(paths[path])))


if __name__ == "__main__":
    unittest.main()
