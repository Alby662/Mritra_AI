import React, { useState, useEffect } from 'react';
import { 
  ArrowRight, 
  AlertTriangle 
} from 'lucide-react';
import { 
  fetchLiveResultsSummary 
} from '../data/telemetryData';
import { useToast } from '../context/ToastContext';

interface OverviewProps {
  onNavigateTab?: (tab: string) => void;
  selectedRunId?: string;
  onSelectRunId?: (id: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({ onNavigateTab }) => {
  const { showToast } = useToast();
  const [quarantined, setQuarantined] = useState<boolean>(true);
  const [isLiveApi, setIsLiveApi] = useState(false);

  useEffect(() => {
    fetchLiveResultsSummary().then((summary) => {
      if (summary && summary.success) {
        setIsLiveApi(true);
      }
    });
  }, []);

  const handleToggleQuarantine = () => {
    const next = !quarantined;
    setQuarantined(next);
    showToast(
      next ? 'Punjab National Bank Quarantined' : 'Quarantine Lifted',
      next ? 'All 33,910 withheld transfer vectors blocked across consortium' : 'Bank reconnected to settlement',
      next ? 'danger' : 'info'
    );
  };

  const LAUNDERING_RINGS = [
    {
      id: 'pattern_268',
      title: 'Pattern #268 — Scatter-Gather Funnel',
      path: 'State Bank of India → HDFC, ICICI, Axis → PNB',
      volume: '$583,762.40 (₹4.8 Cr)',
      transfers: '30 cross-bank transfers',
      riskScore: 0.99,
      status: 'CRITICAL',
      detectedBy: 'C3 Confidential Enclave',
      blindInSilo: '0% in single bank view (blind)',
    },
    {
      id: 'pattern_gather_scatter_29',
      title: 'Pattern #142 — Gather-Scatter Concentration',
      path: 'HDFC, ICICI → Axis Bank',
      volume: '$98,000.00 (₹81 Lakh)',
      transfers: '14 cross-bank transfers',
      riskScore: 0.96,
      status: 'CRITICAL',
      detectedBy: 'C3 Confidential Enclave',
      blindInSilo: '12% in single bank view',
    },
    {
      id: 'pattern_cycle_19',
      title: 'Pattern #88 — Circular Laundering Loop',
      path: 'SBI → HDFC → ICICI → Axis → SBI',
      volume: '$82,100.00 (₹68 Lakh)',
      transfers: '18 circular transfers',
      riskScore: 0.97,
      status: 'CRITICAL',
      detectedBy: 'C3 Confidential Enclave',
      blindInSilo: '8% in single bank view',
    },
    {
      id: 'pattern_fan_in_08',
      title: 'Pattern #205 — Structuring Consolidation Hub',
      path: 'SBI, HDFC, Axis → ICICI Bank',
      volume: '$49,800.00 (₹41 Lakh)',
      transfers: '22 transfers under $10k SAR threshold',
      riskScore: 0.93,
      status: 'HIGH',
      detectedBy: 'C3 Confidential Enclave',
      blindInSilo: '15% in single bank view',
    },
  ];

  const CONSORTIUM_BANKS = [
    { name: 'State Bank of India (SBI)', role: 'Consortium Participant', status: 'Healthy', flaggedTxns: 0, isAdversarial: false },
    { name: 'HDFC Bank', role: 'Consortium Participant', status: 'Healthy', flaggedTxns: 0, isAdversarial: false },
    { name: 'ICICI Bank', role: 'Consortium Participant', status: 'Healthy', flaggedTxns: 0, isAdversarial: false },
    { name: 'Axis Bank', role: 'Consortium Participant', status: 'Healthy', flaggedTxns: 0, isAdversarial: false },
    { name: 'Punjab National Bank (PNB)', role: 'Adversarial Bank', status: quarantined ? 'Quarantined' : 'Active', flaggedTxns: 33910, isAdversarial: true },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* ─── Top Executive Incident Banner ───────────────────────────── */}
      <div 
        className="bento-card animate-bento"
        style={{
          padding: '22px 28px',
          background: 'var(--bg-card-solid)',
          borderLeft: '4px solid var(--apple-red)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', maxWidth: '820px' }}>
          <div style={{ padding: '10px', borderRadius: '12px', background: 'rgba(255, 59, 48, 0.1)', color: 'var(--apple-red)', marginTop: '2px' }}>
            <AlertTriangle size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.68rem', fontWeight: 800 }}>
                ACTIVE AML INTERCEPTION
              </span>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Hardware: IBM Secure Execution on LinuxONE (s390x)
              </span>
              {isLiveApi && (
                <span className="pill-tag pill-tag-success" style={{ fontSize: '0.64rem', padding: '1px 6px' }}>
                  Live API
                </span>
              )}
            </div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              Multi-Bank Laundering Ring Detected Across 5 Institutions
            </h2>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '4px', margin: 0, lineHeight: 1.5 }}>
              Mritra confidential enclave intercepted <strong>$3.95M (₹32.8 Cr)</strong> in cross-bank laundering and caught <strong>33,910 withheld transactions</strong> from Punjab National Bank with 100% catch rate.
            </p>
          </div>
        </div>

        <button
          onClick={() => onNavigateTab?.('chain')}
          className="apple-btn-primary"
          style={{ padding: '10px 18px', fontSize: '0.84rem' }}
        >
          View Money Flow Map <ArrowRight size={15} />
        </button>
      </div>

      {/* ─── 3 Clean Executive KPI Cards ─────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        
        {/* Card 1: Suspicious Flow */}
        <div className="bento-card animate-bento" style={{ padding: '22px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
              SUSPICIOUS MULTI-BANK VOLUME
            </span>
            <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.66rem' }}>
              100% Intercepted
            </span>
          </div>
          <div className="tabular-nums" style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.03em' }}>
            $3.95M
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            ₹32.8 Crore total volume across 5 consortium banks
          </div>
        </div>

        {/* Card 2: Interceptions */}
        <div className="bento-card animate-bento bento-delay-1" style={{ padding: '22px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
              WITHHELD TRANSFERS CAUGHT
            </span>
            <span className="pill-tag pill-tag-success" style={{ fontSize: '0.66rem' }}>
              Zero Data Poisoning
            </span>
          </div>
          <div className="tabular-nums" style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#ff3b30' }}>
            33,910
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Discrepancies caught from PNB via double-entry reconciliation
          </div>
        </div>

        {/* Card 3: Detection Gain */}
        <div className="bento-card animate-bento bento-delay-2" style={{ padding: '22px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
              ENCLAVE DETECTION GAIN
            </span>
            <span className="pill-tag pill-tag-success" style={{ fontSize: '0.66rem' }}>
              +81.7% Gain
            </span>
          </div>
          <div className="tabular-nums" style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--apple-green)' }}>
            +81.7%
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Over siloed single-bank detection (PR-AUC 0.718 vs 0.120)
          </div>
        </div>

      </div>

      {/* ─── 2-Column Core Interface (Laundering Rings + Bank Network) ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '20px' }}>
        
        {/* Left Column: Detected Multi-Bank Laundering Rings */}
        <div className="bento-card animate-bento" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, margin: 0 }}>
                Detected Laundering Rings
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                Multi-hop transaction patterns spanning bank boundaries
              </p>
            </div>
            <button 
              onClick={() => onNavigateTab?.('chain')}
              className="selector-pill"
              style={{ fontSize: '0.76rem', padding: '6px 12px' }}
            >
              Open Full Map <ArrowRight size={13} style={{ marginLeft: '4px' }} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {LAUNDERING_RINGS.map((ring) => (
              <div 
                key={ring.id}
                onClick={() => onNavigateTab?.('chain')}
                style={{
                  padding: '16px 18px',
                  borderRadius: '12px',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-card-subtle)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '12px'
                }}
                className="ring-row-card"
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.88rem', fontWeight: 700 }}>
                      {ring.title}
                    </span>
                    <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.62rem' }}>
                      {(ring.riskScore * 100).toFixed(0)}% RISK
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    {ring.path}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {ring.transfers} · <span style={{ color: 'var(--apple-green)', fontWeight: 600 }}>{ring.detectedBy}</span>
                  </div>
                </div>

                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div className="tabular-nums" style={{ fontSize: '0.96rem', fontWeight: 800 }}>
                    {ring.volume}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#ff3b30', marginTop: '2px' }}>
                    {ring.blindInSilo}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Participating Banks & Live Isolation Control */}
        <div className="bento-card animate-bento" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, margin: 0 }}>
              Consortium Bank Status
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0' }}>
              Zero-knowledge double-entry verification across all 5 institutions
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
            {CONSORTIUM_BANKS.map((b) => (
              <div 
                key={b.name}
                style={{
                  padding: '12px 14px',
                  borderRadius: '10px',
                  border: b.isAdversarial && quarantined ? '1px solid rgba(255, 59, 48, 0.3)' : '1px solid var(--border-subtle)',
                  background: b.isAdversarial && quarantined ? 'rgba(255, 59, 48, 0.05)' : 'var(--bg-card-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.84rem', fontWeight: 700 }}>
                      {b.name}
                    </span>
                    {b.isAdversarial && (
                      <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.6rem' }}>
                        ADVERSARIAL
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {b.role}
                  </span>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span 
                    className={`pill-tag ${b.isAdversarial && quarantined ? 'pill-tag-danger' : 'pill-tag-success'}`}
                    style={{ fontSize: '0.66rem' }}
                  >
                    {b.status}
                  </span>
                  {b.flaggedTxns > 0 && (
                    <div style={{ fontSize: '0.7rem', color: '#ff3b30', marginTop: '2px', fontWeight: 600 }}>
                      {b.flaggedTxns.toLocaleString()} withheld txns
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Quick Quarantine Action for PNB */}
          <div style={{ padding: '14px', borderRadius: '12px', background: 'var(--bg-canvas-subtle)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.76rem', fontWeight: 700 }}>
                PNB Isolation Switch
              </span>
              <span style={{ fontSize: '0.72rem', color: quarantined ? '#ff3b30' : 'var(--apple-green)', fontWeight: 700 }}>
                {quarantined ? 'ISOLATED' : 'CONNECTED'}
              </span>
            </div>
            <button
              onClick={handleToggleQuarantine}
              className={quarantined ? 'apple-btn-secondary' : 'apple-btn-danger'}
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.82rem' }}
            >
              {quarantined ? 'Lift PNB Quarantine' : 'Quarantine Punjab National Bank'}
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
