PYTHON ?= .venv/bin/python
UV ?= uv
COMPOSE ?= docker compose
VERIFY_REPORT_DIR ?= /tmp/adme-dialog-agent-verify
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 3000

.PHONY: setup dev-check test test-unit test-api test-agent test-agent-integration smoke-mock smoke-real smoke-agent-llm backend frontend dev batch-demo onboarding evaluate-rag-baseline docs-check verify-docs verify-backend verify-frontend verify check container-up container-watch container-down container-reset verify-container

setup:
	@command -v $(UV) >/dev/null || { echo "[FAIL] uv 0.11.32 is required. See docs/contributor-environment.md"; exit 1; }
	$(UV) sync --locked --extra dev
	@if [ -f frontend/package.json ]; then cd frontend && npm ci; fi
	@echo "Setup complete. Next: make dev"

dev-check:
	ADME_MOCK_MODE=true $(PYTHON) scripts/dev_check.py

test:
	ADME_MOCK_MODE=true $(PYTHON) -m pytest -v

test-unit:
	ADME_MOCK_MODE=true $(PYTHON) -m pytest -v tests/test_smiles.py tests/test_formatter.py tests/test_agent.py

test-api:
	ADME_MOCK_MODE=true $(PYTHON) -m pytest -v tests/test_api.py

test-agent:
	AGENT_ENABLED=false ADME_MOCK_MODE=true $(PYTHON) -m pytest -q tests/test_agent_*.py

test-agent-integration:
	RUN_AGENT_LLM_INTEGRATION=true AGENT_ENABLED=true ADME_MOCK_MODE=true $(PYTHON) -m pytest -q tests/integration -s

smoke-mock:
	ADME_MOCK_MODE=true $(PYTHON) -c "from app.tools.admet_predictor import predict_one; print(predict_one('CC(=O)OC1=CC=CC=C1C(=O)O'))"

smoke-real:
	env -u ADME_MOCK_MODE $(PYTHON) scripts/smoke_test_admet.py

smoke-agent-llm:
	$(PYTHON) scripts/smoke_test_agent_llm.py

backend:
	$(PYTHON) -m uvicorn app.main:app --reload --reload-dir app --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend:
	cd frontend && npm run dev -- --hostname $(FRONTEND_HOST) --port $(FRONTEND_PORT)

dev:
	./scripts/dev.sh

batch-demo:
	ADME_MOCK_MODE=true $(PYTHON) scripts/batch_demo.py

onboarding:
	ADME_MOCK_MODE=true AGENT_ENABLED=true AGENT_PROVIDER_MODE=mock \
		NEXT_PUBLIC_AGENT_PROVIDER_MODE=mock NEXT_PUBLIC_REVIEW_MODE=false \
		$(COMPOSE) up --build --wait
	@echo "Onboarding workspace: http://127.0.0.1:3000/single"

evaluate-rag-baseline:
	$(PYTHON) scripts/evaluate_evidence_retrieval.py

docs-check:
	$(PYTHON) scripts/check_markdown_links.py

verify-docs:
	@echo "==> Documentation links (retry: make verify-docs)"
	$(MAKE) docs-check

verify-backend:
	@echo "==> Backend tests (retry: make verify-backend)"
	ADME_MOCK_MODE=true AGENT_ENABLED=false RUN_AGENT_LLM_INTEGRATION=0 OPENAI_AGENTS_DISABLE_TRACING=1 $(PYTHON) -m pytest -q
	@echo "==> Deterministic Agent evaluation (retry: make verify-backend)"
	@mkdir -p "$(VERIFY_REPORT_DIR)"
	ADME_MOCK_MODE=true AGENT_ENABLED=false OPENAI_AGENTS_DISABLE_TRACING=1 $(PYTHON) scripts/evaluate_agent.py --mode deterministic_rules --mode mock_provider --json-output "$(VERIFY_REPORT_DIR)/agent-eval.json" --markdown-output "$(VERIFY_REPORT_DIR)/agent-eval.md"
	$(PYTHON) scripts/evaluate_evidence_retrieval.py --json-output "$(VERIFY_REPORT_DIR)/evidence-retrieval-baseline.json" --markdown-output "$(VERIFY_REPORT_DIR)/evidence-retrieval-baseline.md"

verify-frontend:
	@echo "==> Frontend gate (retry: make verify-frontend)"
	cd frontend && npm run verify

verify: verify-docs verify-backend verify-frontend

check: verify

container-up:
	$(COMPOSE) up --build

container-watch:
	$(COMPOSE) watch

container-down:
	$(COMPOSE) down

container-reset:
	$(COMPOSE) down --volumes --remove-orphans

verify-container:
	$(COMPOSE) build
	$(COMPOSE) run --rm --no-deps backend make PYTHON=python verify-docs verify-backend
	$(COMPOSE) run --rm --no-deps frontend npm run verify
