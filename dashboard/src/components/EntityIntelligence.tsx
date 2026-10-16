import React, { useState } from 'react';
import { 
  Building2, 
  Search, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Network,
  Fingerprint,
  Info
} from 'lucide-react';

interface EntityIntelligenceProps {
  onNavigateTab?: (tab: string) => void;
}

interface EntityProfile {
  id: string;
  name: string;
  type: 'Shell Company' | 'Operating Mule' | 'Nominee Vehicle' | 'High-Risk Corporate';
  accountNumber: string;
  bankName: string;
  institutionId: number;
  jurisdiction: string;
  riskScore: number;
  verdict: 'CRITICAL AML RING' | 'HIGH SUSPICION' | 'ELEVATED RISK';
  uboName: string;
  uboShare: string;
  relatedEntitiesCount: number;
  crossBankAccounts: number;
  totalVolume: string;
  passThroughRate: string;
  velocityWindow: string;
  flags: string[];
  connections: {
    targetEntity: string;
    relationship: string;
    bank: string;
    confidence: number;
    crossBank: boolean;
  }[];
}

const ENTITY_DIRECTORY: Record<string, EntityProfile> = {
  '8019C0990': {
    id: 'ENT-2026-9041',
    name: 'Apex Horizon Global Ltd',
    type: 'Shell Company',
    accountNumber: '8019C0990',
    bankName: 'Bank 23842 (Institution 0)',
    institutionId: 0,
    jurisdiction: 'Delaware / Mumbai Liaison',
    riskScore: 0.98,
    verdict: 'CRITICAL AML RING',
    uboName: 'Vikramaditya K. Singhania (Nominee Tracked)',
    uboShare: '78.4% Voting Equity',
    relatedEntitiesCount: 6,
    crossBankAccounts: 5,
    totalVolume: '$1,480,250.00',
    passThroughRate: '98.2% within 45m',
    velocityWindow: '42 mins avg turnaround',
    flags: [
      'Layering Ring Originator (Pattern #268)',
      'Shared Director with 4 Foreign Entities',
      'Zero Legitimate Commercial Payroll Records',
      'Rapid High-Value ACH Outflows'
    ],
    connections: [
      { targetEntity: 'Vanguard Mercantile Corp', relationship: 'Common Director / Shared Nominee', bank: 'Inst 2 (Bank 3149)', confidence: 0.99, crossBank: true },
      { targetEntity: 'Solaria Trade Winds LLC', relationship: 'Circular Payment Off-ramp', bank: 'Inst 4 (Bank 1205)', confidence: 0.96, crossBank: true },
      { targetEntity: 'Bluecrest Logistics FZE', relationship: 'Pass-through Intermediary', bank: 'Inst 1 (Bank 9882)', confidence: 0.94, crossBank: true },
      { targetEntity: 'Singhania Family Trust', relationship: 'Ultimate Beneficial Owner (UBO)', bank: 'Offshore Nominee', confidence: 0.98, crossBank: true }
    ]
  },
  '80145D1D0': {
    id: 'ENT-2026-3829',
    name: 'Vanguard Mercantile Corp',
    type: 'Operating Mule',
    accountNumber: '80145D1D0',
    bankName: 'Bank 3149 (Institution 2)',
    institutionId: 2,
    jurisdiction: 'Maharashtra Domestic',
    riskScore: 0.92,
    verdict: 'HIGH SUSPICION',
    uboName: 'Rameshwar D. Patel (Front Operator)',
    uboShare: '100% Legal Ownership',
    relatedEntitiesCount: 4,
    crossBankAccounts: 3,
    totalVolume: '$890,400.00',
    passThroughRate: '96.5% within 1 hour',
    velocityWindow: '58 mins avg turnaround',
    flags: [
      'Scatter-Gather Intermediate Node',
      'Immediate Cash/Wire Transfer Upon Credit',
      'Address Matches Known Dormant Office Building'
    ],
    connections: [
      { targetEntity: 'Apex Horizon Global Ltd', relationship: 'Upstream Inflow Source', bank: 'Inst 0 (Bank 23842)', confidence: 0.99, crossBank: true },
      { targetEntity: 'Veritas Holdings Pvt Ltd', relationship: 'Co-conspirator Dispersion Route', bank: 'Inst 3 (Bank 4421)', confidence: 0.93, crossBank: true }
    ]
  },
  '80132A880': {
    id: 'ENT-2026-1102',
    name: 'Solaria Trade Winds LLC',
    type: 'Nominee Vehicle',
    accountNumber: '80132A880',
    bankName: 'Bank 1205 (Institution 4)',
    institutionId: 4,
    jurisdiction: 'Dubai Free Zone / Foreign Inward',
    riskScore: 0.89,
    verdict: 'HIGH SUSPICION',
    uboName: 'Vikramaditya K. Singhania (Shadow Controller)',
    uboShare: 'Beneficial Interest via Proxy',
    relatedEntitiesCount: 5,
    crossBankAccounts: 4,
    totalVolume: '$620,100.00',
    passThroughRate: '99.4% Aggregated',
    velocityWindow: '30 mins exit dispersion',
    flags: [
      'Downstream Exit Off-ramp',
      'High-Risk Cross-Border Aggregator',
      'Foreign Inward Remittance Spikes'
    ],
    connections: [
      { targetEntity: 'Apex Horizon Global Ltd', relationship: 'Ultimate Funding Origin', bank: 'Inst 0 (Bank 23842)', confidence: 0.97, crossBank: true },
      { targetEntity: 'Bluecrest Logistics FZE', relationship: 'Sister Entity in Free Zone', bank: 'Inst 1 (Bank 9882)', confidence: 0.91, crossBank: true }
    ]
  }
};

export const EntityIntelligence: React.FC<EntityIntelligenceProps> = ({ onNavigateTab }) => {
  const [selectedAccount, setSelectedAccount] = useState<string>('8019C0990');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [actionDone, setActionDone] = useState<string | null>(null);

  const activeEntity = ENTITY_DIRECTORY[selectedAccount] || ENTITY_DIRECTORY['8019C0990'];

  const filteredKeys = Object.keys(ENTITY_DIRECTORY).filter((acc) => {
    const e = ENTITY_DIRECTORY[acc];
    const q = searchQuery.toLowerCase();
    return (
      e.name.toLowerCase().includes(q) ||
      e.accountNumber.toLowerCase().includes(q) ||
      e.uboName.toLowerCase().includes(q) ||
      e.bankName.toLowerCase().includes(q)
    );
  });

  const handleAction = (name: string) => {
    setActionDone(name);
    setTimeout(() => setActionDone(null), 3000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '12px' }}>
      {/* ─── Top Search & Entity Selector Bar ──────────────────────── */}
      <div 
        className="bento-card animate-bento"
        style={{
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
            <Search 
              size={16} 
              style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} 
            />
            <input 
              type="text"
              placeholder="Search entity name, account, UBO, or bank..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '9px 12px 9px 36px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-medium)',
                background: 'var(--bg-canvas-subtle)',
                color: 'var(--text-primary)',
                fontSize: '0.84rem',
                outline: 'none'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {filteredKeys.map((acc) => {
              const e = ENTITY_DIRECTORY[acc];
              const isSelected = selectedAccount === acc;
              return (
                <button
                  key={acc}
                  onClick={() => setSelectedAccount(acc)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: isSelected ? '1px solid var(--lime-border)' : '1px solid var(--border-subtle)',
                    background: isSelected ? 'var(--lime-soft)' : 'var(--bg-canvas-subtle)',
                    color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: isSelected ? 700 : 500,
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <Building2 size={13} color={isSelected ? 'var(--lime)' : 'currentColor'} />
                  <span>{e.name.split(' ')[0]} ({e.accountNumber})</span>
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.68rem', fontWeight: 700 }}>
            UBO CLUSTER ACTIVE
          </span>
          <span className="pill-tag pill-tag-lime" style={{ fontSize: '0.68rem' }}>
            ENCLAVE ZK LINKAGE
          </span>
        </div>
      </div>

      {/* ─── Profile Overview Bento Grid ───────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        
        {/* Left Column: Entity Master Dossier */}
        <div 
          className="bento-card animate-bento"
          style={{
            padding: '24px',
            background: 'var(--bg-card-solid)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-medium)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          {/* Header Title with Verdict */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {activeEntity.id}
                </span>
                <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.64rem', fontWeight: 800 }}>
                  {activeEntity.verdict}
                </span>
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                {activeEntity.name}
              </h2>
              <span style={{ fontSize: '0.80rem', color: 'var(--text-secondary)' }}>
                {activeEntity.type} · {activeEntity.jurisdiction}
              </span>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.70rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Syndicate Risk Score
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--apple-red)', lineHeight: 1.1 }}>
                {(activeEntity.riskScore * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Key Facts Grid */}
          <div 
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '10px',
              padding: '14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-canvas-subtle)',
              border: '1px solid var(--border-subtle)'
            }}
          >
            <div>
              <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', display: 'block' }}>Primary Account</span>
              <strong style={{ fontSize: '0.86rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {activeEntity.accountNumber}
              </strong>
            </div>
            <div>
              <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', display: 'block' }}>Institution Node</span>
              <strong style={{ fontSize: '0.84rem', color: 'var(--text-primary)' }}>
                {activeEntity.bankName}
              </strong>
            </div>
            <div>
              <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', display: 'block' }}>Total Flow Volume</span>
              <strong style={{ fontSize: '0.86rem', color: 'var(--text-primary)' }}>
                {activeEntity.totalVolume}
              </strong>
            </div>
            <div>
              <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', display: 'block' }}>Pass-Through Velocity</span>
              <strong style={{ fontSize: '0.84rem', color: 'var(--apple-red)' }}>
                {activeEntity.passThroughRate}
              </strong>
            </div>
          </div>

          {/* Beneficial Ownership (UBO) Card */}
          <div 
            style={{
              padding: '14px 16px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(255, 149, 0, 0.08)',
              border: '1px solid rgba(255, 149, 0, 0.22)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px'
            }}
          >
            <Fingerprint size={22} color="var(--apple-amber)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.70rem', fontWeight: 800, color: 'var(--apple-amber)', textTransform: 'uppercase' }}>
                  Cross-Bank Ultimate Beneficial Owner (UBO)
                </span>
              </div>
              <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '2px' }}>
                {activeEntity.uboName}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Holding: {activeEntity.uboShare} · Controls accounts across {activeEntity.crossBankAccounts} separate banks.
              </div>
            </div>
          </div>

          {/* Compliance Red Flags */}
          <div>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Detected Anti-Money Laundering Signals
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
              {activeEntity.flags.map((flag, idx) => (
                <div 
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '0.78rem',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <AlertTriangle size={13} color="var(--apple-red)" style={{ flexShrink: 0 }} />
                  <span>{flag}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Compliance Action Buttons */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: 'auto', paddingTop: '8px' }}>
            <button
              onClick={() => handleAction('lien')}
              className="apple-segment-btn"
              style={{
                flex: 1,
                minWidth: '160px',
                padding: '10px 14px',
                fontSize: '0.80rem',
                fontWeight: 700,
                background: actionDone === 'lien' ? 'var(--apple-green)' : 'rgba(255, 59, 48, 0.10)',
                color: actionDone === 'lien' ? '#ffffff' : 'var(--apple-red)',
                border: '1px solid rgba(255, 59, 48, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
            >
              {actionDone === 'lien' ? <CheckCircle2 size={15} /> : <ShieldAlert size={15} />}
              <span>{actionDone === 'lien' ? 'Disputed Amount Lien Placed' : 'Place Disputed Amount Lien'}</span>
            </button>

            <button
              onClick={() => onNavigateTab && onNavigateTab('chain')}
              className="apple-segment-btn active-lime"
              style={{
                flex: 1,
                minWidth: '160px',
                padding: '10px 14px',
                fontSize: '0.80rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
            >
              <Network size={15} />
              <span>Trace in Money Flow Map</span>
            </button>
          </div>
        </div>

        {/* Right Column: Multi-Bank Related Party & Shell Ring Topology */}
        <div 
          className="bento-card animate-bento"
          style={{
            padding: '24px',
            background: 'var(--bg-card-solid)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-medium)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
                Related-Party & Shell Network Graph
              </h3>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Cross-bank connections synthesized via Confidential Enclave Linkage
              </span>
            </div>
            <span className="pill-tag pill-tag-lime" style={{ fontSize: '0.64rem' }}>
              {activeEntity.connections.length} VERIFIED LINKS
            </span>
          </div>

          {/* Connection List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {activeEntity.connections.map((conn, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px 14px',
                  borderRadius: '12px',
                  background: 'var(--bg-canvas-subtle)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '10px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div 
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      background: 'rgba(0, 113, 227, 0.10)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}
                  >
                    <Building2 size={18} color="var(--apple-blue)" />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {conn.targetEntity}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                      {conn.relationship} · <span style={{ color: 'var(--text-muted)' }}>{conn.bank}</span>
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <span 
                    className="pill-tag pill-tag-success"
                    style={{ fontSize: '0.66rem', fontWeight: 700 }}
                  >
                    {(conn.confidence * 100).toFixed(0)}% Match
                  </span>
                  {conn.crossBank && (
                    <div style={{ fontSize: '0.66rem', color: 'var(--apple-amber)', marginTop: '2px', fontWeight: 600 }}>
                      Inter-Bank Hop
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Regulatory DPDP / Confidentiality Notice */}
          <div 
            style={{
              padding: '12px 14px',
              borderRadius: '10px',
              background: 'var(--bg-canvas)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.74rem',
              color: 'var(--text-muted)',
              lineHeight: 1.5,
              marginTop: 'auto',
              display: 'flex',
              gap: '8px'
            }}
          >
            <Info size={15} style={{ flexShrink: 0, marginTop: '2px', color: 'var(--text-secondary)' }} />
            <span>
              <strong>Zero Raw Data Disclosure:</strong> All related-party links are established inside the confidential compute enclave using hashed pseudonym sets and cryptographic graph intersection. No bank's internal KYC files or account ledgers were shared with counterparties.
            </span>
          </div>

        </div>

      </div>
    </div>
  );
};
export default EntityIntelligence;
