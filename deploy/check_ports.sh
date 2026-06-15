#!/usr/bin/env sh
set -eu

check_port() {
  port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn | grep -q ":$port " && echo "IN USE $port" || echo "FREE $port"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn | grep -q ":$port " && echo "IN USE $port" || echo "FREE $port"
  else
    echo "Cannot check port $port: ss/netstat not found"
  fi
}

check_port 3010
check_port 8001
check_port 5432
