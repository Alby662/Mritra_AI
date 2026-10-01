# THREAT_MODEL.md — Mritra (datathon version)

> **Status:** Draft v0.1 · 1 Oct 2026 · Owner: role D (evaluation & privacy), reviewed by Rehan
> **Scope:** the datathon system in `PROTOCOL.md` v0.1 — five bank services, one enclave service, transparency log, dashboard. Synthetic data only.

This document states what Mritra protects, against whom, how, and — just as importantly — what it does **not** protect. Every "not protected" item is a deliberate, stated limit, not an oversight.

---

## 1. Assets

| ID | Asset | Why it matters |
|---|---|---|
| A1 | Each bank's internal transactions | Customer confidentiality; competitive data; legal duty |
| A2 | Account identifiers | Personal data; link to real people |
| A3 | Labels / suspicion status of accounts | Tipping-off risk; reputational harm to innocents |
| A4 | Boundary summaries and network features | Derived from A1/A2; could leak membership or behaviour |
| A5 | Enclave private key | Decrypts every submission |
| A6 | Transparency log integrity | The basis of "verify, don't trust" |
| A7 | Correctness of cross-bank graph | Poisoned data produces wrong flags on innocent customers |

## 2. Trust boundaries

1. **Bank ↔ network:** everything leaving a bank service is untrusted territory unless encrypted to the enclave.
2. **Enclave boundary:** only code inside the enclave sees decrypted submissions. In the datathon this is either IBM Secure Execution (hardware-enforced) or a **simulated** boundary (an isolated container — process isolation only).
3. **Operator/dashboard:** sees aggregate counts and log entries only.

## 3. Adversaries

| ID | Adversary | Capability | Goal |
|---|---|---|---|
| T1 | **Curious bank** | Honest-but-curious; follows protocol; analyses everything it receives | Learn about other banks' customers (A2–A4) |
| T2 | **Lying bank** | Omits or alters its cross-bank reports; submits fake summaries | Hide its customers' activity; poison others' results (A7) |
| T3 | **Network attacker** | Observes, replays, injects traffic between services | Read or forge submissions (A1–A4) |
| T4 | **Curious/compromised operator** | Controls the host running the enclave, reads logs, can restart services | Read decrypted data (A1–A5); rewrite history (A6) |
| T5 | **Launderer** | Controls mule accounts; observes outcomes (accounts frozen or not) | Evade detection; probe thresholds |
| T6 | **Malicious insider at a bank** | Accesses the bank service's inputs/outputs | Exfiltrate network features; tip off customers (A3, A4) |

## 4. Threats and mitigations

| Threat | Against | Mitigation in datathon version | Status |
|---|---|---|---|
| Bank reads other banks' raw data | T1 | Banks never receive other banks' submissions; responses contain only own accounts (I4) | Mitigated |
| Bank infers other banks' customers from returned features | T1 | Only own-account features; rounding; one fetch per round; MI attack measured (optional) | **Partially** — rounding is not formal privacy; DP is v0.2 |
| Bank omits or alters cross-bank reports | T2 | Double-entry reconciliation (both parties report each `edge_ref`); mismatch reports; per-bank mismatch counts visible to operator | Mitigated for cross-bank edges |
| Bank sends fake boundary summaries | T2 | Not detectable in v0.1 (summaries have no counterpart) | **Not mitigated** — see §5 |
| Eavesdropping, tampering, replay | T3 | mTLS + authenticated `Box` encryption; nonces; one submission per (bank, round) | Mitigated |
| Impersonating a bank | T3 | Registry of bank public keys; mTLS client certs must match `bank_id` | Mitigated |
| Operator reads decrypted data | T4 | **Real path:** Secure Execution isolates enclave memory from the host. **Simulated path:** not protected | Mitigated only on the real path |
| Operator swaps enclave code | T4 | Code measurement (`code_sha256`) in `ENCLAVE_STARTED`; attestation evidence on the real path | Mitigated on real path; detectable in log on simulated path |
| Operator edits or deletes log history | T4 | Hash chain; `verify_log.py`; banks record log heads they received | Detectable (not preventable) |
| Launderer probes the threshold | T5 | Out of datathon scope (randomised thresholds are v2) | **Not mitigated** |
| Launderer routes via rails not in the data | T5 | Out of scope; stated limit | **Not mitigated** |
| Insider exfiltrates features / tips off | T6 | Responses contain features, not labels; bank-side access control out of scope | **Not mitigated** (bank's responsibility) |

## 5. Explicitly not protected (residual risk)

1. **Hardware side channels** against the enclave (timing, cache). Reduced by the TEE, not eliminated.
2. **Simulated enclave:** if Secure Execution is unavailable, the enclave boundary is process isolation only; a host operator could read memory. This is labelled everywhere.
3. **Fake boundary summaries** from a lying bank: no counterpart to reconcile against in v0.1.
4. **Collusion** between the host operator and the hardware vendor.
5. **Inference from rounded features** by a determined curious bank over many rounds — measured, not bounded, in v0.1.
6. **Money outside the payment graph** (cash, hawala, trade-based laundering).
7. **Label and data realism:** all data is synthetic; proxy role labels are approximations.

## 6. Security properties we claim (and only these)

- No within-bank transaction, label, balance or non-boundary account leaves a bank (tested).
- No account identifier leaves a bank outside authenticated encryption to the enclave (tested).
- A bank receives only its own accounts' features (tested).
- Every submission and release is logged in a hash chain whose tampering is detectable (tested).
- Omitted or altered cross-bank reports are detected by reconciliation (measured catch rate).
- **On the real Secure Execution path only:** the host operator cannot read decrypted submissions.

## 7. Verification

| Property | How we check it |
|---|---|
| No leakage (I1–I4) | `tests/test_no_leak.py` over generated rounds |
| Crypto and replay (I3, I6, I7) | `tests/test_crypto.py` |
| Log integrity (A6) | `tests/test_tlog.py`, `scripts/verify_log.py` |
| Reconciliation (T2) | `tests/test_reconcile.py`, `scripts/inject_lying_bank.py` catch rate |
| Membership inference (T1) | `mritra/eval/mi_attack.py` AUC (optional) |

## 8. Roadmap items driven by this model

- Differential privacy on released features (formal bound for T1)
- Randomised thresholds against probing (T5)
- Cross-checking summaries against counterparties' views (T2)
- k-of-n governed enclave upgrades (T4)
- Multi-vendor or split computation to reduce single-TEE reliance
