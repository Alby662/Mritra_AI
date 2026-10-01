.PHONY: setup data h1 test lint format

RUN := uv run

setup:
	uv sync

data:
	$(RUN) python scripts/download_data.py
	$(RUN) python scripts/prepare_data.py

h1:
	$(RUN) python scripts/h1_cross_bank.py

test:
	$(RUN) pytest -q

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format:
	$(RUN) ruff check --fix .
	$(RUN) ruff format .
