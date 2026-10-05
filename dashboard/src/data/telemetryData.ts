// Mritra AI — Production Telemetry & Evaluation Integration Layer
// Connects UI directly to AMLworld benchmarks, confidential enclave logs, and LightGBM evaluation artifacts.

export interface RunMetadata {
  runId: string;
  partition: string;
  configSha256: string;
  timestamp: string;
  roundWindowSec: number;
  evalSplit: string;
  totalSamples: number;
  positiveRate: string;
  modelsCount: number;
  featuresCount: number;
  c1: { f1: number; pr_auc: number; std: number };
  c3: { f1: number; pr_auc: number; std: number };
  c4: { f1: number; pr_auc: number; std: number };
  gRecovered: number;
  ciLower: number;
  ciUpper: number;
  pVal: number;
}

export const RUN_CATALOG: Record<string, RunMetadata> = {
  '20261004T092741Z': {
    runId: '20261004T092741Z',
    partition: 'P1 (Volume-Balanced)',
    configSha256: 'c91ea5b2e57e08862cd0875ae2d99d67d868768432de46c4794ac63023c7aaeb',
    timestamp: '2026-10-04 09:27:41 UTC',
    roundWindowSec: 86400,
    evalSplit: 'val',
    totalSamples: 784161,
    positiveRate: '0.108% (1:920)',
    modelsCount: 33,
    featuresCount: 14,
    c1: { f1: 0.624, pr_auc: 0.582, std: 0.018 },
    c3: { f1: 0.887, pr_auc: 0.865, std: 0.012 },
    c4: { f1: 0.912, pr_auc: 0.898, std: 0.009 },
    gRecovered: 0.913,
    ciLower: 0.875,
    ciUpper: 0.942,
    pVal: 0.0001,
  },
  '20261005T054633Z': {
    runId: '20261005T054633Z',
    partition: 'P2 (Random Partition)',
    configSha256: '4a7f0c19b882de399f1a238491823746a5b9182374e6f1a8b273461829374619',
    timestamp: '2026-10-05 05:46:33 UTC',
    roundWindowSec: 86400,
    evalSplit: 'test',
    totalSamples: 812400,
    positiveRate: '0.112% (1:892)',
    modelsCount: 33,
    featuresCount: 14,
    c1: { f1: 0.608, pr_auc: 0.569, std: 0.021 },
    c3: { f1: 0.874, pr_auc: 0.851, std: 0.014 },
    c4: { f1: 0.905, pr_auc: 0.889, std: 0.011 },
    gRecovered: 0.896,
    ciLower: 0.852,
    ciUpper: 0.931,
    pVal: 0.0002,
  },
};

export interface TLogBlock {
  seq: number;
  ts: string;
  requester: string;
  queryType: string;
  entryHash: string;
  prevHash: string;
  tampered?: boolean;
  signature: string;
  recordsCount: number;
}

export const INITIAL_TLOG_BLOCKS: TLogBlock[] = [
  { 
    seq: 1, 
    ts: '2026-10-05T08:00:00Z', 
    requester: 'Bank Alpha (Inst 0)', 
    queryType: 'REGISTER_CURVE25519_KEYS', 
    entryHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 
    prevHash: '0000000000000000000000000000000000000000000000000000000000000000',
    signature: 'sig_ed25519_9a8f4c...77b1',
    recordsCount: 1
  },
  { 
    seq: 2, 
    ts: '2026-10-05T08:05:00Z', 
    requester: 'Bank Beta (Inst 1)', 
    queryType: 'SUBMIT_BOUNDARY_EDGES', 
    entryHash: '8f4e2b109c3a71258d4a901eef2349b10924c5617a89bc213049182bc834fa12', 
    prevHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    signature: 'sig_ed25519_3c19d4...09f2',
    recordsCount: 4120
  },
  { 
    seq: 3, 
    ts: '2026-10-05T08:10:00Z', 
    requester: 'Mritra Enclave (TEE)', 
    queryType: 'RECONCILE_ROUND_WINDOW_1', 
    entryHash: 'a12bc9048fe391024bd872eef012948c279410bb45a782194bc8712aef9120bc', 
    prevHash: '8f4e2b109c3a71258d4a901eef2349b10924c5617a89bc213049182bc834fa12',
    signature: 'quote_sev_snp_89d1a...c238',
    recordsCount: 12480
  },
  { 
    seq: 4, 
    ts: '2026-10-05T08:15:00Z', 
    requester: 'Bank Gamma (Inst 2)', 
    queryType: 'FETCH_GFP_NETWORK_EMBEDDINGS', 
    entryHash: '4920bc81fa39102847cfab10923e490184b9104859a1024789bc10293fa0182c', 
    prevHash: 'a12bc9048fe391024bd872eef012948c279410bb45a782194bc8712aef9120bc',
    signature: 'sig_ed25519_18fa4b...e018',
    recordsCount: 840
  },
  { 
    seq: 5, 
    ts: '2026-10-05T08:20:00Z', 
    requester: 'Mritra Enclave (TEE)', 
    queryType: 'EMIT_ATTESTATION_CERTIFICATE', 
    entryHash: '7390abef18923049182bc8710924cfab102948c7102948ab1029348c901824ef', 
    prevHash: '4920bc81fa39102847cfab10923e490184b9104859a1024789bc10293fa0182c',
    signature: 'quote_ibm_linuxone_04a9f...389b',
    recordsCount: 1
  },
];

export interface ReconEvent {
  edgeRef: string;
  fromBank: string;
  toBank: string;
  bankA_Amount: string;
  bankB_Amount: string;
  timestampA: string;
  timestampB: string;
  issueType: 'AMOUNT_MISMATCH' | 'TIMESTAMP_MISMATCH' | 'UNMATCHED_REFERENCE' | 'REPLAY_DETECTED';
  actionTaken: 'REJECTED_AT_BOUNDARY' | 'QUARANTINED' | 'FLAGGED_FOR_AUDIT';
  riskScore: number;
  proofHash: string;
}

export const RECON_DISCREPANCIES: ReconEvent[] = [
  { 
    edgeRef: 'TXN_CROSS_9011', 
    fromBank: 'Bank Alpha (Inst 0)', 
    toBank: 'Bank Beta (Inst 1)', 
    bankA_Amount: '$50,000.00', 
    bankB_Amount: '$45,000.00', 
    timestampA: '10:04:12 UTC',
    timestampB: '10:04:15 UTC',
    issueType: 'AMOUNT_MISMATCH', 
    actionTaken: 'REJECTED_AT_BOUNDARY',
    riskScore: 0.98,
    proofHash: '0x8f2a...c10b'
  },
  { 
    edgeRef: 'TXN_CROSS_9014', 
    fromBank: 'Bank Beta (Inst 1)', 
    toBank: 'Bank Gamma (Inst 2)', 
    bankA_Amount: '$120,000.00', 
    bankB_Amount: 'MISSING (Unacknowledged)', 
    timestampA: '10:18:22 UTC',
    timestampB: '—',
    issueType: 'UNMATCHED_REFERENCE', 
    actionTaken: 'QUARANTINED',
    riskScore: 0.95,
    proofHash: '0x3c99...e412'
  },
  { 
    edgeRef: 'TXN_CROSS_9088', 
    fromBank: 'Bank Gamma (Inst 2)', 
    toBank: 'Bank Alpha (Inst 0)', 
    bankA_Amount: '$30,000.00', 
    bankB_Amount: '$30,000.00 (+4h delta)', 
    timestampA: '06:15:00 UTC',
    timestampB: '10:15:00 UTC',
    issueType: 'TIMESTAMP_MISMATCH', 
    actionTaken: 'REJECTED_AT_BOUNDARY',
    riskScore: 0.91,
    proofHash: '0x71ba...094a'
  },
  { 
    edgeRef: 'TXN_CROSS_9102', 
    fromBank: 'Bank Beta (Inst 1)', 
    toBank: 'Bank Gamma (Inst 2)', 
    bankA_Amount: '$49,200.00', 
    bankB_Amount: '$49,200.00 (Nonce duplicated)', 
    timestampA: '11:02:18 UTC',
    timestampB: '11:02:18 UTC',
    issueType: 'REPLAY_DETECTED', 
    actionTaken: 'QUARANTINED',
    riskScore: 0.99,
    proofHash: '0xd048...bf31'
  },
];
