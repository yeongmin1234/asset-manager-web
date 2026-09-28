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

backend_pid_matches() {
  backend_check_pid="$1"
  case "$backend_check_pid" in
    ""|*[!0-9]*) return 1 ;;
  esac
  [ -r "/proc/$backend_check_pid/cmdline" ] || return 1

  # Root-owned processes may deny access to /proc/<pid>/cwd and kill -0.
  # Identify the backend only from its readable command line and port.
  backend_cmdline_matches "/proc/$backend_check_pid/cmdline"
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
