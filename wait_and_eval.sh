#!/bin/bash
set -e
uv run python scripts/train_models.py --configs C4 --run-id 20261005T210833Z
uv run python scripts/run_eval.py --run-id 20261005T210833Z
cat results/runs/20261005T210833Z/eval.json
