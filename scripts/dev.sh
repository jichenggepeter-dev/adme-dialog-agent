#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x .venv/bin/python ]]; then
  echo "[FAIL] .venv is missing. Run: make setup"
  exit 1
fi

if [[ ! -f frontend/package.json ]]; then
  echo "[FAIL] frontend/package.json is missing."
  exit 1
fi

backend_host="${BACKEND_HOST:-127.0.0.1}"
backend_port="${BACKEND_PORT:-8000}"
frontend_host="${FRONTEND_HOST:-127.0.0.1}"
frontend_port="${FRONTEND_PORT:-3000}"
api_base_url="${NEXT_PUBLIC_API_BASE_URL:-http://${backend_host}:${backend_port}}"

cleanup() {
  trap - INT TERM EXIT
  kill "${backend_pid:-}" "${frontend_pid:-}" 2>/dev/null || true
  wait "${backend_pid:-}" "${frontend_pid:-}" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

.venv/bin/python -m uvicorn app.main:app --host "$backend_host" --port "$backend_port" &
backend_pid=$!

(cd frontend && NEXT_PUBLIC_API_BASE_URL="$api_base_url" npm run dev -- --hostname "$frontend_host" --port "$frontend_port") &
frontend_pid=$!

echo "Backend: http://${backend_host}:${backend_port}"
echo "Frontend: http://${frontend_host}:${frontend_port}"
echo "Press Ctrl+C to stop both services."

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

echo "One development service stopped; shutting down the other."
exit 1
