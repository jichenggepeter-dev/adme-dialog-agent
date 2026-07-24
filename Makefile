PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: setup test test-unit test-api test-agent test-agent-integration smoke-mock smoke-real smoke-agent-llm backend frontend dev batch-demo check

setup:
	@if [ ! -d .venv ]; then python3 -m venv .venv; else echo "Using existing .venv (not recreating it)."; fi
	$(PIP) install -r requirements.txt
	@if [ -f frontend/package.json ]; then cd frontend && npm install; fi
	@echo "Setup complete. Next: export ADME_MOCK_MODE=true && make dev"

test:
	ADME_MOCK_MODE=true $(PYTEST) -v

test-unit:
	ADME_MOCK_MODE=true $(PYTEST) -v tests/test_smiles.py tests/test_formatter.py tests/test_agent.py

test-api:
	ADME_MOCK_MODE=true $(PYTEST) -v tests/test_api.py

test-agent:
	AGENT_ENABLED=false ADME_MOCK_MODE=true $(PYTEST) -q tests/test_agent_*.py

test-agent-integration:
	RUN_AGENT_LLM_INTEGRATION=true AGENT_ENABLED=true ADME_MOCK_MODE=true $(PYTEST) -q tests/integration -s

smoke-mock:
	ADME_MOCK_MODE=true $(PYTHON) -c "from app.tools.admet_predictor import predict_one; print(predict_one('CC(=O)OC1=CC=CC=C1C(=O)O'))"

smoke-real:
	env -u ADME_MOCK_MODE $(PYTHON) scripts/smoke_test_admet.py

smoke-agent-llm:
	$(PYTHON) scripts/smoke_test_agent_llm.py

backend:
	$(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	./scripts/dev.sh

batch-demo:
	ADME_MOCK_MODE=true $(PYTHON) scripts/batch_demo.py

check:
	$(PYTHON) scripts/dev_check.py
	$(MAKE) test
	@if [ -f frontend/package.json ]; then cd frontend && npm run lint && npm run typecheck && npm run test && npm run build; fi
