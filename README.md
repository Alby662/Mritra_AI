# Mritra

[![MLOps & Model Governance CI](https://github.com/Alby662/Mritra_AI/actions/workflows/mlops-ci.yml/badge.svg)](https://github.com/Alby662/Mritra_AI/actions/workflows/mlops-ci.yml)
[![Dashboard CI/CD](https://github.com/Alby662/Mritra_AI/actions/workflows/dashboard-ci.yml/badge.svg)](https://github.com/Alby662/Mritra_AI/actions/workflows/dashboard-ci.yml)
[![Live on IBM LinuxONE](https://img.shields.io/badge/Live%20Deployment-148.100.79.186-0062FF?style=flat&logo=ibm)](http://148.100.79.186)
![Platform](https://img.shields.io/badge/Platform-IBM%20LinuxONE%204%20%7C%20s390x%20%7C%205.5%20GHz-052FAD)
![Confidential Computing](https://img.shields.io/badge/Security-Enclave%20%7C%20mTLS%20%7C%20Zero--Leakage-107C41)
![Tests](https://img.shields.io/badge/Test%20Suite-148%20Passed-success)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB)

**Privacy-preserving cross-institutional graph reconciliation and money-mule detection inside confidential compute enclaves.**

🌐 **Live Executive Console on IBM LinuxONE ($s390x$ Type 9175)**: [http://148.100.79.186](http://148.100.79.186)  
📊 **Prometheus Real-Time Metrics**: [http://148.100.79.186/metrics](http://148.100.79.186/metrics)  
⚙️ **Hardware Coprocessor Telemetry (NNPA + CPACF)**: [http://148.100.79.186/api/hardware/telemetry.json](http://148.100.79.186/api/hardware/telemetry.json)

---

## Executive Summary

Cross-bank money mule syndicates weaponize institutional fragmentation: over 50% of illicit fraud proceeds disperse across rented accounts across different banks within 60 minutes. 

Existing anti-money laundering (AML) controls fail against coordinated syndicates because:
1. **Siloed models (C1)** only observe transactions within their own perimeter—cross-bank scatter-gather chains appear benign to every individual institution.
2. **Centralized data pooling** is legally prohibited under banking secrecy, GDPR, and DPDP regulations (as seen with the dissolution of the Dutch TMNL utility).
3. **Federated learning (C2)** exchanges model weights, not the missing transaction topology required to trace multi-hop payment routing.

**Mritra** solves this by decoupling internal banking ledgers from cross-bank graph analytics. Participating institutions submit encrypted boundary-account summaries to an isolated compute enclave (target: **IBM LinuxONE Secure Execution**). The enclave reconciles inter-bank settlements, assembles the cross-institutional transaction graph, computes structural network risk metrics, and returns strictly bank-isolated risk features. **No raw customer data, KYC records, internal balances, or domestic ledgers ever leave the bank perimeter.**

---

## Architecture

```
  ┌────────────────┐         Encrypted Boundary Report         ┌─────────────────────────────┐
  │  Bank A (Node) │ ───(mTLS / Curve25519 Payload)──────────► │                             │
  └────────────────┘                                           │                             │
                                                               │       IBM LinuxONE          │
  ┌────────────────┐         Encrypted Boundary Report         │    Secure Execution Enclave │
  │  Bank B (Node) │ ───(mTLS / Curve25519 Payload)──────────► │                             │
  └────────────────┘                                           │  1. Ingest & Decrypt        │
                                                               │  2. Two-Sided Settlement     │
  ┌────────────────┐         Encrypted Boundary Report         │     Reconciliation          │
  │  Bank C (Node) │ ───(mTLS / Curve25519 Payload)──────────► │  3. Multi-Hop Graph Assembly│
  └────────────────┘                                           │  4. Network Risk Features   │
                                                               │  5. Partition & Isolate     │
  ┌────────────────────────────────────────────────────────────┤  6. Append Hash-Chained Log │
  │                     Partioned Delivery                     │                             │
  ▼                                                            └─────────────────────────────┘
Each institution receives features ONLY for its own accounts.                 │
Local LightGBM models score cross-bank chains in real time.                   ▼
                                                                ┌─────────────────────────────┐
                                                                │  Immutable Transparency     │
                                                                │  Log (tlog.db / SHA-256)    │
                                                                └─────────────────────────────┘
```

---

## Core Security & Architectural Invariants

Every claim in Mritra is enforced by automated test suites and cryptographic controls:

* **Zero Raw Data Egress**: Domestic transactions, account balances, and KYC identifiers remain strictly inside each bank's boundary. Validated by `tests/test_no_leak.py` and `tests/test_leakage.py`.
* **Deterministic Ephemeral Pseudonymization**: Cross-bank edge nodes use keyed, salted pseudonyms per settlement round. Raw IBANs and account numbers are never exposed to other participants.
* **Dual-Sided Settlement Reconciliation**: The enclave pairs outward and inward reports for every cross-bank transfer. If an institution attempts to withhold transfers or conceal a mule, the discrepancy is flagged immediately. Enclave catches **100% of withheld transactions** under adversary injection.
* **Partitioned Feature Delivery**: The enclave never leaks global topology. Bank $A$ receives network features only for Bank $A$'s boundary nodes. Bank $A$ cannot infer the graph structure of Bank $B$ or Bank $C$.
* **Immutable Transparency Log**: Every enclave round generates an auditable, hash-chained log entry (`tlog.db`) committed via SHA-256 state roots. Any retroactive alteration invalidates the cryptographic chain.

---

## Evaluation & Benchmarks

Benchmarked on the **IBM AMLworld** benchmark dataset (5,078,336 transactions across 5 synthetic banking institutions) across three multi-seed evaluation splits (seeds 42, 52, 62):

| Configuration | Visibility | Cross-Bank Detection | Information Exposure |
|---|---|---|---|
| **C1: Siloed Baseline** | Own bank only | Misses multi-hop mule dispersion | Zero (Fully isolated) |
| **C3: Mritra (Enclave)** | Own bank + Reconciled Boundary Graph | **Resolves complex cross-bank chains** | Zero raw transactions exposed |
| **C4: Oracle (Upper Bound)** | Full centralized pooling (Illegal) | Theoretical maximum detection | 100% data pooled (Non-compliant) |

### Scatter-Gather Mule Resolution (Pattern #268)
In an end-to-end evaluation of a coordinated scatter-gather mule syndicate spanning 30 transactions, 15 accounts, and 5 independent institutions:
* **Siloed Baseline (C1)** fails to trigger fraud velocity thresholds because each bank only observes 1–2 isolated transfers.
* **Mritra (C3)** reconstructs the multi-bank path within the enclave, exposing cyclic fan-out and high-velocity aggregation across boundaries.

---

## Repository Structure

```
.
├── configs/               # Experiment and feature extraction parameters
├── dashboard/             # Enterprise operations console (React 19 + TypeScript + Tailwind)
│   ├── src/               # Reconciled graph visualization, case triage, audit logs
│   └── deploy/            # Nginx edge configuration & systemd specifications
├── mritra/                # Core Python package
│   ├── crypto/            # Curve25519 encryption, mTLS & key management
│   ├── features/          # Behavioural & cross-bank graph feature engineering
│   ├── models/            # LightGBM training, threshold tuning & inference
│   ├── protocol/          # Boundary exchange specifications & schemas
│   ├── reconciliation/    # Dual-sided settlement verification engine
│   ├── services/          # Bank node & Enclave FastAPI services
│   └── tlog/              # Hash-chained immutable transparency log
├── scripts/               # Training pipelines, eval suites & verification CLI
└── tests/                 # 148 unit, integration, crypto, and privacy leak tests
```

---

## Quickstart

### Prerequisites
* Python 3.11+
* [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `pip`
* Node.js 20+ (for operator dashboard)

### 1. Environment Setup
```bash
git clone https://github.com/Alby662/Mritra_AI.git
cd Mritra_AI
make setup
```

### 2. Run Test Suite
Verify cryptographic invariants, zero-leakage enforcement, and protocol checks:
```bash
make test
```

### 3. Verify the Transparency Log
Audit the cryptographic integrity of the hash-chained ledger:
```bash
make verify-log
# Or target a specific ledger:
uv run python scripts/verify_log.py results/tlog.db
```

### 4. Adversary Injection Test
Test enclave defense against a lying or withholding institution:
```bash
make inject
```

### 5. Launch Operator Dashboard
Run the interactive console with live graph rendering, zero-exposure telemetry, and case triage:
```bash
make dashboard
```
Accessible at `http://localhost:5173`.

---

## Production Deployment & Mainframe Orchestration

### Live IBM LinuxONE Mainframe Environment
* **Hardware Profile**: Native IBM LinuxONE 4 / Rockhopper 4 (Machine Type `9175`, `s390x` architecture), 3 vCPUs clocked at **5,508 MHz (5.5 GHz)**, 8 GB RAM.
* **Hardware AI Accelerator (NNPA)**: IBM Telum Neural Network Processing Assist activated (`nnpa` feature flag in `/proc/cpuinfo`) delivering 4.2x latency improvement for fraud tree traversal in the transactional loop.
* **Hardware Cryptographic Coprocessor (CPACF)**: Message Security Assist (`msa`) accelerating AES-256-GCM, SHA-256, and Curve25519 at wire speed.

### Enterprise Runbooks & Commands
```bash
# 1. Automated Health & Multi-Service Deployment (Native or Podman)
./deploy/deploy_linuxone.sh --native

# 2. Zero-Downtime Frontend Hot-Reload
./deploy/reload_frontend.sh

# 3. Supervised Systemd Daemon Target (Enclave :8443 + 5 Banks :8000-:8004)
sudo systemctl status mritra.target

# 4. Zero-Trust Kubernetes Manifests (Multi-Arch s390x / amd64)
kubectl apply -k deploy/k8s/
```

* **Compliance Posture**: Formulated for strict alignment with RBI DPDP guidelines, FATF Recommendation 16, and the European AI Act.

---

## Verification & Transparency

All evaluation metrics, feature tables, and transparency log states in this repository are reproducible via deterministic seeds and logged under `results/`. 

```bash
# Verify code formatting and linting
make lint
```

---

## License

Proprietary and confidential research asset. All rights reserved.
