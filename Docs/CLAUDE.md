# CLAUDE.md — instructions for coding agents working on Mritra

Read this file fully before writing or changing code. If an instruction here conflicts with a request, stop and ask the human (Rehan) instead of guessing.

## 1. What this project is

Mritra is a privacy-preserving, cross-bank money-mule detection system built for the **IBM Z Datathon 2026** (17–18 Oct). Five simulated banks each keep their own transaction data. Each round, a bank sends **encrypted** cross-bank transactions and **summaries of its boundary accounts** to an **enclave service** on IBM LinuxONE. The enclave reconciles reports, computes cross-bank network features, and returns to each bank **only its own accounts' features**. Every computation is recorded in a hash-chained transparency log.

The project exists to measure one number honestly: **G**, the share of the detection gap between isolated banks (C1) and an all-seeing model (C4) that Mritra (C3) recovers on cross-bank laundering.

Key documents (read the relevant one before touching its area):

| File | Read before working on |
|---|---|
| `plan.md` | Anything — the overall build plan |
| `PREREGISTRATION.md` | Data, splits, features, training, evaluation |
| `PROTOCOL.md` | `mritra/protocol/`, `mritra/services/` |
| `THREAT_MODEL.md` | Crypto, logging, anything that crosses a service boundary |
| `DATA.md` | Loading, partitioning, labels |
| `DECISIONS.md` | Before re-opening a settled choice |

## 2. Hard rules (never break these)

These are the invariants the whole project rests on. Violating one invalidates results or the privacy claim.

1. **No internal edges leave a bank.** A bank service may send only (a) its cross-bank transactions and (b) summary vectors of its boundary accounts, as defined in `PROTOCOL.md`. Never send within-bank transactions, non-boundary accounts, labels (`is_laund`), or balances.
2. **No plaintext identifiers leave a bank.** Account IDs cross the boundary only inside the encrypted envelope. Never send hashed-only IDs as a privacy measure.
3. **A bank never receives another bank's identifiers or features.** The enclave returns only the requesting bank's own accounts.
4. **No future data in features.** Every feature for a transaction at time *t* uses only transactions with timestamp ≤ *t* (strictly past for labels). Graph features are computed streaming in timestamp order.
5. **Temporal split only.** 60/20/20 by timestamp as defined in `PREREGISTRATION.md`. Never shuffle-split transactions.
6. **Never report accuracy.** Report minority-class F1 and PR-AUC only, on the subsets defined in `PREREGISTRATION.md`.
7. **Frozen config is frozen.** Do not edit `configs/experiment.yaml` or the definitions in `PREREGISTRATION.md`. If a change seems necessary, stop and ask; if approved, record it in the Deviations section of `PREREGISTRATION.md` and in `DECISIONS.md`.
8. **Same model family across C1–C4.** Configurations differ only in the features they can see. Do not tune one configuration more than another.
9. **No hand-typed numbers.** Every number in `README.md`, `RESULTS.md`, the dashboard or slides comes from files written by `make eval`.
10. **Label simulations honestly.** If the enclave runs without hardware attestation, the UI and any generated text must say "Enclave boundary simulated — production target: IBM Secure Execution."
11. **Secrets never enter git.** Kaggle token, private keys, certificates live outside the repo or in gitignored paths.

## 3. Commands

```bash
make setup      # create venv with uv, install pinned requirements
make data       # download AMLworld HI-Small via Kaggle CLI, convert to parquet
make h1         # cross-bank pattern analysis -> results/h1.json
make features   # local graph + behavioural features per institution
make train      # C1, C3, C4 (and C2 if enabled) for all seeds and partitions
make eval       # metrics, G, bootstrap CIs, figures -> results/, RESULTS.md
make demo       # docker/podman compose up: 5 banks + enclave + dashboard
make test       # pytest (must pass before every commit)
make lint       # ruff check + ruff format --check
```

Run `make test lint` before every commit. If a make target doesn't exist yet, create it rather than documenting a manual command.

## 4. Repository layout

```text
configs/                experiment.yaml (frozen), gfp.yaml
data/                   raw/ (gitignored), parquet/ (gitignored)
mritra/data/            load.py, partition.py, split.py, patterns.py, roles.py
mritra/features/        graph_gfp.py, behaviour.py, network.py
mritra/models/          train.py, score.py, fed_xgb.py
mritra/protocol/        messages.py, crypto.py, reconcile.py, tlog.py
mritra/services/        bank_service.py, enclave_service.py
mritra/eval/            metrics.py, lead_time.py, exposure.py, bootstrap.py, mi_attack.py
mritra/trace/           tainted_amount.py
dashboard/app.py        Streamlit
deploy/                 compose.yaml, Containerfile.*, linuxone.md
scripts/                h1_cross_bank.py, verify_log.py, inject_lying_bank.py, replay_stream.py
results/                runs/*.json, figures/, results.csv (generated)
tests/                  test_crypto.py, test_tlog.py, test_reconcile.py, test_no_leak.py
```

Put code in the module that owns it. Don't create new top-level folders without asking.

## 5. Code conventions

- **Python 3.11**, type hints on all public functions, `from __future__ import annotations`.
- **Formatting/linting:** `ruff format`, `ruff check`. Line length 100.
- **Data:** `pandas` 2.x or `polars`; store intermediate data as Parquet; use `category` dtypes for categoricals to stay within 16 GB RAM. Amounts are `float64`, not `float32` — `float32` loses cents above ~$170k, which would break exact-amount double-entry reconciliation (`mritra/data/load.py`, DECISIONS.md 2026-10-01).
- **Messages:** `pydantic` v2 models in `mritra/protocol/messages.py` only. Services import from there; never define ad-hoc dicts for wire messages.
- **Config:** read everything from `configs/*.yaml` via one loader; no magic numbers in code (thresholds, K, seeds, windows).
- **Randomness:** every random operation takes a seed from config.
- **Paths:** use `pathlib` and paths relative to the repo root; no absolute paths.
- **Logging:** standard `logging`, one logger per module; include `round_id` and `bank_id` in service logs. No `print` in library code.
- **Portability:** code must run on x86-64 and **s390x (LinuxONE)**. Avoid dependencies without s390x support in the service path (`mritra/protocol`, `mritra/services`). GPU-only code stays in training, never in services.
- **No notebooks in core code.** Exploration notebooks go in `notebooks/` and are never imported.
- **Functions small and testable**; pure functions for feature and metric computation.

## 6. Testing requirements

- `tests/test_no_leak.py` must assert that every outbound bank message (a) contains no plaintext account ID, (b) contains no within-bank transaction, (c) contains no label field. Add a case whenever the message schema changes.
- `tests/test_crypto.py`: only the enclave key decrypts; tampered ciphertext fails; wrong sender key fails.
- `tests/test_tlog.py`: editing, deleting or reordering any log row fails verification.
- `tests/test_reconcile.py`: injected missing/altered cross-bank transactions are reported.
- Feature code: at least one test proving no future leakage (feature at *t* unchanged when later rows are appended).
- Metrics: test against a hand-computed toy example.

## 7. Workflow for agents

1. Read the relevant docs (table in §1).
2. State the plan in 3–6 bullets before large changes.
3. Make the smallest change that satisfies the requirement; one concern per commit.
4. Run `make test lint`.
5. If you made a design choice not already in the docs, add a one-line dated entry to `DECISIONS.md`.
6. Commit message format: `<area>: <imperative summary>` (e.g. `protocol: add replay protection to round submission`).

## 8. Things not to do

- Don't add features, models or dependencies not in `plan.md` without asking.
- Don't "improve" results by changing partitions, splits, thresholds or seeds after seeing test numbers.
- Don't evaluate on the test period during development; use validation.
- Don't claim hardware attestation, real bank data, or production readiness anywhere.
- Don't silence failing tests or lower thresholds in tests to make them pass.
- Don't commit data files, model binaries over 10 MB, keys or tokens.

## 9. When unsure

Stop and ask with: what you were doing, the specific question, the options you see, and your recommendation.
