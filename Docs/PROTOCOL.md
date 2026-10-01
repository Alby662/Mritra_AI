# PROTOCOL.md — Mritra boundary protocol v0.1

> **Status:** Draft v0.1 · 1 Oct 2026 · Owner: Rehan (role A)
> **Implements:** `mritra/protocol/` (messages, crypto, reconcile, tlog) and `mritra/services/` (bank, enclave)
> **Change rule:** any change to a message or invariant bumps the version, updates `tests/test_no_leak.py`, and gets a line in `DECISIONS.md`.

This is the contract between the five bank services and the enclave service. Three people implement against it in parallel, so it is deliberately exact. If code and this document disagree, the document wins until it is changed.

---

## 1. Parties and trust

| Party | Holds | Trusted to |
|---|---|---|
| **Bank service** (×5, `bank_id` ∈ {`B0`…`B4`}) | Its institution's transactions, labels (for training only), local features, its key pair | Keep its data; send only what §4 allows |
| **Enclave service** | Enclave key pair (generated inside at start), the bank public-key registry, the transparency log | Decrypt, compute §6, return §7, log §8 — nothing else |
| **Operator / dashboard** | Read access to log head, log entries, aggregate reconciliation counts | Observe, never see identifiers |

See `THREAT_MODEL.md` for what happens when any party misbehaves.

## 2. Invariants (tested)

| # | Invariant | Test |
|---|---|---|
| I1 | No within-bank transaction ever leaves a bank | `test_no_leak.py` |
| I2 | No label, balance or non-boundary account ever leaves a bank | `test_no_leak.py` |
| I3 | Account identifiers leave a bank only inside ciphertext | `test_no_leak.py`, `test_crypto.py` |
| I4 | A bank only ever receives data about its own accounts | `test_no_leak.py` (response side) |
| I5 | Every submission and every release is logged before it takes effect | `test_tlog.py` |
| I6 | A submission is accepted at most once per (`bank_id`, `round_id`) | `test_crypto.py` (replay) |
| I7 | Only registered banks can submit; only the enclave can read submissions | `test_crypto.py` |

## 3. Keys and encryption

- **Library:** PyNaCl.
- **Enclave key pair:** X25519, generated **inside the enclave at start-up**; the private key is never written to disk or logged. The public key is published via `GET /v1/enclave/info`.
- **Bank key pairs:** X25519, generated at setup (`scripts/gen_bank_keys.py`); public keys listed in `configs/banks.yaml` (the **registry**), loaded by the enclave at start and recorded in the log (`CONFIG_LOADED`). Private keys stay in each bank's gitignored `secrets/` directory.
- **Submission encryption:** `nacl.public.Box(bank_sk, enclave_pk)` — authenticated: the enclave knows which bank sent it, and a bank cannot impersonate another. (The earlier plan said `SealedBox`; `Box` replaces it because sealed boxes are anonymous.)
- **Response encryption:** `Box(enclave_sk, bank_pk)` — only the addressed bank can read its features.
- **Nonces:** 24 random bytes per message (`nacl.utils.random`), sent alongside the ciphertext.
- **Transport:** mTLS on every connection (self-signed demo CA; certs in gitignored `secrets/`). mTLS authenticates the channel; `Box` protects the payload end to end, so a TLS-terminating proxy still sees nothing.
- **Attestation:** `GET /v1/enclave/info` returns `attestation.type` = `"secure-execution"` with evidence **or** `"simulated"`. Banks log which one they saw. The UI shows it.

## 4. What a bank may send (the whole list)

Per round, and nothing else:

1. **Cross-bank transactions** of that round in which one party is the bank's own account.
2. **Boundary summaries** for the bank's boundary accounts that transacted cross-bank in that round.

Everything else — within-bank transactions, non-boundary accounts, labels, balances, model scores — is forbidden (I1, I2).

## 5. Messages

All wire messages are pydantic v2 models in `mritra/protocol/messages.py`.

### 5.1 Canonical encoding

- JSON via `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, UTF-8.
- Floats rounded to 6 decimal places before encoding; integers stay integers.
- Timestamps: integer Unix seconds, UTC.
- `plaintext_sha256` = SHA-256 hex of the canonical plaintext bytes.

### 5.2 Envelope (on the wire)

```python
class Envelope(BaseModel):
    protocol_version: Literal["0.1"]
    sender: str                 # "B0".."B4" or "ENCLAVE"
    recipient: str              # "ENCLAVE" or "B0".."B4"
    round_id: int               # >= 0
    kind: Literal["submission", "features", "reconciliation"]
    nonce_b64: str              # 24 bytes
    ciphertext_b64: str         # Box(...).encrypt(canonical_plaintext, nonce).ciphertext
    plaintext_sha256: str       # for the log; reveals nothing about content
    sent_at: int                # unix seconds
```

### 5.3 Submission plaintext (bank → enclave)

```python
class CrossBankTxn(BaseModel):
    edge_ref: str               # shared payment reference (simulates UTR); dataset row id
    ts: int
    sender_bank: str            # dataset bank id
    sender_account: str
    receiver_bank: str
    receiver_account: str
    amount_paid: float
    currency_paid: str
    amount_received: float
    currency_received: str
    payment_format: str
    side: Literal["sender", "receiver"]   # which party this bank is

class BoundarySummary(BaseModel):
    bank_account: str           # the bank's own account id
    features: list[float]       # local features, order fixed by schema
    schema_version: Literal["bs-v1"]

class RoundSubmission(BaseModel):
    bank_id: str
    round_id: int
    window_start: int           # inclusive
    window_end: int             # exclusive
    txns: list[CrossBankTxn]
    summaries: list[BoundarySummary]
```

**Summary schema `bs-v1`:** the ordered list of local feature names in `configs/protocol.yaml` (a fixed subset of the bank's Graph Feature Preprocessor and behavioural features, computed at `window_end`). Adding or reordering a feature is a schema bump.

### 5.4 Features plaintext (enclave → bank)

```python
class AccountNetworkFeatures(BaseModel):
    bank_account: str           # always one of the recipient bank's own accounts
    features: list[float]
    schema_version: Literal["nf-v1"]

class FeaturesResponse(BaseModel):
    round_id: int
    bank_id: str
    accounts: list[AccountNetworkFeatures]
    banks_included: list[str]   # which banks' submissions were in this round
```

### 5.5 Reconciliation plaintext (enclave → each involved bank)

```python
class Mismatch(BaseModel):
    edge_ref: str
    kind: Literal["missing_counterpart", "field_mismatch"]
    fields: list[str]           # e.g. ["amount_paid"]; empty for missing_counterpart

class ReconciliationReport(BaseModel):
    round_id: int
    bank_id: str
    mismatches: list[Mismatch]  # only transactions this bank reported or should have
```

The **operator** sees only aggregate counts per bank pair (`GET /v1/rounds/{r}/reconciliation/summary`), never `edge_ref` or accounts.

## 6. Enclave computation (per round)

1. **Collect** submissions until all registered banks have submitted or the round deadline passes (demo default: 30 s wall-clock). Log each receipt (`SUBMISSION_RECEIVED`).
2. **Decrypt and validate** each envelope: correct recipient, registered sender, not a replay (I6), schema valid, `window_*` matches `round_id`. Reject otherwise (§9).
3. **Reconcile** cross-bank transactions: match records by `edge_ref`. A transaction is `matched` if both sides reported it with identical `ts`, accounts, banks, amounts, currencies and format; `field_mismatch` if both reported but fields differ; `missing_counterpart` if only one side reported it (and the other side's bank submitted this round). Only matched transactions enter the boundary graph by default (configurable: include one-sided records flagged as unverified).
4. **Update the boundary graph** (persistent across rounds, inside the enclave): nodes = boundary accounts with their latest summary vector; edges = matched cross-bank transactions.
5. **Compute network features `nf-v1`** for each boundary account that appeared this round, from graph state at `window_end`:
   - cross-bank counts and amounts in/out over 24 h (USD), distinct counterparty institutions in/out, cross-bank pass-through ratio;
   - Graph Feature Preprocessor features on the boundary graph (fan-in/out, scatter-gather, gather-scatter, cycles), settings in `configs/gfp_boundary.yaml`;
   - 1-hop neighbour aggregation: mean and max of each `bs-v1` dimension over cross-bank neighbours;
   - 2-hop: max of the dimensions listed in `configs/protocol.yaml` over 2-hop cross-bank neighbours.
   Feature order is fixed in `configs/protocol.yaml`.
6. **Minimise outputs:** round real values to 4 decimal places; include only the recipient bank's own boundary accounts that appeared this round.
7. **Log** `ROUND_COMPUTED`, then per bank `FEATURES_RELEASED` (with `plaintext_sha256` of each response), then publish responses.

## 7. HTTP API

### Enclave service

| Method | Path | Caller | Returns |
|---|---|---|---|
| GET | `/v1/enclave/info` | anyone | `{protocol_version, enclave_pk_b64, code_sha256, attestation: {type, evidence}}` |
| POST | `/v1/rounds/{round_id}/submissions` | bank | `202 {receipt_entry_hash}` |
| GET | `/v1/rounds/{round_id}/features/{bank_id}` | that bank | `Envelope(kind="features")`; `425` if not ready |
| GET | `/v1/rounds/{round_id}/reconciliation/{bank_id}` | that bank | `Envelope(kind="reconciliation")` |
| GET | `/v1/rounds/{round_id}/reconciliation/summary` | operator | counts per bank pair |
| GET | `/v1/log/head` | anyone | `{seq, entry_hash}` |
| GET | `/v1/log/entries?from_seq=N` | anyone | list of log entries |
| GET | `/v1/health` | anyone | status |

Caller identity for bank-only endpoints is checked by mTLS client certificate **and** the response is encrypted to that bank's key.

### Bank service

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/control/rounds/{round_id}/run` | Demo driver: build, encrypt, submit round; fetch features; score |
| GET | `/v1/cases?limit=N` | Ranked flagged accounts/transactions for the dashboard (own data only) |
| GET | `/v1/exposure/{round_id}` | Fields, counts and bytes sent in that round |
| GET | `/v1/health` | Status, observed attestation type |

## 8. Transparency log

- **Storage:** SQLite table `tlog` in the enclave's data volume; append-only by code path (no update/delete functions exist).
- **Entry:**

```python
class LogEntry(BaseModel):
    seq: int
    ts: int
    type: Literal["ENCLAVE_STARTED", "CONFIG_LOADED", "SUBMISSION_RECEIVED",
                  "SUBMISSION_REJECTED", "ROUND_COMPUTED", "FEATURES_RELEASED",
                  "RECONCILIATION_REPORT"]
    actor: str                  # "ENCLAVE" or bank_id
    round_id: int | None
    input_sha256: str | None
    output_sha256: str | None
    detail: dict                # counts only, never identifiers
    code_sha256: str            # enclave code measurement
    prev_hash: str              # "0"*64 for seq 0
    entry_hash: str             # sha256(prev_hash + canonical_json(entry without entry_hash))
```

- `ENCLAVE_STARTED.detail` records attestation type and enclave public-key fingerprint.
- `scripts/verify_log.py` recomputes every `entry_hash` from seq 0 and exits non-zero at the first mismatch, printing its `seq`.

## 9. Errors

| Code | When |
|---|---|
| 400 | Schema invalid, wrong recipient, window/round mismatch |
| 401 | Unknown sender, decryption/authentication failure, mTLS identity ≠ `bank_id` |
| 409 | Duplicate submission for (`bank_id`, `round_id`) |
| 410 | Round closed (deadline passed) |
| 425 | Features not ready yet |

Every rejection is logged as `SUBMISSION_REJECTED` with the reason code and no payload content.

## 10. Rounds

- **Round length:** one simulated hour of transaction time (`configs/protocol.yaml`).
- `round_id = floor((window_start − t0) / 3600)`, `t0` = first test-period timestamp for the demo, first train timestamp for offline runs.
- Offline experiments call the same `enclave` computation functions directly (no HTTP) so results and demo share one code path.
- **Missing bank:** the round is computed with the banks that submitted; `banks_included` records who; missing banks are logged.

## 11. Open points (v0.2 candidates)

- Differential-privacy noise on released features (currently rounding only)
- 2-hop internal-neighbourhood variant (sends pseudonymised internal structure; needs its own exposure accounting)
- Real Secure Execution attestation evidence format
