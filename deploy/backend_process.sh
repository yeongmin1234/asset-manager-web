#!/usr/bin/env sh
# Shared, read-only process checks for direct backend deployment.
# ROOT_DIR and BACKEND_PORT must be set by the caller.

backend_cmdline_matches() {
  tr '\000' '\n' < "$1" | awk -v port="$BACKEND_PORT" '
    NR == 1 && $0 !~ /(^|\/)python([0-9.]*)?$/ { interpreter = 0; next }
    NR == 1 { interpreter = 1 }
    previous_two == "-m" && previous == "uvicorn" && $0 == "app.main:app" { application = 1 }
    previous == "--port" { port_count++; if ($0 == port) matching_port = 1 }
    { previous_two = previous; previous = $0 }
    END { exit !(interpreter && application && matching_port && port_count == 1) }
  '
}

backend_ps_command_matches() {
  printf '%s\n' "$1" | awk -v port="$BACKEND_PORT" '
    {
      count = split($0, fields, /[[:space:]]+/)
      application = ($0 ~ /(^|\/)python([0-9.]*)?[[:space:]]+-m[[:space:]]+uvicorn[[:space:]]+app\.main:app([[:space:]]|$)/)
      for (field = 2; field <= count; field++) {
        if (fields[field - 1] == "--port") {
          port_count++
          if (fields[field] == port) matching_port = 1
        }
      }
    }
    END { exit !(application && matching_port && port_count == 1) }
  '
}

backend_ps_command_for_pid() {
  backend_ps_target="$1"
  if ps -p "$backend_ps_target" -o args= >/dev/null 2>&1; then
    ps -p "$backend_ps_target" -o args= 2>/dev/null
  else
    ps -ef 2>/dev/null | awk -v pid="$backend_ps_target" '
      $2 == pid { for (field = 8; field <= NF; field++) printf "%s%s", $field, (field < NF ? " " : "\n") }
    '
  fi
}

backend_pid_matches() {
  backend_check_pid="$1"
  case "$backend_check_pid" in
    ""|*[!0-9]*) return 1 ;;
  esac
  # Root-owned processes may deny access to /proc; ps is a read-only fallback.
  if [ -r "/proc/$backend_check_pid/cmdline" ] &&
     backend_cmdline_matches "/proc/$backend_check_pid/cmdline" 2>/dev/null; then
    return 0
  fi
  backend_ps_command="$(backend_ps_command_for_pid "$backend_check_pid")" || return 1
  [ -n "$backend_ps_command" ] && backend_ps_command_matches "$backend_ps_command"
}

backend_ps_pids() {
  if ps -eo pid=,args= >/dev/null 2>&1; then
    ps -eo pid=,args= 2>/dev/null | awk '
      { pid = $1; $1 = ""; if ($0 ~ /uvicorn/ && $0 ~ /app\.main:app/ && $0 ~ /--port/) print pid }
    '
  else
    ps -ef 2>/dev/null | awk '
      $0 ~ /uvicorn/ && $0 ~ /app\.main:app/ && $0 ~ /--port/ { print $2 }
    '
  fi
}

# Return 0 when occupied, 1 when free, and 2 when no usable inspection tool exists.
backend_port_status() {
  if command -v ss >/dev/null 2>&1; then
    backend_sockets="$(ss -ltn 2>/dev/null)" || backend_sockets=""
    if [ -n "$backend_sockets" ]; then
      printf '%s\n' "$backend_sockets" | grep -E -q ":${BACKEND_PORT}[[:space:]]"
      return $?
    fi
  fi
  if command -v netstat >/dev/null 2>&1; then
    backend_sockets="$(netstat -ltn 2>/dev/null)" || backend_sockets=""
    if [ -n "$backend_sockets" ]; then
      printf '%s\n' "$backend_sockets" | grep -E -q ":${BACKEND_PORT}[[:space:]]"
      return $?
    fi
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "$BACKEND_PORT/tcp" >/dev/null 2>&1
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import socket, sys; sock = socket.socket(); sock.bind(("0.0.0.0", int(sys.argv[1]))); sock.close()' "$BACKEND_PORT" >/dev/null 2>&1; then
      return 1
    fi
    return 0
  fi
  return 2
}

backend_listener_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$BACKEND_PORT" -sTCP:LISTEN 2>/dev/null || true
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "$BACKEND_PORT/tcp" 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+$' || true
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | grep -E ":${BACKEND_PORT}[[:space:]]" |
      sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' || true
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -ltnp 2>/dev/null | awk -v port="$BACKEND_PORT" '
      $4 ~ ":" port "$" && $7 ~ /^[0-9]+\// { split($7, owner, "/"); print owner[1] }
    ' || true
  fi
}
