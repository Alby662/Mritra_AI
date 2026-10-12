# Mritra AI Pipeline Audit

## Phase 1: Architecture Map & End-to-End Data Flow

### Verified Data Flow
1. **Raw Data Ingestion:** `scripts/prepare_data.py` reads `HI-Small_Trans.csv` and `HI-Small_Patterns.txt`.
2. **Preprocessing & Splitting:** `scripts/prepare_data.py` applies a strictly chronological split (60/20/20 by default) based on `ts`. The split labels are assigned sequentially, guaranteeing no rows sharing a timestamp straddle a split boundary. 
3. **Partitioning:** Transactions are grouped into simulated institutions using `mritra/data/partition.py`.
4. **Feature Engineering:** `scripts/build_features.py` builds graphs and executes feature creation using `views.py`.
   - **C1 (Siloed):** Bank sees only its internal transactions + its own side of cross-bank transactions.
   - **C3 (Protocol):** Simulated cryptographic feature protocol via `EnclaveService`.
   - **C4 (Oracle):** Sees every transaction and every account globally.
5. **Model Training:** `scripts/train_models.py` uses LightGBM. It trains using the training split, tunes threshold and hyperparameters using the validation split (`average_precision_score`), and saves the model. 
6. **Evaluation:** `scripts/run_eval.py` evaluates the models, calculates the $G$ metric (Gap Recovered), PR-AUC, minority-class F1, and bootstrap confidence intervals.

---

## Phase 2: Audit Checklist

- [x] **Data:** Integrity, leakage, duplicates, missing values, preprocessing flow. (VERIFIED: Temporal splitting is leak-proof. `compute_behavioural_features` uses rolling metrics properly without lookahead. GFP aggregates in timestamp batches).
- [x] **Splitting & Validation:** Train/val/test boundaries, entity/group leakage, metric validity. (VERIFIED: Boundaries are tight. But **Validation metrics evaluation procedure is flawed.**)
- [x] **C1-C4 Implementation:** Exact data access checks, feature overlap, comparability. (VERIFIED: `views.py` correctly restricts graph topologies according to C1/C3/C4 definitions. Enclave guarantees are properly simulated.)
- [x] **Model Pipelines:** Target definitions, feature alignment, metric correctness. (VERIFIED: LightGBM grid search handles class weights correctly. Features align.)

---

## Findings

### 1. Critical Methodological Flaw: Target Leakage during Test Evaluation
- **Severity:** CRITICAL
- **Evidence:** In `scripts/run_eval.py` (lines ~183-185), the F1 threshold for the Gap Metric is calculated using `_optimal_threshold(y, prob)` on the *current evaluation split* (e.g. `args.split`).
- **Impact:** If `run_eval.py` is executed with `--split test`, the script mathematically guarantees target leakage by optimizing the classification threshold using the test labels. This artificially inflates the $G$ metric (Gap Recovered) by choosing whichever threshold overfits the test subset the most. This is a direct violation of `PREREGISTRATION.md §5` ("applied unchanged to test").
- **Recommended Fix:** `run_eval.py` must load the threshold trained on the Validation set for evaluating the Test set. Do not dynamically call `_optimal_threshold` on the evaluation dataset.

### 2. Protocol Violation: Ignoring Saved Thresholds for Gap Computation
- **Severity:** HIGH
- **Evidence:** `scripts/train_models.py` accurately calculates the optimal F1 threshold for C3 and C4 on the validation set, storing it in `run_info["threshold"]` (written to `manifest.json`). However, `scripts/run_eval.py` completely ignores this saved threshold for the $G$ metric bootstrap and recalculates it over the cross-bank subset.
- **Impact:** The evaluation ignores the mathematically proven validation threshold and substitutes it with an opportunistic subset threshold, making the comparison unreliable and violating the protocol.
- **Recommended Fix:** The gap metric calculation for C3 and C4 should use their respective `train_run_info["threshold"]` values extracted from `manifest.json`.

### 3. Missing Storage of C1 Cross-Bank Ensemble Threshold
- **Severity:** HIGH
- **Evidence:** C1's cross-bank predictions aggregate probabilities using `max(prob_from, prob_to)`. `train_models.py` trains individual bank models but never computes or saves the threshold for this `max()` aggregate.
- **Impact:** Without a validation-derived threshold stored anywhere for the C1 cross-bank combination, `run_eval.py` is forced to calculate it on the fly, perpetuating the test-set leakage mentioned above.
- **Recommended Fix:** Explicitly calculate the optimal `C1` combined cross-bank threshold on the Validation set (perhaps within a new final step of `train_models.py` or a dedicated validation scoring script) and persist it, so that the test run can load it.

### 4. Global Scope Leakage in roles.py
- **Severity:** LOW
- **Evidence:** `mritra/data/roles.py` computes total laundering inflows globally across all timestamps (`df.groupby... sum()`). 
- **Impact:** If used for feature engineering, it would be catastrophic target leakage. Fortunately, a scan of the repository confirms `assign_roles` is only used inside `tests/test_leakage.py` and never in the data pipeline or feature generation.
- **Recommended Fix:** No urgent fix needed for training, but consider adding a comment inside `roles.py` explicitly forbidding its use in feature calculation.

---

## Overall Pipeline Verdicts

- **Data Integrity & Architecture:** READY (Excellent streaming design, strict timestamp tracking, robust batch processing).
- **Splitting & Partitions:** READY (Temporal split is correctly implemented).
- **C1-C4 Isolation:** READY (Simulated enclave boundary is strictly enforced).
- **Model Training:** READY (LightGBM grid search and feature streaming are memory-safe and mathematically sound).
- **Evaluation Methodology:** **NOT READY** (Target leakage via dynamic thresholding in `run_eval.py` renders test results invalid).

## Training Readiness: NOT READY
**Do not run a final test evaluation.** The current evaluation script will contaminate the results with test-set data leakage via dynamic thresholding. 

The three thresholding bugs in `run_eval.py` and `train_models.py` (Findings 1, 2, and 3) must be resolved first. Once validation thresholds are properly saved and applied unchanged to the test evaluation, the pipeline will be ready for training.
