import React, { useState } from 'react';
import { 
  Download, 
  Copy, 
  Check 
} from 'lucide-react';
import { RECON_DISCREPANCIES } from '../data/telemetryData';
import type { ReconEvent } from '../data/telemetryData';

export const Reconciliation: React.FC = () => {
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'AMOUNT_MISMATCH' | 'UNMATCHED_REFERENCE' | 'TIMESTAMP_MISMATCH' | 'REPLAY_DETECTED'>('ALL');
  const [inspectedIssue, setInspectedIssue] = useState<ReconEvent | null>(null);
  const [copiedProof, setCopiedProof] = useState(false);

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
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(RECON_DISCREPANCIES, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", "mritra_double_entry_reconciliation.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ─── Apple Overview Stat Cards ──────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
        <div className="bento-card animate-bento bento-delay-1" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
            Injected Attack Vectors
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px' }}>
            4
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Simulated lying bank inject_lying_bank.py
          </div>
        </div>

        <div className="bento-card animate-bento bento-delay-2" style={{ padding: '20px 24px', border: '1.5px solid var(--lime-border)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-primary)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
            Enclave Intercepted
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px', color: 'var(--apple-green)' }}>
            4 / 4
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Neutralized prior to boundary graph entry
          </div>
        </div>

        <div className="bento-card animate-bento bento-delay-3" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
            Reconciliation Catch Rate
          </div>
          <div className="tabular-nums" style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '4px', color: 'var(--text-primary)' }}>
            100.0%
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Zero poisoning of downstream features
          </div>
        </div>
      </div>

      {/* ─── Apple Table Card with Filtering & Export ───────────── */}
      <div className="apple-table-card animate-bento bento-delay-2">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px' }}>
          <div>
            <h3 className="bento-card-title">Reconciled Double-Entry Audit Log</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Verifies matching credits and debits across institutional boundaries
            </span>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {/* Filter buttons */}
            <div className="apple-segmented-control">
              <button 
                onClick={() => setSelectedFilter('ALL')} 
                className={`apple-segment-btn ${selectedFilter === 'ALL' ? 'active' : ''}`}
              >
                All (4)
              </button>
              <button 
                onClick={() => setSelectedFilter('AMOUNT_MISMATCH')} 
                className={`apple-segment-btn ${selectedFilter === 'AMOUNT_MISMATCH' ? 'active' : ''}`}
              >
                Amount Mismatch
              </button>
              <button 
                onClick={() => setSelectedFilter('UNMATCHED_REFERENCE')} 
                className={`apple-segment-btn ${selectedFilter === 'UNMATCHED_REFERENCE' ? 'active' : ''}`}
              >
                Missing Ref
              </button>
              <button 
                onClick={() => setSelectedFilter('REPLAY_DETECTED')} 
                className={`apple-segment-btn ${selectedFilter === 'REPLAY_DETECTED' ? 'active' : ''}`}
              >
                Replay
              </button>
            </div>

            <button 
              onClick={handleExportJSON}
              className="selector-pill"
              title="Export Audit Log as JSON"
            >
              <Download size={14} /> Export JSON
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Txn Reference</th>
                <th>Sender Entity</th>
                <th>Receiver Entity</th>
                <th>Sender Ledger</th>
                <th>Receiver Ledger</th>
                <th>Discrepancy Category</th>
                <th>Enclave Action</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredIssues.map((issue) => (
                <tr key={issue.edgeRef}>
                  <td className="code-font" style={{ fontWeight: 800 }}>
                    {issue.edgeRef}
                  </td>
                  <td style={{ fontWeight: 600 }}>{issue.fromBank}</td>
                  <td style={{ fontWeight: 600 }}>{issue.toBank}</td>
                  <td className="tabular-nums code-font" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                    {issue.bankA_Amount}
                  </td>
                  <td className="tabular-nums code-font" style={{ color: issue.bankB_Amount.includes('MISSING') ? 'var(--apple-red)' : 'var(--apple-amber)', fontWeight: 700 }}>
                    {issue.bankB_Amount}
                  </td>
                  <td>
                    <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.68rem' }}>
                      {issue.issueType.replace('_', ' ')}
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
              Transaction amounts reported by the sender institution do not balance against receiver ledger records.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>SENDER: {inspectedIssue.fromBank}</div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px' }}>
                  {inspectedIssue.bankA_Amount}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>Timestamp: {inspectedIssue.timestampA}</div>
              </div>

              <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>RECEIVER: {inspectedIssue.toBank}</div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px', color: 'var(--apple-red)' }}>
                  {inspectedIssue.bankB_Amount}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>Timestamp: {inspectedIssue.timestampB}</div>
              </div>
            </div>

            <div style={{ background: '#f5f5f7', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>ENCLAVE REJECTION PROOF HASH</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700 }}>{inspectedIssue.proofHash}</div>
              </div>
              <button 
                onClick={() => handleCopy(inspectedIssue.proofHash)}
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
