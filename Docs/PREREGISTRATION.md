# PREREGISTRATION.md — Mritra datathon experiments

> **Status:** DRAFT — becomes FROZEN when committed with the tag `prereg-v1`, before any C1/C3/C4 run on the **validation or test** period.
> **Version:** v1 · **Drafted:** 1 Oct 2026 · **Frozen on:** ____ (date + commit hash)
> **Owner:** Rehan · **Machine-readable copy:** `configs/experiment.yaml` (must match this file)

This document fixes, in advance, what we will measure, how, and what result would count as success or failure. Anything changed after freezing goes in **§9 Deviations** with a date and reason. The purpose is to make it impossible — for us or an agent — to tune definitions until the result looks good.

---

## 1. Research question

On bank-partitioned synthetic transaction data, does exchanging encrypted boundary-account information through an enclave (C3, Mritra) recover a meaningful share of the detection gap between isolated banks (C1) and a single model that sees all data (C4), specifically on laundering transactions that cross institutions?

## 2. Hypotheses

| ID | Hypothesis | Type | Test |
|---|---|---|---|
| **H1** | A meaningful share of laundering patterns crosses institutions under partition P1 | Precondition | Share of Patterns-file attempts touching > 1 institution; gate at ≈ 15% |
| **H0-gap** | C4 outperforms C1 on cross-bank laundering | Precondition | F1 and PR-AUC, C4 − C1 on cross-bank subset, validation period |
| **HP (primary)** | G > 0 on cross-bank laundering, with the paired bootstrap 95% CI of (F1_C3 − F1_C1) excluding 0, under both P1 and P2 | Primary | §6.2 |
| HS1 | C3 ≥ C2 (federated training alone does not recover the gap) | Secondary (if C2 built) | Same metrics, C3 vs C2 |
| HS2 | C3 flags laundering patterns earlier than C1 (lead time before exit) | Secondary | §6.3 |
| HS3 | At matched recall, C3 flags no more innocent money than C1 | Secondary | §6.4 |
| HS4 | Double-entry reconciliation catches ≥ 90% of injected mismatches | Secondary | §6.6 |

**Only HP is the headline claim.** Secondary results are reported whatever they show.

## 3. Data

- **Dataset:** IBM AMLworld **HI-Small** (Kaggle `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`): `HI-Small_Trans.csv`, `HI-Small_Patterns.txt`, `HI-Small_accounts.csv`.
- **Optional replication:** LI-Small, same protocol, reported separately and never mixed with HI-Small numbers.
- **Cleaning:** drop exact duplicate rows; nothing else. Record row counts before/after in `DATA.md`.
- **Amounts:** converted to a single reference currency (USD) with the fixed rate table documented in `DATA.md`; the table is built once, before experiments.

## 4. Frozen definitions

| Term | Definition |
|---|---|
| Account key | `(bank_id, account_id)` |
| Institutions | **K = 5** |
| **Partition P1** (primary) | Sort bank IDs by total transaction count (sender + receiver), descending, ties by bank ID ascending; assign each to the institution with the lowest current total count (lowest index on ties) |
| **Partition P2** (robustness) | Uniform random assignment of bank IDs to institutions with `numpy.random.default_rng(42)`, drawing one institution index per bank in ascending bank-ID order (so the result does not depend on load order) |
| Institution of an account | Institution of its bank |
| Cross-bank transaction | Sender institution ≠ receiver institution |
| Within-bank transaction | Sender institution = receiver institution |
| Cross-bank pattern | A laundering attempt in the Patterns file whose transactions touch > 1 institution |
| Boundary account of institution *i* at time *t* | An account at *i* with ≥ 1 cross-bank transaction at time ≤ *t* |
| **Temporal split** | Sort all transactions by timestamp (stable). Train = first 60%, validation = next 20%, test = last 20%, by row count; transactions sharing the boundary timestamp go to the earlier split |
| Leakage rule | Features and scores for a transaction are produced at the end of its round, using only data up to that round's end. Rounds are fixed windows of `protocol.round_window_sec` (3600s). No data from any later round is used. Labels are never features. |
| Exit transaction | `Payment Format` ∈ {cash, bitcoin categories as spelled in the data — recorded in `DATA.md`} |
| Role: mule (proxy) | Account that both receives and sends ≥ 1 laundering transaction |
| Role: source (proxy) | Sends ≥ 1 laundering transaction, receives none |
| Role: innocent-looking recipient (proxy) | Receives ≥ 1 laundering transaction, sends none, and laundering is < 10% of its received amount |

## 5. Configurations and model

All configurations use the **same model and hyperparameter search budget**; they differ only in features.

| Config | Features |
|---|---|
| **C1 Siloed** | For each institution: Graph Feature Preprocessor features and behavioural features computed on that institution's view (all transactions touching its accounts). One model per institution. A cross-bank transaction receives the **max** of its two institutions' scores |
| **C2 Federated** (optional) | C1 features; Flower federated XGBoost (bagging), 5 clients |
| **C3 Mritra** | C1 features + enclave network features per `PROTOCOL.md` |
| **C4 Oracle** | Graph Feature Preprocessor + behavioural features on the full graph; one model |

- **Model:** LightGBM binary classifier at transaction level.
- **Imbalance:** `scale_pos_weight = n_neg / n_pos` on the training set.
- **Hyperparameters:** a fixed small grid (defined in `configs/experiment.yaml`) searched on **validation PR-AUC**, the same grid for every configuration.
- **Threshold:** chosen per configuration, seed and partition to maximise minority-class F1 on **validation**; applied unchanged to test.
- **Graph Feature Preprocessor settings:** copied from IBM's AML example (`configs/gfp.yaml`), identical across configurations.
- **Seeds:** 42, 52, 62 (model training); partition seed for P2 is fixed at 42.

## 6. Analysis plan

### 6.1 Primary metrics (test period only)

For each configuration × seed × partition, on three subsets of test transactions — **all**, **cross-bank**, **within-bank**:
- Minority-class **F1** (`sklearn.metrics.f1_score`, `pos_label=1`)
- **PR-AUC** (`sklearn.metrics.average_precision_score`)

Accuracy and ROC-AUC are not reported as headline metrics.

### 6.2 Gap recovered and inference

```
G = (F1_C3 − F1_C1) / (F1_C4 − F1_C1)     on the cross-bank subset
```

- Computed per seed × partition, reported as mean ± std, and per partition.
- **Paired bootstrap:** 1,000 resamples of test transactions stratified by label; the same resample indices for C1 and C3; 95% percentile CI of F1_C3 − F1_C1 on the cross-bank subset, per partition (pooling seeds by averaging scores).
- **HP is supported** if the CI excludes 0 under both P1 and P2. If F1_C4 − F1_C1 ≤ 0.01, G is reported as "undefined (no gap)" and HP is not tested.

### 6.3 Lead time before exit

For each laundering pattern with ≥ 1 transaction in the test period and ≥ 1 exit transaction:
- `t_exit` = timestamp of its first exit transaction
- `t_flag` = the **end of the round** in which any of its transactions first scores ≥ threshold (round granularity, `protocol.round_window_sec`; matches the leakage rule in §4 — a score is only available once its round has ended)
- flagged-before-exit if `t_flag < t_exit`; lead = `t_exit − t_flag`

Report the share flagged before exit and the median lead (hours) among those, per configuration.

### 6.4 Innocent money flagged

At each configuration's threshold, and additionally at C1's recall level (matched recall):
- sum of USD amounts of legitimate transactions scored ≥ threshold
- number of accounts flagged that have no laundering transaction

### 6.5 Data exposure and coverage

- Per round: fields sent, bytes, number of boundary accounts, per bank (from protocol logs).
- Coverage: share of test transaction volume each configuration's detector can observe.

### 6.6 Reconciliation (HS4)

`scripts/inject_lying_bank.py` modifies institution 4's (0-indexed) submissions: drops 30% of its cross-bank transactions and perturbs amounts of 10% by ±5–20%, seed 42. Catch rate = flagged injected mismatches / injected mismatches.

### 6.7 Optional analyses (report if run, never selectively)

- C2 federated baseline
- 2-hop variant and privacy-utility curve
- Per-account tainted amount (pro-rata tracing) vs laundering ground truth and vs whole-balance freeze
- Membership-inference AUC on released outputs
- LI-Small replication

## 7. Decision rules (kill and pivot criteria)

| Checkpoint | Condition | Action |
|---|---|---|
| H1 | < ~15% of patterns cross institutions under P1 | Stop; re-partition by region or payment format; re-freeze as prereg-v2 before any model run |
| H0-gap (validation) | F1_C4 − F1_C1 on cross-bank ≤ 0.01 | No gap to recover: report honestly; shift emphasis to privacy and integrity results |
| HP (test) | CI includes 0 under either partition | Report as "not supported"; present privacy-utility curve and negative result |
| HS1 | C2 ≥ C3 | Report; it falsifies the claim that boundary exchange is needed |

## 8. What we will report regardless of outcome

All primary metrics for every configuration, seed and partition; G with CIs; every secondary metric that was run; all deviations. No configuration, seed or partition is dropped from the report.

## 9. Deviations

| Date | Change | Reason | Approved by | Affects |
|---|---|---|---|---|
| 2026-10-02 | §4 leakage rule and §6.3 lead-time `t_flag` restated at round granularity ("produced at the end of its round... Rounds are fixed windows of `protocol.round_window_sec`"), replacing the continuous-time "timestamp ≤ t" wording | Snap ML's `GraphFeaturePreprocessor.transform()` inserts its whole input batch before computing features ("...and computes the graph-based features using the updated graph", snapml 1.17.2 docstring) -- there is no insert-free method, so continuous-time "≤ t" causality isn't achievable at dataset scale; round-batched causality is what the implementation (and the real enclave protocol, PROTOCOL.md §10) actually provides. Clarification made before any C1/C3/C4 model results. | Rehan | §4, §6.3; CLAUDE.md rule 4; PROTOCOL.md §10 |
