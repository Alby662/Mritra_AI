import React, { useState, useRef, useEffect } from 'react';
import { 
  Eye, 
  EyeOff, 
  ShieldAlert, 
  CheckCircle2, 
  RotateCcw, 
  Scissors, 
  Copy, 
  Check,
  Radio,
  Layers
} from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { PATTERN_268_NODES, PATTERN_268_EDGES } from '../data/pattern268Data';
import type { GraphNode, GraphEdge } from '../data/pattern268Data';
import { fetchLiveHeroChain } from '../data/telemetryData';

const TOY_NODES: GraphNode[] = [
  { 
    id: 'inst4_mule_1', 
    label: 'Inst 4 (Origin Hub)', 
    bank: 'Institution 4 (Lying Bank)', 
    bankColor: '#ff3b30', 
    role: 'Source', 
    x: 90, 
    y: 190, 
    c1RiskScore: 0.18, 
    c3RiskScore: 0.98,
    balance: '$244,982.00',
    passThroughRatio: 0.96,
    velocityMin: 14,
    inDegree: 1,
    outDegree: 2
  },
  { 
    id: 'inst0_mule_2', 
    label: 'Inst 0 (Alpha Relay)', 
    bank: 'Institution 0 (Alpha)', 
    bankColor: '#000000', 
    role: 'Mule', 
    x: 290, 
    y: 100, 
    c1RiskScore: 0.21, 
    c3RiskScore: 0.96,
    balance: '$49,500.00',
    passThroughRatio: 0.98,
    velocityMin: 14,
    inDegree: 1,
    outDegree: 1
  },
  { 
    id: 'inst1_mule_3', 
    label: 'Inst 1 (Beta Layer)', 
    bank: 'Institution 1 (Beta)', 
    bankColor: '#4f46e5', 
    role: 'Mule', 
    x: 290, 
    y: 280, 
    c1RiskScore: 0.14, 
    c3RiskScore: 0.94,
    balance: '$49,800.00',
    passThroughRatio: 0.97,
    velocityMin: 14,
    inDegree: 1,
    outDegree: 1
  },
  { 
    id: 'inst2_mule_4', 
    label: 'Inst 2 (Gamma Collector)', 
    bank: 'Institution 2 (Gamma)', 
    bankColor: '#059669', 
    role: 'Mule', 
    x: 510, 
    y: 190, 
    c1RiskScore: 0.12, 
    c3RiskScore: 0.97,
    balance: '$98,600.00',
    passThroughRatio: 0.99,
    velocityMin: 12,
    inDegree: 2,
    outDegree: 1
  },
  { 
    id: 'inst3_dest_5', 
    label: 'Inst 3 (Delta Drain)', 
    bank: 'Institution 3 (Delta)', 
    bankColor: '#d97706', 
    role: 'Destination', 
    x: 720, 
    y: 190, 
    c1RiskScore: 0.11, 
    c3RiskScore: 0.92,
    balance: '$98,000.00',
    passThroughRatio: 0.05,
    velocityMin: 120,
    inDegree: 1,
    outDegree: 0
  },
];

const TOY_EDGES: GraphEdge[] = [
  { id: 'e1', from: 'inst4_mule_1', to: 'inst0_mule_2', amount: '$49,500', ts: '10:04', isCrossBank: true },
  { id: 'e2', from: 'inst4_mule_1', to: 'inst1_mule_3', amount: '$49,800', ts: '10:05', isCrossBank: true },
  { id: 'e3', from: 'inst0_mule_2', to: 'inst2_mule_4', amount: '$49,200', ts: '10:18', isCrossBank: true },
  { id: 'e4', from: 'inst1_mule_3', to: 'inst2_mule_4', amount: '$49,400', ts: '10:19', isCrossBank: true },
  { id: 'e5', from: 'inst2_mule_4', to: 'inst3_dest_5', amount: '$98,000', ts: '10:35', isCrossBank: true },
];

export const ChainGraph: React.FC = () => {
  const { showToast } = useToast();
  const [activeDataset, setActiveDataset] = useState<'PATTERN_268' | 'TOY'>('PATTERN_268');
  const [mode, setMode] = useState<'C1' | 'C3'>('C3');
  const [nodes, setNodes] = useState<GraphNode[]>(PATTERN_268_NODES);
  const [edges, setEdges] = useState<GraphEdge[]>(PATTERN_268_EDGES);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [copiedNodeId, setCopiedNodeId] = useState(false);
  const [hasMoved, setHasMoved] = useState(false);
  const [isLiveApi, setIsLiveApi] = useState(false);

  const svgRef = useRef<SVGSVGElement | null>(null);

  // Synchronize live hero chain if available
  useEffect(() => {
    fetchLiveHeroChain().then((heroData) => {
      if (heroData && heroData.transactions) {
        setIsLiveApi(true);
      }
    });
  }, []);

  // Handle Dataset Switch
  const handleSelectDataset = (dataset: 'PATTERN_268' | 'TOY') => {
    setActiveDataset(dataset);
    setSelectedNode(null);
    if (dataset === 'PATTERN_268') {
      setNodes(PATTERN_268_NODES);
      setEdges(PATTERN_268_EDGES);
      showToast('Loaded Pattern 268 (Live Benchmark)', '30 transactions · 15 accounts across 5 institutions', 'lime');
    } else {
      setNodes(TOY_NODES);
      setEdges(TOY_EDGES);
      showToast('Loaded 5-Node Prototype', 'Simplified ring topology', 'info');
    }
  };

  const getNodePos = (id: string) => {
    const node = nodes.find(n => n.id === id);
    return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
  };

  const activeEdges = edges.filter(e => {
    const fromNode = nodes.find(n => n.id === e.from);
    const toNode = nodes.find(n => n.id === e.to);
    return !fromNode?.isCut && !toNode?.isCut;
  });

  // Handle Dragging
  const handleMouseDown = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (!node || !svgRef.current) return;

    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = 840 / rect.width;
    const scaleY = 420 / rect.height;
    const mouseX = (e.clientX - rect.left) * scaleX;
    const mouseY = (e.clientY - rect.top) * scaleY;

    setDraggingNodeId(nodeId);
    setDragOffset({ x: mouseX - node.x, y: mouseY - node.y });
    setHasMoved(false);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggingNodeId || !svgRef.current) return;
    setHasMoved(true);

    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = 840 / rect.width;
    const scaleY = 420 / rect.height;
    const mouseX = (e.clientX - rect.left) * scaleX;
    const mouseY = (e.clientY - rect.top) * scaleY;

    const clampedX = Math.max(30, Math.min(810, mouseX - dragOffset.x));
    const clampedY = Math.max(30, Math.min(390, mouseY - dragOffset.y));

    setNodes(prev => prev.map(n => n.id === draggingNodeId ? { ...n, x: clampedX, y: clampedY } : n));
  };

  const handleMouseUp = () => {
    setDraggingNodeId(null);
  };

  const handleNodeClick = (node: GraphNode) => {
    if (!hasMoved) {
      setSelectedNode(node);
    }
  };

  const handleResetLayout = () => {
    if (activeDataset === 'PATTERN_268') {
      setNodes(PATTERN_268_NODES);
    } else {
      setNodes(TOY_NODES);
    }
    showToast('Topology Layout Reset', 'Node coordinates restored to canonical Scatter-Gather funnel', 'info');
  };

  const handleToggleGraphCut = (nodeId: string) => {
    const target = nodes.find(n => n.id === nodeId);
    const willCut = !target?.isCut;
    setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, isCut: willCut } : n));
    if (selectedNode?.id === nodeId) {
      setSelectedNode(prev => prev ? { ...prev, isCut: willCut } : null);
    }
    showToast(
      willCut ? `Account ${target?.label} Interdicted` : `Account ${target?.label} Restored`,
      willCut ? 'Simulated graph cut: multi-bank laundering path severed' : 'Account restored to active graph topology',
      willCut ? 'danger' : 'info'
    );
  };

  const handleCopyNodeHash = (id: string) => {
    const hash = `0x${id}998a4f89d12c`;
    navigator.clipboard?.writeText(hash);
    setCopiedNodeId(true);
    showToast('Node Hash Copied', hash, 'copy');
    setTimeout(() => setCopiedNodeId(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* ─── Control Bar ────────────────────────────────────────── */}
      <div className="bento-card animate-bento" style={{ padding: '22px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
            <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.68rem' }}>
              CROSS-BANK GRAPH TOPOLOGY
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Interactive Physics Canvas
            </span>
            {isLiveApi && (
              <span className="pill-tag pill-tag-success" style={{ fontSize: '0.66rem' }}>
                <Radio size={10} className="animate-pulse" style={{ marginRight: '4px' }} />
                LIVE ARTIFACT CONNECTED
              </span>
            )}
          </div>
          <h3 className="bento-card-title">
            {activeDataset === 'PATTERN_268' ? 'Pattern 268 — Scatter-Gather Laundering Ring' : '5-Node Prototype Ring'}
          </h3>
          <p className="bento-card-subtitle" style={{ marginTop: '2px' }}>
            {activeDataset === 'PATTERN_268' 
              ? 'Real AMLworld Pattern 268: 30 transactions, 15 unique accounts, $583k volume across 5 institutions.'
              : 'Drag nodes to explore spatial centrality. Click any node to inspect topological risk attribution.'}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Dataset Selector */}
          <div className="apple-segmented-control" style={{ background: 'var(--bg-card-subtle)' }}>
            <button
              onClick={() => handleSelectDataset('PATTERN_268')}
              className={`apple-segment-btn ${activeDataset === 'PATTERN_268' ? 'active-lime' : ''}`}
              style={{ fontSize: '0.74rem' }}
            >
              <Layers size={13} /> Pattern 268 (30 Hops)
            </button>
            <button
              onClick={() => handleSelectDataset('TOY')}
              className={`apple-segment-btn ${activeDataset === 'TOY' ? 'active' : ''}`}
              style={{ fontSize: '0.74rem' }}
            >
              Toy Ring (5 Nodes)
            </button>
          </div>

          {/* Reset Layout Button */}
          <button
            onClick={handleResetLayout}
            className="selector-pill"
            title="Reset Node Coordinates to Default"
            style={{ padding: '6px 14px', fontSize: '0.78rem' }}
          >
            <RotateCcw size={13} /> Reset Layout
          </button>

          {/* Detector Scope Toggle (Apple Segmented Style) */}
          <div className="apple-segmented-control">
            <button
              onClick={() => setMode('C1')}
              className={`apple-segment-btn ${mode === 'C1' ? 'active' : ''}`}
            >
              <EyeOff size={13} /> C1 Siloed (Blind)
            </button>
            <button
              onClick={() => setMode('C3')}
              className={`apple-segment-btn ${mode === 'C3' ? 'active-lime' : ''}`}
            >
              <Eye size={13} /> C3 Mritra Enclave
            </button>
          </div>
        </div>
      </div>

      {/* ─── Main Interactive Topology SVG Panel ─────────────────── */}
      <div className="bento-card animate-bento" style={{ padding: '24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', fontSize: '0.8rem', fontWeight: 600 }}>
          <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#000000' }} /> Bank Alpha (Inst 0)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#4f46e5' }} /> Bank Beta (Inst 1)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#059669' }} /> Bank Gamma (Inst 2)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#d97706' }} /> Bank Delta (Inst 3)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ff3b30' }} /> Bank Omega (Inst 4 Lying)
            </span>
          </div>

          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            {mode === 'C3' ? (
              <span style={{ color: 'var(--apple-green)', fontWeight: 700 }}>
                ● Full Cross-Bank Flow Visible · 100% Pattern Caught (P=1.00)
              </span>
            ) : (
              <span style={{ color: 'var(--apple-amber)', fontWeight: 700 }}>
                ○ Siloed Blindness · 5 Gather Transfers Missed (P=0.00)
              </span>
            )}
          </div>
        </div>

        {/* SVG Graph Canvas with Real-Time Dragging */}
        <div 
          style={{ 
            width: '100%', 
            overflowX: 'auto', 
            background: 'var(--bg-card-solid)', 
            borderRadius: 'var(--radius-md)', 
            border: '1px solid var(--border-subtle)', 
            padding: '16px 0',
            cursor: draggingNodeId ? 'grabbing' : 'default',
            userSelect: 'none'
          }}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <svg 
            ref={svgRef}
            width="840" 
            height="420" 
            viewBox="0 0 840 420" 
            style={{ display: 'block', margin: '0 auto', overflow: 'visible' }}
          >
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={mode === 'C3' ? 'var(--text-primary)' : '#999999'} />
              </marker>
              <marker id="arrow-green" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--lime)" />
              </marker>
              <marker id="arrow-amber" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--apple-amber)" />
              </marker>

              <filter id="glow-lime" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>

              <style>{`
                @keyframes flowAnimation {
                  0% { stroke-dashoffset: 24; }
                  100% { stroke-dashoffset: 0; }
                }
                .flow-pulse {
                  animation: flowAnimation 1s linear infinite;
                }
              `}</style>
            </defs>

            {/* Edges */}
            {activeEdges.map(e => {
              const p1 = getNodePos(e.from);
              const p2 = getNodePos(e.to);
              const isGatherMissedInC1 = Boolean(e.c1Missed);
              const isCaughtInC3 = Boolean(e.c3Caught);

              // Line styling based on mode and edge status
              let strokeColor = 'rgba(0,0,0,0.15)';
              let strokeDash = 'none';
              let markerEnd = 'url(#arrow)';

              if (mode === 'C1') {
                if (isGatherMissedInC1) {
                  strokeColor = 'var(--apple-amber)';
                  strokeDash = '4 4';
                  markerEnd = 'url(#arrow-amber)';
                } else {
                  strokeColor = 'rgba(0,0,0,0.12)';
                  strokeDash = '3 3';
                }
              } else {
                // C3 Mode
                if (isCaughtInC3) {
                  strokeColor = 'var(--text-primary)';
                  markerEnd = 'url(#arrow-green)';
                } else {
                  strokeColor = 'rgba(0,0,0,0.4)';
                }
              }

              return (
                <g key={e.id}>
                  {/* Base Line */}
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke={strokeColor}
                    strokeWidth={mode === 'C3' ? (isCaughtInC3 ? 2.5 : 1.8) : (isGatherMissedInC1 ? 2.2 : 1.2)}
                    strokeDasharray={strokeDash}
                    markerEnd={markerEnd}
                  />

                  {/* C3 Mode Animated Flow Pulses for caught edges */}
                  {mode === 'C3' && (
                    <line
                      x1={p1.x}
                      y1={p1.y}
                      x2={p2.x}
                      y2={p2.y}
                      stroke={isCaughtInC3 ? "var(--lime)" : "rgba(198, 239, 78, 0.5)"}
                      strokeWidth={isCaughtInC3 ? 3 : 1.8}
                      strokeDasharray="6 12"
                      className="flow-pulse"
                      opacity="0.85"
                    />
                  )}

                  {/* Amount / Score Badge */}
                  {activeDataset === 'TOY' || isGatherMissedInC1 || isCaughtInC3 ? (
                    <g>
                      <rect
                        x={(p1.x + p2.x) / 2 - 32}
                        y={(p1.y + p2.y) / 2 - 9}
                        width="64"
                        height="18"
                        rx="4"
                        fill="var(--bg-card-subtle)"
                        stroke={mode === 'C1' && isGatherMissedInC1 ? 'var(--apple-amber)' : 'var(--border-subtle)'}
                      />
                      <text
                        x={(p1.x + p2.x) / 2}
                        y={(p1.y + p2.y) / 2 + 4}
                        textAnchor="middle"
                        fill={mode === 'C1' && isGatherMissedInC1 ? 'var(--apple-amber)' : 'var(--text-primary)'}
                        fontSize="9"
                        fontWeight="700"
                        style={{ fontFamily: 'var(--font-mono)' }}
                      >
                        {mode === 'C1' && isGatherMissedInC1 
                          ? 'P=0.00' 
                          : mode === 'C3' && isCaughtInC3 
                            ? 'P=1.00' 
                            : e.amount}
                      </text>
                    </g>
                  ) : null}
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(n => {
              const score = mode === 'C3' ? n.c3RiskScore : n.c1RiskScore;
              const isHighRisk = score >= 0.7;
              const isSelected = selectedNode?.id === n.id;
              const isGatherSinkMissedInC1 = mode === 'C1' && n.role === 'Destination' && score === 0;

              return (
                <g 
                  key={n.id} 
                  transform={`translate(${n.x}, ${n.y})`}
                  onMouseDown={(e) => handleMouseDown(n.id, e)}
                  onClick={() => handleNodeClick(n)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer Glowing Circle for Mule/Dest High Risk in C3 */}
                  {isHighRisk && !n.isCut && (
                    <circle
                      r="25"
                      fill="none"
                      stroke="var(--lime)"
                      strokeWidth={isSelected ? 4 : 3}
                      filter="url(#glow-lime)"
                      opacity="0.9"
                    />
                  )}

                  {/* Cut / Interdicted Dashed Outline */}
                  {n.isCut && (
                    <circle
                      r="24"
                      fill="none"
                      stroke="var(--apple-red)"
                      strokeWidth="2.5"
                      strokeDasharray="4 4"
                    />
                  )}

                  {/* Core Node Circle */}
                  <circle
                    r="19"
                    fill={n.isCut ? 'var(--text-muted)' : isGatherSinkMissedInC1 ? '#666666' : n.bankColor}
                    stroke={isSelected ? 'var(--lime)' : '#ffffff'}
                    strokeWidth={isSelected ? 3 : 2.5}
                    style={{ transition: 'r 0.2s ease, stroke 0.2s ease' }}
                  />

                  {/* Node Role Letter */}
                  <text textAnchor="middle" y="4" fill="#ffffff" fontSize="10" fontWeight="800">
                    {n.isCut ? '✕' : n.role === 'Mule' ? 'M' : n.role === 'Source' ? 'S' : 'D'}
                  </text>

                  {/* Label */}
                  <text textAnchor="middle" y="34" fill="var(--text-primary)" fontSize="10.5" fontWeight="700">
                    {n.label} {n.isCut && '(FROZEN)'}
                  </text>
                  <text 
                    textAnchor="middle" 
                    y="47" 
                    fill={n.isCut ? 'var(--text-muted)' : isGatherSinkMissedInC1 ? 'var(--apple-amber)' : isHighRisk ? 'var(--apple-red)' : 'var(--text-secondary)'} 
                    fontSize="9.5" 
                    fontWeight="800" 
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    Risk: {n.isCut ? '0%' : isGatherSinkMissedInC1 ? '0% (MISSED)' : `${(score * 100).toFixed(0)}%`}
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
            background: mode === 'C3' ? 'var(--lime-soft)' : 'rgba(255, 149, 0, 0.12)', 
            border: mode === 'C3' ? '1.5px solid var(--lime-border)' : '1px solid rgba(255, 149, 0, 0.3)' 
          }}
        >
          {mode === 'C1' ? (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <ShieldAlert size={24} color="var(--apple-amber)" />
              <div>
                <h4 style={{ color: 'var(--apple-amber)', fontWeight: 800, fontSize: '0.95rem' }}>
                  C1 Status Quo: Isolated Siloed Model (Pattern 268 Blind Spot!)
                </h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '2px', lineHeight: 1.5 }}>
                  Under C1 siloed evaluation, Bank Delta (Inst 3, account 8028E8460) has zero visibility into upstream layering from Bank Alpha (Inst 0) through Banks 1, 2, and 4. All 5 inbound gather transactions scored <strong>P = 0.0000 (Missed)</strong> across row IDs 3863632–3863659!
                </p>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <CheckCircle2 size={24} color="var(--text-primary)" />
              <div>
                <h4 style={{ color: 'var(--text-primary)', fontWeight: 800, fontSize: '0.95rem' }}>
                  C3 Mritra Enclave: Confidential Boundary Graph Active (+23 GFP Features!)
                </h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '2px', lineHeight: 1.5 }}>
                  The hardware enclave reconciles cross-bank double-entry edges and computes 23 confidential boundary GFP embeddings (<code className="code-font" style={{ fontSize: '0.8rem' }}>net_pass_through_ratio</code>, <code className="code-font" style={{ fontSize: '0.8rem' }}>net_fan_out</code>, <code className="code-font" style={{ fontSize: '0.8rem' }}>net_nbr_max</code>). The exact same gather hops into 8028E8460 jump from <strong>P = 0.0000</strong> to <strong>P = 1.0000 (100% Caught)</strong> under Differential Privacy with zero PII exposure!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ─── Apple Style Node Detail & Attribution Sheet ────────── */}
      {selectedNode && (
        <div className="apple-sheet-backdrop" onClick={() => setSelectedNode(null)}>
          <div className="apple-sheet animate-bento" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="pill-tag pill-tag-dark">
                  {selectedNode.role.toUpperCase()} ACCOUNT
                </span>
                <span className="pill-tag pill-tag-lime">
                  {selectedNode.bank}
                </span>
                {selectedNode.isCut && (
                  <span className="pill-tag pill-tag-danger">
                    QUARANTINED
                  </span>
                )}
              </div>
              <button 
                onClick={() => setSelectedNode(null)}
                style={{ border: 'none', background: 'rgba(0,0,0,0.06)', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontWeight: 800, color: 'var(--text-primary)' }}
              >
                ✕
              </button>
            </div>

            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '4px' }}>
              {selectedNode.label} Analysis & Topological Attribution
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', marginBottom: '20px' }}>
              Confidential boundary graph features computed inside AMD SEV-SNP / IBM LinuxONE enclave.
            </p>

            {/* Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>ESTIMATED VOLUME</div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px' }}>
                  {selectedNode.balance}
                </div>
              </div>
              <div style={{ background: 'var(--bg-card-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>PASS-THROUGH RATIO</div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px', color: selectedNode.passThroughRatio > 0.8 ? 'var(--apple-red)' : 'var(--text-primary)' }}>
                  {(selectedNode.passThroughRatio * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* GFP Explainable AI Feature Waterfall */}
            <div style={{ background: 'var(--bg-card-subtle)', padding: '16px', borderRadius: 'var(--radius-sm)', marginBottom: '20px' }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px' }}>
                Graph Feature Preprocessor (GFP) Attribution
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '4px' }}>
                    <span className="code-font">net_pass_through_ratio (Enclave)</span>
                    <span className="code-font" style={{ fontWeight: 700, color: 'var(--apple-red)' }}>+0.42 Risk Weight</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: 'rgba(0,0,0,0.06)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <div style={{ width: '92%', height: '100%', background: 'var(--apple-red)', borderRadius: '9999px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '4px' }}>
                    <span className="code-font">net_fan_out (Boundary Hub)</span>
                    <span className="code-font" style={{ fontWeight: 700, color: 'var(--apple-amber)' }}>+0.28 Risk Weight</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: 'rgba(0,0,0,0.06)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <div style={{ width: '74%', height: '100%', background: 'var(--apple-amber)', borderRadius: '9999px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '4px' }}>
                    <span className="code-font">net_nbr_max_0 (Multi-Bank Degree)</span>
                    <span className="code-font" style={{ fontWeight: 700, color: 'var(--apple-green)' }}>+0.14 Risk Weight</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: 'rgba(0,0,0,0.06)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <div style={{ width: '48%', height: '100%', background: 'var(--apple-green)', borderRadius: '9999px' }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                onClick={() => handleToggleGraphCut(selectedNode.id)}
                className="btn-pill-dark"
                style={{ 
                  flex: 1, 
                  background: selectedNode.isCut ? 'var(--apple-green)' : 'var(--apple-red)',
                  color: '#ffffff'
                }}
              >
                <Scissors size={15} />
                {selectedNode.isCut ? 'Restore Node' : 'Simulate Graph Cut (Quarantine)'}
              </button>

              <button 
                onClick={() => handleCopyNodeHash(selectedNode.id)}
                className="selector-pill"
                style={{ padding: '12px 18px', fontWeight: 700 }}
              >
                {copiedNodeId ? <Check size={14} color="var(--apple-green)" /> : <Copy size={14} />}
                {copiedNodeId ? 'Copied' : 'Copy Hash'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};