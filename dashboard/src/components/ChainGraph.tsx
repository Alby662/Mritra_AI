import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  EyeOff, 
  RotateCcw, 
  Scissors, 
  Copy, 
  Check, 
  Sparkles
} from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { PATTERN_268_NODES, PATTERN_268_EDGES } from '../data/pattern268Data';
import type { GraphNode, GraphEdge } from '../data/pattern268Data';
import { getHeroChain } from '../api/mritraApi';
import type { HeroChainData } from '../api/mritraApi';

// Exact column coordinates aligned with the 5 institutional bank lanes (width: 840px / 5 = 168px each)
const CLEAN_COORDINATES: Record<string, { x: number; y: number }> = {
  // Lane 0: State Bank of India (SBI) - Center ~84px
  '8019C0990': { x: 84, y: 210 },
  // Lane 1: HDFC Bank - Center ~252px
  '80514DE20': { x: 252, y: 210 },
  // Lane 2: ICICI Bank - Center ~420px (generously spaced vertically)
  '80145D1D0': { x: 420, y: 65 },
  '800F24BE0': { x: 420, y: 135 },
  '8006A6CF0': { x: 420, y: 210 },
  '806E5B990': { x: 420, y: 285 },
  '80779F730': { x: 420, y: 355 },
  // Lane 3: Axis Bank - Center ~588px (generously spaced vertically)
  '800459750': { x: 588, y: 65 },
  '802FBEBC0': { x: 588, y: 135 },
  '803616220': { x: 588, y: 210 },
  '805A16080': { x: 588, y: 285 },
  '8053BE3E0': { x: 588, y: 355 },
  // Lane 4: Punjab National Bank (PNB) - Center ~756px
  '8016EFD70': { x: 756, y: 110 },
  '80381C7A0': { x: 756, y: 210 },
  '8028E8460': { x: 756, y: 310 },
};

export const ChainGraph: React.FC = () => {
  const { showToast } = useToast();
  const [mode, setMode] = useState<'C1' | 'C3'>('C3');
  const [nodes, setNodes] = useState<GraphNode[]>(PATTERN_268_NODES);
  const [edges, setEdges] = useState<GraphEdge[]>(PATTERN_268_EDGES);
  const [heroMeta, setHeroMeta] = useState<HeroChainData | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [copiedNodeId, setCopiedNodeId] = useState(false);
  const [hasMoved, setHasMoved] = useState(false);

  const svgRef = useRef<SVGSVGElement | null>(null);

  // Synchronize live hero chain from model API (/api/hero-chain)
  const syncHeroChain = useCallback(async () => {
    try {
      const heroData = await getHeroChain();
      if (heroData && heroData.transactions && heroData.transactions.length > 0) {
        setHeroMeta(heroData);

        const BANK_MAPPING: Record<number, { name: string; color: string }> = {
          0: { name: 'State Bank of India (SBI)', color: '#000000' },
          1: { name: 'HDFC Bank', color: '#4f46e5' },
          2: { name: 'ICICI Bank', color: '#059669' },
          3: { name: 'Axis Bank', color: '#d97706' },
          4: { name: 'Punjab National Bank (PNB)', color: '#ff3b30' },
        };

        // 1. Map live API transactions to graph edges
        const liveEdges: GraphEdge[] = heroData.transactions.map((tx, idx) => ({
          id: `tx_${tx.row_id || idx}`,
          from: String(tx.from_account),
          to: String(tx.to_account),
          amount: `$${Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          ts: new Date(tx.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isCrossBank: tx.from_institution !== tx.to_institution,
          c1Missed: tx.c1_missed,
          c3Caught: tx.c3_caught,
          c1Prob: tx.c1_siloed_prob,
          c3Prob: tx.c3_enclave_prob,
        }));
        setEdges(liveEdges);

        // 2. Set live nodes directly from model data with lane alignment
        if (heroData.nodes && heroData.nodes.length > 0) {
          const mappedNodes = (heroData.nodes as GraphNode[]).map(n => ({
            ...n,
            x: CLEAN_COORDINATES[n.id]?.x ?? n.x,
            y: CLEAN_COORDINATES[n.id]?.y ?? n.y,
          }));
          setNodes(mappedNodes);
        } else {
          const acctMap: Record<string, {
            id: string;
            inst: number;
            inDeg: number;
            outDeg: number;
            inAmt: number;
            outAmt: number;
            c1Scores: number[];
            c3Scores: number[];
          }> = {};

          heroData.transactions.forEach((tx) => {
            const fa = String(tx.from_account);
            const ta = String(tx.to_account);

            if (!acctMap[fa]) {
              acctMap[fa] = {
                id: fa,
                inst: tx.from_institution,
                inDeg: 0,
                outDeg: 0,
                inAmt: 0,
                outAmt: 0,
                c1Scores: [],
                c3Scores: [],
              };
            }
            acctMap[fa].outDeg += 1;
            acctMap[fa].outAmt += Number(tx.amount);
            acctMap[fa].c1Scores.push(tx.c1_siloed_prob);
            acctMap[fa].c3Scores.push(tx.c3_enclave_prob);

            if (!acctMap[ta]) {
              acctMap[ta] = {
                id: ta,
                inst: tx.to_institution,
                inDeg: 0,
                outDeg: 0,
                inAmt: 0,
                outAmt: 0,
                c1Scores: [],
                c3Scores: [],
              };
            }
            acctMap[ta].inDeg += 1;
            acctMap[ta].inAmt += Number(tx.amount);
            acctMap[ta].c1Scores.push(tx.c1_siloed_prob);
            acctMap[ta].c3Scores.push(tx.c3_enclave_prob);
          });

          const dynamicNodes: GraphNode[] = Object.values(acctMap).map((a) => {
            const bankInfo = BANK_MAPPING[a.inst] || { name: `Bank ${a.inst}`, color: '#64748b' };
            let role: 'Source' | 'Mule' | 'Destination' = 'Mule';
            let label = `Mule: ${a.id.slice(0, 5)}..`;
            if (a.inDeg === 0) {
              role = 'Source';
              label = `Src: ${a.id}`;
            } else if (a.outDeg === 0) {
              role = 'Destination';
              label = `Dest: ${a.id}`;
            }

            const pos = CLEAN_COORDINATES[a.id] || { x: 420, y: 210 };
            const totalVol = a.inAmt + a.outAmt;
            const passThrough = a.inAmt > 0 ? a.outAmt / a.inAmt : 0;
            const maxC1 = a.c1Scores.length > 0 ? Math.max(...a.c1Scores) : 0;
            const maxC3 = a.c3Scores.length > 0 ? Math.max(...a.c3Scores) : 0;

            return {
              id: a.id,
              label,
              bank: bankInfo.name,
              bankColor: bankInfo.color,
              role,
              x: pos.x,
              y: pos.y,
              c1RiskScore: maxC1,
              c3RiskScore: maxC3,
              balance: `$${totalVol.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              passThroughRatio: Math.min(Number(passThrough.toFixed(2)), 1.0),
              velocityMin: 12,
              inDegree: a.inDeg,
              outDegree: a.outDeg,
            };
          });

          setNodes(dynamicNodes);
        }
      }
    } catch (err) {
      console.warn('[ChainGraph] Model API sync fallback to preloaded Pattern 268:', err);
    }
  }, []);

  useEffect(() => {
    syncHeroChain();
  }, [syncHeroChain]);

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
    const resetNodes = PATTERN_268_NODES.map(n => ({
      ...n,
      x: CLEAN_COORDINATES[n.id]?.x ?? n.x,
      y: CLEAN_COORDINATES[n.id]?.y ?? n.y,
    }));
    setNodes(resetNodes);
    showToast('Layout Reset', 'Nodes aligned cleanly to institutional lanes', 'info');
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
      willCut ? 'Topology interdiction active: multi-bank laundering path severed' : 'Account restored to active graph topology',
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* ─── Minimal Executive Control Header ────────────────────────── */}
      <div 
        className="bento-card animate-bento" 
        style={{ 
          padding: '18px 24px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          flexWrap: 'wrap', 
          gap: '14px' 
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
            <span className="pill-tag pill-tag-danger" style={{ fontSize: '0.68rem', fontWeight: 700 }}>
              RING #268 DETECTED
            </span>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              $583,762.40 Total Tracked · {heroMeta?.num_transactions || 30} Cross-Bank Transfers
            </span>
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
            Cross-Bank Money Flow Map
          </h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px', margin: 0 }}>
            {mode === 'C3' 
              ? 'Confidential Enclave View: Exposing multi-bank laundering hops between SBI, HDFC, ICICI, Axis & PNB.'
              : 'Siloed Single-Bank View: Blind to cross-bank topology. Transfers appear as normal isolated transactions.'}
          </p>
        </div>

        {/* View Mode Toggle (Siloed vs Enclave) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div className="apple-segmented-control" style={{ padding: '3px' }}>
            <button
              onClick={() => setMode('C1')}
              className={`apple-segment-btn ${mode === 'C1' ? 'active' : ''}`}
              style={{ fontSize: '0.78rem', padding: '6px 14px' }}
              title="What individual banks see in isolation"
            >
              <EyeOff size={14} /> Siloed Bank View (Blind)
            </button>
            <button
              onClick={() => setMode('C3')}
              className={`apple-segment-btn ${mode === 'C3' ? 'active-lime' : ''}`}
              style={{ fontSize: '0.78rem', padding: '6px 14px' }}
              title="What Mritra enclave reveals across all banks"
            >
              <Sparkles size={14} /> Enclave View (Full Ring)
            </button>
          </div>

          <button
            onClick={handleResetLayout}
            className="selector-pill"
            title="Reset node positions"
            style={{ padding: '6px 12px', fontSize: '0.76rem' }}
          >
            <RotateCcw size={13} style={{ marginRight: '4px' }} />
            Reset Layout
          </button>
        </div>
      </div>

      {/* ─── Main Interactive Canvas & Sidebar ───────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedNode ? '1fr 340px' : '1fr', gap: '16px', transition: 'grid-template-columns 0.3s ease' }}>
        
        {/* SVG Physics Graph Viewport */}
        <div 
          className="bento-card animate-bento" 
          style={{ 
            padding: 0, 
            height: '460px', 
            position: 'relative', 
            overflow: 'hidden', 
            background: 'var(--bg-card-subtle)',
            border: '1px solid var(--border-subtle)'
          }}
        >
          {/* Institutional Background Zone Bands */}
          <div style={{ position: 'absolute', inset: 0, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', pointerEvents: 'none', opacity: 0.65 }}>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '10px 6px', textAlign: 'center', fontSize: '0.64rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.04em' }}>STATE BANK OF INDIA</div>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '10px 6px', textAlign: 'center', fontSize: '0.64rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.04em' }}>HDFC BANK</div>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '10px 6px', textAlign: 'center', fontSize: '0.64rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.04em' }}>ICICI BANK</div>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '10px 6px', textAlign: 'center', fontSize: '0.64rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.04em' }}>AXIS BANK</div>
            <div style={{ padding: '10px 6px', textAlign: 'center', fontSize: '0.64rem', color: 'var(--apple-red)', fontWeight: 700, letterSpacing: '0.04em' }}>PUNJAB NATIONAL BANK (PNB)</div>
          </div>

          <svg
            ref={svgRef}
            viewBox="0 0 840 420"
            style={{ width: '100%', height: '100%', cursor: draggingNodeId ? 'grabbing' : 'default', userSelect: 'none' }}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <defs>
              {/* Arrow Markers */}
              <marker id="arrow-c1" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#64748b" opacity="0.6" />
              </marker>
              <marker id="arrow-c3" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#ff3b30" />
              </marker>

              {/* Pulsating Filter for C3 Enclave Alerts */}
              <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Edge Connections */}
            {activeEdges.map(edge => {
              const from = getNodePos(edge.from);
              const to = getNodePos(edge.to);
              const isFlaggedInMode = mode === 'C3';
              const isHighlighted = selectedNode && (edge.from === selectedNode.id || edge.to === selectedNode.id);
              const isHovered = hoveredEdgeId === edge.id;

              return (
                <g 
                  key={edge.id} 
                  className="graph-edge-group"
                  onMouseEnter={() => setHoveredEdgeId(edge.id)}
                  onMouseLeave={() => setHoveredEdgeId(null)}
                >
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={isFlaggedInMode ? '#ff3b30' : '#64748b'}
                    strokeWidth={isHighlighted ? 3.5 : (isFlaggedInMode ? 2 : 1)}
                    strokeOpacity={isHighlighted ? 1 : (isFlaggedInMode ? 0.75 : 0.25)}
                    strokeDasharray={isFlaggedInMode ? 'none' : '4 3'}
                    markerEnd={isFlaggedInMode ? 'url(#arrow-c3)' : 'url(#arrow-c1)'}
                    filter={isFlaggedInMode && isHighlighted ? 'url(#glow-red)' : 'none'}
                  />

                  {/* Laser particle animation in C3 Enclave Mode */}
                  {isFlaggedInMode && (
                    <circle r={isHighlighted ? 3 : 2} fill="var(--lime, #4f46e5)">
                      <animateMotion
                        path={`M ${from.x} ${from.y} L ${to.x} ${to.y}`}
                        dur={isHighlighted ? "1.2s" : "2.2s"}
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}

                  {/* Flow Amount Badge ONLY on hover or when connected node is selected - prevents hairball! */}
                  {(isHighlighted || isHovered) && (
                    <g pointerEvents="none">
                      <rect
                        x={(from.x + to.x) / 2 - 32}
                        y={(from.y + to.y) / 2 - 14}
                        width="64"
                        height="18"
                        rx="4"
                        fill="#000000"
                        opacity="0.9"
                      />
                      <text
                        x={(from.x + to.x) / 2}
                        y={(from.y + to.y) / 2 - 2}
                        fill="var(--lime, #4f46e5)"
                        fontSize="9"
                        fontFamily="JetBrains Mono, monospace"
                        textAnchor="middle"
                        fontWeight="700"
                      >
                        {edge.amount}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(node => {
              const isSelected = selectedNode?.id === node.id;
              const isSource = node.role === 'Source';
              const isDest = node.role === 'Destination';
              const isCut = node.isCut;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onMouseDown={(e) => handleMouseDown(node.id, e)}
                  onClick={() => handleNodeClick(node)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Selection Ring */}
                  {isSelected && (
                    <circle
                      r="22"
                      fill="none"
                      stroke="var(--apple-green)"
                      strokeWidth="2.5"
                      strokeDasharray="4 2"
                      className="animate-spin"
                      style={{ animationDuration: '8s' }}
                    />
                  )}

                  {/* Node Outer Halo */}
                  <circle
                    r={isSource || isDest ? 16 : 13}
                    fill={isCut ? '#475569' : (mode === 'C3' ? '#ff3b30' : node.bankColor)}
                    opacity={isCut ? 0.3 : (mode === 'C3' ? 0.95 : 0.7)}
                    filter={mode === 'C3' && (node.c3RiskScore > 0.8) ? 'url(#glow-red)' : 'none'}
                  />

                  {/* Inner Core */}
                  <circle
                    r={isSource || isDest ? 10 : 8}
                    fill={isCut ? '#1e293b' : '#ffffff'}
                  />

                  {/* Node Label Text */}
                  <text
                    y={24}
                    fill="var(--text-primary)"
                    fontSize="9.5"
                    fontFamily="var(--font-display)"
                    textAnchor="middle"
                    fontWeight="700"
                    style={{ pointerEvents: 'none' }}
                  >
                    {node.label}
                  </text>

                  {/* Role Sub-badge */}
                  {(isSource || isDest) && (
                    <text
                      y={34}
                      fill={isSource ? 'var(--apple-green)' : '#ff9500'}
                      fontSize="7.5"
                      fontFamily="var(--font-display)"
                      textAnchor="middle"
                      fontWeight="800"
                      letterSpacing="0.05em"
                      style={{ pointerEvents: 'none' }}
                    >
                      {node.role.toUpperCase()}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Canvas Guide Footer */}
          <div style={{ position: 'absolute', bottom: '10px', left: '16px', right: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', pointerEvents: 'none' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Hover any transfer to view volume. Click account node for investigation details.
            </span>
            <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#000000' }}></span> SBI
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#4f46e5' }}></span> HDFC
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#059669' }}></span> ICICI
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#d97706' }}></span> Axis
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--apple-red)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ff3b30' }}></span> PNB
              </span>
            </div>
          </div>
        </div>

        {/* ─── Node Inspector Sidebar ──────────────────────────────── */}
        {selectedNode && (
          <div className="bento-card animate-bento" style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '14px', height: '460px', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.66rem' }}>
                ACCOUNT ATTRIBUTION
              </span>
              <button 
                onClick={() => setSelectedNode(null)} 
                className="selector-pill"
                style={{ padding: '2px 8px', fontSize: '0.7rem' }}
              >
                ✕ Close
              </button>
            </div>

            <div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 800, margin: 0 }}>
                {selectedNode.label}
              </h4>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Bank: <strong>{selectedNode.bank}</strong>
              </div>
            </div>

            {/* Risk Scores Comparison */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ padding: '12px', background: 'var(--bg-card-subtle)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  LOCAL VIEW
                </div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px', color: 'var(--text-secondary)' }}>
                  {(selectedNode.c1RiskScore * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                  Siloed Bank
                </div>
              </div>

              <div style={{ padding: '12px', background: 'rgba(198, 239, 78, 0.05)', borderRadius: '10px', border: '1px solid var(--lime-border)' }}>
                <div style={{ fontSize: '0.66rem', color: 'var(--apple-green)', fontWeight: 700 }}>
                  ENCLAVE VIEW
                </div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px', color: '#ff3b30' }}>
                  {(selectedNode.c3RiskScore * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.66rem', color: 'var(--apple-green)' }}>
                  GFP Enclave
                </div>
              </div>
            </div>

            {/* Account Metrics Table */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.76rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Tracked Flow:</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{selectedNode.balance}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pass-Through Ratio:</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{(selectedNode.passThroughRatio * 100).toFixed(1)}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Cross-Bank Transfers:</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{selectedNode.inDegree} in / {selectedNode.outDegree} out</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Status:</span>
                <span style={{ color: selectedNode.isCut ? '#ff3b30' : 'var(--apple-green)', fontWeight: 700 }}>
                  {selectedNode.isCut ? 'INTERDICTED' : 'ACTIVE IN TOPOLOGY'}
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: 'auto' }}>
              <button
                onClick={() => handleToggleGraphCut(selectedNode.id)}
                className="apple-btn-secondary"
                style={{ width: '100%', justifyContent: 'center', fontSize: '0.78rem' }}
              >
                <Scissors size={14} />
                {selectedNode.isCut ? 'Restore Node to Graph' : 'Interdict & Quarantine Node'}
              </button>

              <button
                onClick={() => handleCopyNodeHash(selectedNode.id)}
                className="apple-btn-primary"
                style={{ width: '100%', justifyContent: 'center', fontSize: '0.78rem' }}
              >
                {copiedNodeId ? <Check size={14} /> : <Copy size={14} />}
                {copiedNodeId ? 'Node Reference Copied' : 'Copy Evidence Reference'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};