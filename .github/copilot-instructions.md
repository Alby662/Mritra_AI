# Copilot instructions for Mritra

This repository is not a generic Python app; it is a privacy-preserving, cross-bank money-mule detection pipeline built for the IBM Z Datathon 2026. The key objective is to measure G, the portion of the cross-bank detection gap recovered by Mritra without leaking raw data across bank boundaries.

## Read before changing behavior

The project relies on fixed protocol/data/measurement rules. Before touching data, protocol, crypto, features, or evaluation code, read the relevant docs:

- `Docs/README.md`
- `Docs/CLAUDE.md`
- `Docs/plan.md`
- `Docs/PREREGISTRATION.md`
- `Docs/PROTOCOL.md`
- `Docs/THREAT_MODEL.md`
- `Docs/DATA.md`
- `Docs/DECISIONS.md`

When the repo says a config or protocol is frozen, treat it as frozen unless the change is explicitly approved and recorded.

## Build, test, and lint commands

Use the repository make targets from the repo root:

```bash
make setup      # create or refresh the uv environment and install pinned deps
make data       # download AMLworld data and prepare parquet inputs
make h1         # run the cross-bank pattern analysis
make features   # compute local graph + behavioural features
make train      # train C1/C3/C4 configs and any enabled C2 runs
make eval       # generate metrics and results under results/
make demo       # launch the simulated 5-bank + enclave dashboard flow
make test       # pytest -q
make lint       # ruff check . && ruff format --check .
make test lint  # required pre-commit verification in this repo
```

Single-test examples:

```bash
uv run pytest tests/test_protocol.py -q
uv run pytest tests/test_no_leak.py -q
uv run pytest tests/test_reconcile.py -q
```

Targeted lint on a file or directory:

```bash
uv run ruff check mritra/protocol
uv run ruff check tests/test_crypto.py
```

## High-level architecture

The repo is organized in a few connected stages:

1. Data and partitioning
   - `scripts/download_data.py` and `scripts/prepare_data.py` load the synthetic AMLworld dataset into parquet-backed inputs.
   - `mritra/data/` handles loading, partitioning, splits, roles, and pattern definitions.
   - `configs/experiment.yaml` and `configs/gfp.yaml` are the frozen runtime config for feature, split, and protocol settings.

2. Bank-local feature generation
   - `mritra/features/` contains the feature pipeline: graph-aware features, behavioural features, and network features.
   - Each bank keeps its own dataset and computes local features without exposing sensitive internal edges or labels.

3. Enclave boundary exchange
   - `mritra/services/bank_service.py` prepares encrypted cross-bank transaction reports and boundary-account summaries for the enclave.
   - `mritra/services/enclave_service.py` decrypts submissions, reconciles double-entry transactions, updates the persistent boundary graph, computes network features, and returns only the requesting bank's own account features.
   - `mritra/protocol/` contains the message schema, crypto, reconciliation, and transparency log logic.

4. Model training and evaluation
   - `mritra/models/` trains and scores the model family across C1, C3, and C4 configurations.
   - `mritra/eval/` contains metrics, lead-time analysis, exposure, bootstrap confidence intervals, and sensitivity tests.
   - `results/` stores run artifacts and generated figures; `Docs/RESULTS.md` is produced by `make eval` rather than edited manually.

5. UI and simulation tooling
   - `dashboard/app.py` is a Streamlit app for replaying the protocol and inspecting outputs.
   - `scripts/` includes data replay, verification, config auditing, and injected-bank attack scenarios.

## Project-specific conventions and invariants

These are not generic coding standards; they are the repo's real invariants:

- Never send within-bank transactions, non-boundary accounts, labels, or plaintext account identifiers outside a bank. `Docs/PROTOCOL.md` and `Docs/THREAT_MODEL.md` define the allowed boundary exchange.
- The enclave computes features only from data up to the round's end (`protocol.round_window_sec`, currently `3600s` in `configs/experiment.yaml`); no future data may appear in features.
- Use a strict temporal split (60/20/20 by timestamp), never a random shuffle split.
- Evaluate with minority-class F1 and PR-AUC only; do not report classification accuracy.
- Model family and feature policy must stay consistent across C1-C4; the configurations differ by available features, not by model tuning.
- Use Pydantic v2 models in `mritra/protocol/messages.py` for wire formats; do not invent ad-hoc dict payloads for service boundaries.
- Use `from __future__ import annotations`, type hints on public functions, `pathlib` for repo-relative paths, and `logging` instead of `print` in library code.
- Keep amounts as `float64`, not `float32`; use category dtypes for categoricals when feasible to stay within memory constraints.
- Keep code portable across x86-64 and LinuxONE/s390x; avoid service-path dependencies that lack s390x support.
- Do not create new top-level folders without approval; keep code in the module that owns it.
- If you change a frozen config or protocol definition, record a dated deviation in `Docs/DECISIONS.md` and the relevant source doc, if the repo allows it.

## Testing expectations

The repo includes explicit leakage and protocol tests. When changing message schemas or service behavior, ensure the relevant checks still pass:

- `tests/test_no_leak.py` verifies outbound bank messages do not contain within-bank transaction data, plaintext IDs, or labels.
- `tests/test_crypto.py` checks correct encryption/decryption and rejection of tampering.
- `tests/test_tlog.py` ensures the transparency log can detect edits, deletions, or reordering.
- `tests/test_reconcile.py` checks mismatched or missing cross-bank transactions are reported.
- `tests/test_protocol.py` enforces the round-window causality and cross-configuration rules.

## When working in this repo

Prefer the smallest change that matches the protocol and the existing design. If there is uncertainty, read the exact protocol doc for the area and ask a targeted question before changing frozen assumptions.

This project intentionally treats privacy and reproducibility as first-class requirements, not optional polish.
