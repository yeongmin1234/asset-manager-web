import unittest

from app.schemas.user import normalize_menu_permissions


class MenuPermissionSplitTest(unittest.TestCase):
    def test_legacy_network_permission_expands_to_both_new_permissions(self):
        self.assertEqual(
            normalize_menu_permissions(["dashboard", "network"]),
            ["dashboard", "access_info", "equipment_status"],
        )

    def test_new_permissions_remain_independent(self):
        self.assertEqual(normalize_menu_permissions(["access_info"]), ["access_info"])
        self.assertEqual(normalize_menu_permissions(["equipment_status"]), ["equipment_status"])


if __name__ == "__main__":
    unittest.main()
