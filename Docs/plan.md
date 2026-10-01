# Mritra — IBM Z Datathon 2026 Build Plan

> **Status:** Draft v1 · 1 Oct 2026 · Owner: Rehan (team lead)
> **Event:** IBM Z Datathon 2026 · 24-hour sprint · 17–18 Oct 2026 · mandatory LinuxONE setup 16 Oct · registration closes **1 Oct**
> **Track:** "AI Secured: Innovation Without Exposure" (privacy-preserving AI for sensitive data)
> **Working name:** Mritra (check how it reads to Hindi/Marathi speakers — *mṛt* = "dead" — before it goes on slides)

---

## Table of contents

1. [One-line claim](#1-one-line-claim)
2. [Problem statement (v2)](#2-problem-statement-v2)
3. [What we prove in 24 hours](#3-what-we-prove-in-24-hours)
4. [Scope (MoSCoW)](#4-scope-moscow)
5. [Architecture](#5-architecture)
6. [Data plan](#6-data-plan)
7. [Methods](#7-methods)
8. [The boundary protocol](#8-the-boundary-protocol)
9. [Privacy, security and integrity](#9-privacy-security-and-integrity)
10. [Evaluation protocol](#10-evaluation-protocol)
11. [Tech stack](#11-tech-stack)
12. [IBM Z / LinuxONE plan](#12-ibm-z--linuxone-plan)
13. [Repository layout](#13-repository-layout)
14. [Team roles](#14-team-roles)
15. [Timeline](#15-timeline)
16. [Demo script](#16-demo-script)
17. [Deliverables and slide outline](#17-deliverables-and-slide-outline)
18. [Prior art and positioning](#18-prior-art-and-positioning)
19. [Jury Q&A preparation](#19-jury-qa-preparation)
20. [Risks, fallbacks and gates](#20-risks-fallbacks-and-gates)
21. [Open items to verify](#21-open-items-to-verify)
22. [Post-datathon roadmap](#22-post-datathon-roadmap)
23. [References](#23-references)

---

## 1. One-line claim

> **Each bank alone misses the laundering chain; one all-seeing model is illegal; Mritra recovers most of that gap by exchanging encrypted boundary-account information through an IBM LinuxONE enclave — without any bank's raw data leaving it.**

The whole 24 hours exists to measure one number, **G** (gap recovered), honestly.

---

## 2. Problem statement (v2)

**Context.** Cyber-enabled fraud is India's largest money-laundering risk (FATF Mutual Evaluation, 2024). Its proceeds are laundered through networks of rented mule accounts that deliberately span multiple banks and payment formats before exiting as cash or crypto — typically within hours (≈53% of mule-account money leaves within one hour; RUSI, 2025).

**Problem.** Each institution sees only its own slice of a chain, so fan-out, scatter-gather, cycle and layering patterns that cross banks are invisible to single-institution monitoring. Current sharing (e.g. DPIP's salted-hash registry) reveals *who* is known-bad, not *how money flows* across institutions, and hashed low-entropy identifiers can be reversed. When chains are found, responses are coarse — whole-account freezes that High Courts (Delhi 2025, Rajasthan 20 Aug 2026) now restrict to the disputed amount.

**Objective.** Detect cross-institution laundering chains and, for each involved account, estimate its role (mule / innocent recipient / source) and the path and amount of tainted flow — early enough to act before exit — without any institution's raw data, identifiers or reversible derivatives leaving it.

**Approach.** Directed-multigraph features (IBM Graph Feature Preprocessor) + cross-bank boundary-account exchange computed inside an attested IBM LinuxONE Secure Execution enclave (or a clearly labelled stand-in), with a tamper-evident transparency log.

**Scope.** Payment-graph laundering of fraud proceeds across banks and payment formats.
**Out of scope:** restitution processes, on-chain crypto analytics, cash/hawala/trade-based laundering, real bank data.

**Success criteria** (AMLworld, bank-partitioned, temporal split, multiple seeds): gap recovered on cross-bank patterns; lead time before exit; innocent money flagged; data exposed; (stretch) tainted-amount accuracy and membership-inference advantage.

---

## 3. What we prove in 24 hours

Three results, each with numbers:

1. **Gap recovered (G)** on cross-bank laundering — siloed → Mritra → oracle, one bar chart with confidence intervals.
2. **Nothing sensitive left a bank** — exact list of fields that crossed, encrypted to the enclave key; transparency-log entry per query; `test_no_leak.py` passing.
3. **It runs on IBM Z** — enclave service and Snap ML inference on LinuxONE (s390x), with timings.

---

## 4. Scope (MoSCoW)

Cut from the bottom of a column when time runs short. **Never cut a Must.** No Could item starts before Gate 2.

| Priority | Items |
|---|---|
| **Must** | Bank partitioning + H1 cross-bank count · temporal split · C1 siloed baseline · C4 oracle · C3 Mritra boundary exchange · metrics split within-bank vs cross-bank · enclave service on LinuxONE with encryption to its key · transparency log · dashboard showing a demo chain · results chart · slides |
| **Should** | Lead time before exit · innocent money flagged · proxy role labels · double-entry reconciliation with an injected lying bank · Snap ML inference timing on Z accelerator · second partition method (P2) |
| **Could** | C2 federated XGBoost (Flower) · per-account tainted amount (pro-rata tracing) · membership-inference attack · Multi-GNN backbone · 2-hop variant + privacy-utility curve · SHAP / LLM evidence narrative |
| **Won't (slides only)** | Friction ladder · incentive/pricing design · k-of-n governance · CFCFRMS labels · policy-as-code · real bank data · restitution |

---

## 5. Architecture

```
             ┌───────────────────────── LinuxONE (s390x) ─────────────────────────┐
┌────────┐   │  ┌──────────────────────────────────────────┐    ┌──────────────────┐ │
│ Bank 1 │◄──┼─►│ MRITRA ENCLAVE                           │───►│ Transparency log │ │
├────────┤   │  │ 1 Decrypt (key generated inside)         │    │ hash-chained     │ │
│ Bank 2 │◄──┼─►│ 2 Reconcile both reports of transfers    │    │ verify_log.py    │ │
├────────┤   │  │ 3 Build boundary graph                   │    └──────────────────┘ │
│ Bank 3 │◄──┼─►│ 4 Graph features on boundary graph       │    ┌──────────────────┐ │
├────────┤   │  │ 5 Aggregate neighbour summaries          │───►│ Dashboard        │ │
│ Bank 4 │◄──┼─►│ 6 Return own-account features only       │    │ chain/role/amount│ │
├────────┤   │  │ [Secure Execution or labelled stand-in]  │    │ results C1–C4    │ │
│ Bank 5 │◄──┼─►└──────────────────────────────────────────┘    └──────────────────┘ │
└────────┘   └────────────────────────────────────────────────────────────────────────┘
  local features + LightGBM / Snap ML scoring
  IN:  encrypted cross-bank transactions + boundary-account summaries
  OUT: each bank's own accounts' network features (rounded, logged)
  NEVER: internal edges, plaintext identifiers
```

- **Offline track (laptop, RTX 4060):** data prep, feature engineering, training, the four-way experiment, all metrics.
- **Runtime track (LinuxONE):** five bank services + enclave service + log + dashboard, replaying the test period as a stream for the live demo.

---

## 6. Data plan

### 6.1 Source

- **IBM Transactions for Anti-Money Laundering (AMLworld)**, Kaggle: `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`
- Use **HI-Small** for all 24-hour work (fits 16 GB RAM). **LI-Small** only if time remains.
- Files: `HI-Small_Trans.csv`, `HI-Small_Patterns.txt`, `HI-Small_accounts.csv`
- Download: `kaggle datasets download -d ealtman2019/ibm-transactions-for-anti-money-laundering-aml`
- Columns (verify on load): `Timestamp, From Bank, Account, To Bank, Account, Amount Received, Receiving Currency, Amount Paid, Payment Currency, Payment Format, Is Laundering`
- Convert once to Parquet with `category` / `float32` dtypes; share Parquet internally.

### 6.2 Frozen definitions (commit to `configs/experiment.yaml` before any result)

| Term | Definition |
|---|---|
| Account key | `(bank_id, account_id)`; belongs to the institution its bank is assigned to |
| Institutions | K = 5 |
| Partition **P1** (volume-balanced) | Sort bank IDs by transaction count (desc); assign each to the currently lightest institution |
| Partition **P2** (random) | Seeded random bank → institution assignment (seed 42) |
| Cross-bank transaction | Sender institution ≠ receiver institution |
| Cross-bank pattern | Laundering attempt (Patterns file) touching > 1 institution |
| Boundary account (for inst. *i*) | Account at *i* with ≥ 1 transaction to/from another institution, using only data up to current time |
| Temporal split | Sort by Timestamp: first 60% train · next 20% validation · last 20% test (same convention as IBM Multi-GNN) |
| Leakage rule | All graph/behaviour features computed streaming in time order — no feature sees the future |
| Exit transaction | Payment Format = cash or bitcoin (check exact strings on load) |
| Role: mule (proxy) | Account both receiving and sending laundering transactions |
| Role: source (proxy) | Sends laundering, never receives it |
| Role: innocent-looking recipient (proxy) | Receives laundering, sends none onward, laundering < 10% of its inflow |

### 6.3 H1 — run first (week 1)

```python
import pandas as pd, numpy as np

df = pd.read_csv("HI-Small_Trans.csv")
df.columns = ["ts","from_bank","from_acct","to_bank","to_acct",
              "amt_recv","cur_recv","amt_paid","cur_paid","fmt","is_laund"]

K = 5
vol = pd.concat([df.from_bank, df.to_bank]).value_counts()
load, inst_of = np.zeros(K), {}
for bank, n in vol.items():                 # P1: volume-balanced
    k = int(load.argmin()); inst_of[bank] = k; load[k] += n

df["from_inst"] = df.from_bank.map(inst_of)
df["to_inst"]   = df.to_bank.map(inst_of)
df["cross"]     = df.from_inst != df.to_inst

print("cross share, all txns       :", round(df.cross.mean(), 3))
print("cross share, laundering txns:", round(df[df.is_laund == 1].cross.mean(), 3))
print("payment formats             :", df.fmt.value_counts().to_dict())
```

Then parse `HI-Small_Patterns.txt` (blocks between `BEGIN LAUNDERING ATTEMPT - <TYPE>` and `END LAUNDERING ATTEMPT` lines; one transaction per line in the Trans column order — verify on download) and report **share of patterns crossing institutions, per pattern type**.

```python
def parse_patterns(path):
    pats, cur = [], None
    for line in open(path):
        line = line.strip()
        if line.startswith("BEGIN LAUNDERING ATTEMPT"):
            cur = {"type": line.split("-", 1)[-1].strip(), "rows": []}
        elif line.startswith("END LAUNDERING ATTEMPT"):
            pats.append(cur); cur = None
        elif cur is not None and line:
            cur["rows"].append(line.split(","))
    return pats
```

**Gate H1:** if < ~15% of patterns cross institutions → switch partition (region / payment format) or reframe to the vertical split before building anything else.

---

## 7. Methods

**Principle:** all configurations use the **same model family**; they differ **only in which features they can see**. Any gain is information, not a better model.

### 7.1 Features

1. **Graph features — IBM Graph Feature Preprocessor** (`snapml.GraphFeaturePreprocessor`)
   - Input: float numpy array `[edge_id, src_id, dst_id, timestamp, amount, …]`, **sorted by timestamp**.
   - Output: original columns + fan-in/out, degree, scatter-gather, gather-scatter, temporal-cycle, simple-cycle and vertex-statistics features.
   - Config: copy from IBM's AML example in `IBM/snapml-examples`; **do not hand-tune**. Not supported on Windows.
2. **Behavioural features per account** (rolling 1 h / 24 h / 7 d, past only):
   - pass-through ratio = amount out ÷ amount in
   - median dwell time (receive → next send)
   - transaction velocity; new counterparties in last 24 h
   - payment-format switches; currency switches
   - share of flow going to other institutions
   - deviation from the account's own 30-day baseline
   - *Not* account age as a core signal — ~60% of real mule accounts are > 1 year old (RUSI)
3. **Mritra network features** — returned by the enclave (Section 8).

### 7.2 Model

- **LightGBM** binary classifier at transaction level; `scale_pos_weight` for imbalance; threshold chosen on validation to maximise minority-class F1.
- Account score = max of its transaction scores.
- On LinuxONE: same features scored with **Snap ML `BoostingMachine`** (or LightGBM model converted) inside `icr.io/ibmz/ibmz-accelerated-for-snapml` for accelerator timing.
- Seeds: 42, 52, 62.

### 7.3 The four configurations

| # | Name | Features available | Purpose |
|---|---|---|---|
| **C1** | Siloed | Each institution's own view (its accounts' edges, including one hop across its boundary); model trained per institution; a cross-bank txn takes the max of its two banks' scores | Status quo |
| **C2** | Federated *(Could)* | Siloed features; Flower federated XGBoost (bagging) across 5 institutions | Shows FL alone doesn't add missing edges |
| **C3** | **Mritra** | Siloed features + enclave-returned network features | Our method |
| **C4** | Oracle | Full-graph features, one model | Upper bound (illegal in practice) |

### 7.4 Stretch methods

- **2-hop variant:** banks also send a pseudonymised 2-hop internal neighbourhood of each boundary account → plot detection vs data exposed (privacy-utility curve).
- **Tainted amount (pro-rata tracing):** a transfer out of an account carries taint proportional to the account's tainted share of its balance at that moment. Compare per-account tainted amount with laundering ground truth and with a blanket whole-balance freeze. Legal tracing rule = stated assumption.
- **Multi-GNN backbone:** `python main.py --data Small_HI --model gin --emlps --reverse_mp --ego --ports` (IBM/Multi-GNN), embeddings as boundary summaries.
- **Explanations:** SHAP top-5 per flagged transaction rendered as abstracted evidence ("counterparty at another institution: 14 sources in 48 h, 92% forwarded within 3 h"); optional small local LLM narrative that must cite evidence IDs.

---

## 8. The boundary protocol

Each **round** = one simulated hour of transactions.

### 8.1 Bank → Enclave (encrypted to enclave public key)

```python
# mritra/protocol/messages.py (pydantic v2) — plaintext shape BEFORE encryption
class CrossBankTxn(BaseModel):
    edge_id: str
    own_account: str          # raw ID, only readable inside enclave
    direction: Literal["out", "in"]
    counterparty_bank: str
    counterparty_account: str
    ts: int                   # unix seconds
    amount: float
    currency: str
    fmt: str                  # payment format

class BoundarySummary(BaseModel):
    account: str
    features: list[float]     # locally computed GFP + behaviour vector
    feature_schema_version: str

class RoundSubmission(BaseModel):
    bank_id: str
    round_id: int
    txns: list[CrossBankTxn]
    summaries: list[BoundarySummary]

class SealedEnvelope(BaseModel):      # what actually travels
    bank_id: str
    round_id: int
    ciphertext_b64: str               # PyNaCl SealedBox(enclave_pk).encrypt(json)
    payload_sha256: str               # digest of plaintext, for the log
```

**Never sent:** internal (within-bank) edges, non-boundary accounts, labels, raw balances.

### 8.2 Enclave processing

1. **Decrypt** with the private key generated inside the enclave at boot.
2. **Reconcile:** each cross-bank txn must be reported by both banks with matching `(accounts, ts, amount, currency)`; mismatches → reconciliation report.
3. **Build boundary graph:** nodes = boundary accounts (with summary vectors); edges = reconciled cross-bank txns.
4. **Compute network features:** Graph Feature Preprocessor on the boundary graph (cross-bank fan, scatter-gather, cycles) + 1–2-hop aggregation (mean / max / sum) of neighbours' summary vectors + cross-bank in/out amounts.
5. **Return** to each bank only its own accounts' network features, rounded to fixed precision.
6. **Log** the round (Section 9.3).

### 8.3 Enclave → Bank

```python
class NetworkFeatures(BaseModel):
    round_id: int
    account: str
    features: list[float]
    schema_version: str
```

### 8.4 Honest limit

Paths **inside** another bank are summarised, not traversed. The 2-hop variant (Could) quantifies what that costs.

---

## 9. Privacy, security and integrity

### 9.1 Transport and payload

- **mTLS** on every connection (self-signed CA via `cryptography`/`openssl` for the demo).
- **Payload encryption:** X25519 sealed boxes (PyNaCl `SealedBox`) to the enclave's public key; key pair generated inside the enclave at boot; public key published (with attestation record if Secure Execution is available).

### 9.2 Output minimisation

- Only own-account features returned; rounded; per-bank rate limit per round.
- No other bank's identifiers ever returned.

### 9.3 Transparency log

- Append-only SQLite table `tlog(seq, ts, requester, query_type, input_sha256, output_sha256, enclave_code_sha256, prev_hash, entry_hash)`.
- `entry_hash = SHA256(prev_hash || canonical_json(entry_without_hash))`.
- `scripts/verify_log.py` recomputes the chain and reports the first broken link (if any).
- Dashboard shows the latest entries and chain head.

### 9.4 Integrity test (Should)

- `scripts/inject_lying_bank.py`: Bank 5 drops 30% of its cross-bank txns / perturbs 10% of amounts.
- Metric: share of injected mismatches caught by reconciliation.

### 9.5 Tests the judges will poke

| Test | Asserts |
|---|---|
| `test_crypto.py` | Only the enclave key decrypts; tampered ciphertext fails |
| `test_tlog.py` | Any edited log row breaks verification |
| `test_reconcile.py` | Injected mismatches are detected |
| `test_no_leak.py` | No outbound bank message contains a plaintext account ID or any internal edge |

### 9.6 Membership inference (Could)

Train a classifier on what bank A received to predict labels of bank B's accounts; report AUC vs 0.5 (FedGraph-VASP reports 0.95 for unprotected embedding exchange).

---

## 10. Evaluation protocol

- Test period only. Mean ± std over **3 seeds × 2 partitions**. **1,000-sample bootstrap 95% CI** on the C3 − C1 difference. **Never report accuracy.**

| Metric | Definition | Tool |
|---|---|---|
| Minority-class F1 | On laundering txns; subsets: all / cross-bank / within-bank | `sklearn.metrics.f1_score` |
| PR-AUC | Average precision on same subsets | `sklearn.metrics.average_precision_score` |
| **Gap recovered G** | see below — headline, cross-bank subset | computed |
| Lead time before exit | Per pattern with an exit txn: `t_exit − t_first_flag`; median + share flagged before exit | Patterns file |
| Innocent money flagged | Sum of legitimate txn amounts flagged; # accounts flagged with no laundering involvement | computed |
| Coverage | Share of txn volume visible to each configuration's detector | computed |
| Data exposed | Fields and bytes crossing a boundary per round | protocol logs |
| Latency | Enclave round time; per-txn inference on LinuxONE vs laptop | `time.perf_counter` |
| Reconciliation catch rate | Injected mismatches flagged / injected | computed |

**Gap recovered:**

```
G = (F1_C3 − F1_C1) / (F1_C4 − F1_C1)
```

G = 0 → Mritra adds nothing over isolated banks. G = 1 → matches the all-seeing model.

**Pre-registered claim:** "G > 0 with a bootstrap interval excluding 0 on cross-bank laundering, under both partitions." If C2 ≈ C3, report it — it falsifies the thesis and judges respect honesty.

**Reference ranges (for sanity):** IBM reports GNN minority-class F1 ≈ 8% (LI-Medium) to ≈ 39% (HI-Small); Graph Feature Preprocessor + boosting up to +46% F1 over plain boosting.

---

## 11. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Dev OS / hardware | Ubuntu 24.04, RTX 4060, 16 GB RAM | GFP unsupported on Windows |
| Python | 3.11 | Pin all versions day one |
| Env | `uv`; separate conda env for Multi-GNN (`env.yml`) | Isolate torch versions |
| Data | `pandas` 2.x, `polars`, `pyarrow`, `numpy` | Parquet + categorical dtypes |
| Graph features | `snapml` (GraphFeaturePreprocessor), `networkx` (sanity checks) | IBM's AML feature engine |
| Models | `lightgbm`, `xgboost`, `scikit-learn`, `shap` | Same family across C1–C4 |
| GNN *(Could)* | `torch`, `torch_geometric` via IBM/Multi-GNN | CUDA on 4060 |
| Federated *(Could)* | `flwr` (Flower) XGBoost bagging example | C2 |
| Services | `fastapi`, `uvicorn`, `pydantic` v2, `httpx` | 5 banks + enclave |
| Crypto | `PyNaCl`, `cryptography`, `hashlib` | Sealed boxes, mTLS, SHA-256 |
| Storage | Parquet, SQLite | Log + results |
| Containers | Podman/Docker + compose | Build s390x images **on** LinuxONE |
| IBM Z | LinuxONE VM; `icr.io/ibmz/ibmz-accelerated-for-snapml` | AI accelerator on z16+ |
| Confidential compute | Secure Execution / Hyper Protect if granted; else labelled stand-in | Never claim attestation you lack |
| Dashboard | `streamlit`, `plotly`, `pyvis` | Chain graph + results |
| Quality | `pytest`, `ruff` | Tests in 9.5 |
| Data access | Kaggle CLI + API token | |
| Collaboration | Private GitHub repo, Projects board, shared results sheet | |
| Presentation | Slides (PDF export), OBS backup video | |

**`requirements.txt` (pin exact versions after first install):**

```
pandas
polars
pyarrow
numpy
scikit-learn
lightgbm
xgboost
snapml
shap
networkx
fastapi
uvicorn[standard]
pydantic>=2
httpx
pynacl
cryptography
streamlit
plotly
pyvis
pyyaml
pytest
ruff
# optional
flwr
```

---

## 12. IBM Z / LinuxONE plan

### 12.1 What runs where

| Component | Laptop (x86 + GPU) | LinuxONE (s390x) |
|---|---|---|
| Feature engineering, training, C1–C4 experiments | ✅ | ❌ |
| Bank services ×5 | dev | ✅ demo |
| Enclave service + transparency log | dev | ✅ demo |
| Snap ML inference timing | baseline | ✅ accelerator container |
| Dashboard | ✅ | optional |

### 12.2 Setup checklist (16 Oct, or earlier on LinuxONE Community Cloud)

- [ ] VM: OS, vCPUs, RAM, disk, sudo, outbound internet (pip, `icr.io`), **z16 or later?**
- [ ] Install Podman/Docker; `podman pull icr.io/ibmz/ibmz-accelerated-for-snapml`; 10-line Snap ML scoring test
- [ ] Verify s390x installs: `fastapi uvicorn pynacl cryptography pandas lightgbm`; if wheels missing → build from source or use the IBM container's Python
- [ ] Ask organisers: Secure Execution / Hyper Protect access for teams?
- [ ] Open service ports or SSH tunnel
- [ ] Record exact commands in `deploy/linuxone.md`

### 12.3 Enclave — two honest paths

1. **Real:** package the enclave service as a Secure Execution / Hyper Protect workload; generate keys inside; publish attestation record + code measurement in the transparency log.
2. **Fallback:** isolated container on LinuxONE, same API/crypto/log. Label on every slide and in the UI: **"Enclave boundary simulated — production target: IBM Secure Execution."**

---

## 13. Repository layout

```text
mritra/
├─ README.md               # claim, results table, reproduce steps, what is simulated
├─ Makefile                # make data | h1 | features | train | eval | demo | test
├─ configs/
│  ├─ experiment.yaml      # K, seeds, partitions, split, thresholds (frozen)
│  └─ gfp.yaml             # Graph Feature Preprocessor settings (from IBM example)
├─ data/                   # raw CSV (gitignored) → parquet/
├─ mritra/
│  ├─ data/        load.py, partition.py, split.py, patterns.py, roles.py
│  ├─ features/    graph_gfp.py, behaviour.py, network.py
│  ├─ models/      train.py, score.py, fed_xgb.py (Could)
│  ├─ protocol/    messages.py, crypto.py, reconcile.py, tlog.py
│  ├─ services/    bank_service.py, enclave_service.py
│  ├─ eval/        metrics.py, lead_time.py, exposure.py, bootstrap.py, mi_attack.py (Could)
│  └─ trace/       tainted_amount.py (Could)
├─ dashboard/app.py        # Streamlit demo
├─ deploy/
│  ├─ compose.yaml         # 5 banks + enclave + dashboard
│  ├─ Containerfile.bank
│  ├─ Containerfile.enclave
│  └─ linuxone.md
├─ scripts/     h1_cross_bank.py, verify_log.py, inject_lying_bank.py, replay_stream.py
├─ results/     runs/*.json, figures/*.png, results.csv
└─ tests/       test_crypto.py, test_tlog.py, test_reconcile.py, test_no_leak.py
```

**Make targets:** `data` (download + parquet) → `h1` → `features` → `train` (C1, C3, C4 [, C2]) → `eval` (metrics + figures) → `demo` (compose up) → `test`.

---

## 14. Team roles

| Role | Owns | Hands off to |
|---|---|---|
| **A — Lead / integration (Rehan)** | Scope, definitions, boundary protocol, service wiring, cut decisions at gates | Everyone |
| **B — Data** | Loading, P1/P2, temporal split, Patterns parsing, roles, H1 | C |
| **C — Features & models** | GFP, behavioural + network features, LightGBM C1/C3/C4, Flower C2 (Could) | D |
| **D — Evaluation & privacy** | Metrics, G, lead time, exposure, bootstrap, reconciliation injection, MI attack (Could), figures | E |
| **E — Platform & story** | LinuxONE, containers, Snap ML timing, dashboard, slides, backup video, rehearsal | Judges |

Rules: one owner per file; PRs reviewed by Rehan; results only from `make eval` (no hand-copied numbers).

---

## 15. Timeline

> Read the official rules first. If pre-written code is not allowed, do the pre-event items as research/notes only and write code during the 24 hours.

### 15.1 Pre-event (1–16 Oct)

| Dates | Work | Exit check |
|---|---|---|
| **1 Oct** | **Register (deadline)**; read rules: prior code, external datasets, IP | Registered; rules known |
| 2–4 Oct | Download data; Parquet; **H1**; environments; LinuxONE Community Cloud account | H1 gate passed or partition changed |
| 5–8 Oct | C1 and C4 baselines (GFP + LightGBM) | **C4 clearly beats C1 on cross-bank** — else rethink |
| 9–12 Oct | Protocol, enclave service, crypto, log, tests; first C3 run | G computed end to end |
| 13–15 Oct | Dashboard skeleton, demo chain chosen, slide draft, full dry run | 5-minute run-through exists |
| **16 Oct** | Mandatory LinuxONE setup; s390x installs; Snap ML container; ask about Secure Execution | Services start on Z |

### 15.2 The 24 hours

| Hours | A (lead) | B (data) | C (models) | D (eval) | E (platform/story) |
|---|---|---|---|---|---|
| 0–1 | Kick-off; freeze definitions | Confirm data | Confirm configs | Metric stubs | VM access |
| 1–5 | Protocol + services | Partitions, split, roles | Features, C1, C4 | Metrics, bootstrap | Containers on LinuxONE |
| **5** | **Gate 1 — C1 and C4 numbers exist** | | | | |
| 5–10 | Wire C3 end to end | P2 partition | C3 training | G, subsets | Enclave + log on Z |
| **10** | **Gate 2 — G computed. If G ≤ 0: pivot story to privacy-utility curve + honest negative** | | | | |
| 10–14 | Reconciliation injection | Exit / lead-time data | Snap ML export | Lead time, exposure | Snap ML timing on Z |
| 14–16 | Sleep rotation — 2 people off for 2 h at a time | | | | |
| 16–19 | Could items only if all gates green | Tainted amount | C2 or Multi-GNN | MI attack | Dashboard demo path |
| **19** | **Gate 3 — feature freeze** | | | | |
| 19–22 | README | Results table | Figures | Final numbers | Slides + backup video |
| 22–24 | Two rehearsals · **submit by hour 23** · 1 h buffer | | | | |

---

## 16. Demo script (5 minutes)

1. **0:00–0:40 — Problem:** ₹547 crore Telangana network (mule web → USDT → Cambodia). 53% of mule money leaves within an hour. India refunds ≈ 2% of what it freezes.
2. **0:40–1:30 — Siloed (live):** five banks score their own accounts; one cross-bank scatter-gather rated "low risk" by every bank.
3. **1:30–2:30 — Mritra (live):** encrypted boundary data to the LinuxONE enclave; the chain lights up with role, path and amount per account.
4. **2:30–3:30 — Results:** G with interval, PR-AUC, lead time before exit, innocent money flagged.
5. **3:30–4:20 — Trust:** transparency log verification; reconciliation catches the injected lying bank; `test_no_leak.py` green.
6. **4:20–5:00 — Where it goes:** complements DPIP/MuleHunter; amount-precise liens (Rajasthan HC, Aug 2026); roadmap.

**Pick the demo chain before the event** (a real cross-bank scatter-gather from the test period that C1 misses and C3 catches). Record a backup video.

---

## 17. Deliverables and slide outline

### 17.1 Slides (10)

1. Title + one-sentence claim
2. The problem in India: ₹19–23k crore/yr reported lost; 53% of mule money gone in 1 h; refunds ≈ 2% of frozen
3. Why single banks fail: one real cross-bank chain, drawn
4. Why obvious fixes fail: pooling (TMNL shut down), hashing (reversible), federated learning (no missing edges)
5. Mritra architecture on LinuxONE (with simulated/real enclave label)
6. The boundary protocol: what crosses, what never does
7. Results: G, PR-AUC, lead time, innocent money flagged — with intervals
8. Trust: transparency log + reconciliation catching a lying bank
9. Prior art and our difference
10. Roadmap: amount-precise liens, DPIP integration, friction ladder

### 17.2 Submission checklist

- [ ] Judge-accessible repo; README with claim, results table, reproduce steps, **what is simulated**
- [ ] `make h1 train eval` reproduces headline numbers
- [ ] Results table: mean ± std + bootstrap CIs, both partitions
- [ ] Architecture + protocol diagrams
- [ ] 3-minute backup demo video
- [ ] Slides as PDF
- [ ] LinuxONE evidence: logs/screenshots of services + Snap ML timing on s390x
- [ ] Transparency log file + `verify_log.py` output
- [ ] Team IP/authorship agreement signed
- [ ] Decision on provisional patent vs publication taken **before** the public demo

---

## 18. Prior art and positioning

| Work | What it does | Our difference |
|---|---|---|
| IBM Multi-GNN (AAAI 2024) & Graph Feature Preprocessor (ICAIF 2024) | Graph detection on AMLworld; +30% / +46% F1 | Our **baselines**, not competitors |
| FedGraph-VASP (arXiv, Jan 2026) | Boundary-embedding exchange with post-quantum crypto (Elliptic) | Enclave hides embeddings *and* matches from banks (their MI AUC 0.95); bank data, not crypto; reconciliation |
| Tian et al., WWW 2025 | Cross-institution subgroup detection, Alipay + ECB real data | Hardware-isolated computation; graph features; runs on Z |
| TNO + ABN AMRO + Rabobank (MPC) | Cross-bank risk propagation; 15%→40% precision; ~3 h / 200k txns | TEE → near-native speed |
| Swift + Google Cloud (2024–25) | Federated fraud model, server in TEE | Weights-only; no graph; fraud not AML |
| BIS Project Hertha / Aurora | Network view finds +12% (+26% novel) illicit accounts | Evidence the cross-institution view pays |
| DPIP (RBI, Sep 2026) / MuleHunter.AI | Salted-hash registry; per-bank models | Complement: multi-hop cross-bank structure; stronger than hashing |
| Consilient, Tookitaki AFC | Federated models; shared typologies | No cross-bank graph structure |
| OCBC mule pipeline (KDD'26 workshop) | Single-bank production: 89% yield vs 61% rules | The single-bank bar we add to |
| "Group-aware deep graph learning" (IEEE TKDE 2023) | Published method with that name | Cite; don't claim the term |

---

## 19. Jury Q&A preparation

| Question | Answer |
|---|---|
| Isn't this just federated learning? | No. FL shares what patterns look like, not missing edges; C2 vs C3 measures exactly that. |
| Why not pool the data in the enclave? | Data residency and least privilege: only boundary summaries leave the bank; TMNL-style pooling was shut down. |
| Can embeddings/features be reversed? | Only the enclave sees them; banks get only their own accounts' features; MI attack result (if run). |
| Is the enclave real? | State plainly which path you used; the protocol, crypto and log are real either way. |
| It's synthetic data. | Yes — so are Swift's sandbox and Project Hertha; real bank data can't be shared, which is the point. |
| How do banks know boundary accounts? | From counterparty bank codes on their own payment messages. |
| What about DPIP / MuleHunter? | Complementary: they match known identities; we detect multi-hop cross-bank structure. |
| Isn't this Palantir / surveillance? | Opposite architecture: no central data; fixed query types; public log; purpose-bound. |
| Why IBM Z? | Secure Execution for the enclave; on-chip AI accelerator for real-time scoring; where banks already run. |
| What if a bank lies? | Double-entry reconciliation: both banks report each transfer; mismatches flagged (demo). |
| What's the business model? | Network intelligence layer feeding existing AML systems; hosted by a neutral utility (slide 10). |

---

## 20. Risks, fallbacks and gates

| Risk | Early signal | Fallback |
|---|---|---|
| Few patterns cross institutions | H1 < ~15% | Partition by region/format; reframe to vertical split |
| Oracle barely beats siloed | C4 ≈ C1 | Present honestly; try LI-Small; lead with privacy/integrity results |
| G ≤ 0 | Gate 2 | Privacy-utility curve + negative result; add 2-hop variant |
| FL alone matches Mritra | C2 ≈ C3 | Report it — falsifies claim |
| No Secure Execution | 16 Oct | Labelled stand-in, same API/crypto |
| s390x wheels fail | 16 Oct | IBM container Python; source builds; only enclave + Snap ML on Z |
| GFP config wrong/slow | Pre-event | IBM example config; subsample windows |
| OOM on 16 GB | Data load | Parquet + categories; polars; time-chunking |
| VM unreachable at demo | Rehearsal | Backup video + laptop containers |
| Scope creep | Could work before Gate 2 | Lead blocks it |
| Fatigue errors | Hour 18+ | Sleep rotation; freeze at 19; checklist submission |

**Go / no-go gates:** H1 (pre-event) · C4 > C1 cross-bank (by 8 Oct) · Gate 1 (h5) · Gate 2 (h10) · Freeze (h19).

---

## 21. Open items to verify

- [ ] Registration completed (deadline 1 Oct)
- [ ] Official rules: pre-written code? external datasets? IP terms?
- [ ] Exact AMLworld column names and Payment Format strings
- [ ] Patterns file format
- [ ] Graph Feature Preprocessor config keys (from IBM example notebook)
- [ ] Datathon VM hardware generation (z16+ for accelerator), sudo, internet
- [ ] Secure Execution / Hyper Protect availability
- [ ] Name check ("Mritra")
- [ ] Team IP/authorship agreement; patent-vs-paper decision

---

## 22. Post-datathon roadmap

1. **Paper (≈ 6 weeks):** H1–H4 (cross-bank share, gap recovered, query mode, privacy attack) + cross-simulator transfer (AMLworld → AMLGentex / SAML-D). Venues: ACM ICAIF, privacy/FL workshops, arXiv first.
2. **System:** reconciliation at scale, friction-ladder simulation, incentive (repeated-game) simulation, tainted-amount tracing vs court rules.
3. **Institutional:** legal opinion on DPDP s.17; conversations with a bank compliance officer / cyber-police lien handler; RBIH / DPIP / co-operative bank federation; RBI HaRBInger.

---

## 23. References

**Data & methods**
- IBM AMLworld dataset (Kaggle): https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- Altman et al., Realistic Synthetic Financial Transactions for AML (NeurIPS 2023): https://arxiv.org/html/2306.16424v1
- Egressy et al., Multi-GNN (AAAI 2024): https://research.ibm.com/publications/provably-powerful-graph-neural-networks-for-directed-multigraphs · code: https://github.com/IBM/Multi-GNN
- Graph Feature Preprocessor (ICAIF 2024): https://arxiv.org/html/2402.08593v2 · docs: https://github.com/IBM/snapml-docs/blob/main/docs/source/graph_preprocessor.rst · examples: https://github.com/IBM/snapml-examples
- IBM Z Accelerated for Snap ML: https://ibm.github.io/ibm-z-oss-hub/containers/ibmz-accelerated-for-snapml.html
- Flower federated XGBoost: https://flower.ai/docs/examples/xgboost-comprehensive.html
- Temporal 60/20/20 split reference: https://github.com/412-Aman/aml-ml-gnn-comparison
- LinuxONE Community Cloud: https://community.ibm.com/zsystems/l1cc/

**Prior art**
- FedGraph-VASP: https://arxiv.org/abs/2601.17935
- Tian et al., Towards Collaborative AML (WWW 2025): https://arxiv.org/abs/2502.19952
- TNO, AML with MPC: https://eprint.iacr.org/2024/065
- US-UK PETs Prize (financial crime): https://pmc.ncbi.nlm.nih.gov/articles/PMC11229673/
- Swift + Google Cloud FL: https://cloud.google.com/blog/products/identity-security/google-cloud-and-swift-pioneer-advanced-ai-and-federated-learning-tech
- BIS Project Hertha: https://www.bis.org/publications/project-hertha-identifying-financial-crime-patterns-real-time-retail-payment-systems
- OCBC mule pipeline: https://arxiv.org/html/2607.17586

**Context & numbers**
- FATF India MER 2024: https://www.fatf-gafi.org/content/dam/fatf-gafi/mer/Executive-Summary-MER%20India%202024.pdf.coredownload.inline.pdf
- FATF, Illicit Financial Flows from Cyber-Enabled Fraud (2023): https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Illicit-financial-flows-cyber-enabled-fraud.pdf.coredownload.inline.pdf
- RUSI, Following the Fraud — money mules: https://static.rusi.org/following-the-fraud-the-role-of-money-mules.pdf
- MHA/I4C figures (₹56,087 cr reported, ₹11,158 cr saved, ₹206 cr refunded): https://www.sarkaritel.com/national-cyber-crime-reporting-portal-saves-11158-crore/
- DPIP Smart Registry: https://www.medianama.com/2026/09/223-dpip-smart-registry-fraud-prevention/
- Rajasthan HC lien directions: https://www.pinkcitypost.com/lien-on-disputed-amount-not-blanket-freeze-rajasthan-high-court-issues-statewide-cyber-fraud-banking-directions/
- ₹547 crore Telangana network: https://www.cryptotimes.io/2026/04/16/india-uncovers-inr-547-cr-crypto-laundering-network-with-cambodia-links/
- IBM Z Datathon 2026: https://www.starhacks.org/ibm-z-datathon-2026
