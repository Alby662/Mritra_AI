# Frontend Integration Guide (Mritra AI)

This guide documents the API endpoints, mTLS security setup, and demo data structures for connecting the React frontend to the Mritra backend services.

---

## 1. Architecture Overview

```
┌─────────────────────────┐          HTTP          ┌─────────────────────────┐
│   React Frontend (UI)   │ ─────────────────────► │ Vite / Node Dev Proxy   │
│  (Browser: localhost)   │                        │  (mTLS Client Agent)    │
└─────────────────────────┘                        └───────────┬─────────────┘
                                                               │
                                         HTTPS + mTLS (B1.crt) │
                                                               ▼
                                                   ┌─────────────────────────┐
                                                   │ FastAPI Services        │
                                                   │ • Bank Service (:8000)  │
                                                   │ • Enclave Service(:8443)│
                                                   └─────────────────────────┘
```

Because browsers cannot dynamically supply client certificates via standard `fetch()` or `axios`, your local frontend development server (Vite, Next.js, or Express) must act as an **mTLS Reverse Proxy**.

---

## 2. mTLS Configuration

The services enforce mutual TLS (`--ssl-cert-reqs 2`). You must present a valid client certificate signed by `secrets/ca.crt`.

### Certificate Files (in `secrets/`):
- **CA Certificate:** `secrets/ca.crt`
- **Bank Client Certificate:** `secrets/B1.crt` (or `B0.crt` through `B4.crt`)
- **Bank Client Private Key:** `secrets/B1.key` (or `B0.key` through `B4.key`)

### A. Vite Configuration (`vite.config.ts`)
Add an `https.Agent` with client certificates to your `server.proxy`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';
import https from 'https';

// Load mTLS certificates from repo secrets directory
const secretsDir = path.resolve(__dirname, '../secrets');
const httpsAgent = new https.Agent({
  ca: fs.readFileSync(path.join(secretsDir, 'ca.crt')),
  cert: fs.readFileSync(path.join(secretsDir, 'B1.crt')),
  key: fs.readFileSync(path.join(secretsDir, 'B1.key')),
  rejectUnauthorized: false, // Allows self-signed CA in local development
});

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api/bank': {
        target: 'https://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/bank/, ''),
        agent: httpsAgent,
        secure: false,
      },
      '/api/enclave': {
        target: 'https://localhost:8443',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/enclave/, ''),
        agent: httpsAgent,
        secure: false,
      },
    },
  },
});
```

### B. Node.js Express / Proxy Alternative (`proxy.js`)
```javascript
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const https = require('https');
const fs = require('fs');

const app = express();
const agent = new https.Agent({
  ca: fs.readFileSync('./secrets/ca.crt'),
  cert: fs.readFileSync('./secrets/B1.crt'),
  key: fs.readFileSync('./secrets/B1.key'),
  rejectUnauthorized: false,
});

app.use('/api/bank', createProxyMiddleware({
  target: 'https://localhost:8000',
  pathRewrite: { '^/api/bank': '' },
  agent,
  changeOrigin: true,
}));

app.use('/api/enclave', createProxyMiddleware({
  target: 'https://localhost:8443',
  pathRewrite: { '^/api/enclave': '' },
  agent,
  changeOrigin: true,
}));

app.listen(3001, () => console.log('mTLS Proxy running on port 3001'));
```

---

## 3. Bank Service API Endpoints

The Bank Service represents a single financial institution (e.g. Bank 1).

### `GET /v1/health`
Returns service operational health.
```json
{
  "status": "ok",
  "bank_id": "B1"
}
```

### `GET /v1/cases?limit=10`
Returns the highest risk accounts flagged for AML review by this bank.
```json
{
  "bank_id": "B1",
  "cases": [
    {
      "account": "B1_acct_0",
      "score": 0.99,
      "flagged": true
    },
    {
      "account": "B1_acct_1",
      "score": 0.98,
      "flagged": true
    }
  ]
}
```

### `GET /v1/exposure/{round_id}`
Returns the telemetry on data boundary exposure for a specific hourly round. Demonstrates to the user that raw internal transactions never leave the bank.
```json
{
  "round_id": 0,
  "bank_id": "B1",
  "bytes_sent": 1024,
  "fields_exposed": [
    "amount",
    "ts",
    "currency",
    "fmt",
    "own_account",
    "counterparty_bank",
    "counterparty_account"
  ]
}
```

---

## 4. Enclave Service API Endpoints

The Enclave Service coordinates zero-trust boundary reconciliation, cryptographic attestation, and the immutable transparency log.

### `GET /v1/enclave/info`
Returns public keys and attestation status.
```json
{
  "public_key": "4f7a...",
  "attestation": {
    "type": "simulated"
  }
}
```
> **UI Banner Requirement:** When `attestation.type === "simulated"`, display a subtle badge: `"Enclave boundary simulated"`.

### `GET /v1/log/head`
Returns the latest entry in the cryptographic transparency ledger.
```json
{
  "seq": 142,
  "entry_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### `GET /v1/log/entries?from_seq=0`
Returns the tamper-evident hash chain ledger entries.
```json
[
  {
    "seq": 0,
    "ts": 1728500000,
    "type": "ENCLAVE_STARTED",
    "actor": "ENCLAVE",
    "round_id": null,
    "input_sha256": null,
    "output_sha256": null,
    "code_sha256": "3a8f...",
    "detail": {
      "attestation": "simulated",
      "banks": 5
    },
    "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "entry_hash": "a1b2c3..."
  },
  {
    "seq": 1,
    "ts": 1728503600,
    "type": "ROUND_COMPUTED",
    "actor": "ENCLAVE",
    "round_id": 0,
    "input_sha256": "b4c5...",
    "output_sha256": "c6d7...",
    "code_sha256": "3a8f...",
    "detail": {
      "banks": 5,
      "matched_edges_added": 412,
      "unmatched_refs": 0,
      "mismatched_refs": 0,
      "skipped_unmatched_txn_reports": 0
    },
    "prev_hash": "a1b2c3...",
    "entry_hash": "f8e9..."
  }
]
```

### `GET /v1/rounds/{round_id}/reconciliation/summary`
Returns double-entry counterparty mismatch counts (used to prove detection of lying/adversarial participants).
```json
{
  "round_id": 42,
  "summary": {
    "0-4": {
      "matched": 120,
      "mismatched": 14
    }
  },
  "total_mismatches": 14,
  "total_unmatched": 3,
  "total_issues": 17
}
```

---

## 5. Live Demo: The "Hero Chain" (`results/demo_hero_chain.json`)

To showcase the value of Mritra in the visual interactive graph:
- A multi-bank **scatter-gather** ring is pre-computed and stored in `results/demo_hero_chain.json`.
- The source account scatters funds through multiple intermediary mule accounts across different banks, which then funnel into a central sink account.

### Schema of `results/demo_hero_chain.json`:
```json
{
  "pattern_id": 2,
  "pattern_type": "SCATTER-GATHER",
  "num_transactions": 32,
  "avg_c1_score": 0.1245,
  "avg_c3_score": 0.9412,
  "max_c3_score": 0.9850,
  "detection_gap": 0.8167,
  "transactions": [
    {
      "row_id": 165,
      "ts": 1662019020,
      "from_bank": 213952,
      "from_account": "808338D40",
      "to_bank": 25534,
      "to_account": "8095B6AF0",
      "from_institution": 0,
      "to_institution": 1,
      "amount": 20649.41,
      "format": "ACH",
      "c1_siloed_prob": 0.1102,
      "c3_enclave_prob": 0.9520,
      "c1_missed": true,
      "c3_caught": true
    }
  ]
}
```

### UI Presentation Best Practice:
1. **Siloed View (C1):** Render edges in muted grey/green; show prediction `< 0.40` ("Legitimate / Unflagged"). Each bank only sees its single transfer and assumes normal activity.
2. **Mritra Enclave View (C3):** Switch edges to pulsating red; show prediction `> 0.90` ("Flagged - Cross-Bank Laundering Ring"). Animate the fan-out from the source account and convergence into the destination account.
