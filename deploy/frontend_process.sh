#!/usr/bin/env sh
# Shared, read-only process checks for the direct frontend static server.
# ROOT_DIR and FRONTEND_PORT must be set by the caller.

frontend_cmdline_matches() {
  frontend_script="$ROOT_DIR/deploy/static_server.py"
  frontend_dist="$ROOT_DIR/frontend/dist"
  tr '\000' '\n' < "$1" |
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

frontend_ps_command_matches() {
  frontend_script="$ROOT_DIR/deploy/static_server.py"
  frontend_dist="$ROOT_DIR/frontend/dist"
  printf '%s\n' "$1" | awk -v script="$frontend_script" -v directory="$frontend_dist" -v port="$FRONTEND_PORT" '
    {
      count = split($0, fields, /[[:space:]]+/)
      interpreter = ($0 ~ /(^|\/)python([0-9.]*)?[[:space:]]+/)
      static_script = (index($0, script) > 0)
      matching_directory = (index($0, "--directory " directory) > 0)
      for (field = 2; field <= count; field++) {
        if (fields[field - 1] == "-m" && fields[field] == "http.server") http_server = 1
        if (fields[field - 1] == "--port" && fields[field] == port) static_port = 1
        if (fields[field - 1] == "http.server" && fields[field] == port) module_port = 1
      }
    }
    END { exit !(interpreter && matching_directory && ((static_script && static_port) || (http_server && module_port))) }
  '
}

frontend_ps_command_for_pid() {
  frontend_ps_target="$1"
  if ps -p "$frontend_ps_target" -o args= >/dev/null 2>&1; then
    ps -p "$frontend_ps_target" -o args= 2>/dev/null
  else
    ps -ef 2>/dev/null | awk -v pid="$frontend_ps_target" '
      $2 == pid { for (field = 8; field <= NF; field++) printf "%s%s", $field, (field < NF ? " " : "\n") }
    '
  fi
}

frontend_pid_matches() {
  frontend_check_pid="$1"
  case "$frontend_check_pid" in
    ""|*[!0-9]*) return 1 ;;
  esac
  if [ -r "/proc/$frontend_check_pid/cmdline" ] &&
     frontend_cmdline_matches "/proc/$frontend_check_pid/cmdline" 2>/dev/null; then
    return 0
  fi
  frontend_ps_command="$(frontend_ps_command_for_pid "$frontend_check_pid")" || return 1
  [ -n "$frontend_ps_command" ] && frontend_ps_command_matches "$frontend_ps_command"
}

frontend_ps_pids() {
  if ps -eo pid=,args= >/dev/null 2>&1; then
    ps -eo pid=,args= 2>/dev/null | awk '
      { pid = $1; $1 = ""; if ($0 ~ /static_server\.py|http\.server/ && $0 ~ /--directory/) print pid }
    '
  else
    ps -ef 2>/dev/null | awk '
      $0 ~ /static_server\.py|http\.server/ && $0 ~ /--directory/ { print $2 }
    '
  fi
}

frontend_listener_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$FRONTEND_PORT" -sTCP:LISTEN 2>/dev/null || true
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "$FRONTEND_PORT/tcp" 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+$' || true
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | grep -E ":${FRONTEND_PORT}[[:space:]]" |
      sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' || true
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -ltnp 2>/dev/null | awk -v port="$FRONTEND_PORT" '
      $4 ~ ":" port "$" && $7 ~ /^[0-9]+\// { split($7, owner, "/"); print owner[1] }
    ' || true
  fi
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
