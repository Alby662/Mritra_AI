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
    { id: 'acct_101', label: 'Acct #101', bank: 'Bank Alpha (Inst 0)', bankColor: '#38bdf8', role: 'Source', x: 80, y: 180, c1RiskScore: 0.15, c3RiskScore: 0.92 },
    { id: 'acct_204', label: 'Acct #204 (Mule 1)', bank: 'Bank Beta (Inst 1)', bankColor: '#a78bfa', role: 'Mule', x: 280, y: 100, c1RiskScore: 0.22, c3RiskScore: 0.96 },
    { id: 'acct_205', label: 'Acct #205 (Mule 2)', bank: 'Bank Beta (Inst 1)', bankColor: '#a78bfa', role: 'Mule', x: 280, y: 260, c1RiskScore: 0.18, c3RiskScore: 0.94 },
    { id: 'acct_309', label: 'Acct #309 (Hub)', bank: 'Bank Gamma (Inst 2)', bankColor: '#f43f5e', role: 'Mule', x: 480, y: 180, c1RiskScore: 0.12, c3RiskScore: 0.98 },
    { id: 'acct_412', label: 'Acct #412', bank: 'Bank Alpha (Inst 0)', bankColor: '#38bdf8', role: 'Destination', x: 680, y: 180, c1RiskScore: 0.08, c3RiskScore: 0.91 },
  ];

  const edges: Edge[] = [
    { id: 'e1', from: 'acct_101', to: 'acct_204', amount: '$49,500', ts: '10:04:12', isCrossBank: true },
    { id: 'e2', from: 'acct_101', to: 'acct_205', amount: '$49,800', ts: '10:05:30', isCrossBank: true },
    { id: 'e3', from: 'acct_204', to: 'acct_309', amount: '$49,200', ts: '10:18:00', isCrossBank: true },
    { id: 'e4', from: 'acct_205', to: 'acct_309', amount: '$49,400', ts: '10:19:15', isCrossBank: true },
    { id: 'e5', from: 'acct_309', to: 'acct_412', amount: '$98,000', ts: '10:35:40', isCrossBank: true },
  ];

  const getNodePos = (id: string) => {
    const node = nodes.find(n => n.id === id);
    return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Control Bar */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            Cross-Bank Money Mule Ring Topology
          </h3>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '2px' }}>
            Interactive topology rendering split-laundering across 3 financial institutions.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 500 }}>Detector View:</span>
          <div style={{ display: 'flex', gap: '4px', background: 'rgba(15, 23, 42, 0.8)', padding: '4px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <button
              onClick={() => setMode('C1')}
              className={`tab-btn ${mode === 'C1' ? 'active' : ''}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            >
              <EyeOff size={14} /> C1 (Siloed Bank View)
            </button>
            <button
              onClick={() => setMode('C3')}
              className={`tab-btn ${mode === 'C3' ? 'active' : ''}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            >
              <Eye size={14} /> C3 (Mritra Enclave View)
            </button>
          </div>
        </div>
      </div>

      {/* Main Interactive Topology SVG Panel */}
      <div className="glass-panel" style={{ padding: '24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ marginBottom: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '0.8rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#38bdf8' }} /> Bank Alpha (Inst 0)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#a78bfa' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#a78bfa' }} /> Bank Beta (Inst 1)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f43f5e' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f43f5e' }} /> Bank Gamma (Inst 2)
          </span>
        </div>

        {/* SVG Graph Canvas */}
        <div style={{ width: '100%', overflowX: 'auto', background: 'rgba(10, 15, 30, 0.6)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)', padding: '20px 0' }}>
          <svg width="780" height="340" viewBox="0 0 780 340" style={{ display: 'block', margin: '0 auto' }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={mode === 'C3' ? '#f43f5e' : '#64748b'} />
              </marker>
              <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="6" result="blur" />
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
                    stroke={mode === 'C3' ? 'rgba(244, 63, 94, 0.7)' : 'rgba(100, 116, 139, 0.4)'}
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
                    fill="rgba(15, 23, 42, 0.95)"
                    stroke="rgba(255, 255, 255, 0.1)"
                  />
                  <text
                    x={(p1.x + p2.x) / 2}
                    y={(p1.y + p2.y) / 2 + 3}
                    textAnchor="middle"
                    fill={mode === 'C3' ? '#fda4af' : '#94a3b8'}
                    fontSize="10"
                    fontWeight="600"
                    className="code-font"
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
                      r="26"
                      fill="none"
                      stroke="#f43f5e"
                      strokeWidth="2.5"
                      filter="url(#glow-red)"
                      opacity="0.8"
                    />
                  )}

                  <circle
                    r="20"
                    fill={n.bankColor}
                    stroke="#ffffff"
                    strokeWidth="2"
                    style={{ cursor: 'pointer' }}
                  />

                  <text textAnchor="middle" y="4" fill="#0f172a" fontSize="10" fontWeight="800">
                    {n.role === 'Mule' ? 'M' : n.role === 'Source' ? 'S' : 'D'}
                  </text>

                  {/* Label */}
                  <text textAnchor="middle" y="38" fill="#f8fafc" fontSize="11" fontWeight="600">
                    {n.label}
                  </text>
                  <text textAnchor="middle" y="52" fill={isHighRisk ? '#f43f5e' : '#94a3b8'} fontSize="10" fontWeight="700" className="code-font">
                    Risk: {(score * 100).toFixed(0)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Dynamic Mode Explanatory Card */}
        <div style={{ marginTop: '20px', padding: '16px', borderRadius: '12px', background: mode === 'C3' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', border: mode === 'C3' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)' }}>
          {mode === 'C1' ? (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <ShieldAlert size={24} color="#f59e0b" />
              <div>
                <h4 style={{ color: '#fbbf24', fontWeight: 700, fontSize: '0.95rem' }}>
                  C1 Status Quo: Isolated Bank View (Laundering Ring Missed!)
                </h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', marginTop: '2px' }}>
                  Bank Alpha only sees internal transactions $101 \rightarrow 204$ and $309 \rightarrow 412$. Bank Beta only sees $204 \rightarrow 309$. Because amounts are split under \$50,000 threshold, each bank's local model computes low risk (&lt; 22%) and misses the structured fan-in/fan-out ring.
                </p>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <CheckCircle2 size={24} color="#10b981" />
              <div>
                <h4 style={{ color: '#34d399', fontWeight: 700, fontSize: '0.95rem' }}>
                  C3 Mritra Enclave: Cross-Bank Boundary Graph Active (Ring Caught!)
                </h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', marginTop: '2px' }}>
                  The confidential enclave reconciles cross-bank transactions and returns non-leaking network features (Pass-through ratio = 0.98, Temporal-cycle = 12 mins). Risk scores jump to 96% and automatically flag all 3 mule accounts without revealing raw account histories to competitors!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
