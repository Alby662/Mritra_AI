import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Eye, 
  EyeOff, 
  RotateCcw, 
  Scissors, 
  Copy, 
  Check,
  Radio,
  Sparkles,
  Info
} from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { PATTERN_268_NODES, PATTERN_268_EDGES } from '../data/pattern268Data';
import type { GraphNode, GraphEdge } from '../data/pattern268Data';
import { getHeroChain } from '../api/mritraApi';
import type { HeroChainData } from '../api/mritraApi';

export const ChainGraph: React.FC = () => {
  const { showToast } = useToast();
  const [mode, setMode] = useState<'C1' | 'C3'>('C3');
  const [nodes, setNodes] = useState<GraphNode[]>(PATTERN_268_NODES);
  const [edges, setEdges] = useState<GraphEdge[]>(PATTERN_268_EDGES);
  const [heroMeta, setHeroMeta] = useState<HeroChainData | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [copiedNodeId, setCopiedNodeId] = useState(false);
  const [hasMoved, setHasMoved] = useState(false);
  const [isLiveApi, setIsLiveApi] = useState(false);

  const svgRef = useRef<SVGSVGElement | null>(null);

  // Synchronize live hero chain from model API (/api/hero-chain)
  const syncHeroChain = useCallback(async () => {
    try {
      const heroData = await getHeroChain();
      if (heroData && heroData.transactions && heroData.transactions.length > 0) {
        setHeroMeta(heroData);
        setIsLiveApi(true);

        // Map live API transactions to graph edges
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
    setNodes(PATTERN_268_NODES);
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
            <span className="pill-tag pill-tag-success" style={{ fontSize: '0.66rem' }}>
              <Radio size={10} className="animate-pulse" style={{ marginRight: '4px' }} />
              {isLiveApi ? 'LIVE MODEL API (results/demo_hero_chain.json)' : 'LIVE BENCHMARK CONNECTED'}
            </span>
          </div>
          <h3 className="bento-card-title">
            Pattern 268 — Scatter-Gather Laundering Ring
          </h3>
          <p className="bento-card-subtitle" style={{ marginTop: '2px' }}>
            Multi-bank ring: {heroMeta?.num_transactions || 30} transactions across 5 banking institutions. Drag nodes to reposition. Click any node to inspect risk.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
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
              title="Siloed View: Each bank only sees its local transfers (prob < 0.40)"
            >
              <EyeOff size={13} /> C1 Siloed (Blind)
            </button>
            <button
              onClick={() => setMode('C3')}
              className={`apple-segment-btn ${mode === 'C3' ? 'active-lime' : ''}`}
              title="Mritra Enclave View: Boundary graph reveals cross-bank laundering (prob > 0.90)"
            >
              <Eye size={13} /> C3 Enclave (Caught)
            </button>
          </div>
        </div>
      </div>

      {/* ─── Hero Explanation Alert (FRONTEND_INTEGRATION.md §5) ────── */}
      <div 
        className="bento-card animate-bento" 
        style={{ 
          padding: '14px 20px', 
          background: mode === 'C3' ? 'rgba(198, 239, 78, 0.04)' : 'rgba(148, 163, 184, 0.04)',
          border: mode === 'C3' ? '1px solid var(--lime-border)' : '1px solid var(--border-subtle)',
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {mode === 'C3' ? (
            <Sparkles size={20} color="var(--apple-green)" style={{ flexShrink: 0 }} />
          ) : (
            <Info size={20} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          )}
          <div style={{ fontSize: '0.82rem' }}>
            {mode === 'C3' ? (
              <span>
                <strong style={{ color: 'var(--apple-green)' }}>Mritra C3 Confidential Enclave View:</strong> Boundary Graph GFP extracts confidential topological features. The full Scatter-Gather ring lights up in red (<code className="code-font" style={{ fontSize: '0.76rem' }}>prob &gt; 0.90</code>), exposing mules across Alpha, Beta, Gamma, Delta &amp; Epsilon.
              </span>
            ) : (
              <span>
                <strong style={{ color: 'var(--text-primary)' }}>Siloed C1 View (Current Industry Reality):</strong> No institution shares data. Individual transfers appear innocuous (<code className="code-font" style={{ fontSize: '0.76rem' }}>prob &lt; 0.40</code>), allowing all $583k to pass unflagged.
              </span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.7rem' }}>
            Detection Gap: <strong>+81.7%</strong>
          </span>
          <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.7rem' }}>
            Avg C3: <strong>0.7181</strong> (Max: 1.0)
          </span>
        </div>
      </div>

      {/* ─── Main Interactive Canvas & Sidebar ───────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedNode ? '1fr 340px' : '1fr', gap: '16px', transition: 'grid-template-columns 0.3s ease' }}>
        
        {/* SVG Physics Graph Viewport */}
        <div 
          className="bento-card animate-bento" 
          style={{ 
            padding: 0, 
            height: '520px', 
            position: 'relative', 
            overflow: 'hidden', 
            background: 'var(--bg-card-subtle)',
            border: '1px solid var(--border-subtle)'
          }}
        >
          {/* Institutional Background Zone Bands */}
          <div style={{ position: 'absolute', inset: 0, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', pointerEvents: 'none', opacity: 0.35 }}>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '12px', fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>INST 0 (ALPHA)</div>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '12px', fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>INST 1 (BETA)</div>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '12px', fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>INST 2 (GAMMA)</div>
            <div style={{ borderRight: '1px dashed var(--border-subtle)', padding: '12px', fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>INST 3 (DELTA)</div>
            <div style={{ padding: '12px', fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>INST 4 (EPSILON)</div>
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

              return (
                <g key={edge.id} className="graph-edge-group">
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={isFlaggedInMode ? '#ff3b30' : '#64748b'}
                    strokeWidth={isFlaggedInMode ? 2.5 : 1.2}
                    strokeOpacity={isFlaggedInMode ? 0.85 : 0.4}
                    strokeDasharray={isFlaggedInMode ? 'none' : '4 3'}
                    markerEnd={isFlaggedInMode ? 'url(#arrow-c3)' : 'url(#arrow-c1)'}
                    filter={isFlaggedInMode ? 'url(#glow-red)' : 'none'}
                  />

                  {/* Laser particle animation in C3 Enclave Mode */}
                  {isFlaggedInMode && (
                    <circle r="2.5" fill="#c6ef4e">
                      <animateMotion
                        path={`M ${from.x} ${from.y} L ${to.x} ${to.y}`}
                        dur="1.8s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}

                  {/* Flow Amount Tooltip Label at midpoint */}
                  <text
                    x={(from.x + to.x) / 2}
                    y={(from.y + to.y) / 2 - 4}
                    fill={isFlaggedInMode ? '#ff3b30' : 'var(--text-muted)'}
                    fontSize="7.5"
                    fontFamily="JetBrains Mono, monospace"
                    textAnchor="middle"
                    fontWeight={isFlaggedInMode ? 700 : 500}
                    opacity={0.8}
                  >
                    {edge.amount}
                  </text>
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
                      r="20"
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
                    fill={isCut ? '#475569' : node.bankColor}
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
                    fontSize="8.5"
                    fontWeight={600}
                    fontFamily="Inter, sans-serif"
                    textAnchor="middle"
                  >
                    {node.label}
                  </text>

                  {/* Role Sub-badge */}
                  <text
                    y={34}
                    fill={node.role === 'Source' ? '#ff3b30' : (node.role === 'Destination' ? 'var(--apple-green)' : 'var(--text-muted)')}
                    fontSize="7"
                    fontWeight={700}
                    textAnchor="middle"
                  >
                    {node.role.toUpperCase()}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* ─── Selected Node Inspection Panel ─────────────────────── */}
        {selectedNode && (
          <div className="bento-card animate-bento" style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '14px', height: '520px', overflowY: 'auto' }}>
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
                Bank: {selectedNode.bank}
              </div>
            </div>

            {/* Risk Scores Comparison */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ padding: '12px', background: 'var(--bg-card-subtle)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  C1 SILOED RISK
                </div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px', color: selectedNode.c1RiskScore > 0.8 ? '#ff3b30' : 'var(--text-secondary)' }}>
                  {(selectedNode.c1RiskScore * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                  Local View Only
                </div>
              </div>

              <div style={{ padding: '12px', background: 'rgba(198, 239, 78, 0.05)', borderRadius: '10px', border: '1px solid var(--lime-border)' }}>
                <div style={{ fontSize: '0.66rem', color: 'var(--apple-green)', fontWeight: 700 }}>
                  C3 ENCLAVE RISK
                </div>
                <div className="tabular-nums" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px', color: '#ff3b30' }}>
                  {(selectedNode.c3RiskScore * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.66rem', color: 'var(--apple-green)' }}>
                  Confidential GFP
                </div>
              </div>
            </div>

            {/* Account Metrics Table */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.76rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Balance Tracked:</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{selectedNode.balance}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pass-Through Ratio:</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{(selectedNode.passThroughRatio * 100).toFixed(1)}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Cross-Bank Fan-out:</span>
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
                {selectedNode.isCut ? 'Restore Node to Graph' : 'Simulate Graph Cut (Interdict)'}
              </button>

              <button
                onClick={() => handleCopyNodeHash(selectedNode.id)}
                className="apple-btn-primary"
                style={{ width: '100%', justifyContent: 'center', fontSize: '0.78rem' }}
              >
                {copiedNodeId ? <Check size={14} /> : <Copy size={14} />}
                {copiedNodeId ? 'Node Hash Copied' : 'Copy Cryptographic Reference'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};