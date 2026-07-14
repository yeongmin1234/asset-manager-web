import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import Request

from app.api.routers.company_vehicles import create_new_company_vehicle, update_existing_company_vehicle
from app.api.routers.vehicle_insurance_histories import update_existing_vehicle_insurance_history
from app.models.company_vehicle import VehicleOwnershipType
from app.models.user import User
from app.schemas.company_vehicle import CompanyVehicleCreate, CompanyVehicleUpdate
from app.schemas.vehicle_insurance_history import VehicleInsuranceHistoryUpdate


def request(path):
    return Request({"type": "http", "method": "PUT", "path": path, "headers": [], "client": ("127.0.0.1", 1), "server": ("test", 8010), "scheme": "http", "query_string": b""})


def user():
    return User(id=1, username="admin", name="관리자", password_hash="-", role="admin")


def vehicle(**updates):
    values = dict(
        id=3, company_name="더리모", vehicle_number="12가3456", vehicle_name="테스트차량",
        driver_name="홍길동", ownership_type=VehicleOwnershipType.COMPANY,
        insurance_company="기존보험", insurance_type="종합", insurance_start_date=None,
        insurance_end_date=None, lease_company=None, lease_start_date=None, lease_end_date=None,
        monthly_lease_amount=None, lease_payment_day=None, tax_note=None,
    )
    values.update(updates)
    return SimpleNamespace(**values)


class CompanyVehicleAuditRegressionTest(unittest.TestCase):
    def test_vehicle_create_has_defined_user_and_no_stale_vehicle_id_reference(self):
        db = MagicMock()
        result = vehicle()
        payload = CompanyVehicleCreate(vehicle_number="12가3456", vehicle_name="테스트차량")
        with patch("app.api.routers.company_vehicles.create_company_vehicle", return_value=result), patch("app.api.routers.company_vehicles.record_audit_log", return_value=True) as audit:
            response = create_new_company_vehicle(request("/vehicles"), payload, db, user())
        self.assertEqual(response.id, 3)
        self.assertEqual(audit.call_args.kwargs["action_type"], "create")

    def test_vehicle_insurance_update_builds_serializable_changes(self):
        db = MagicMock()
        db.get.return_value = vehicle()
        result = vehicle(insurance_company="새보험", insurance_end_date=None)
        payload = CompanyVehicleUpdate(
            company_name="더리모", vehicle_number="12가3456", vehicle_name="테스트차량",
            driver_name="홍길동", ownership_type="회사", insurance_company="새보험", insurance_type="종합",
        )
        with patch("app.api.routers.company_vehicles.update_company_vehicle", return_value=result), patch("app.api.routers.company_vehicles.record_audit_log", return_value=False) as audit:
            response = update_existing_company_vehicle(request("/vehicles/3"), 3, payload, db, user())
        self.assertEqual(response.insurance_company, "새보험")
        self.assertEqual(audit.call_args.kwargs["changed_fields"], ["insurance_company"])
        self.assertEqual(audit.call_args.kwargs["after_data"], {"insurance_company": "새보험"})

    def test_insurance_history_update_records_audit_without_affecting_result(self):
        db = MagicMock()
        before = SimpleNamespace(id=7, vehicle_id=3, start_date=None, end_date=None, insurance_type="책임", driver_name=None, amount=1000, payment_method=None, note=None)
        after = SimpleNamespace(id=7, vehicle_id=3, start_date=None, end_date=None, insurance_type="종합", driver_name=None, amount=1000, payment_method=None, note=None)
        payload = VehicleInsuranceHistoryUpdate(insurance_type="종합", amount=1000)
        with patch("app.api.routers.vehicle_insurance_histories.get_vehicle_insurance_history", return_value=before), patch("app.api.routers.vehicle_insurance_histories.update_vehicle_insurance_history", return_value=after), patch("app.api.routers.vehicle_insurance_histories.record_audit_log", return_value=False) as audit:
            response = update_existing_vehicle_insurance_history(request("/vehicles/insurance-histories/7"), 7, payload, db, user())
        self.assertEqual(response.insurance_type, "종합")
        self.assertEqual(audit.call_args.kwargs["changed_fields"], ["insurance_type"])


if __name__ == "__main__":
    unittest.main()
