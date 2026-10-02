.PHONY: setup data h1 features train eval config-audit test lint format

RUN := uv run
RUN_ID_FILE := results/runs/.last_run_id
# Override with: make train RUN_ID=20261002T120000Z
RUN_ID = $(shell cat $(RUN_ID_FILE) 2>/dev/null)

setup:
	uv sync

data:
	$(RUN) python scripts/download_data.py
	$(RUN) python scripts/prepare_data.py

h1:
	$(RUN) python scripts/h1_cross_bank.py

features:
	$(RUN) python scripts/build_features.py

train:
	$(RUN) python scripts/train_models.py --run-id $(RUN_ID)

eval:
	$(RUN) python scripts/run_eval.py --run-id $(RUN_ID)

config-audit:
	$(RUN) python scripts/config_audit.py

test:
	$(RUN) pytest -q

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format:
	$(RUN) ruff check --fix .
	$(RUN) ruff format .
