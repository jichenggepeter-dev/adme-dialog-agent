FROM ghcr.io/astral-sh/uv:0.11.32 AS uv

FROM python:3.11.15-bookworm

COPY --from=uv /uv /uvx /bin/

ENV PATH="/opt/venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

COPY .python-version pyproject.toml uv.lock README.md ./
RUN uv sync --locked --extra dev --no-install-project

COPY . .

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]
