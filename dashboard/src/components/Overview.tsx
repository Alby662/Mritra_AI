import React, { useState } from 'react';
import { 
  ShieldCheck, 
  TrendingUp, 
  ArrowRight, 
  CheckCircle, 
  Cpu, 
  Lock, 
  ChevronDown,
  Copy,
  Check
} from 'lucide-react';
import { RUN_CATALOG } from '../data/telemetryData';
import type { RunMetadata } from '../data/telemetryData';

interface OverviewProps {
  onNavigateTab?: (tab: string) => void;
  selectedRunId?: string;
  onSelectRunId?: (id: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({ 
  onNavigateTab,
  selectedRunId = '20261004T092741Z'
}) => {
  const currentRun: RunMetadata = RUN_CATALOG[selectedRunId] || RUN_CATALOG['20261004T092741Z'];
  const [hoveredRadarAxis, setHoveredRadarAxis] = useState<string | null>(null);
  const [targetAccount, setTargetAccount] = useState('acct_309');
  const [quarantineStatus, setQuarantineStatus] = useState<string | null>(null);
  const [selectedStreamFilter, setSelectedStreamFilter] = useState<'all' | 'flagged'>('all');
  const [showProofModal, setShowProofModal] = useState(false);
  const [inspectedTx, setInspectedTx] = useState<any | null>(null);
  const [copiedTxId, setCopiedTxId] = useState(false);
  const [activeSplinePoint, setActiveSplinePoint] = useState<number>(4);

  // Live mule streams data (styled like Pinterest recent transactions)
  const streamData = [
    {
      id: 'tx_881',
      title: 'Deutsche Mule Fan-Out',
      bank: 'Bank Beta → Alpha',
      timestamp: 'Today · 11:55 AM',
      amount: '-$49,200.00',
      riskScore: 0.98,
      status: 'CRITICAL',
      icon: '🏛️',
      color: '#000000',
      hash: '0x8f2a...c10b',
      reason: 'Rapid fan-out pass-through within 14 minutes across 2 institutions.',
    },
    {
      id: 'tx_882',
      title: 'Layering Hop 3',
      bank: 'NeoPay → Vault',
      timestamp: 'Today · 09:50 AM',
      amount: '-$12,450.00',
      riskScore: 0.94,
      status: 'HIGH',
      icon: '⚡',
      color: '#4f46e5',
      hash: '0x3c99...e412',
      reason: 'High entropy outbound structuring under $15k ceiling.',
    },
    {
      id: 'tx_883',
      title: 'Structured Smurfing',
      bank: 'Bank Gamma → Beta',
      timestamp: 'Yesterday · 11:17 AM',
      amount: '-$9,800.00',
      riskScore: 0.89,
      status: 'HIGH',
      icon: '🛡️',
      color: '#059669',
      hash: '0x71ba...094a',
      reason: 'Sub-threshold currency deposit split across multiple accounts.',
    },
    {
      id: 'tx_884',
      title: 'Cross-Border Relay',
      bank: 'Nordic Trust → Alpha',
      timestamp: '6 July · 09:35 AM',
      amount: '-$98,000.00',
      riskScore: 0.92,
      status: 'CRITICAL',
      icon: '🌐',
      color: '#d97706',
      hash: '0xd048...bf31',
      reason: 'Cross-jurisdiction high-volume wire with immediate onward relay.',
    },
    {
      id: 'tx_885',
      title: 'Rapid Dispersal Hub',
      bank: 'Bank Alpha → Multi',
      timestamp: '6 July · 07:12 AM',
      amount: '-$49,800.00',
      riskScore: 0.96,
      status: 'CRITICAL',
      icon: '🔄',
      color: '#e11d48',
      hash: '0x55ee...a928',
      reason: '1:5 fan-out tree flagged by enclave topological embedding.',
    }
  ];

  // Radar Chart Vertices
  const radarAxes = [
    { name: 'Hop Velocity', key: 'velocity', c3: 0.95, c1: 0.28, angle: -90 },
    { name: 'Dispersal', key: 'dispersal', c3: 0.91, c1: 0.35, angle: -18 },
    { name: 'Structuring', key: 'structuring', c3: 0.88, c1: 0.42, angle: 54 },
    { name: 'Cross-Bank', key: 'crossBank', c3: 0.96, c1: 0.18, angle: 126 },
    { name: 'Entropy', key: 'entropy', c3: 0.84, c1: 0.32, angle: 198 },
  ];

  const getPolygonCoords = (scaleFactor: number, values: number[]) => {
    const center = 110;
    const maxRadius = 80;
    return values.map((val, idx) => {
      const angleRad = (radarAxes[idx].angle * Math.PI) / 180;
      const r = maxRadius * (val * scaleFactor);
      const x = center + r * Math.cos(angleRad);
      const y = center + r * Math.sin(angleRad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  };

  const c3Coords = getPolygonCoords(1.0, radarAxes.map(a => a.c3));
  const c1Coords = getPolygonCoords(1.0, radarAxes.map(a => a.c1));

  // Spline Data Points (Bezier curve like "Budget" in inspiration)
  const splinePoints = [
    { round: '10 Rnd', c3: 0.74, c4: 0.78, label: 'G = 74.2%', amount: '$14,200' },
    { round: '15 Rnd', c3: 0.81, c4: 0.84, label: 'G = 81.5%', amount: '$19,850' },
    { round: '20 Rnd', c3: 0.86, c4: 0.88, label: 'G = 86.9%', amount: '$22,400' },
    { round: '25 Rnd', c3: 0.89, c4: 0.91, label: 'G = 89.4%', amount: '$25,120' },
    { round: '30 Rnd', c3: currentRun.gRecovered, c4: 0.925, label: `G = ${(currentRun.gRecovered * 100).toFixed(1)}%`, amount: '$26,590.40' },
  ];

  const handleQuarantine = () => {
    setQuarantineStatus(`Account ${targetAccount} quarantined across all 3 consortium banks. Interdicted funds: $49,200.00.`);
    setTimeout(() => setQuarantineStatus(null), 6000);
  };

  const handleCopyHash = (text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedTxId(true);
    setTimeout(() => setCopiedTxId(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* ─── Top Masonry Stat Strip (Live Integrated Metrics) ─────── */}
      <div 
        style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', 
          gap: '14px' 
        }}
      >
        {/* Stat 1: Thesis Metric G */}
        <div 
          className="bento-card animate-bento bento-delay-1"
          style={{ padding: '18px 22px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Thesis Gap Recovered (G)
            </div>
            <div className="tabular-nums" style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px', color: 'var(--text-primary)' }}>
              {(currentRun.gRecovered * 100).toFixed(1)}% <span style={{ fontSize: '0.75rem', color: 'var(--apple-green)', fontWeight: 800 }}>+42.1% F1</span>
            </div>
            <div className="tabular-nums" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              95% CI: [{(currentRun.ciLower * 100).toFixed(1)}% – {(currentRun.ciUpper * 100).toFixed(1)}%]
            </div>
          </div>
          <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'var(--lime-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={21} color="#000" />
          </div>
        </div>

        {/* Stat 2: Enclave Proof */}
        <div 
          className="bento-card animate-bento bento-delay-2"
          style={{ padding: '18px 22px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Hardware Enclave
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              Verified <span className="badge-dot" style={{ position: 'static', width: '8px', height: '8px', background: 'var(--apple-green)' }}></span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              IBM LinuxONE / AMD SEV-SNP
            </div>
          </div>
          <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'rgba(0,0,0,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Cpu size={21} color="#000" />
          </div>
        </div>

        {/* Stat 3: DP Budget */}
        <div 
          className="bento-card animate-bento bento-delay-3"
          style={{ padding: '18px 22px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Differential Privacy
            </div>
            <div className="tabular-nums" style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px', color: 'var(--text-primary)' }}>
              ε = 1.15 <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>/ 2.0 max</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              Zero Raw PII Leakage
            </div>
          </div>
          <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'rgba(0,0,0,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Lock size={21} color="#000" />
          </div>
        </div>

        {/* Stat 4: Evaluated Dataset */}
        <div 
          className="bento-card animate-bento bento-delay-4"
          style={{ padding: '18px 22px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              AMLworld Benchmark
            </div>
            <div className="tabular-nums" style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '2px', color: 'var(--text-primary)' }}>
              {currentRun.totalSamples.toLocaleString()} <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>rows</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {currentRun.partition} · {currentRun.featuresCount} Features
            </div>
          </div>
          <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'var(--lime-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShieldCheck size={21} color="#000" />
          </div>
        </div>
      </div>

      {/* ─── Main 3-Column Pinterest Bento Grid ──────────────────── */}
      <div className="bento-grid">
        
        {/* ── COLUMN 1: Feed + Lime Bank Card ────────────────────── */}
        <div className="bento-column">
          
          {/* Card 1: Recent Interventions Stream (Apple Card Style) */}
          <div className="bento-card animate-bento bento-delay-1" style={{ flex: 1 }}>
            <div className="bento-card-header">
              <div>
                <h3 className="bento-card-title">Recent interventions</h3>
                <span className="bento-card-subtitle">Live cross-bank mule interdictions</span>
              </div>
              <button 
                onClick={() => onNavigateTab && onNavigateTab('chain')}
                className="selector-pill" 
                style={{ padding: '4px 12px', fontSize: '0.72rem', background: '#000000', color: '#ffffff', border: 'none' }}
              >
                View all &gt;
              </button>
            </div>

            {/* Filter tags */}
            <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
              <button 
                onClick={() => setSelectedStreamFilter('all')}
                className={`pill-tag ${selectedStreamFilter === 'all' ? 'pill-tag-dark' : 'pill-tag-glass'}`}
                style={{ cursor: 'pointer', border: 'none' }}
              >
                All feeds
              </button>
              <button 
                onClick={() => setSelectedStreamFilter('flagged')}
                className={`pill-tag ${selectedStreamFilter === 'flagged' ? 'pill-tag-lime' : 'pill-tag-glass'}`}
                style={{ cursor: 'pointer', border: 'none' }}
              >
                Critical risk (5)
              </button>
            </div>

            {/* Stream rows */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {streamData.slice(0, 5).map((item) => (
                <div 
                  key={item.id} 
                  className="stream-row"
                  onClick={() => setInspectedTx(item)}
                  title="Click to inspect cryptographic proof"
                >
                  <div className="stream-left">
                    <div className="stream-icon-badge">
                      {item.icon}
                    </div>
                    <div>
                      <div className="stream-name">{item.title}</div>
                      <div className="stream-sub">{item.timestamp} · {item.bank}</div>
                    </div>
                  </div>
                  <div>
                    <div className="stream-amount tabular-nums">{item.amount}</div>
                    <div className="tabular-nums" style={{ fontSize: '0.68rem', fontWeight: 800, textAlign: 'right', color: item.status === 'CRITICAL' ? 'var(--apple-red)' : 'var(--apple-amber)' }}>
                      {(item.riskScore * 100).toFixed(0)}% RISK
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Card 2: Lime Enclave Passport Card */}
          <div className="enclave-passport-card animate-bento bento-delay-2">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.7 }}>
                  Platina Secure Vault
                </span>
                <h4 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', marginTop: '2px' }}>
                  Mritra Enclave
                </h4>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, opacity: 0.7 }}>Interdicted</span>
                <div className="tabular-nums" style={{ fontSize: '1.2rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>$8,523.20K</div>
              </div>
            </div>

            {/* Chip graphic */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '22px' }}>
              <div className="enclave-chip-graphic">
                <div className="enclave-chip-line"></div>
                <div className="enclave-chip-line"></div>
                <div className="enclave-chip-line"></div>
                <div className="enclave-chip-line"></div>
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 800, letterSpacing: '0.08em', opacity: 0.75 }}>
                VISA / SEV-SNP
              </div>
            </div>

            {/* Card identifiers */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '18px' }}>
              <div>
                <div style={{ fontSize: '0.72rem', opacity: 0.65, fontWeight: 700 }}>ATTESTATION HASH</div>
                <div style={{ fontSize: '1rem', fontWeight: 800, fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>
                  *9423 06/28
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.68rem', opacity: 0.65, fontWeight: 700 }}>PRIVACY BUDGET</div>
                <div className="tabular-nums" style={{ fontSize: '0.82rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                  ε = 1.15 / 2.0
                </div>
              </div>
            </div>

            <button 
              onClick={() => onNavigateTab && onNavigateTab('tlog')}
              className="btn-pill-dark"
              style={{ fontSize: '0.82rem', padding: '10px 18px' }}
            >
              + Verify Enclave Proof
            </button>
          </div>

        </div>

        {/* ── COLUMN 2: Radar Chart + Curvy Bezier Graph ─────────── */}
        <div className="bento-column">
          
          {/* Card 3: Spending / Risk Radar (Interactive SVG) */}
          <div className="bento-card animate-bento bento-delay-2" style={{ padding: '24px' }}>
            <div className="bento-card-header" style={{ marginBottom: '10px' }}>
              <div>
                <h3 className="bento-card-title">Cross-Bank Risk Vector</h3>
                <span className="bento-card-subtitle">Multilateral topology vs Siloed baseline</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="pill-tag pill-tag-lime" style={{ fontSize: '0.68rem' }}>
                  <span className="badge-dot" style={{ position: 'static', width: '6px', height: '6px' }}></span>
                  Enclave Active
                </span>
              </div>
            </div>

            {/* Interactive SVG Radar Chart */}
            <div className="chart-container" style={{ margin: '8px 0' }}>
              <svg width="220" height="220" viewBox="0 0 220 220" style={{ overflow: 'visible' }}>
                {/* Background concentric reference rings */}
                {[0.25, 0.5, 0.75, 1.0].map((ring, i) => (
                  <circle
                    key={i}
                    cx="110"
                    cy="110"
                    r={80 * ring}
                    fill="none"
                    stroke="rgba(0, 0, 0, 0.06)"
                    strokeWidth="1"
                    strokeDasharray={ring === 1.0 ? 'none' : '3 3'}
                  />
                ))}

                {/* Radar Axis spokes */}
                {radarAxes.map((axis, i) => {
                  const angleRad = (axis.angle * Math.PI) / 180;
                  const x = 110 + 80 * Math.cos(angleRad);
                  const y = 110 + 80 * Math.sin(angleRad);
                  const isHovered = hoveredRadarAxis === axis.key;
                  return (
                    <g key={i}>
                      <line
                        x1="110"
                        y1="110"
                        x2={x}
                        y2={y}
                        stroke="rgba(0, 0, 0, 0.08)"
                        strokeWidth="1"
                      />
                      <text
                        x={110 + 96 * Math.cos(angleRad)}
                        y={110 + 96 * Math.sin(angleRad) + 4}
                        textAnchor="middle"
                        fontSize="9"
                        fontWeight={isHovered ? '800' : '600'}
                        fill={isHovered ? '#000000' : '#777777'}
                        style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                        onMouseEnter={() => setHoveredRadarAxis(axis.key)}
                        onMouseLeave={() => setHoveredRadarAxis(null)}
                      >
                        {axis.name}
                      </text>
                    </g>
                  );
                })}

                {/* C1 Siloed Polygon (Grey baseline) */}
                <polygon
                  points={c1Coords}
                  fill="rgba(0, 0, 0, 0.06)"
                  stroke="#999999"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />

                {/* C3 Mritra Enclave Polygon (Lime saturated glow) */}
                <polygon
                  points={c3Coords}
                  fill="rgba(198, 239, 78, 0.65)"
                  stroke="var(--lime)"
                  strokeWidth="2.5"
                  style={{ filter: 'drop-shadow(0 4px 10px rgba(198, 239, 78, 0.45))' }}
                />

                {/* Data Points on C3 */}
                {radarAxes.map((axis, idx) => {
                  const angleRad = (axis.angle * Math.PI) / 180;
                  const r = 80 * axis.c3;
                  const x = 110 + r * Math.cos(angleRad);
                  const y = 110 + r * Math.sin(angleRad);
                  return (
                    <circle
                      key={idx}
                      cx={x}
                      cy={y}
                      r={hoveredRadarAxis === axis.key ? 5 : 3.5}
                      fill="#000000"
                      stroke="var(--lime)"
                      strokeWidth="2"
                      style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                      onMouseEnter={() => setHoveredRadarAxis(axis.key)}
                      onMouseLeave={() => setHoveredRadarAxis(null)}
                    />
                  );
                })}
              </svg>

              {/* Chart Legend */}
              <div className="radar-legend">
                <span style={{ display: 'flex', alignItems: 'center' }}>
                  <span className="legend-dot" style={{ background: 'var(--lime)' }}></span>
                  C3 Mritra Enclave ({(currentRun.gRecovered * 100).toFixed(1)}% Coverage)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>
                  <span className="legend-dot" style={{ background: '#999999' }}></span>
                  C1 Siloed Status Quo
                </span>
              </div>
            </div>
          </div>

          {/* Card 4: Curvy Bezier Convergence Graph */}
          <div className="bento-card animate-bento bento-delay-3" style={{ flex: 1, padding: '24px' }}>
            <div className="bento-card-header">
              <div>
                <h3 className="bento-card-title">Convergence Trajectory</h3>
                <span className="bento-card-subtitle">G-metric recovery over training rounds</span>
              </div>
              <div className="selector-pill" style={{ padding: '4px 12px', fontSize: '0.72rem' }}>
                30 Rounds <ChevronDown size={12} />
              </div>
            </div>

            {/* Bezier Spline Chart Container */}
            <div style={{ position: 'relative', width: '100%', height: '170px', marginTop: '10px' }}>
              <svg width="100%" height="100%" viewBox="0 0 380 140" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                <defs>
                  <linearGradient id="splineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="var(--lime)" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="var(--lime)" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Horizontal reference grid lines */}
                <line x1="20" y1="20" x2="360" y2="20" stroke="rgba(0,0,0,0.05)" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="20" y1="60" x2="360" y2="60" stroke="rgba(0,0,0,0.05)" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="20" y1="100" x2="360" y2="100" stroke="rgba(0,0,0,0.05)" strokeWidth="1" strokeDasharray="3 3" />

                {/* Y-axis labels */}
                <text x="5" y="24" fontSize="8" fill="#aaa">95%</text>
                <text x="5" y="64" fontSize="8" fill="#aaa">85%</text>
                <text x="5" y="104" fontSize="8" fill="#aaa">75%</text>

                {/* C1 Siloed curve (low flat line) */}
                <path
                  d="M 30,110 C 110,108 200,105 350,102"
                  fill="none"
                  stroke="#cccccc"
                  strokeWidth="2"
                  strokeDasharray="4 4"
                />

                {/* C4 Oracle curve (upper bound) */}
                <path
                  d="M 30,85 C 100,50 180,30 350,18"
                  fill="none"
                  stroke="#111111"
                  strokeWidth="2"
                  strokeOpacity="0.3"
                />

                {/* Area fill under C3 spline */}
                <path
                  d="M 30,95 C 100,60 180,38 350,24 L 350,120 L 30,120 Z"
                  fill="url(#splineGradient)"
                />

                {/* C3 Mritra Spline (Smooth curving bezier) */}
                <path
                  d="M 30,95 C 100,60 180,38 350,24"
                  fill="none"
                  stroke="#000000"
                  strokeWidth="2.5"
                />

                {/* Interactive Points on C3 */}
                {[
                  { x: 30, y: 95, idx: 0 },
                  { x: 110, y: 68, idx: 1 },
                  { x: 190, y: 52, idx: 2 },
                  { x: 270, y: 38, idx: 3 },
                  { x: 350, y: 24, idx: 4 },
                ].map((pt) => {
                  const isActive = activeSplinePoint === pt.idx;
                  return (
                    <g key={pt.idx} onClick={() => setActiveSplinePoint(pt.idx)} style={{ cursor: 'pointer' }}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r={isActive ? 6 : 4}
                        fill={isActive ? 'var(--lime)' : '#ffffff'}
                        stroke="#000000"
                        strokeWidth="2.5"
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Floating Pill Tooltip */}
              <div 
                style={{ 
                  position: 'absolute', 
                  top: activeSplinePoint === 4 ? '4px' : '45px', 
                  right: activeSplinePoint === 4 ? '15px' : '40%', 
                  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)' 
                }}
              >
                <div className="chart-tooltip-pill">
                  <span className="badge-dot" style={{ position: 'static', width: '6px', height: '6px' }}></span>
                  <span>{splinePoints[activeSplinePoint].amount}</span>
                  <span style={{ color: 'var(--lime)', fontSize: '0.72rem' }}>
                    {splinePoints[activeSplinePoint].label}
                  </span>
                </div>
              </div>

              {/* X Axis dates / rounds */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 20px', marginTop: '6px', fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <span>10 Dec</span>
                <span>25 Dec</span>
                <span>1 Jan</span>
                <span>8 Jan</span>
                <span>22 Jan</span>
                <span>29 Jan</span>
              </div>
            </div>
          </div>

        </div>

        {/* ── COLUMN 3: Quick Action + Tall Lime Promo Card ──────── */}
        <div className="bento-column">
          
          {/* Card 5: Quick Quarantine Dispatch */}
          <div className="bento-card animate-bento bento-delay-3">
            <div className="bento-card-header">
              <div>
                <h3 className="bento-card-title">Quick quarantine</h3>
                <span className="bento-card-subtitle">Instant consortium freeze trigger</span>
              </div>
            </div>

            {/* Avatar circle row with + button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', overflowX: 'auto', paddingBottom: '4px' }}>
              {[
                { id: 'acct_309', label: '309', color: '#000000' },
                { id: 'acct_204', label: '204', color: '#4f46e5' },
                { id: 'acct_205', label: '205', color: '#059669' },
                { id: 'acct_101', label: '101', color: '#d97706' },
                { id: 'acct_412', label: '412', color: '#e11d48' },
              ].map((acc) => (
                <button
                  key={acc.id}
                  onClick={() => setTargetAccount(acc.id)}
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '50%',
                    background: acc.color,
                    color: '#ffffff',
                    border: targetAccount === acc.id ? '2.5px solid var(--lime)' : '2px solid transparent',
                    boxShadow: targetAccount === acc.id ? '0 0 10px rgba(198, 239, 78, 0.6)' : 'none',
                    fontSize: '0.75rem',
                    fontWeight: 800,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    transition: 'all 0.2s ease',
                  }}
                >
                  {acc.label}
                </button>
              ))}
              
              <button 
                onClick={() => onNavigateTab && onNavigateTab('chain')}
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '50%',
                  background: 'rgba(0,0,0,0.06)',
                  border: '1.5px dashed rgba(0,0,0,0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: 600,
                  flexShrink: 0,
                }}
              >
                +
              </button>
            </div>

            {/* Input field */}
            <div style={{ position: 'relative', marginBottom: '14px' }}>
              <input
                type="text"
                value={targetAccount}
                onChange={(e) => setTargetAccount(e.target.value)}
                placeholder="Target Account / Node ID"
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1.5px solid var(--border-medium)',
                  background: '#ffffff',
                  fontSize: '0.9rem',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  outline: 'none',
                  transition: 'border-color 0.2s ease',
                }}
              />
              <span className="tabular-nums" style={{ position: 'absolute', right: '12px', top: '13px', fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                $49,200.00
              </span>
            </div>

            {/* Black Send button */}
            <button 
              onClick={handleQuarantine}
              className="btn-pill-dark"
            >
              Freeze Node (Consortium)
            </button>

            {quarantineStatus && (
              <div 
                className="animate-bento"
                style={{
                  marginTop: '12px',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'rgba(52, 199, 89, 0.12)',
                  border: '1px solid rgba(52, 199, 89, 0.3)',
                  fontSize: '0.74rem',
                  color: 'var(--apple-green)',
                  fontWeight: 600,
                }}
              >
                <CheckCircle size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                {quarantineStatus}
              </div>
            )}
          </div>

          {/* Card 6: Tall Lime Spotlight */}
          <div className="bento-spotlight-card animate-bento bento-delay-4" style={{ flex: 1 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.68rem' }}>
                  THEORY OF CHANGE
                </span>
                <span style={{ fontSize: '0.72rem', fontWeight: 800 }}>PREREGISTERED §5</span>
              </div>

              <h2 className="bento-spotlight-heading">
                How to recover
                <span className="bento-spotlight-highlight">{(currentRun.gRecovered * 100).toFixed(1)}%</span>
                gap without raw PII ?
              </h2>
            </div>

            {/* Architectural Vector Illustration */}
            <div style={{ margin: '20px 0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ position: 'relative', width: '130px', height: '90px' }}>
                <svg width="130" height="90" viewBox="0 0 130 90" fill="none">
                  <ellipse cx="65" cy="70" rx="45" ry="12" fill="#000000" fillOpacity="0.12" />
                  <path
                    d="M 35,45 Q 65,15 95,45 L 85,70 Q 65,85 45,70 Z"
                    fill="none"
                    stroke="#000000"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <circle cx="65" cy="50" r="8" fill="#000000" />
                  <rect x="62" y="52" width="6" height="12" fill="#000000" rx="2" />
                  <path d="M 22,35 A 40 40 0 0 1 108,35" stroke="#000000" strokeWidth="2.5" strokeDasharray="4 4" />
                </svg>
              </div>
            </div>

            {/* Learn more white button */}
            <div>
              <button 
                onClick={() => setShowProofModal(true)}
                style={{
                  background: '#ffffff',
                  color: '#000000',
                  border: 'none',
                  padding: '12px 22px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.85rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-display)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  width: '100%',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.15)',
                  transition: 'all 0.2s ease',
                }}
              >
                Learn more <ArrowRight size={16} />
              </button>
            </div>
          </div>

        </div>

      </div>

      {/* ─── Apple Style Transaction Inspection Sheet ───────────── */}
      {inspectedTx && (
        <div className="apple-sheet-backdrop" onClick={() => setInspectedTx(null)}>
          <div className="apple-sheet animate-bento" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="pill-tag pill-tag-danger">
                  {inspectedTx.status} RISK ({(inspectedTx.riskScore * 100).toFixed(0)}%)
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {inspectedTx.id}
                </span>
              </div>
              <button 
                onClick={() => setInspectedTx(null)}
                style={{ border: 'none', background: 'rgba(0,0,0,0.06)', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontWeight: 800 }}
              >
                ✕
              </button>
            </div>

            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.025em', marginBottom: '6px' }}>
              {inspectedTx.title}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '20px' }}>
              {inspectedTx.reason}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>INTERDICTED AMOUNT</div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px' }}>
                  {inspectedTx.amount}
                </div>
              </div>
              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>TRANSACTION ROUTE</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '4px' }}>
                  {inspectedTx.bank}
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>PROOF COMMITMENT HASH</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>{inspectedTx.hash}</div>
              </div>
              <button 
                onClick={() => handleCopyHash(inspectedTx.hash)}
                style={{ padding: '6px 12px', border: 'none', background: 'var(--bg-card-solid)', color: 'var(--text-primary)', borderRadius: 'var(--radius-xs)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600 }}
              >
                {copiedTxId ? <Check size={14} color="var(--apple-green)" /> : <Copy size={14} />}
                {copiedTxId ? 'Copied' : 'Copy Hash'}
              </button>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                onClick={() => {
                  setTargetAccount('acct_309');
                  setInspectedTx(null);
                  handleQuarantine();
                }}
                className="btn-pill-dark"
                style={{ flex: 1 }}
              >
                Trigger Consortium Freeze
              </button>
              <button 
                onClick={() => {
                  setInspectedTx(null);
                  if (onNavigateTab) onNavigateTab('chain');
                }}
                className="selector-pill"
                style={{ padding: '12px 20px', fontWeight: 700 }}
              >
                Inspect in Graph &gt;
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Apple Style Formal Proof & Audit Modal ─────────────── */}
      {showProofModal && (
        <div className="apple-sheet-backdrop" onClick={() => setShowProofModal(false)}>
          <div className="apple-sheet animate-bento" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <span className="pill-tag pill-tag-lime">Mathematical Proof §5</span>
              <button 
                onClick={() => setShowProofModal(false)}
                style={{ border: 'none', background: 'rgba(0,0,0,0.06)', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontWeight: 800, color: 'var(--text-primary)' }}
              >
                ✕
              </button>
            </div>

            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.025em', marginBottom: '12px' }}>
              Zero-Knowledge Cross-Bank Parity
            </h3>

            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.6, marginBottom: '16px' }}>
              Mritra proves that confidential graph synthesis inside a hardware enclave matches centralized upper-bound oracle performance while strictly bounding leakage under (ε=1.15, δ=10⁻⁶)-Differential Privacy.
            </p>

            <div style={{ background: 'var(--bg-card-subtle)', borderRadius: 'var(--radius-md)', padding: '16px', marginBottom: '20px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
              <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>// Primary Hypothesis Metric:</div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                G = (F1_C3 - F1_C1) / (F1_C4 - F1_C1) = {currentRun.gRecovered}
              </div>
              <div style={{ color: 'var(--apple-green)', marginTop: '6px' }}>
                ✓ Gate min_gap_f1 ≥ 0.01 satisfied (p-value &lt; {currentRun.pVal})
              </div>
            </div>

            <button 
              onClick={() => {
                setShowProofModal(false);
                if (onNavigateTab) onNavigateTab('audit');
              }}
              className="btn-pill-dark"
            >
              Inspect Parity Audit Table &gt;
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
