"""Generate the proposed 4-2 permission inventory from the 4-1 design files."""

import csv
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

API_MENU = {
    "users": "/settings/accounts", "stores": "/store-management/stores",
    "employees": "/store-management/staff", "marketplaces": "/settings/markets",
    "code-groups": "/settings/codes", "codes": "/settings/codes",
    "system-settings": "/settings", "customers": "/customers",
    "consultations": "/consultations", "as-requests": "/as",
    "as-symptoms": "/settings/symptoms", "as-parts": "/settings/symptoms",
    "products": "/store-management/products", "sales": "/sales",
    "purchase-orders": "/order-support", "goods-receipts": "/customer-consulting/logistics-list",
    "inventory-balances": "/customer-consulting/logistics-list",
    "inventory-movements": "/customer-consulting/logistics-list",
    "serial-inventories": "/customer-consulting/logistics-list",
    "stock-transfers": "/customer-consulting/logistics-management",
    "inventory-adjustments": "/customer-consulting/logistics-management",
    "logistics-orders": "/logistics", "notices": "/notices",
    "memos": "/memo-search", "sms-templates": "/settings/filter-sms",
    "sms-send-logs": "/settings/send-status", "sms": "/settings/filter-sms",
    "sms-opt-outs": "/settings/opt-out", "batch-jobs": "/settings/batches",
    "serial-bulk-jobs": "/settings/serial-update", "dashboard": "/",
    "reports": "/store-management/statistics", "audit-logs": "/activity",
}


def action_for(method: str, endpoint: str, hint: str) -> str:
    if endpoint == "/auth/login":
        return "public (4-1 제안; 이번 단계 미구현)"
    if endpoint == "/auth/logout":
        return "auth.logout"
    if endpoint == "/auth/me":
        return "system.access"
    if endpoint == "/audit-logs":
        return "audit.read"
    if endpoint.endswith("/apply") and endpoint.startswith("/serial-bulk-jobs"):
        return "approval.grant + bulk.change"
    if endpoint.endswith("/approve") or hint == "승인":
        return "approval.grant"
    if endpoint.endswith("/apply") or endpoint.endswith("/complete") or endpoint.endswith("/status"):
        return "status.change"
    if endpoint.startswith("/serial-bulk-jobs") and method == "POST":
        return "excel.upload" if endpoint == "/serial-bulk-jobs" else "bulk.change"
    if endpoint == "/sms/dry-run":
        return "sms.dry_run"
    if endpoint.endswith("/read"):
        return "notice.read"
    if endpoint.endswith("/runs") and method == "POST":
        return "batch.run"
    return {"GET": "data.read", "POST": "data.create", "PATCH": "data.update", "DELETE": "data.delete"}[method]


def main():
    with (DOCS / "SCM_MENU_DB_MAPPING.csv").open(encoding="utf-8-sig", newline="") as file:
        menus = list(csv.DictReader(file))
    endpoints = []
    pattern = re.compile(r"^\| `((?:GET|POST|PATCH|DELETE)) (/[^`]+)` \|.*\|([^|]+)\|$")
    for line in (DOCS / "SCM_API_SPEC.md").read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            method, endpoint, detail = match.groups()
            fields = [item.strip() for item in detail.split(";")]
            hint = fields[-3] if len(fields) >= 3 else "미정"
            endpoints.append((method, endpoint, hint))
    if len(menus) != 39 or len(endpoints) != 115:
        raise ValueError(f"설계 인벤토리 변경: 메뉴 {len(menus)}, API {len(endpoints)}")

    lines = [
        "# 신규 SCM 권한 매트릭스 (4-2단계)", "",
        "2026-10-27 기준. 4-1 설계의 표시 경로 39개·업무 API 제안 115개를 매핑했다. **제안 목록이며 업무 API 115개는 아직 구현되지 않았다.**",
        "", "## 정책", "",
        "- 서버의 검증된 사용자에게 `system.access`가 명시적으로 부여되어야 한다. 기본 grant는 비어 있으며 `users.account_type=admin`만으로 권한을 얻지 않는다.",
        "- 메뉴 grant는 화면 경로와 분리하고, API action grant는 각 엔드포인트에서 별도 검사한다. 메뉴가 보인다는 이유로 API 사용을 허용하지 않는다.",
        "- 관리자 기능은 활성 사용자 + `system.access` + `account_type=admin` + `admin.manage`를 함께 요구한다. 기존 `users`에는 grant 저장 컬럼/테이블이 없다.",
        "- 매장/고객/개인정보의 행·필드별 범위, 승인자 분리, 상태 전이, 업로드·일괄 변경은 API 구현 전에 별도 서버 정책을 확정해야 한다.",
        "- 아래 API의 관련 화면은 탐색용 대응이다. API 허가는 해당 화면 grant와 독립이다. 숨김/404 화면도 기본 거부다.",
        "", "## 메뉴 경로 39개", "", "| 화면 | 경로 (메뉴 grant 후보) | 추가 조건 | 현재 상태 |", "|---|---|---|---|",
    ]
    for row in menus:
        path = row["URL"].strip("`")
        extra = "관리자 + `admin.manage`" if path.startswith("/settings") else "`system.access` + 명시적 경로 grant"
        if path == "/settings/general":
            extra += "; 현재 404"
        lines.append(f"| {row['메뉴']} | `{path}` | {extra} | 매핑 제안; 서버 업무 API 미구현 |")

    lines += ["", "## 업무 API 제안 115개", "", "| Method | Endpoint | 관련 화면 | API action grant | 추가 검증 | 상태 |", "|---|---|---|---|---|---|"]
    for method, endpoint, hint in endpoints:
        base = endpoint.split("/")[1]
        menu = API_MENU.get(base, "미정")
        action = action_for(method, endpoint, hint)
        extra = "관리자 + `admin.manage`" if hint in {"관리", "감사"} else hint
        if hint == "승인":
            extra = "별도 승인자 + 자기 승인 금지"
        state = "공통 API 구현; 검증기 미연결로 401" if endpoint == "/auth/me" else "미구현"
        lines.append(f"| {method} | `{endpoint}` | `{menu}` | `{action}` | {extra} | {state} |")
    lines += [
        "", "## 실제 구현과 저장소 제약", "",
        "- 구현된 인증 API: `GET /api/v1/auth/me` 1개. 현재 검증기가 미연결이므로 실제 호출은 401이다. 테스트 주입으로만 200/403 경계를 확인했다.",
        "- 구현된 서버 공통 검사: 활성 검증 사용자, `system.access`, 독립 메뉴 grant, 독립 action grant, 관리자 이중 조건. 업무 API 라우터가 없어 115개 엔드포인트별 검사 실행은 0개다.",
        "- `users(id,username,name,email,password_hash,account_type,status,...)`에는 세부 권한과 외부 통합 사용자 연결 키가 없다. 새 테이블/컬럼을 만들지 않았다.",
        "- 후속 스키마 제안: 외부 주체와 SCM 사용자 매핑(유일 키·활성 여부), 역할/사용자별 메뉴·action grant, 매장 범위, 승인 분리, 변경 감사. 설계 승인 전 마이그레이션 금지.",
    ]
    (DOCS / "SCM_PERMISSION_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"menus={len(menus)} api_designs={len(endpoints)}")


if __name__ == "__main__":
    main()
