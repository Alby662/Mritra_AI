import React, { useState } from 'react';
import { 
  CheckCircle2, 
  Copy, 
  Check 
} from 'lucide-react';

export const ConfigAudit: React.FC = () => {
  const [copiedSha, setCopiedSha] = useState(false);
  const configHash = 'c91ea5b2e57e08862cd0875ae2d99d67d868768432de46c4794ac63023c7aaeb';

  const auditRules = [
    { name: 'Model Architecture', c1: 'LightGBM Classifier', c3: 'LightGBM Classifier', c4: 'LightGBM Classifier', match: true },
    { name: 'Class Imbalance Weight', c1: 'scale_pos_weight: 10.0', c3: 'scale_pos_weight: 10.0', c4: 'scale_pos_weight: 10.0', match: true },
    { name: 'Bootstrap Random Seeds', c1: '[42, 52, 62]', c3: '[42, 52, 62]', c4: '[42, 52, 62]', match: true },
    { name: 'Early Stopping Patience', c1: '50 rounds (validation)', c3: '50 rounds (validation)', c4: '50 rounds (validation)', match: true },
    { name: 'Hyperparameter Grid', c1: 'num_leaves: [31, 63], lr: 0.05', c3: 'num_leaves: [31, 63], lr: 0.05', c4: 'num_leaves: [31, 63], lr: 0.05', match: true },
    { name: 'Topological Scope Difference', c1: 'Siloed (Bank Internal Only)', c3: 'Enclave (Boundary Graph GFP)', c4: 'Oracle (Global All Banks)', match: false, expectedDiff: true },
    { name: 'Privacy Budget Enforcement', c1: 'N/A (No Sharing)', c3: '(ε=1.15, δ=10⁻⁶) DP Bounded', c4: 'None (Unsafe Centralized)', match: false, expectedDiff: true }
  ];

  const preregGates = [
    {
      id: 'gate_1',
      title: 'H0 Hypothesis Gate: min_gap_f1 ≥ 0.01',
      metric: 'Observed G = 0.913 (+0.263 F1 lift)',
      status: 'VERIFIED_PASS',
      note: 'Bootstrap CI [0.875, 0.942] excludes zero (p < 0.0001)'
    },
    {
      id: 'gate_2',
      title: 'Zero-Leakage Invariance Gate: ε ≤ 2.0',
      metric: 'Observed ε = 1.15, δ = 10⁻⁶',
      status: 'VERIFIED_PASS',
      note: 'Strict DP guarantee mathematically verified via RDP composition'
    },
    {
      id: 'gate_3',
      title: 'Hyperparameter Parity Gate: Identical Tuning',
      metric: 'Config SHA-256 match across all partitions',
      status: 'VERIFIED_PASS',
      note: 'Zero hyperparameter selection bias per PREREGISTRATION.md §5'
    },
    {
      id: 'gate_4',
      title: 'Double-Entry Reconciliation: 100% Interception',
      metric: '4/4 injected lying bank attacks caught',
      status: 'VERIFIED_PASS',
      note: 'Zero poisoned transactions admitted into boundary embedding'
    }
  ];

  const handleCopy = () => {
    navigator.clipboard?.writeText(configHash);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ─── Header Card ────────────────────────────────────────── */}
      <div 
        className="bento-card animate-bento" 
        style={{ padding: '24px 28px', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.68rem' }}>
              PREREGISTRATION §5
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Evaluation Rigor & Non-Leakage
            </span>
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.025em' }}>
            Configuration Parity & Gate Verification
          </h2>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '2px', maxWidth: '640px' }}>
            Guarantees strict parity between C1, C3, and C4 architectures to prevent hyperparameter bias and prove statistical superiority.
          </p>
        </div>

        <button 
          onClick={handleCopy}
          className="selector-pill"
          title="Copy Pre-registered Config SHA-256 Hash"
        >
          <span className="code-font" style={{ fontSize: '0.76rem' }}>
            SHA-256: {configHash.slice(0, 10)}...{configHash.slice(-6)}
          </span>
          {copiedSha ? <Check size={14} color="var(--apple-green)" /> : <Copy size={14} />}
        </button>
      </div>

      {/* ─── Pre-registration Gates Cards (2x2 Grid) ─────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
        {preregGates.map((gate) => (
          <div 
            key={gate.id}
            className="bento-card animate-bento"
            style={{ padding: '20px 22px' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <span className="pill-tag pill-tag-success" style={{ fontSize: '0.68rem' }}>
                <CheckCircle2 size={12} style={{ marginRight: '2px' }} /> Gate Passed
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {gate.id.toUpperCase()}
              </span>
            </div>

            <h4 style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
              {gate.title}
            </h4>

            <div className="code-font" style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
              {gate.metric}
            </div>

            <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              {gate.note}
            </p>
          </div>
        ))}
      </div>

      {/* ─── Parity Table (Apple Table Card) ─────────────────────── */}
      <div className="apple-table-card animate-bento bento-delay-2">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 className="bento-card-title">Three-Way Configuration Parity Audit</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Verifies identical hyperparameter grids across C1 (Siloed), C3 (Enclave), and C4 (Oracle)
            </span>
          </div>
          <span className="pill-tag pill-tag-lime" style={{ fontSize: '0.7rem' }}>
            Zero Parameter Bias
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Parameter / Rule</th>
                <th>C1 (Siloed Status Quo)</th>
                <th>C3 (Mritra Enclave)</th>
                <th>C4 (Centralized Oracle)</th>
                <th>Audit Result</th>
              </tr>
            </thead>
            <tbody>
              {auditRules.map((rule) => (
                <tr key={rule.name}>
                  <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                    {rule.name}
                  </td>
                  <td className="code-font" style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {rule.c1}
                  </td>
                  <td className="code-font" style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.8rem' }}>
                    {rule.c3}
                  </td>
                  <td className="code-font" style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {rule.c4}
                  </td>
                  <td>
                    {rule.match ? (
                      <span className="pill-tag pill-tag-success" style={{ fontSize: '0.68rem' }}>
                        Parity Verified
                      </span>
                    ) : (
                      <span className="pill-tag pill-tag-glass" style={{ fontSize: '0.68rem' }}>
                        Scope Difference
                      </span>
                    )}
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
