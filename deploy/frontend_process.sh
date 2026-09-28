#!/usr/bin/env sh
# Shared, read-only process checks for the direct frontend static server.
# ROOT_DIR and FRONTEND_PORT must be set by the caller.

frontend_pid_matches() {
  frontend_check_pid="$1"
  case "$frontend_check_pid" in
    ""|*[!0-9]*) return 1 ;;
  esac
  [ -r "/proc/$frontend_check_pid/cmdline" ] || return 1
  kill -0 "$frontend_check_pid" 2>/dev/null || return 1
  frontend_script="$ROOT_DIR/deploy/static_server.py"
  frontend_dist="$ROOT_DIR/frontend/dist"

  tr '\000' '\n' < "/proc/$frontend_check_pid/cmdline" |
    awk -v script="$frontend_script" -v directory="$frontend_dist" -v port="$FRONTEND_PORT" '
      NR == 1 && $0 !~ /(^|\/)python([0-9.]*)?$/ { interpreter = 0; next }
      NR == 1 { interpreter = 1 }
      $0 == script { static_script = 1 }
      previous == "-m" && $0 == "http.server" { http_server = 1 }
      previous == "--port" && $0 == port { static_port = 1 }
      previous == "http.server" && $0 == port { module_port = 1 }
      previous == "--directory" && $0 == directory { matching_directory = 1 }
      { previous = $0 }
      END { exit !(interpreter && matching_directory &&
        ((static_script && static_port) || (http_server && module_port))) }
    '
}

# Return 0 when occupied, 1 when free, and 2 when inspection is unavailable.
frontend_port_status() {
  if command -v ss >/dev/null 2>&1; then
    frontend_sockets="$(ss -ltn 2>/dev/null)" || frontend_sockets=""
    if [ -n "$frontend_sockets" ]; then
      printf '%s\n' "$frontend_sockets" | grep -E -q ":${FRONTEND_PORT}[[:space:]]"
      return $?
    fi
  fi
  if command -v netstat >/dev/null 2>&1; then
    frontend_sockets="$(netstat -ltn 2>/dev/null)" || frontend_sockets=""
    if [ -n "$frontend_sockets" ]; then
      printf '%s\n' "$frontend_sockets" | grep -E -q ":${FRONTEND_PORT}[[:space:]]"
      return $?
    fi
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$FRONTEND_PORT" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "$FRONTEND_PORT/tcp" >/dev/null 2>&1
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import socket, sys; sock = socket.socket(); sock.bind(("0.0.0.0", int(sys.argv[1]))); sock.close()' "$FRONTEND_PORT" >/dev/null 2>&1; then
      return 1
    fi
    return 0
  fi
  return 2
}
