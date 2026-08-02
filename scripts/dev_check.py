from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000"))
API_BASE_URL = os.getenv("NEXT_PUBLIC_API_BASE_URL", f"http://127.0.0.1:{BACKEND_PORT}")
REQUIRED_PACKAGES = ("fastapi", "pydantic", "uvicorn", "admet-ai")


def report(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def command_version(command: str, flag: str = "--version") -> str | None:
    executable = shutil.which(command)
    if executable is None:
        return None
    result = subprocess.run([executable, flag], capture_output=True, text=True, check=False)
    output = (result.stdout or result.stderr).strip()
    return output or None


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def fetch_status() -> dict | None:
    try:
        with urllib.request.urlopen(f"{API_BASE_URL}/status", timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def main() -> int:
    critical_failures = 0
    report("INFO", f"Python executable: {sys.executable}")
    report("PASS", f"Python version: {sys.version.split()[0]}")

    in_venv = sys.prefix != sys.base_prefix
    report("PASS" if in_venv else "FAIL", "Python virtual environment active" if in_venv else "Activate .venv first")
    critical_failures += int(not in_venv)

    for package in REQUIRED_PACKAGES:
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report("FAIL", f"Required package missing: {package}")
            critical_failures += 1
        else:
            report("PASS", f"{package} {version} installed")

    node_version = command_version("node")
    npm_version = command_version("npm")
    report("PASS" if node_version else "FAIL", f"Node: {node_version or 'not found'}")
    report("PASS" if npm_version else "FAIL", f"npm: {npm_version or 'not found'}")
    critical_failures += int(node_version is None or npm_version is None)

    frontend_exists = (ROOT / "frontend" / "package.json").exists()
    report("PASS" if frontend_exists else "WARN", "Frontend directory exists" if frontend_exists else "Frontend has not been created yet")
    report("INFO", f"API base URL: {API_BASE_URL}")

    status = fetch_status()
    if status:
        report("PASS", f"Backend reachable at {API_BASE_URL}")
        report("INFO", f"Prediction mode: {status.get('prediction_mode', 'unknown')}")
        if status.get("prediction_mode") == "real" and not status.get("model_loaded"):
            report("WARN", "Real ADMET model has not been loaded")
    else:
        report("WARN", f"Backend is not reachable at {API_BASE_URL}")

    for port in (FRONTEND_PORT, BACKEND_PORT):
        available = port_is_available(port)
        report("PASS" if available else "INFO", f"Port {port} is {'available' if available else 'in use'}")

    mock_mode = os.getenv("ADME_MOCK_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
    report("INFO", f"Mock mode is {'active' if mock_mode else 'inactive'}")
    return 1 if critical_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
