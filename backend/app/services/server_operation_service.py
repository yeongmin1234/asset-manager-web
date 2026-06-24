from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.schemas.server_operation import ScmStatusResponse


SCM_SERVER_NAME = "SCM"
SCM_CONFIG_REQUIRED_MESSAGE = "SCM 서버 접속 정보가 설정되지 않았습니다."
SCM_SSH_UNAVAILABLE_MESSAGE = "SCM 서버 상태 확인 기능을 사용할 수 없습니다."
SCM_CONNECTION_OK_MESSAGE = "SCM 서버 연결이 확인되었습니다."
SCM_CONNECTION_FAILED_MESSAGE = "SCM 서버 연결을 확인하지 못했습니다."


def get_scm_status() -> ScmStatusResponse:
    checked_at = datetime.utcnow()
    if not _has_scm_connection_config():
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            reachable=False,
            uptime_text=None,
            checked_at=checked_at,
            message=SCM_CONFIG_REQUIRED_MESSAGE,
            status="configuration_required",
        )

    try:
        uptime_text = _read_scm_uptime()
    except ImportError:
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            reachable=False,
            uptime_text=None,
            checked_at=checked_at,
            message=SCM_SSH_UNAVAILABLE_MESSAGE,
            status="check_unavailable",
        )
    except Exception:
        return ScmStatusResponse(
            server_name=SCM_SERVER_NAME,
            reachable=False,
            uptime_text=None,
            checked_at=checked_at,
            message=SCM_CONNECTION_FAILED_MESSAGE,
            status="connection_failed",
        )

    return ScmStatusResponse(
        server_name=SCM_SERVER_NAME,
        reachable=True,
        uptime_text=uptime_text or "확인됨",
        checked_at=checked_at,
        message=SCM_CONNECTION_OK_MESSAGE,
        status="ok",
    )


def validate_scm_reboot_dry_run(reason: str, confirm_text: str) -> None:
    if not str(reason or "").strip():
        raise ValueError("재부팅 사유를 입력해주세요.")
    if str(confirm_text or "").strip() != "REBOOT":
        raise ValueError("확인 문구를 정확히 REBOOT로 입력해주세요.")


def _has_scm_connection_config() -> bool:
    return all(
        [
            str(settings.scm_reboot_host or "").strip(),
            str(settings.scm_reboot_user or "").strip(),
            str(settings.scm_reboot_password or "").strip(),
        ]
    )


def _read_scm_uptime() -> Optional[str]:
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
        if uptime_text:
            return uptime_text
        raw_uptime = _run_ssh_command(client, "cat /proc/uptime")
        return _format_proc_uptime(raw_uptime)
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


def execute_scm_reboot_placeholder() -> None:
    # Step 3 will wire the actual reboot command after an explicit safety review.
    raise RuntimeError("SCM reboot execution is disabled in this phase.")
