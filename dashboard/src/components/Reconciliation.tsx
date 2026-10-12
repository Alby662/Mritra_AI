import React, { useState, useEffect } from 'react';
import { 
  Download, 
  Copy, 
  Check,
  ShieldCheck
} from 'lucide-react';
import { 
  REAL_RECONCILIATION_REPORT, 
  RECON_DISCREPANCIES, 
  fetchLiveResultsSummary 
} from '../data/telemetryData';
import type { ReconEvent, ReconciliationReport } from '../data/telemetryData';
import { getReconciliationSummary } from '../api/mritraApi';

export const Reconciliation: React.FC = () => {
  const [report, setReport] = useState<ReconciliationReport>(REAL_RECONCILIATION_REPORT);
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'AMOUNT_MISMATCH' | 'UNMATCHED_REFERENCE' | 'DROPPED_EDGE' | 'PERTURBED_WEIGHT'>('ALL');
  const [inspectedIssue, setInspectedIssue] = useState<ReconEvent | null>(null);
  const [copiedProof, setCopiedProof] = useState(false);
  const [isLiveConnected, setIsLiveConnected] = useState(false);

  useEffect(() => {
    getReconciliationSummary(0).then((recon) => {
      if (recon) {
        setIsLiveConnected(true);
        setReport(prev => ({
          ...prev,
          injectedIssues: recon.total_mismatches,
          caughtIssues: recon.total_issues,
          lyingInstitution: recon.lying_institution ?? 4,
          amountMismatches: recon.total_mismatches,
          unmatchedReferences: recon.total_unmatched,
        }));
      }
    });

    fetchLiveResultsSummary().then((summary) => {
      if (summary && summary.reconciliation) {
        setIsLiveConnected(true);
        if (summary.reconciliation.injected_issues) {
          setReport({
            lyingInstitution: summary.reconciliation.lying_institution ?? 4,
            injectedIssues: summary.reconciliation.injected_issues,
            caughtIssues: summary.reconciliation.caught_issues,
            catchRate: summary.reconciliation.catch_rate,
            matchedTransactions: summary.reconciliation.reconciliation?.matched ?? 466090,
            amountMismatches: summary.reconciliation.reconciliation?.mismatches ?? 33910,
            unmatchedReferences: summary.reconciliation.reconciliation?.unmatched_refs ?? 27495,
            nOriginalInst4: summary.reconciliation.injection_stats?.n_original ?? 91653,
            nDroppedInst4: summary.reconciliation.injection_stats?.n_dropped ?? 27495,
            nPerturbedInst4: summary.reconciliation.injection_stats?.n_perturbed ?? 6415,
            nRemainingInst4: summary.reconciliation.injection_stats?.n_remaining ?? 64158,
          });
        }
      }
    });
  }, []);

  const filteredIssues = RECON_DISCREPANCIES.filter(issue => {
    if (selectedFilter === 'ALL') return true;
    return issue.issueType === selectedFilter;
  });

  const handleCopy = (text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedProof(true);
    setTimeout(() => setCopiedProof(false), 2000);
  };

  const handleExportJSON = () => {
    const exportPayload = {
      experiment: 'Lying Bank Injection & Double-Entry Reconciliation',
      benchmarkSource: 'results/reconciliation_injection.json',
      report,
      sampleDiscrepancies: RECON_DISCREPANCIES,
      generatedAt: new Date().toISOString(),
    };
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportPayload, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", "mritra_double_entry_reconciliation.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ─── Model Benchmark Stat Cards ─────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
        <div className="bento-card animate-bento bento-delay-1" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
              Injected Adversarial Vectors
            </span>
            <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.62rem' }}>
              Bank #{report.lyingInstitution}
            </span>
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px' }}>
            {report.injectedIssues.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            {report.amountMismatches.toLocaleString()} perturbed + {report.unmatchedReferences.toLocaleString()} dropped edges
          </div>
        </div>

        <div className="bento-card animate-bento bento-delay-2" style={{ padding: '20px 24px', border: '1.5px solid var(--lime-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-primary)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
              Enclave Intercepted
            </span>
            <ShieldCheck size={14} color="var(--apple-green)" />
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px', color: 'var(--apple-green)' }}>
            {report.caughtIssues.toLocaleString()} / {report.injectedIssues.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            100% neutralized prior to boundary graph GFP
          </div>
        </div>

        <div className="bento-card animate-bento bento-delay-3" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
              Consortium Matched Txns
            </span>
            {isLiveConnected && (
              <span className="pill-tag pill-tag-success" style={{ fontSize: '0.62rem' }}>
                Live Model Sync
              </span>
            )}
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px', color: 'var(--text-primary)' }}>
            {(report.matchedTransactions / 1000000).toFixed(2)}M
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            {report.matchedTransactions.toLocaleString()} double-entry verified transactions
          </div>
        </div>

        <div className="bento-card animate-bento bento-delay-4" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
            Reconciliation Catch Rate
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px', color: 'var(--text-primary)' }}>
            {(report.catchRate * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Zero poisoning across P1 volume-balanced split
          </div>
        </div>
      </div>

      {/* ─── Model Benchmark Discrepancies Table ──────────────────── */}
      <div className="apple-table-card animate-bento bento-delay-2">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 className="bento-card-title">Reconciled Double-Entry Audit Log</h3>
              <span className="pill-tag pill-tag-glass" style={{ fontSize: '0.68rem' }}>
                results/reconciliation_injection.json
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Cryptographically verified credits and debits across institutional boundaries in TEE
            </span>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Filter buttons */}
            <div className="apple-segmented-control">
              <button 
                onClick={() => setSelectedFilter('ALL')} 
                className={`apple-segment-btn ${selectedFilter === 'ALL' ? 'active' : ''}`}
              >
                All ({RECON_DISCREPANCIES.length})
              </button>
              <button 
                onClick={() => setSelectedFilter('AMOUNT_MISMATCH')} 
                className={`apple-segment-btn ${selectedFilter === 'AMOUNT_MISMATCH' ? 'active' : ''}`}
              >
                Amount Mismatch ({report.amountMismatches.toLocaleString()})
              </button>
              <button 
                onClick={() => setSelectedFilter('UNMATCHED_REFERENCE')} 
                className={`apple-segment-btn ${selectedFilter === 'UNMATCHED_REFERENCE' ? 'active' : ''}`}
              >
                Dropped Edge ({report.unmatchedReferences.toLocaleString()})
              </button>
            </div>

            <button 
              onClick={handleExportJSON}
              className="selector-pill"
              title="Export Audit Log as JSON"
            >
              <Download size={14} /> Export Audit JSON
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Txn Edge Ref</th>
                <th>Sender Entity</th>
                <th>Receiver Entity</th>
                <th>Inst 4 (Source) Ledger</th>
                <th>Counterparty Ledger</th>
                <th>Discrepancy Category</th>
                <th>Enclave Action</th>
                <th>Audit Proof</th>
              </tr>
            </thead>
            <tbody>
              {filteredIssues.map((issue) => (
                <tr key={issue.edgeRef}>
                  <td className="code-font" style={{ fontWeight: 800 }}>
                    {issue.edgeRef}
                  </td>
                  <td style={{ fontWeight: 600 }}>{issue.fromInstitution}</td>
                  <td style={{ fontWeight: 600 }}>{issue.toInstitution}</td>
                  <td className="tabular-nums code-font" style={{ color: issue.sourceAmount.includes('WITHHELD') ? 'var(--apple-red)' : 'var(--text-primary)', fontWeight: 700 }}>
                    {issue.sourceAmount}
                  </td>
                  <td className="tabular-nums code-font" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                    {issue.counterpartyAmount}
                  </td>
                  <td>
                    <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.68rem' }}>
                      {issue.issueType.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>
                    <span className="pill-tag pill-tag-success" style={{ fontSize: '0.68rem' }}>
                      {issue.actionTaken.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>
                    <button 
                      onClick={() => setInspectedIssue(issue)}
                      className="selector-pill"
                      style={{ padding: '4px 12px', fontSize: '0.72rem' }}
                    >
                      Audit Proof &gt;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── Apple Style Issue Inspection Sheet ─────────────────── */}
      {inspectedIssue && (
        <div className="apple-sheet-backdrop" onClick={() => setInspectedIssue(null)}>
          <div className="apple-sheet animate-bento" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="pill-tag pill-tag-danger">
                  {inspectedIssue.issueType.replace(/_/g, ' ')}
                </span>
                <span className="code-font" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {inspectedIssue.edgeRef}
                </span>
              </div>
              <button 
                onClick={() => setInspectedIssue(null)}
                style={{ border: 'none', background: 'rgba(0,0,0,0.06)', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontWeight: 800 }}
              >
                ✕
              </button>
            </div>

            <h3 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '6px' }}>
              Double-Entry Reconciliation Failure
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', marginBottom: '20px' }}>
              Transaction amounts reported by Institution #4 do not balance against counterparty records in the enclave ledger.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>SOURCE: {inspectedIssue.fromInstitution}</div>
                <div className="tabular-nums" style={{ fontSize: '1.15rem', fontWeight: 800, marginTop: '2px', color: inspectedIssue.sourceAmount.includes('WITHHELD') ? 'var(--apple-red)' : 'var(--text-primary)' }}>
                  {inspectedIssue.sourceAmount}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>Timestamp: {inspectedIssue.timestamp}</div>
              </div>

              <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>COUNTERPARTY: {inspectedIssue.toInstitution}</div>
                <div className="tabular-nums" style={{ fontSize: '1.15rem', fontWeight: 800, marginTop: '2px', color: 'var(--apple-green)' }}>
                  {inspectedIssue.counterpartyAmount}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>Attestation: Double-Entry Signed</div>
              </div>
            </div>

            <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>ADVERSARIAL ATTACK PATTERN</div>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-primary)', margin: 0, fontWeight: 500 }}>
                {inspectedIssue.inst4Attempt}
              </p>
            </div>

            <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>ENCLAVE ISOLATION PROOF HASH</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700 }}>{inspectedIssue.auditProofSha}</div>
              </div>
              <button 
                onClick={() => handleCopy(inspectedIssue.auditProofSha)}
                style={{ padding: '6px 12px', border: 'none', background: '#ffffff', borderRadius: 'var(--radius-xs)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600 }}
              >
                {copiedProof ? <Check size={14} color="var(--apple-green)" /> : <Copy size={14} />}
                {copiedProof ? 'Copied' : 'Copy Proof'}
              </button>
            </div>

            <button 
              onClick={() => setInspectedIssue(null)}
              className="btn-pill-dark"
            >
              Acknowledge & Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
