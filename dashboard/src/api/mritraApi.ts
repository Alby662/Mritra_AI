// Mritra AI — API Client Layer (FRONTEND_INTEGRATION.md)
// Connects the React dashboard to the Enclave Service (:8443) and Bank Service (:8000/:8001)
// via the mTLS reverse proxy (/api/enclave and /api/bank).

export interface EnclaveInfo {
  protocol_version: string;
  enclave_pk_b64: string;
  code_sha256: string;
  attestation: {
    type: 'simulated' | 'ibm_secure_execution' | 'sev_snp';
    evidence?: string;
    hardware_target?: string;
  };
}

export interface LogHead {
  seq: number;
  entry_hash: string;
}

export interface EnclaveLogEntry {
  seq: number;
  ts: number | string;
  type: string;
  actor: string;
  round_id: number | null;
  input_sha256: string | null;
  output_sha256: string | null;
  code_sha256: string;
  detail: any;
  prev_hash: string;
  entry_hash: string;
}

export interface BankHealth {
  status: string;
  bank_id: string;
}

export interface BankCase {
  account: string;
  score: number;
  flagged: boolean;
}

export interface BankCasesResponse {
  bank_id: string;
  cases: BankCase[];
}

export interface BankExposureResponse {
  round_id: number;
  bank_id: string;
  bytes_sent: number;
  fields_exposed: string[];
}

export interface ReconciliationSummary {
  round_id: number;
  summary: Record<string, { matched: number; mismatched: number }>;
  total_mismatches: number;
  total_unmatched: number;
  total_issues: number;
  lying_institution?: number;
  catch_rate?: number;
}

export interface HeroChainTransaction {
  row_id: number;
  ts: number;
  from_bank: number;
  from_account: string;
  to_bank: number;
  to_account: string;
  from_institution: number;
  to_institution: number;
  amount: number;
  format: string;
  c1_siloed_prob: number;
  c3_enclave_prob: number;
  c1_missed: boolean;
  c3_caught: boolean;
}

export interface HeroChainData {
  pattern_id: number;
  pattern_type: string;
  num_transactions: number;
  avg_c1_score: number;
  avg_c3_score: number;
  max_c3_score: number;
  detection_gap: number;
  transactions: HeroChainTransaction[];
}

export interface ResultsSummary {
  success: boolean;
  timestamp: string;
  data_stats: any;
  reconciliation: any;
  h1: any;
  audit: any;
}

// ─── API Methods ─────────────────────────────────────────────────────────────

async function tryFetchJson<T>(paths: string[]): Promise<T | null> {
  for (const path of paths) {
    try {
      const res = await fetch(path, { headers: { Accept: 'application/json' } });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // try next path
    }
  }
  return null;
}

/**
 * GET /v1/enclave/info
 * Returns enclave public key, code SHA-256, and hardware attestation.
 */
export async function getEnclaveInfo(): Promise<EnclaveInfo | null> {
  return tryFetchJson<EnclaveInfo>([
    '/api/enclave/v1/enclave/info',
    '/v1/enclave/info',
  ]);
}

/**
 * GET /v1/log/head
 * Returns the latest entry hash in the tamper-evident transparency ledger.
 */
export async function getLogHead(): Promise<LogHead | null> {
  return tryFetchJson<LogHead>([
    '/api/enclave/v1/log/head',
    '/v1/log/head',
  ]);
}

/**
 * GET /v1/log/entries?from_seq=0
 * Returns the immutable cryptographic hash chain entries.
 */
export async function getLogEntries(fromSeq = 0): Promise<EnclaveLogEntry[]> {
  const data = await tryFetchJson<EnclaveLogEntry[]>([
    `/api/enclave/v1/log/entries?from_seq=${fromSeq}`,
    `/v1/log/entries?from_seq=${fromSeq}`,
  ]);
  return data || [];
}

/**
 * GET /v1/rounds/{round_id}/reconciliation/summary
 * Returns double-entry counterparty mismatch counts.
 */
export async function getReconciliationSummary(roundId = 0): Promise<ReconciliationSummary | null> {
  return tryFetchJson<ReconciliationSummary>([
    `/api/enclave/v1/rounds/${roundId}/reconciliation/summary`,
    `/v1/rounds/${roundId}/reconciliation/summary`,
  ]);
}

/**
 * GET /v1/health
 * Returns Bank service operational health and bank identifier.
 */
export async function getBankHealth(): Promise<BankHealth | null> {
  return tryFetchJson<BankHealth>([
    '/api/bank/v1/health',
    '/v1/health',
  ]);
}

/**
 * GET /v1/cases?limit=10
 * Returns highest risk accounts flagged for AML review by this bank.
 */
export async function getBankCases(limit = 10): Promise<BankCasesResponse | null> {
  return tryFetchJson<BankCasesResponse>([
    `/api/bank/v1/cases?limit=${limit}`,
    `/v1/cases?limit=${limit}`,
  ]);
}

/**
 * GET /v1/exposure/{round_id}
 * Returns telemetry proving raw internal transactions never leave the bank.
 */
export async function getBankExposure(roundId = 0): Promise<BankExposureResponse | null> {
  return tryFetchJson<BankExposureResponse>([
    `/api/bank/v1/exposure/${roundId}`,
    `/v1/exposure/${roundId}`,
  ]);
}

/**
 * GET /api/hero-chain
 * Returns the live multi-bank scatter-gather laundering ring (Pattern #268).
 */
export async function getHeroChain(): Promise<HeroChainData | null> {
  return tryFetchJson<HeroChainData>([
    '/api/hero-chain',
    '/api/hero-chain/268',
  ]);
}

/**
 * GET /api/results/summary
 * Consolidated model evaluation and benchmark statistics.
 */
export async function getResultsSummary(): Promise<ResultsSummary | null> {
  return tryFetchJson<ResultsSummary>([
    '/api/results/summary',
  ]);
}

/**
 * GET /api/runs
 * Catalog of model runs and evaluation metrics.
 */
export async function getRuns(): Promise<any[]> {
  const data = await tryFetchJson<{ runs: any[] }>([
    '/api/runs',
  ]);
  return data?.runs || [];
}
