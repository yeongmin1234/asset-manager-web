from datetime import datetime
import socket
from typing import Optional

from app.core.config import settings
from app.schemas.server_operation import ScmStatusResponse


SCM_SERVER_NAME = "SCM"
SCM_CONFIG_REQUIRED_MESSAGE = "SCM 서버 접속 정보가 설정되지 않았습니다."
SCM_SSH_UNAVAILABLE_MESSAGE = "SCM 서버 상태 확인 기능을 사용할 수 없습니다."
SCM_CONNECTION_OK_MESSAGE = "SCM 서버 연결이 확인되었습니다."
SCM_CONNECTION_FAILED_MESSAGE = "SCM 서버 연결을 확인하지 못했습니다."
MARIADB_DRY_RUN_SUCCESS_MESSAGE = "MariaDB 재시작 조건 확인이 완료되었습니다. 현재 단계에서는 실제 재시작 명령을 실행하지 않습니다."


def get_scm_status() -> ScmStatusResponse:
    checked_at = datetime.utcnow()
    if not _has_scm_connection_config():
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            server_reachable=False,
            uptime_text=None,
            uptime_display=None,
            mariadb_status="unknown",
            mariadb_active=False,
            mariadb_message="SCM SSH 접속 정보가 설정되지 않아 MariaDB 상태를 확인할 수 없습니다.",
            db_port_reachable=False,
            db_port_message="SCM SSH 접속 정보가 설정되지 않아 3306 포트를 확인할 수 없습니다.",
            checked_at=checked_at,
            message=SCM_CONFIG_REQUIRED_MESSAGE,
            status="configuration_required",
        )

    try:
        health = _read_scm_mariadb_health()
    except ImportError:
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            server_reachable=False,
            uptime_text=None,
            uptime_display=None,
            mariadb_status="unknown",
            mariadb_active=False,
            mariadb_message="SCM 서버 상태 확인 기능을 사용할 수 없습니다.",
            db_port_reachable=False,
            db_port_message="SCM 서버 3306 포트 확인 기능을 사용할 수 없습니다.",
            checked_at=checked_at,
            message=SCM_SSH_UNAVAILABLE_MESSAGE,
            status="check_unavailable",
        )
    except Exception:
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            server_reachable=False,
            uptime_text=None,
            uptime_display=None,
            mariadb_status="unknown",
            mariadb_active=False,
            mariadb_message="MariaDB 상태를 확인하지 못했습니다.",
            db_port_reachable=False,
            db_port_message="3306 포트 상태를 확인하지 못했습니다.",
            checked_at=checked_at,
            message=SCM_CONNECTION_FAILED_MESSAGE,
            status="connection_failed",
        )

    return ScmStatusResponse(
        server_name=SCM_SERVER_NAME,
        server_reachable=True,
        uptime_text=health.get("uptime_text") or "확인됨",
        uptime_display=health.get("uptime_display"),
        mariadb_status=health.get("mariadb_status") or "unknown",
        mariadb_active=bool(health.get("mariadb_active")),
        mariadb_message=health.get("mariadb_message") or "MariaDB 상태를 확인했습니다.",
        db_port_reachable=bool(health.get("db_port_reachable")),
        db_port_message=health.get("db_port_message") or "3306 포트 상태를 확인했습니다.",
        checked_at=checked_at,
        message=SCM_CONNECTION_OK_MESSAGE,
        status="ok",
    )


def validate_scm_mariadb_restart_dry_run(reason: str, confirm_text: str) -> None:
    if not str(reason or "").strip():
        raise ValueError("MariaDB 재시작 사유를 입력해주세요.")
    if str(confirm_text or "").strip() != "MARIADB":
        raise ValueError("확인 문구를 정확히 MARIADB로 입력해주세요.")


def _has_scm_connection_config() -> bool:
    return all(
        [
            str(settings.scm_reboot_host or "").strip(),
            str(settings.scm_reboot_user or "").strip(),
            str(settings.scm_reboot_password or "").strip(),
        ]
    )


def _read_scm_mariadb_health() -> dict:
    try:
        import paramiko
    except ImportError as exc:
        raise ImportError("paramiko is not available") from exc

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=str(settings.scm_reboot_host),
            port=int(settings.scm_reboot_port or 22),
            username=str(settings.scm_reboot_user),
            password=str(settings.scm_reboot_password),
            timeout=5,
            banner_timeout=5,
            auth_timeout=5,
            look_for_keys=False,
            allow_agent=False,
        )
        uptime_text = _run_ssh_command(client, "uptime -p")
        if not uptime_text:
            raw_uptime = _run_ssh_command(client, "cat /proc/uptime")
            uptime_text = _format_proc_uptime(raw_uptime)

        mariadb_status = _normalize_mariadb_status(_run_ssh_command_text(client, "systemctl is-active mariadb"))
        db_port_reachable = _check_mariadb_port_from_ssh(client)
        if db_port_reachable is None:
            db_port_reachable = _check_mariadb_port_socket()

        return {
            "uptime_text": uptime_text,
            "uptime_display": format_uptime_display(uptime_text),
            "mariadb_status": mariadb_status,
            "mariadb_active": mariadb_status == "active",
            "mariadb_message": _get_mariadb_message(mariadb_status),
            "db_port_reachable": bool(db_port_reachable),
            "db_port_message": _get_db_port_message(bool(db_port_reachable)),
        }
    finally:
        client.close()


def _run_ssh_command(client, command: str) -> Optional[str]:
    stdin, stdout, stderr = client.exec_command(command, timeout=5)
    del stdin
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        return None
    output = stdout.read().decode("utf-8", errors="replace").strip()
    return output or None


def _run_ssh_command_text(client, command: str) -> Optional[str]:
    stdin, stdout, stderr = client.exec_command(command, timeout=5)
    del stdin, stderr
    stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", errors="replace").strip()
    return output or None


def _format_proc_uptime(raw_uptime: Optional[str]) -> Optional[str]:
    if not raw_uptime:
        return None
    try:
        seconds = int(float(str(raw_uptime).split()[0]))
    except (IndexError, TypeError, ValueError):
        return None

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append("{} days".format(days))
    if hours:
        parts.append("{} hours".format(hours))
    if minutes or not parts:
        parts.append("{} minutes".format(minutes))
    return "up {}".format(", ".join(parts))


def format_uptime_display(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    unit_labels = {
        "week": "주",
        "weeks": "주",
        "day": "일",
        "days": "일",
        "hour": "시간",
        "hours": "시간",
        "minute": "분",
        "minutes": "분",
        "second": "초",
        "seconds": "초",
    }
    words = str(value).strip().replace(",", "").split()
    if words and words[0].lower() == "up":
        words = words[1:]

    parts = []
    index = 0
    while index + 1 < len(words):
        amount = words[index]
        unit = words[index + 1].lower()
        if amount.isdigit() and unit in unit_labels:
            parts.append("{}{}".format(amount, unit_labels[unit]))
        index += 2

    return " ".join(parts) if parts else str(value)


def _normalize_mariadb_status(value: Optional[str]) -> str:
    status = str(value or "").strip().lower()
    if status in ("active", "inactive", "failed", "activating", "deactivating"):
        return status
    return "unknown"


def _check_mariadb_port_from_ssh(client) -> Optional[bool]:
    output = _run_ssh_command(client, "ss -ltn sport = :3306")
    if output:
        return True
    return False


def _check_mariadb_port_socket() -> bool:
    try:
        with socket.create_connection((str(settings.scm_reboot_host), 3306), timeout=3):
            return True
    except Exception:
        return False


def _get_mariadb_message(status: str) -> str:
    if status == "active":
        return "MariaDB 서비스가 실행 중입니다."
    if status == "inactive":
        return "MariaDB 서비스가 비활성 상태입니다."
    if status == "failed":
        return "MariaDB 서비스가 실패 상태입니다."
    return "MariaDB 서비스 상태를 확인하지 못했습니다."


def _get_db_port_message(is_reachable: bool) -> str:
    if is_reachable:
        return "3306 포트가 응답 가능합니다."
    return "3306 포트가 응답하지 않습니다. MariaDB freeze 가능성이 있습니다."


def execute_scm_mariadb_restart_placeholder() -> None:
    # 3단계 실제 MariaDB 재시작 시 안전 검토 후 polling API와 연결 예정입니다.
    raise RuntimeError("SCM MariaDB restart execution is disabled in this phase.")
