import React, { useState } from 'react';
import { Eye, EyeOff, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  bank: string;
  bankColor: string;
  role: 'Source' | 'Mule' | 'Destination' | 'Innocent';
  x: number;
  y: number;
  c1RiskScore: number;
  c3RiskScore: number;
}

interface Edge {
  id: string;
  from: string;
  to: string;
  amount: string;
  ts: string;
  isCrossBank: boolean;
}

export const ChainGraph: React.FC = () => {
  const [mode, setMode] = useState<'C1' | 'C3'>('C3');

  const nodes: Node[] = [
    { id: 'acct_101', label: 'Acct #101', bank: 'Bank Alpha', bankColor: '#000000', role: 'Source', x: 80, y: 170, c1RiskScore: 0.15, c3RiskScore: 0.92 },
    { id: 'acct_204', label: 'Acct #204', bank: 'Bank Beta', bankColor: '#4f46e5', role: 'Mule', x: 270, y: 90, c1RiskScore: 0.22, c3RiskScore: 0.96 },
    { id: 'acct_205', label: 'Acct #205', bank: 'Bank Beta', bankColor: '#4f46e5', role: 'Mule', x: 270, y: 250, c1RiskScore: 0.18, c3RiskScore: 0.94 },
    { id: 'acct_309', label: 'Acct #309', bank: 'Bank Gamma', bankColor: '#059669', role: 'Mule', x: 470, y: 170, c1RiskScore: 0.12, c3RiskScore: 0.98 },
    { id: 'acct_412', label: 'Acct #412', bank: 'Bank Alpha', bankColor: '#000000', role: 'Destination', x: 670, y: 170, c1RiskScore: 0.08, c3RiskScore: 0.91 },
  ];

  const edges: Edge[] = [
    { id: 'e1', from: 'acct_101', to: 'acct_204', amount: '$49,500', ts: '10:04', isCrossBank: true },
    { id: 'e2', from: 'acct_101', to: 'acct_205', amount: '$49,800', ts: '10:05', isCrossBank: true },
    { id: 'e3', from: 'acct_204', to: 'acct_309', amount: '$49,200', ts: '10:18', isCrossBank: true },
    { id: 'e4', from: 'acct_205', to: 'acct_309', amount: '$49,400', ts: '10:19', isCrossBank: true },
    { id: 'e5', from: 'acct_309', to: 'acct_412', amount: '$98,000', ts: '10:35', isCrossBank: true },
  ];

  const getNodePos = (id: string) => {
    const node = nodes.find(n => n.id === id);
    return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Control Bar */}
      <div className="bento-card animate-bento" style={{ padding: '22px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h3 className="bento-card-title">
            Laundering Ring Topology
          </h3>
          <p className="bento-card-subtitle" style={{ marginTop: '3px' }}>
            Structured cross-bank split laundering across 3 independent institutions
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Detector Scope:</span>
          <div style={{ display: 'flex', gap: '6px', background: 'rgba(0,0,0,0.06)', padding: '4px', borderRadius: 'var(--radius-full)' }}>
            <button
              onClick={() => setMode('C1')}
              className={`selector-pill ${mode === 'C1' ? 'pill-tag-dark' : ''}`}
              style={{ 
                padding: '6px 14px', 
                fontSize: '0.78rem',
                background: mode === 'C1' ? '#000000' : 'transparent',
                color: mode === 'C1' ? '#ffffff' : 'var(--text-primary)',
                border: 'none',
              }}
            >
              <EyeOff size={13} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> C1 Siloed (Blind)
            </button>
            <button
              onClick={() => setMode('C3')}
              className={`selector-pill ${mode === 'C3' ? 'pill-tag-lime' : ''}`}
              style={{ 
                padding: '6px 14px', 
                fontSize: '0.78rem',
                background: mode === 'C3' ? 'var(--lime)' : 'transparent',
                color: '#000000',
                border: 'none',
                fontWeight: 800,
              }}
            >
              <Eye size={13} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> C3 Mritra Enclave
            </button>
          </div>
        </div>
      </div>

      {/* Main Interactive Topology SVG Panel */}
      <div className="bento-card animate-bento" style={{ padding: '24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ marginBottom: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '0.8rem', fontWeight: 600 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#000000' }} /> Bank Alpha
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#4f46e5' }} /> Bank Beta
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#059669' }} /> Bank Gamma
          </span>
        </div>

        {/* SVG Graph Canvas */}
        <div style={{ width: '100%', overflowX: 'auto', background: '#ffffff', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', padding: '20px 0' }}>
          <svg width="780" height="340" viewBox="0 0 780 340" style={{ display: 'block', margin: '0 auto' }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={mode === 'C3' ? '#000000' : '#999999'} />
              </marker>
              <filter id="glow-lime" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Edges */}
            {edges.map(e => {
              const p1 = getNodePos(e.from);
              const p2 = getNodePos(e.to);
              return (
                <g key={e.id}>
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke={mode === 'C3' ? '#000000' : '#bbbbbb'}
                    strokeWidth={mode === 'C3' ? 2.5 : 1.5}
                    strokeDasharray={mode === 'C1' ? '4 4' : 'none'}
                    markerEnd="url(#arrow)"
                  />
                  <rect
                    x={(p1.x + p2.x) / 2 - 28}
                    y={(p1.y + p2.y) / 2 - 10}
                    width="56"
                    height="18"
                    rx="4"
                    fill="#f6f7f7"
                    stroke="rgba(0, 0, 0, 0.1)"
                  />
                  <text
                    x={(p1.x + p2.x) / 2}
                    y={(p1.y + p2.y) / 2 + 3}
                    textAnchor="middle"
                    fill="#000000"
                    fontSize="10"
                    fontWeight="700"
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    {e.amount}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(n => {
              const score = mode === 'C3' ? n.c3RiskScore : n.c1RiskScore;
              const isHighRisk = score >= 0.7;

              return (
                <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
                  {/* Outer Glowing Circle for Mule High Risk in C3 */}
                  {isHighRisk && (
                    <circle
                      r="27"
                      fill="none"
                      stroke="var(--lime)"
                      strokeWidth="3.5"
                      filter="url(#glow-lime)"
                      opacity="0.9"
                    />
                  )}

                  <circle
                    r="20"
                    fill={n.bankColor}
                    stroke="#ffffff"
                    strokeWidth="2.5"
                    style={{ cursor: 'pointer' }}
                  />

                  <text textAnchor="middle" y="4" fill="#ffffff" fontSize="10" fontWeight="800">
                    {n.role === 'Mule' ? 'M' : n.role === 'Source' ? 'S' : 'D'}
                  </text>

                  {/* Label */}
                  <text textAnchor="middle" y="38" fill="var(--text-primary)" fontSize="11" fontWeight="700">
                    {n.label}
                  </text>
                  <text 
                    textAnchor="middle" 
                    y="52" 
                    fill={isHighRisk ? '#dc2626' : '#888888'} 
                    fontSize="10" 
                    fontWeight="800" 
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    Risk: {(score * 100).toFixed(0)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Dynamic Mode Explanatory Card */}
        <div 
          style={{ 
            marginTop: '20px', 
            padding: '18px 22px', 
            borderRadius: 'var(--radius-md)', 
            background: mode === 'C3' ? 'rgba(198, 239, 78, 0.25)' : 'rgba(245, 158, 11, 0.12)', 
            border: mode === 'C3' ? '1.5px solid var(--lime-border)' : '1px solid rgba(245, 158, 11, 0.3)' 
          }}
        >
          {mode === 'C1' ? (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <ShieldAlert size={24} color="#d97706" />
              <div>
                <h4 style={{ color: '#b45309', fontWeight: 800, fontSize: '0.95rem' }}>
                  C1 Status Quo: Isolated Bank View (Laundering Ring Missed!)
                </h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '2px', lineHeight: 1.5 }}>
                  Bank Alpha only sees internal transactions $101 → $204 and $309 → $412. Bank Beta only sees $204 → $309. Because amounts are split under $50,000 threshold, each bank's local model computes low risk (&lt; 22%) and misses the structured fan-in/fan-out ring.
                </p>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <CheckCircle2 size={24} color="#000000" />
              <div>
                <h4 style={{ color: '#000000', fontWeight: 800, fontSize: '0.95rem' }}>
                  C3 Mritra Enclave: Cross-Bank Boundary Graph Active (Ring Caught!)
                </h4>
                <p style={{ color: '#222222', fontSize: '0.85rem', marginTop: '2px', lineHeight: 1.5 }}>
                  The confidential enclave reconciles cross-bank transactions and returns non-leaking network features (Pass-through ratio = 0.98, Temporal-cycle = 12 mins). Risk scores jump to 98% and automatically flag all 3 mule accounts without revealing raw account histories to competitors!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};