from datetime import datetime
import re
import socket
import time
from typing import Optional

from app.core.config import settings
from app.schemas.server_operation import ScmStatusResponse


SCM_SERVER_NAME = "SCM"
SCM_CONFIG_REQUIRED_MESSAGE = "SCM 서버 접속 정보가 설정되지 않았습니다."
SCM_SSH_UNAVAILABLE_MESSAGE = "SCM 서버 상태 확인 기능을 사용할 수 없습니다."
SCM_CONNECTION_OK_MESSAGE = "SCM 서버 연결이 확인되었습니다."
SCM_CONNECTION_FAILED_MESSAGE = "SCM 서버 연결을 확인하지 못했습니다."
MARIADB_DRY_RUN_SUCCESS_MESSAGE = "MariaDB 재시작 조건 확인이 완료되었습니다. 현재 단계에서는 실제 재시작 명령을 실행하지 않습니다."
MARIADB_RESTART_SUCCESS_MESSAGE = "MariaDB 재시작 명령을 실행했습니다."


def get_scm_status() -> ScmStatusResponse:
    checked_at = datetime.utcnow()
    if not _has_scm_connection_config():
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            server_reachable=False,
            uptime_text=None,
            uptime_display=None,
            server_uptime_text=None,
            server_uptime_display=None,
            mariadb_active_since=None,
            mariadb_uptime_text=None,
            mariadb_uptime_display=None,
            mariadb_uptime_days=None,
            mariadb_status="unknown",
            mariadb_active=False,
            mariadb_message="SCM SSH 접속 정보가 설정되지 않아 MariaDB 상태를 확인할 수 없습니다.",
            db_port_reachable=False,
            db_port_message="SCM SSH 접속 정보가 설정되지 않아 3306 포트를 확인할 수 없습니다.",
            mariadb_restart_enabled=is_scm_mariadb_restart_enabled(),
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
            server_uptime_text=None,
            server_uptime_display=None,
            mariadb_active_since=None,
            mariadb_uptime_text=None,
            mariadb_uptime_display=None,
            mariadb_uptime_days=None,
            mariadb_status="unknown",
            mariadb_active=False,
            mariadb_message="SCM 서버 상태 확인 기능을 사용할 수 없습니다.",
            db_port_reachable=False,
            db_port_message="SCM 서버 3306 포트 확인 기능을 사용할 수 없습니다.",
            mariadb_restart_enabled=is_scm_mariadb_restart_enabled(),
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
            server_uptime_text=None,
            server_uptime_display=None,
            mariadb_active_since=None,
            mariadb_uptime_text=None,
            mariadb_uptime_display=None,
            mariadb_uptime_days=None,
            mariadb_status="unknown",
            mariadb_active=False,
            mariadb_message="MariaDB 상태를 확인하지 못했습니다.",
            db_port_reachable=False,
            db_port_message="3306 포트 상태를 확인하지 못했습니다.",
            mariadb_restart_enabled=is_scm_mariadb_restart_enabled(),
            checked_at=checked_at,
            message=SCM_CONNECTION_FAILED_MESSAGE,
            status="connection_failed",
        )

    return ScmStatusResponse(
        server_name=SCM_SERVER_NAME,
        server_reachable=True,
        uptime_text=health.get("uptime_text") or "확인됨",
        uptime_display=health.get("uptime_display"),
        server_uptime_text=health.get("server_uptime_text") or health.get("uptime_text") or "확인됨",
        server_uptime_display=health.get("server_uptime_display") or health.get("uptime_display"),
        mariadb_active_since=health.get("mariadb_active_since"),
        mariadb_uptime_text=health.get("mariadb_uptime_text"),
        mariadb_uptime_display=health.get("mariadb_uptime_display"),
        mariadb_uptime_days=health.get("mariadb_uptime_days"),
        mariadb_status=health.get("mariadb_status") or "unknown",
        mariadb_active=bool(health.get("mariadb_active")),
        mariadb_message=health.get("mariadb_message") or "MariaDB 상태를 확인했습니다.",
        db_port_reachable=bool(health.get("db_port_reachable")),
        db_port_message=health.get("db_port_message") or "3306 포트 상태를 확인했습니다.",
        mariadb_restart_enabled=is_scm_mariadb_restart_enabled(),
        checked_at=checked_at,
        message=SCM_CONNECTION_OK_MESSAGE,
        status="ok",
    )


def validate_scm_mariadb_restart_dry_run(reason: str, confirm_text: str) -> None:
    if not str(reason or "").strip():
        raise ValueError("MariaDB 재시작 사유를 입력해주세요.")
    if str(confirm_text or "").strip() != "MARIADB":
        raise ValueError("확인 문구를 정확히 MARIADB로 입력해주세요.")


def is_scm_mariadb_restart_enabled() -> bool:
    return bool(settings.scm_mariadb_restart_enabled)


def execute_scm_mariadb_restart() -> dict:
    if not is_scm_mariadb_restart_enabled():
        raise RuntimeError("현재 실제 MariaDB 재시작은 비활성화되어 있습니다.")
    if not _has_scm_connection_config():
        raise RuntimeError("SCM SSH 접속 정보가 설정되지 않아 MariaDB 재시작을 실행할 수 없습니다.")

    client = _create_scm_ssh_client()
    try:
        before_status = _normalize_mariadb_status(_run_ssh_command_text(client, "systemctl is-active mariadb"))
        _check_mariadb_port_from_ssh(client)
        restart_result = _run_ssh_command_result(client, "systemctl restart mariadb", timeout=15)
        if not restart_result.get("ok"):
            raise RuntimeError("MariaDB 재시작 명령 실행에 실패했습니다.")

        time.sleep(4)
        after_status = _normalize_mariadb_status(_run_ssh_command_text(client, "systemctl is-active mariadb"))
        db_port_reachable = _check_mariadb_port_from_ssh(client)
        if db_port_reachable is None:
            db_port_reachable = _check_mariadb_port_socket()

        return {
            "ok": after_status == "active",
            "message": MARIADB_RESTART_SUCCESS_MESSAGE,
            "before_status": before_status,
            "after_status": after_status,
            "db_port_reachable": bool(db_port_reachable),
            "checked_at": datetime.utcnow(),
        }
    except RuntimeError:
        raise
    except ImportError as exc:
        raise RuntimeError("SCM 서버 상태 확인 기능을 사용할 수 없습니다.") from exc
    except Exception as exc:
        raise RuntimeError("SCM 서버 SSH 연결 또는 MariaDB 재확인에 실패했습니다.") from exc
    finally:
        client.close()


def _has_scm_connection_config() -> bool:
    return all(
        [
            str(settings.scm_reboot_host or "").strip(),
            str(settings.scm_reboot_user or "").strip(),
            str(settings.scm_reboot_password or "").strip(),
        ]
    )


def _read_scm_mariadb_health() -> dict:
    client = _create_scm_ssh_client()
    try:
        uptime_text = _run_ssh_command(client, "uptime -p")
        if not uptime_text:
            raw_uptime = _run_ssh_command(client, "cat /proc/uptime")
            uptime_text = _format_proc_uptime(raw_uptime)

        mariadb_status = _normalize_mariadb_status(_run_ssh_command_text(client, "systemctl is-active mariadb"))
        mariadb_uptime = _read_mariadb_uptime(client)
        db_port_reachable = _check_mariadb_port_from_ssh(client)
        if db_port_reachable is None:
            db_port_reachable = _check_mariadb_port_socket()

        server_uptime_display = format_uptime_display(uptime_text)
        return {
            "uptime_text": uptime_text,
            "uptime_display": server_uptime_display,
            "server_uptime_text": uptime_text,
            "server_uptime_display": server_uptime_display,
            "mariadb_active_since": mariadb_uptime.get("active_since"),
            "mariadb_uptime_text": mariadb_uptime.get("uptime_text"),
            "mariadb_uptime_display": mariadb_uptime.get("uptime_display"),
            "mariadb_uptime_days": mariadb_uptime.get("uptime_days"),
            "mariadb_status": mariadb_status,
            "mariadb_active": mariadb_status == "active",
            "mariadb_message": _get_mariadb_message(mariadb_status),
            "db_port_reachable": bool(db_port_reachable),
            "db_port_message": _get_db_port_message(bool(db_port_reachable)),
        }
    finally:
        client.close()


def _create_scm_ssh_client():
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
        return client
    except Exception:
        client.close()
        raise


def _run_ssh_command_result(client, command: str, timeout: int = 5) -> dict:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    del stdin
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", errors="replace").strip()
    error_output = stderr.read().decode("utf-8", errors="replace").strip()
    return {
        "ok": exit_status == 0,
        "exit_status": exit_status,
        "output": output,
        "error": error_output,
    }


def _read_mariadb_uptime(client) -> dict:
    active_since_text = _run_ssh_command(
        client,
        "systemctl show mariadb --property=ActiveEnterTimestamp --value",
    )
    if not active_since_text:
        status_text = _run_ssh_command_text(client, "systemctl status mariadb --no-pager")
        active_since_text = _parse_active_since_from_status(status_text)

    active_since = _parse_systemctl_timestamp(active_since_text)
    if not active_since:
        return {
            "active_since": _normalize_active_since_display(active_since_text),
            "uptime_text": None,
            "uptime_display": "확인 실패" if active_since_text else None,
            "uptime_days": None,
        }

    now = datetime.now()
    total_seconds = int((now - active_since).total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    uptime_display = format_duration_display(total_seconds)
    return {
        "active_since": active_since.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_text": uptime_display,
        "uptime_display": uptime_display,
        "uptime_days": total_seconds // 86400,
    }


def _parse_active_since_from_status(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    match = re.search(r"Active:\s+.*?\bsince\s+(.+?);", str(value), re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"Active:\s+.*?\bsince\s+(.+)$", str(value), re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _parse_systemctl_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("n/a", "none"):
        return None

    match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", text)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _normalize_active_since_display(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(value).strip() or None


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


def format_duration_display(total_seconds: int) -> str:
    if total_seconds < 0:
        total_seconds = 0

    total_minutes = total_seconds // 60
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days >= 30:
        months = days // 30
        remaining_days = days % 30
        parts = ["{}개월".format(months)]
        if remaining_days:
            parts.append("{}일".format(remaining_days))
        return " ".join(parts)

    if days:
        parts = ["{}일".format(days)]
        if hours:
            parts.append("{}시간".format(hours))
        return " ".join(parts)

    if hours:
        parts = ["{}시간".format(hours)]
        if minutes:
            parts.append("{}분".format(minutes))
        return " ".join(parts)

    return "{}분".format(total_minutes)


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
