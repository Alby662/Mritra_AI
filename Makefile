.PHONY: setup data h1 features train eval demo test lint format verify-log inject dashboard

RUN := uv run

setup:
	uv sync

data:
	$(RUN) python scripts/download_data.py
	$(RUN) python scripts/prepare_data.py

h1:
	$(RUN) python scripts/h1_cross_bank.py

features:
	@echo "Feature engineering — run after data + h1 gate passes"
	@echo "TODO: wire feature pipeline script"

train:
	@echo "Training C1, C3, C4 — run after features"
	@echo "TODO: wire training pipeline script"

eval:
	@echo "Evaluation — run after train"
	@echo "TODO: wire evaluation pipeline script"

demo:
	$(RUN) python scripts/replay_stream.py --max-rounds 10

inject:
	$(RUN) python scripts/inject_lying_bank.py

verify-log:
	$(RUN) python scripts/verify_log.py

dashboard:
	$(RUN) streamlit run dashboard/app.py

test:
	$(RUN) pytest -q

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format:
	$(RUN) ruff check --fix .
	$(RUN) ruff format .
