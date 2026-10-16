import React, { useState } from 'react';
import { 
  Building2, 
  Search, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Network,
  Fingerprint,
  Info,
  FileText,
  Download,
  X,
  Copy,
  Check,
  ArrowRight
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
    accountNumber?: string;
  }[];
}

const ENTITY_DIRECTORY: Record<string, EntityProfile> = {
  '8019C0990': {
    id: 'ENT-2026-9041',
    name: 'Apex Horizon Global Ltd',
    type: 'Shell Company',
    accountNumber: '8019C0990',
    bankName: 'State Bank of India (SBI)',
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
      { targetEntity: 'Vanguard Mercantile Corp', relationship: 'Common Director / Shared Nominee', bank: 'ICICI Bank', confidence: 0.99, crossBank: true, accountNumber: '80145D1D0' },
      { targetEntity: 'Solaria Trade Winds LLC', relationship: 'Circular Payment Off-ramp', bank: 'Punjab National Bank', confidence: 0.96, crossBank: true, accountNumber: '80132A880' },
      { targetEntity: 'Bluecrest Logistics FZE', relationship: 'Pass-through Intermediary', bank: 'HDFC Bank', confidence: 0.94, crossBank: true, accountNumber: '80129B710' },
      { targetEntity: 'Singhania Family Trust', relationship: 'Ultimate Beneficial Owner (UBO)', bank: 'Offshore Nominee', confidence: 0.98, crossBank: true, accountNumber: '80111F001' }
    ]
  },
  '80145D1D0': {
    id: 'ENT-2026-3829',
    name: 'Vanguard Mercantile Corp',
    type: 'Operating Mule',
    accountNumber: '80145D1D0',
    bankName: 'ICICI Bank',
    institutionId: 2,
    jurisdiction: 'Maharashtra Domestic',
    riskScore: 0.92,
    verdict: 'HIGH SUSPICION',
    uboName: 'Rameshwar D. Patel (Front Operator)',
    uboShare: '100% Legal Ownership (Proxy)',
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
      { targetEntity: 'Apex Horizon Global Ltd', relationship: 'Upstream Inflow Source', bank: 'State Bank of India', confidence: 0.99, crossBank: true, accountNumber: '8019C0990' },
      { targetEntity: 'Solaria Trade Winds LLC', relationship: 'Downstream Consolidation Sink', bank: 'Punjab National Bank', confidence: 0.95, crossBank: true, accountNumber: '80132A880' },
      { targetEntity: 'Bluecrest Logistics FZE', relationship: 'Parallel Layering Route', bank: 'HDFC Bank', confidence: 0.92, crossBank: true, accountNumber: '80129B710' }
    ]
  },
  '80132A880': {
    id: 'ENT-2026-1102',
    name: 'Solaria Trade Winds LLC',
    type: 'Nominee Vehicle',
    accountNumber: '80132A880',
    bankName: 'Punjab National Bank (PNB)',
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
      { targetEntity: 'Apex Horizon Global Ltd', relationship: 'Ultimate Funding Origin', bank: 'State Bank of India', confidence: 0.97, crossBank: true, accountNumber: '8019C0990' },
      { targetEntity: 'Vanguard Mercantile Corp', relationship: 'Transit Layer Source', bank: 'ICICI Bank', confidence: 0.95, crossBank: true, accountNumber: '80145D1D0' },
      { targetEntity: 'Bluecrest Logistics FZE', relationship: 'Sister Entity in Free Zone', bank: 'HDFC Bank', confidence: 0.91, crossBank: true, accountNumber: '80129B710' }
    ]
  },
  '80129B710': {
    id: 'ENT-2026-7731',
    name: 'Bluecrest Logistics FZE',
    type: 'Operating Mule',
    accountNumber: '80129B710',
    bankName: 'HDFC Bank',
    institutionId: 1,
    jurisdiction: 'Sharjah Airport Free Zone (SAIF)',
    riskScore: 0.88,
    verdict: 'HIGH SUSPICION',
    uboName: 'Vikramaditya K. Singhania (Nominee Tracked)',
    uboShare: '65.0% Voting Stake',
    relatedEntitiesCount: 4,
    crossBankAccounts: 3,
    totalVolume: '$524,300.00',
    passThroughRate: '97.1% within 2 hours',
    velocityWindow: '1.2h avg turnaround',
    flags: [
      'Pass-Through Layering Conduit',
      'Invoices For Generic Non-Existent IT Services',
      'High Fan-Out to PNB Foreign Accounts'
    ],
    connections: [
      { targetEntity: 'Apex Horizon Global Ltd', relationship: 'Primary Originator', bank: 'State Bank of India', confidence: 0.94, crossBank: true, accountNumber: '8019C0990' },
      { targetEntity: 'Solaria Trade Winds LLC', relationship: 'Off-ramp Destination', bank: 'Punjab National Bank', confidence: 0.91, crossBank: true, accountNumber: '80132A880' }
    ]
  },
  '80111F001': {
    id: 'ENT-2026-0005',
    name: 'Singhania Family Trust',
    type: 'High-Risk Corporate',
    accountNumber: '80111F001',
    bankName: 'Offshore Nominee Hub',
    institutionId: 3,
    jurisdiction: 'George Town, Grand Cayman',
    riskScore: 0.95,
    verdict: 'CRITICAL AML RING',
    uboName: 'Vikramaditya K. Singhania (Sole Beneficiary)',
    uboShare: '100% Beneficial Interest',
    relatedEntitiesCount: 8,
    crossBankAccounts: 6,
    totalVolume: '$3,952,140.00',
    passThroughRate: 'Controlled Holding Structure',
    velocityWindow: 'Ultimate Capital Accumulator',
    flags: [
      'Ultimate Beneficial Owner Umbrella Vehicle',
      'Layered Behind 3 Strata of Nominee Directors',
      'Cryptographic Boundary Synthesis Match Score 99.2%'
    ],
    connections: [
      { targetEntity: 'Apex Horizon Global Ltd', relationship: 'Controlled Operating Vehicle', bank: 'State Bank of India', confidence: 0.98, crossBank: true, accountNumber: '8019C0990' },
      { targetEntity: 'Solaria Trade Winds LLC', relationship: 'Repatriation Funnel Sink', bank: 'Punjab National Bank', confidence: 0.96, crossBank: true, accountNumber: '80132A880' }
    ]
  }
};

export const EntityIntelligence: React.FC<EntityIntelligenceProps> = ({ onNavigateTab }) => {
  const [selectedAccount, setSelectedAccount] = useState<string>('8019C0990');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [actionDone, setActionDone] = useState<string | null>(null);
  const [showSarModal, setShowSarModal] = useState<boolean>(false);
  const [copiedSar, setCopiedSar] = useState<boolean>(false);

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
          flexDirection: 'column',
          gap: '12px',
          background: 'var(--bg-card-solid)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-medium)'
        }}
      >
        {/* Full-width Search Field */}
        <div style={{ position: 'relative', width: '100%' }}>
          <Search 
            size={16} 
            style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} 
          />
          <input 
            type="text"
            placeholder="Search entity name, account number, UBO, or bank..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px 10px 40px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-medium)',
              background: 'var(--bg-canvas-subtle)',
              color: 'var(--text-primary)',
              fontSize: '0.86rem',
              outline: 'none'
            }}
          />
        </div>

        {/* Quick Filter Chips & Status */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Target Syndicates:
            </span>
            {filteredKeys.map((acc) => {
              const e = ENTITY_DIRECTORY[acc];
              const isSelected = selectedAccount === acc;
              return (
                <button
                  key={acc}
                  onClick={() => setSelectedAccount(acc)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-full)',
                    border: isSelected ? '1px solid var(--lime-border)' : '1px solid var(--border-subtle)',
                    background: isSelected ? 'var(--lime-soft)' : 'var(--bg-canvas-subtle)',
                    color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: isSelected ? 800 : 500,
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <Building2 size={13} color={isSelected ? 'var(--lime)' : 'currentColor'} />
                  <span>{e.name} ({e.bankName.split(' ')[0]})</span>
                </button>
              );
            })}
          </div>

          <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.66rem', fontWeight: 800 }}>
            UBO CLUSTER ACTIVE
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
              <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)', display: 'block' }}>Bank</span>
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
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: 'auto', paddingTop: '8px' }}>
            <button
              onClick={() => handleAction('lien')}
              className={actionDone === 'lien' ? "apple-btn-secondary" : "apple-btn-danger"}
              style={{ flex: 1, minWidth: '130px', fontSize: '0.80rem' }}
            >
              {actionDone === 'lien' ? <CheckCircle2 size={15} color="var(--apple-green)" /> : <ShieldAlert size={15} />}
              <span>{actionDone === 'lien' ? 'Lien Placed' : 'Place Lien'}</span>
            </button>

            <button
              onClick={() => setShowSarModal(true)}
              className="apple-btn-secondary"
              style={{ flex: 1, minWidth: '130px', fontSize: '0.80rem' }}
            >
              <FileText size={15} />
              <span>Export SAR</span>
            </button>

            <button
              onClick={() => onNavigateTab && onNavigateTab('chain')}
              className="apple-btn-lime"
              style={{ flex: 1, minWidth: '140px', fontSize: '0.80rem' }}
            >
              <Network size={15} />
              <span>Trace Money Flow</span>
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

          {/* Interactive Topology Mini-Map */}
          <div style={{ background: 'var(--bg-canvas-subtle)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '12px 14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Syndicate Hierarchy (Click Node to Pivot)
              </span>
              <span style={{ fontSize: '0.68rem', color: 'var(--apple-green)', fontWeight: 600 }}>
                ● 5 Linked Enclave Accounts
              </span>
            </div>
            
            <svg viewBox="0 0 460 170" style={{ width: '100%', height: '145px', overflow: 'visible' }}>
              <defs>
                <marker id="mini-arrow" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="var(--apple-red)" opacity="0.75" />
                </marker>
              </defs>

              {/* Connecting Lines */}
              <line x1="230" y1="28" x2="230" y2="60" stroke="var(--apple-amber)" strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="230" y1="84" x2="115" y2="116" stroke="var(--apple-red)" strokeWidth="1.5" markerEnd="url(#mini-arrow)" />
              <line x1="230" y1="84" x2="345" y2="116" stroke="var(--apple-red)" strokeWidth="1.5" markerEnd="url(#mini-arrow)" />
              <line x1="115" y1="138" x2="230" y2="152" stroke="var(--apple-red)" strokeWidth="1.5" markerEnd="url(#mini-arrow)" />
              <line x1="345" y1="138" x2="230" y2="152" stroke="var(--apple-red)" strokeWidth="1.5" markerEnd="url(#mini-arrow)" />

              {/* Node 1: Singhania Family Trust (UBO) */}
              <g onClick={() => setSelectedAccount('80111F001')} style={{ cursor: 'pointer' }}>
                <rect x="145" y="6" width="170" height="24" rx="12" 
                  fill={selectedAccount === '80111F001' ? 'var(--apple-amber)' : 'var(--bg-card-solid)'}
                  stroke="var(--apple-amber)" strokeWidth={selectedAccount === '80111F001' ? "2" : "1"}
                />
                <text x="230" y="22" textAnchor="middle" fontSize="9.5" fontWeight="700" 
                  fill={selectedAccount === '80111F001' ? '#000000' : 'var(--text-primary)'}>
                  Singhania Trust (UBO 100%)
                </text>
              </g>

              {/* Node 2: Apex Horizon (Originator) */}
              <g onClick={() => setSelectedAccount('8019C0990')} style={{ cursor: 'pointer' }}>
                <rect x="140" y="60" width="180" height="24" rx="12" 
                  fill={selectedAccount === '8019C0990' ? 'var(--lime)' : 'var(--bg-card-solid)'}
                  stroke="var(--lime)" strokeWidth={selectedAccount === '8019C0990' ? "2.5" : "1"}
                />
                <text x="230" y="76" textAnchor="middle" fontSize="9.5" fontWeight="700" 
                  fill={selectedAccount === '8019C0990' ? '#000000' : 'var(--text-primary)'}>
                  Apex Horizon Global (SBI)
                </text>
              </g>

              {/* Node 3: Bluecrest (HDFC) */}
              <g onClick={() => setSelectedAccount('80129B710')} style={{ cursor: 'pointer' }}>
                <rect x="35" y="116" width="160" height="24" rx="12" 
                  fill={selectedAccount === '80129B710' ? 'var(--lime)' : 'var(--bg-card-solid)'}
                  stroke="var(--border-subtle)" strokeWidth={selectedAccount === '80129B710' ? "2.5" : "1"}
                />
                <text x="115" y="132" textAnchor="middle" fontSize="9.5" fontWeight="700" 
                  fill={selectedAccount === '80129B710' ? '#000000' : 'var(--text-primary)'}>
                  Bluecrest Logistics (HDFC)
                </text>
              </g>

              {/* Node 4: Vanguard (ICICI) */}
              <g onClick={() => setSelectedAccount('80145D1D0')} style={{ cursor: 'pointer' }}>
                <rect x="265" y="116" width="160" height="24" rx="12" 
                  fill={selectedAccount === '80145D1D0' ? 'var(--lime)' : 'var(--bg-card-solid)'}
                  stroke="var(--border-subtle)" strokeWidth={selectedAccount === '80145D1D0' ? "2.5" : "1"}
                />
                <text x="345" y="132" textAnchor="middle" fontSize="9.5" fontWeight="700" 
                  fill={selectedAccount === '80145D1D0' ? '#000000' : 'var(--text-primary)'}>
                  Vanguard Merc. (ICICI)
                </text>
              </g>

              {/* Node 5: Solaria (PNB) */}
              <g onClick={() => setSelectedAccount('80132A880')} style={{ cursor: 'pointer' }}>
                <rect x="140" y="152" width="180" height="22" rx="11" 
                  fill={selectedAccount === '80132A880' ? 'var(--apple-red)' : 'var(--bg-card-solid)'}
                  stroke="var(--apple-red)" strokeWidth={selectedAccount === '80132A880' ? "2" : "1"}
                />
                <text x="230" y="167" textAnchor="middle" fontSize="9" fontWeight="700" 
                  fill={selectedAccount === '80132A880' ? '#ffffff' : 'var(--apple-red)'}>
                  Solaria Trade Winds (PNB)
                </text>
              </g>
            </svg>
          </div>

          {/* Connection List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {activeEntity.connections.map((conn, idx) => (
              <div
                key={idx}
                onClick={() => conn.accountNumber && setSelectedAccount(conn.accountNumber)}
                style={{
                  padding: '12px 14px',
                  borderRadius: '12px',
                  background: 'var(--bg-canvas-subtle)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '10px',
                  cursor: conn.accountNumber ? 'pointer' : 'default',
                  transition: 'all 0.2s ease'
                }}
                className="ring-row-card"
                title={conn.accountNumber ? `Click to inspect dossier for ${conn.targetEntity}` : undefined}
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

                <div style={{ textAlign: 'right', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div>
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
                  {conn.accountNumber && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      <ArrowRight size={14} />
                    </span>
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

      {/* ─── Cryptographic SAR Case Dossier Modal ─────────────────── */}
      {showSarModal && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}
          onClick={() => setShowSarModal(false)}
        >
          <div 
            className="apple-sheet animate-bento"
            style={{
              width: '100%',
              maxWidth: '680px',
              padding: '28px',
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              flexDirection: 'column',
              gap: '18px'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.68rem', fontWeight: 800 }}>
                  CONFIDENTIAL FIU CASE DOSSIER
                </span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '4px', margin: 0 }}>
                  Cryptographic SAR Package #SAR-2026-9041
                </h3>
              </div>
              <button 
                className="icon-circle-btn"
                onClick={() => setShowSarModal(false)}
                style={{ width: '32px', height: '32px' }}
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.78rem', background: 'var(--bg-canvas-subtle)', padding: '14px', borderRadius: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block' }}>Target Syndicate</span>
                <strong>{activeEntity.name}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block' }}>Hardware Attestation</span>
                <strong>IBM Secure Execution on LinuxONE (s390x)</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block' }}>Privacy Guarantee</span>
                <strong style={{ color: 'var(--apple-green)' }}>Differential Privacy (ε=1.15, δ=10⁻⁶)</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block' }}>Total Syndicate Volume</span>
                <strong>$3,952,140.00 (₹32.8 Cr)</strong>
              </div>
            </div>

            <div style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', background: 'var(--bg-canvas)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
              <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>// Cryptographic Proof Signature</div>
              <div>sha256: e8d47b6a9c1f2038475a6c8b9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e</div>
              <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>curve25519_vrf: 0x9f4a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f</div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button
                className="selector-pill"
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(activeEntity, null, 2));
                  setCopiedSar(true);
                  setTimeout(() => setCopiedSar(false), 2000);
                }}
                style={{ fontSize: '0.80rem' }}
              >
                {copiedSar ? <Check size={14} color="var(--apple-green)" /> : <Copy size={14} />}
                <span>{copiedSar ? 'Copied JSON' : 'Copy Enclave JSON'}</span>
              </button>
              <button
                className="apple-btn-primary"
                onClick={() => {
                  const blob = new Blob([JSON.stringify(activeEntity, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `SAR_${activeEntity.accountNumber}.json`;
                  a.click();
                  setShowSarModal(false);
                }}
                style={{ fontSize: '0.80rem', padding: '8px 16px' }}
              >
                <Download size={14} />
                <span>Download Certified SAR</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
export default EntityIntelligence;
