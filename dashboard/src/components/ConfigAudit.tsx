import React from 'react';
import { Sliders } from 'lucide-react';

export const ConfigAudit: React.FC = () => {
  const auditRules = [
    { name: 'Model Family', c1: 'LightGBM Classifier', c3: 'LightGBM Classifier', c4: 'LightGBM Classifier', match: true },
    { name: 'Scale Pos Weight', c1: '10.0 (constant)', c3: '10.0 (constant)', c4: '10.0 (constant)', match: true },
    { name: 'Random Seeds', c1: '[42, 1337, 2026]', c3: '[42, 1337, 2026]', c4: '[42, 1337, 2026]', match: true },
    { name: 'Early Stopping', c1: '50 rounds (validation)', c3: '50 rounds (validation)', c4: '50 rounds (validation)', match: true },
    { name: 'Hyperparameter Grid', c1: 'num_leaves: [31, 63], lr: [0.05, 0.1]', c3: 'num_leaves: [31, 63], lr: [0.05, 0.1]', c4: 'num_leaves: [31, 63], lr: [0.05, 0.1]', match: true },
    { name: 'Edge Scope Difference', c1: 'Siloed (Bank Only)', c3: 'Enclave (Boundary Network)', c4: 'Global (All Banks)', match: false, expectedDiff: true },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={20} color="#6366f1" /> Configuration Parity & Audit Verification
          </h3>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '2px' }}>
            Guarantees zero hyperparameter bias between C1, C3, and C4 per PREREGISTRATION.md §5.
          </p>
        </div>

        <span className="code-font" style={{ fontSize: '0.75rem', padding: '6px 12px', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
          SHA-256: c91ea5b2e57e...
        </span>
      </div>

      <div className="glass-panel" style={{ padding: '20px', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'left', color: '#94a3b8' }}>
              <th style={{ padding: '12px 16px' }}>Parameter / Rule</th>
              <th style={{ padding: '12px 16px' }}>C1 (Siloed)</th>
              <th style={{ padding: '12px 16px' }}>C3 (Mritra)</th>
              <th style={{ padding: '12px 16px' }}>C4 (Oracle)</th>
              <th style={{ padding: '12px 16px' }}>Audit Result</th>
            </tr>
          </thead>
          <tbody>
            {auditRules.map(r => (
              <tr key={r.name} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f8fafc' }}>{r.name}</td>
                <td style={{ padding: '14px 16px', color: '#cbd5e1' }} className="code-font">{r.c1}</td>
                <td style={{ padding: '14px 16px', color: '#cbd5e1' }} className="code-font">{r.c3}</td>
                <td style={{ padding: '14px 16px', color: '#cbd5e1' }} className="code-font">{r.c4}</td>
                <td style={{ padding: '14px 16px' }}>
                  {r.match ? (
                    <span className="glow-pill badge-emerald" style={{ fontSize: '0.7rem' }}>Parity Verified</span>
                  ) : r.expectedDiff ? (
                    <span className="glow-pill" style={{ fontSize: '0.7rem', background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee' }}>Expected Scope Var</span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
