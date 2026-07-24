#!/bin/zsh

set -euo pipefail

ROOT="${0:A:h:h}"
LOG_DIR="$ROOT/data/demo-logs"
FRONTEND_LABEL="org.adme-dialog-agent.frontend"
BACKEND_LABEL="org.adme-dialog-agent.backend"
PYTHON_BIN="$ROOT/.venv/bin/python"
NPM_BIN="${NPM_BIN:-$(command -v npm || true)}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  print -u2 "Missing $PYTHON_BIN. Run: make setup"
  exit 1
fi

BASE_PYTHON="$("$PYTHON_BIN" -c 'import sys; print(sys._base_executable)')"
SITE_PACKAGES="$("$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"

if [[ -z "$NPM_BIN" || ! -x "$NPM_BIN" ]]; then
  print -u2 "npm was not found. Install Node.js and npm, or set NPM_BIN."
  exit 1
fi

mkdir -p "$LOG_DIR"

remove_job() {
  /bin/launchctl remove "$1" >/dev/null 2>&1 || true
  for ((attempt = 1; attempt <= 20; attempt++)); do
    if ! /bin/launchctl list "$1" >/dev/null 2>&1; then
      return 0
    fi
    /bin/sleep 0.2
  done
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts=30

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if /usr/bin/curl --silent --fail --max-time 2 "$url" >/dev/null 2>&1; then
      print "$name: ready"
      return 0
    fi
    /bin/sleep 1
  done

  print -u2 "$name: did not become ready; inspect $LOG_DIR"
  return 1
}

start_services() {
  remove_job "$FRONTEND_LABEL"
  remove_job "$BACKEND_LABEL"

  /bin/launchctl submit -l "$BACKEND_LABEL" \
    -o "$LOG_DIR/backend.log" -e "$LOG_DIR/backend.log" -- \
    /bin/zsh -lc "cd '$ROOT' && export PYTHONPATH='$SITE_PACKAGES' && exec '$BASE_PYTHON' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

  /bin/launchctl submit -l "$FRONTEND_LABEL" \
    -o "$LOG_DIR/frontend.log" -e "$LOG_DIR/frontend.log" -- \
    /bin/zsh -lc "cd '$ROOT/frontend' && exec '$NPM_BIN' run dev -- --hostname 127.0.0.1 --port 3000"

  wait_for_url "FastAPI backend" "http://127.0.0.1:8000/health"
  wait_for_url "Next.js frontend" "http://127.0.0.1:3000/single"
  print "ADME demo: http://127.0.0.1:3000/single"
  print "LLM provider: configure and run separately when AGENT_ENABLED=true"
}

status_services() {
  local failed=0
  wait_for_url "FastAPI backend" "http://127.0.0.1:8000/health" || failed=1
  wait_for_url "Next.js frontend" "http://127.0.0.1:3000/single" || failed=1
  return "$failed"
}

stop_services() {
  remove_job "$FRONTEND_LABEL"
  remove_job "$BACKEND_LABEL"
  print "ADME demo services stopped."
}

case "${1:-start}" in
  start) start_services ;;
  status) status_services ;;
  stop) stop_services ;;
  *)
    print -u2 "Usage: $0 {start|status|stop}"
    exit 2
    ;;
esac
