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

cleanup() {
  trap - INT TERM EXIT
  kill "${backend_pid:-}" "${frontend_pid:-}" 2>/dev/null || true
  wait "${backend_pid:-}" "${frontend_pid:-}" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
backend_pid=$!

(cd frontend && npm run dev) &
frontend_pid=$!

echo "Backend: http://127.0.0.1:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both services."

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

echo "One development service stopped; shutting down the other."
exit 1
