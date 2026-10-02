import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';

interface ReconIssue {
  edgeRef: string;
  fromBank: string;
  toBank: string;
  bankA_Amount: string;
  bankB_Amount: string;
  issueType: 'AMOUNT_MISMATCH' | 'TIMESTAMP_MISMATCH' | 'UNMATCHED_REFERENCE';
  status: 'CAUGHT';
}

export const Reconciliation: React.FC = () => {
  const [issues] = useState<ReconIssue[]>([
    { edgeRef: 'TXN_CROSS_9011', fromBank: 'Bank Alpha (Inst 0)', toBank: 'Bank Beta (Inst 1)', bankA_Amount: '$50,000.00', bankB_Amount: '$45,000.00', issueType: 'AMOUNT_MISMATCH', status: 'CAUGHT' },
    { edgeRef: 'TXN_CROSS_9014', fromBank: 'Bank Beta (Inst 1)', toBank: 'Bank Gamma (Inst 2)', bankA_Amount: '$120,000.00', bankB_Amount: 'MISSING', issueType: 'UNMATCHED_REFERENCE', status: 'CAUGHT' },
    { edgeRef: 'TXN_CROSS_9088', fromBank: 'Bank Gamma (Inst 2)', toBank: 'Bank Alpha (Inst 0)', bankA_Amount: '$30,000.00', bankB_Amount: '$30,000.00 (+4h delta)', issueType: 'TIMESTAMP_MISMATCH', status: 'CAUGHT' },
  ]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Overview Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Injected Malicious Edges</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>3</div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Simulated lying bank attacks</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
          <div style={{ fontSize: '0.75rem', color: '#34d399', textTransform: 'uppercase', fontWeight: 600 }}>Enclave Caught Issues</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#34d399', marginTop: '4px' }}>3</div>
          <div style={{ fontSize: '0.75rem', color: '#34d399', marginTop: '4px' }}>Detected before graph entry</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Reconciliation Catch Rate</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>100.0%</div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Zero fake edges entered boundary</div>
        </div>
      </div>

      {/* Reconciled Issues Table */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={20} color="#10b981" /> Reconciled Double-Entry Audit Log
        </h3>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'left', color: '#94a3b8' }}>
                <th style={{ padding: '12px 16px' }}>Txn Ref</th>
                <th style={{ padding: '12px 16px' }}>Sender Bank</th>
                <th style={{ padding: '12px 16px' }}>Receiver Bank</th>
                <th style={{ padding: '12px 16px' }}>Sender Amount</th>
                <th style={{ padding: '12px 16px' }}>Receiver Amount</th>
                <th style={{ padding: '12px 16px' }}>Discrepancy Type</th>
                <th style={{ padding: '12px 16px' }}>Enclave Action</th>
              </tr>
            </thead>
            <tbody>
              {issues.map(item => (
                <tr key={item.edgeRef} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <td style={{ padding: '14px 16px', fontWeight: 700 }} className="code-font">{item.edgeRef}</td>
                  <td style={{ padding: '14px 16px', color: '#cbd5e1' }}>{item.fromBank}</td>
                  <td style={{ padding: '14px 16px', color: '#cbd5e1' }}>{item.toBank}</td>
                  <td style={{ padding: '14px 16px', fontWeight: 600 }} className="code-font">{item.bankA_Amount}</td>
                  <td style={{ padding: '14px 16px', color: '#f87171', fontWeight: 600 }} className="code-font">{item.bankB_Amount}</td>
                  <td style={{ padding: '14px 16px' }}>
                    <span className="glow-pill badge-amber" style={{ fontSize: '0.7rem' }}>{item.issueType}</span>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span className="glow-pill badge-emerald" style={{ fontSize: '0.7rem' }}>Rejected & Logged</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
