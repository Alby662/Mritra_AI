# Mritra — PRD (Datathon)

Oct 1, 2026 · @Rehan

Mritra lets banks detect money-mule chains that cross institutions without sharing their data: each bank sends encrypted boundary-account summaries to an IBM LinuxONE enclave and receives back only network features for its own accounts. This PRD defines the datathon release (IBM Z Datathon 2026, 17–18 Oct, track "AI Secured: Innovation Without Exposure"): what it must do, for whom, and how we know it works. Implementation detail lives in plan.md and the Datathon Build Plan.

## Overview

**Problem.** Cyber-enabled fraud is India's largest money-laundering risk (FATF, 2024). Proceeds move through rented mule accounts spread across banks and payment formats, and about half leaves a mule account within an hour. Each bank sees one slice of the chain, so patterns that cross banks look normal to every single bank. Existing sharing (DPIP's salted-hash registry) matches known identities but not how money flows, and pooling data has failed legally (the Dutch TMNL utility wound down in 2024).

**Product.** A network-intelligence layer that sits beside a bank's existing AML system:

- each bank computes its own features and keeps its data;
- it sends only encrypted cross-bank transactions and boundary-account summaries to an enclave on IBM LinuxONE;
- the enclave reconciles, computes cross-bank network features, and returns each bank only its own accounts' features;
- every computation is recorded in a hash-chained transparency log.

**Why now.** DPIP went live with 8 banks on 1 Sep 2026; High Courts now require liens on the disputed amount only (Rajasthan, 20 Aug 2026); IBM Z provides confidential computing and an on-chip AI accelerator where banks already run.

## Goals, non-goals and success metrics

The release succeeds if it proves one measured claim and demonstrates it live on IBM Z; it does not need to be production software.

**Goals**

1. Show that boundary exchange through an enclave recovers a meaningful share of the detection gap between isolated banks and an all-seeing model, on cross-bank laundering.
2. Show that no raw data, identifiers or internal transactions leave any bank.
3. Run the enclave and scoring on LinuxONE and demo them live.

**Non-goals (datathon)**

- Production deployment, real bank data, or regulator integration
- The friction ladder, incentive/pricing mechanisms, k-of-n governance, restitution workflows
- Beating production systems such as Google AML AI or OCBC's model
- Crypto on-chain analytics, cash, hawala or trade-based laundering

**Success metrics**

| Metric | Target | Priority |
| --- | --- | --- |
| Gap recovered G on cross-bank laundering (test period) | G > 0, bootstrap 95% CI excluding 0, both partitions | Must |
| PR-AUC and minority F1, split cross-bank vs within-bank | Reported for C1, C3, C4 with mean ± std | Must |
| Plaintext identifiers or internal edges leaving a bank | 0 (enforced by test) | Must |
| Transparency log verification | 100% of entries verify; any tampering detected | Must |
| Services running on LinuxONE (s390x) | Enclave + 5 banks + log | Must |
| Median lead time before exit transaction | Reported; C3 ≥ C1 | Should |
| Innocent money flagged | Reported; C3 ≤ C1 at matched recall | Should |
| Reconciliation catch rate on injected lying bank | ≥ 90% | Should |
| Snap ML inference latency on LinuxONE | Reported per transaction | Should |
| Membership-inference AUC on released outputs | Close to 0.5 | Could |

## Users and personas

The datathon's real audience is the judges, but the product is designed for the people who would use it in a bank; every screen should make sense to them.

| Persona | Who | Needs | What they must see |
| --- | --- | --- | --- |
| **Compliance analyst** | Investigator at a bank's AML/fraud team | Fewer, better alerts; a reason for each | Case with role, path, amount and evidence, for their bank's accounts only |
| **Head of fraud risk / MLRO** | Accountable for the bank's AML outcomes | Evidence that joining improves detection without legal exposure | Uplift over their own model; exactly what data left the bank |
| **Network operator / regulator** | Neutral host (a DPIP/RBIH-type utility) or supervisor | Trust without seeing data; catch weak or lying members | Transparency log, reconciliation report, per-bank participation |
| **Datathon judge** | IBM Z experts, AI and security reviewers | A clear claim, honest numbers, real use of IBM Z | Results chart with intervals, live run on LinuxONE, what is simulated |

## User stories

Each story has acceptance criteria a tester can check in the demo environment.

| ID | As a… | I want… | So that… | Acceptance criteria | Priority |
| --- | --- | --- | --- | --- | --- |
| US-1 | Compliance analyst | to see cross-bank risk on my own accounts | I catch chains my bank can't see alone | For a chosen test-period chain, C1 scores its accounts below threshold and C3 above; dashboard shows it | Must |
| US-2 | Compliance analyst | each flag to show role, path and evidence | I can act and justify the action | Case view shows role label, own-bank path segment, top evidence statements; no other bank's identifiers | Must (role, evidence: Should) |
| US-3 | Head of fraud risk | to see the uplift over my bank's own model | I can justify joining | Results page shows C1 vs C3 vs C4 per partition with intervals | Must |
| US-4 | Head of fraud risk | to see exactly what left my bank | I can answer legal and audit questions | "Data exposed" panel lists fields and bytes per round; `test_no_leak.py` passes | Must |
| US-5 | Network operator | to verify every computation after the fact | trust doesn't depend on my word | `verify_log.py` validates the chain; editing any row fails verification | Must |
| US-6 | Network operator | to detect a member that under-reports transfers | a lying bank can't poison the network | Injected lying bank: ≥ 90% of mismatches flagged in reconciliation report | Should |
| US-7 | Compliance analyst | to know how much of an account is tainted | liens cover only the disputed amount | Per-account tainted amount shown, compared with the whole balance | Could |
| US-8 | Datathon judge | to see it run on IBM Z | the IBM Z use is real, not decorative | Services visibly running on s390x; Snap ML timing on LinuxONE; enclave path labelled real or simulated | Must (Snap ML timing: Should) |

## Functional requirements

Requirements are grouped by component; the IDs are what tests and commits reference.

| ID | Requirement | Priority |
| --- | --- | --- |
| **Data** |  |  |
| FR-D1 | Load AMLworld HI-Small, convert to Parquet with typed columns | Must |
| FR-D2 | Assign bank IDs to K = 5 institutions by P1 (volume-balanced); P2 (seeded random) as second partition | Must / Should |
| FR-D3 | Temporal 60/20/20 split by timestamp; features computed streaming, past-only | Must |
| FR-D4 | Parse the Patterns file; mark each pattern and transaction as cross-bank or within-bank | Must |
| FR-D5 | Derive proxy role labels (mule, source, innocent-looking recipient) and exit transactions (cash/bitcoin formats) | Should |
| **Features and models** |  |  |
| FR-M1 | Local graph features per institution with IBM's Graph Feature Preprocessor | Must |
| FR-M2 | Behavioural features per account over 1 h / 24 h / 7 d windows | Must |
| FR-M3 | Train LightGBM for C1 (siloed), C3 (Mritra), C4 (oracle) with identical settings; threshold from validation | Must |
| FR-M4 | C2 federated XGBoost via Flower | Could |
| FR-M5 | Export scoring model to run with Snap ML on LinuxONE | Should |
| **Bank service** |  |  |
| FR-B1 | Replay its institution's transactions as a time-ordered stream | Must |
| FR-B2 | Each round, build cross-bank transaction list and boundary-account summaries | Must |
| FR-B3 | Encrypt the round to the enclave's public key and send it | Must |
| FR-B4 | Receive network features; score its accounts; raise cases above threshold | Must |
| **Enclave service** |  |  |
| FR-E1 | Generate its key pair at start; expose the public key (with attestation record if available) | Must |
| FR-E2 | Decrypt submissions; reject malformed or replayed rounds | Must |
| FR-E3 | Reconcile each cross-bank transaction against the counterparty bank's report; produce a mismatch report | Should |
| FR-E4 | Build the boundary graph and compute network features (graph features + 1–2-hop neighbour aggregation) | Must |
| FR-E5 | Return to each bank only its own accounts' features, rounded | Must |
| FR-E6 | Append one log entry per round and per query | Must |
| **Transparency log** |  |  |
| FR-L1 | Append-only hash chain: entry hash = SHA-256(previous hash ‖ canonical entry) | Must |
| FR-L2 | `verify_log.py` recomputes the chain and reports the first broken link | Must |
| **Evaluation** |  |  |
| FR-V1 | Compute F1, PR-AUC per configuration on all / cross-bank / within-bank subsets | Must |
| FR-V2 | Compute G with bootstrap 95% CI over seeds and partitions | Must |
| FR-V3 | Lead time before exit; innocent money flagged; data exposed; coverage | Should |
| FR-V4 | Per-account tainted amount by pro-rata tracing | Could |
| FR-V5 | Membership-inference attack on released outputs | Could |
| **Dashboard** |  |  |
| FR-UI1 | See section: Dashboard and UX requirements | Must |

## Non-functional requirements

Privacy requirements are hard constraints: a feature that violates one is dropped, not shipped.

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-P1 | Privacy | No internal (within-bank) transaction, non-boundary account, label or balance leaves a bank |
| NFR-P2 | Privacy | Identifiers leave a bank only inside ciphertext readable by the enclave key; never hashed-only |
| NFR-P3 | Privacy | A bank never receives another bank's identifiers or features |
| NFR-P4 | Privacy | Released features are rounded and rate-limited per round |
| NFR-S1 | Security | mTLS on every service connection |
| NFR-S2 | Security | Enclave private key generated inside the enclave and never exported |
| NFR-S3 | Security | Replay protection: each submission carries bank ID + round ID; duplicates rejected |
| NFR-S4 | Honesty | If hardware attestation is unavailable, UI and slides say "enclave boundary simulated — production target: IBM Secure Execution" |
| NFR-R1 | Reproducibility | `make data h1 features train eval` regenerates every reported number from the raw CSV |
| NFR-R2 | Reproducibility | All definitions and seeds live in `configs/experiment.yaml`, frozen before results |
| NFR-R3 | Evaluation integrity | Temporal split only; no feature uses future data; accuracy never reported |
| NFR-PF1 | Portability | Bank and enclave services run unchanged on x86 (laptop) and s390x (LinuxONE) in containers |
| NFR-PF2 | Performance | One enclave round (5 banks, one simulated hour) completes in under 60 s on LinuxONE during the demo |
| NFR-PF3 | Performance | Full HI-Small pipeline fits in 16 GB RAM |
| NFR-O1 | Observability | Every service logs round IDs, message sizes and timings; dashboard shows them |
| NFR-Q1 | Quality | `pytest` passes: crypto, log, reconciliation, no-leak |

## Dashboard and UX requirements

One Streamlit app with a bank selector at the top; whichever bank is selected, the screen shows only what that bank would legitimately see, except on the Operator and Results pages.

| Page | Shows | Requirement IDs |
| --- | --- | --- |
| **1. Bank view** | Selected bank's accounts ranked by risk; toggle Siloed vs Mritra; cases above threshold | UI-1 (Must) |
| **2. Case view** | One flagged chain: own-bank path segment drawn as a graph; role label; abstracted evidence from other banks ("counterparty at another institution: 14 sources in 48 h"); tainted amount if available | UI-2 (Must; role, amount: Should/Could) |
| **3. Data exposed** | Per round: fields sent, bytes, number of boundary accounts; confirmation that no internal edges left | UI-3 (Must) |
| **4. Operator** | Transparency log head and recent entries; "Verify chain" button; reconciliation report with mismatches by bank | UI-4 (Must; reconciliation: Should) |
| **5. Results** | Bar chart C1 / C3 / C4 (C2 if built) on cross-bank laundering, with intervals; G; lead time; innocent money flagged; partition switch | UI-5 (Must) |
| **6. Platform** | Where each service runs (x86 or s390x), enclave path (real or simulated), Snap ML latency | UI-6 (Must; latency: Should) |

**UX rules**

- The demo path is Bank view → Case view → Results → Operator, one click each.
- Every number shown comes from `results/` files written by `make eval`; nothing typed by hand.
- A persistent banner states "Synthetic data (IBM AMLworld)" and, if applicable, "Enclave boundary simulated".
- Readable on a projector: large fonts, at most one chart per screen, colour never the only signal.

## Data, assumptions, constraints and dependencies

The release depends on one public dataset and IBM's platform; everything else is open-source Python.

**Data requirements**

- IBM AMLworld HI-Small (Kaggle `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`): transactions, Patterns file, accounts file. LI-Small optional.
- No real or personal data is used; all identifiers are synthetic.

**Assumptions**

- A meaningful share of laundering patterns crosses institutions under our partition (verified by H1 before building).
- The oracle (C4) clearly beats siloed (C1) on cross-bank laundering; otherwise there is no gap to recover.
- Payment format (cash, bitcoin) is a usable proxy for exit.
- Proxy role labels approximate real roles well enough to demonstrate the concept; they are labelled as proxies.

**Constraints**

- 24-hour build window (17–18 Oct); rules on pre-written code and external datasets to be confirmed.
- Team of five; laptop with RTX 4060 and 16 GB RAM; LinuxONE VM without GPU.
- Secure Execution access unknown; simulated enclave must be labelled.

**Dependencies**

| Dependency | Used for | Risk if unavailable |
| --- | --- | --- |
| `snapml` (Graph Feature Preprocessor) | Graph features | Fall back to hand-written fan/degree/cycle features with `networkx` |
| LinuxONE VM (datathon or Community Cloud) | Runtime demo | Backup video + laptop containers |
| `icr.io/ibmz/ibmz-accelerated-for-snapml` | Accelerator timing | Report CPU timing on s390x only |
| Secure Execution / Hyper Protect | Real attestation | Labelled simulated enclave |
| LightGBM, FastAPI, PyNaCl, Streamlit on s390x | Services | Build from source or use IBM container Python |
| Flower (`flwr`) | C2 baseline | Drop C2 (Could) |

## Milestones, release criteria, risks and open questions

The release ships when every Must requirement passes its check; Should and Could items are reported as done or not done, never implied.

**Milestones**

| Date | Milestone | Exit check |
| --- | --- | --- |
| 1 Oct | Registered; rules read | Confirmation received |
| 4 Oct | H1 done | Cross-bank pattern share known; partition fixed |
| 8 Oct | C1 and C4 baselines | C4 > C1 on cross-bank laundering |
| 12 Oct | End-to-end C3 | G computed once |
| 15 Oct | Dry run | 5-minute demo runs start to finish |
| 16 Oct | LinuxONE ready | Services start on s390x |
| 18 Oct, hour 23 | Submission | Release criteria met |

**Release criteria**

- [ ] All Must functional requirements implemented and demonstrated
- [ ] Success metrics G, PR-AUC/F1 subsets, zero-leak and log verification reported
- [ ] `pytest` green; `make` pipeline reproduces the numbers
- [ ] Services demonstrably running on LinuxONE; enclave path labelled correctly
- [ ] README states what is synthetic, simulated and out of scope
- [ ] Backup demo video recorded

**Risks**

| Risk | Mitigation |
| --- | --- |
| Few cross-bank patterns (H1 fails) | Re-partition by region/format before building |
| No gap between C1 and C4 | Present honestly; lead with privacy and integrity results |
| G ≤ 0 | Present privacy-utility curve and negative result |
| Federated baseline matches Mritra | Report it; it falsifies the claim |
| No Secure Execution | Labelled simulated enclave |
| s390x install failures | IBM container Python; only enclave + scoring on Z |
| Scope creep | No Could work before the hour-10 gate |

**Open questions**

- [ ] Do the rules allow code written before 17 Oct and external datasets?
- [ ] Is Secure Execution / Hyper Protect available to teams?
- [ ] Is the datathon VM z16 or later (accelerator)?
- [ ] Exact column names, Payment Format strings and Patterns file format
- [ ] Graph Feature Preprocessor configuration from IBM's example
- [ ] Final product name (check how "Mritra" reads in Hindi/Marathi)
- [ ] Team IP/authorship agreement; provisional patent vs publication before the public demo
