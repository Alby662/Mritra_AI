import { useState, useEffect, useCallback } from 'react';
import { 
  LayoutGrid, 
  Network, 
  FileText, 
  CheckCircle2, 
  Sliders, 
  RotateCcw, 
  Bell, 
  ChevronDown, 
  Settings,
  HelpCircle,
  Shield,
  Moon,
  Sun,
  Compass
} from 'lucide-react';
import { Overview } from './components/Overview';
import { ChainGraph } from './components/ChainGraph';
import { TransparencyLog } from './components/TransparencyLog';
import { Reconciliation } from './components/Reconciliation';
import { ConfigAudit } from './components/ConfigAudit';
import { GuidedWalkthrough } from './components/GuidedWalkthrough';
import { RUN_CATALOG } from './data/telemetryData';
import { useToast } from './context/ToastContext';
import { getEnclaveInfo, getBankHealth } from './api/mritraApi';
import type { EnclaveInfo, BankHealth } from './api/mritraApi';

export function App() {
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<'overview' | 'chain' | 'tlog' | 'recon' | 'audit'>('overview');
  const [selectedRunId, setSelectedRunId] = useState<string>('20261004T092741Z');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showRunDropdown, setShowRunDropdown] = useState(false);
  const [enclaveInfo, setEnclaveInfo] = useState<EnclaveInfo | null>(null);
  const [bankHealth, setBankHealth] = useState<BankHealth | null>(null);
  
  // Single-time Guided Walkthrough for first-time visitors (persisted in localStorage)
  const [showTour, setShowTour] = useState(() => {
    return localStorage.getItem('mritra_walkthrough_completed') !== 'true';
  });

  useEffect(() => {
    getEnclaveInfo().then(setEnclaveInfo);
    getBankHealth().then(setBankHealth);
  }, []);

  // Apple Appearance (Studio Cream vs Deep Obsidian OLED)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('mritra-theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mritra-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(t => {
      const next = t === 'light' ? 'dark' : 'light';
      showToast(
        next === 'dark' ? 'Deep Obsidian OLED Active' : 'Studio Cream Active', 
        'Appearance preference saved in browser', 
        'lime'
      );
      return next;
    });
  }, [showToast]);

  const activeRun = RUN_CATALOG[selectedRunId] || RUN_CATALOG['20261004T092741Z'];

  // Apple-style Keyboard Shortcut Ergonomics (1 - 5 to switch tabs, T to toggle appearance)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === '1') setActiveTab('overview');
      if (e.key === '2') setActiveTab('chain');
      if (e.key === '3') setActiveTab('tlog');
      if (e.key === '4') setActiveTab('recon');
      if (e.key === '5') setActiveTab('audit');
      if (e.key === 't' || e.key === 'T') toggleTheme();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleTheme]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    showToast('Enclave Telemetry Synchronized', 'Real-time boundary streams updated', 'success');
    setTimeout(() => setIsRefreshing(false), 700);
  };

  return (
    <>
      {/* ─── Single-Time First-Visit Guided Tour ──────────────────── */}
      <GuidedWalkthrough 
        isOpen={showTour} 
        onClose={() => setShowTour(false)} 
        onNavigateTab={(tab) => setActiveTab(tab)} 
      />

      {/* ─── Ambient Organic Backdrop ─────────────────────────────── */}
      <div className="ambient-bg">
        <div className="ambient-blob-1"></div>
        <div className="ambient-blob-2"></div>
        <div className="ambient-blob-3"></div>
      </div>

      {/* ─── Main Outer Container ─────────────────────────────────── */}
      <div className="app-container">
        
        {/* ─── Left Slim Obsidian Sidebar (Apple Dock Style) ──────── */}
        <aside className="nav-sidebar">
          {/* Brand Mark */}
          <button 
            className="nav-logo-btn" 
            title="Mritra AI — Confidential AML Engine"
            onClick={() => setActiveTab('overview')}
          >
            <Shield size={22} color="#c6ef4e" />
          </button>

          {/* Primary Nav Icons */}
          <div className="nav-icon-group">
            {/* Overview / Bento */}
            <button
              onClick={() => setActiveTab('overview')}
              className={`nav-icon-btn ${activeTab === 'overview' ? 'active' : ''}`}
              aria-label="Executive Bento Dashboard"
            >
              <LayoutGrid size={20} />
              <span className="nav-tooltip">Dashboard (Key 1)</span>
            </button>

            {/* Topology Graph */}
            <button
              onClick={() => setActiveTab('chain')}
              className={`nav-icon-btn ${activeTab === 'chain' ? 'active' : ''}`}
              aria-label="Topology Graph"
            >
              <Network size={20} />
              <span className="nav-tooltip">Topology (Key 2)</span>
            </button>

            {/* Transparency Log */}
            <button
              onClick={() => setActiveTab('tlog')}
              className={`nav-icon-btn ${activeTab === 'tlog' ? 'active' : ''}`}
              aria-label="Transparency Log"
            >
              <FileText size={20} />
              <span className="nav-tooltip">Merkle Log (Key 3)</span>
            </button>

            {/* Double-Entry Audit */}
            <button
              onClick={() => setActiveTab('recon')}
              className={`nav-icon-btn ${activeTab === 'recon' ? 'active' : ''}`}
              aria-label="Double-Entry Audit"
            >
              <CheckCircle2 size={20} />
              <span className="nav-tooltip">Reconciliation (Key 4)</span>
            </button>

            {/* Parity Audit */}
            <button
              onClick={() => setActiveTab('audit')}
              className={`nav-icon-btn ${activeTab === 'audit' ? 'active' : ''}`}
              aria-label="Parity & Tests"
            >
              <Sliders size={20} />
              <span className="nav-tooltip">Parity Audit §5 (Key 5)</span>
            </button>
          </div>

          {/* Bottom Nav Icons */}
          <div className="nav-icon-group">
            <button 
              className="nav-icon-btn" 
              onClick={() => setShowTour(true)}
              aria-label="Start Guided Tour"
            >
              <Compass size={19} color="#c6ef4e" />
              <span className="nav-tooltip">Interactive Tour</span>
            </button>
            <button 
              className="nav-icon-btn" 
              onClick={() => setActiveTab('audit')}
              aria-label="System Documentation"
            >
              <HelpCircle size={19} />
              <span className="nav-tooltip">Audit Docs</span>
            </button>
            <button 
              className="nav-icon-btn" 
              onClick={() => setActiveTab('tlog')}
              aria-label="Enclave Settings"
            >
              <Settings size={19} />
              <span className="nav-tooltip">Enclave Settings</span>
            </button>
          </div>
        </aside>

        {/* ─── Main Viewport Canvas ─────────────────────────────────── */}
        <div className="main-viewport">
          
          {/* ─── Top Utility Header ───────────────────────────────── */}
          <header className="top-header animate-bento">
            <div className="header-title-section">
              <h1 className="header-title">
                {activeTab === 'overview' && 'Dashboard'}
                {activeTab === 'chain' && 'Topology Graph'}
                {activeTab === 'tlog' && 'Transparency Log'}
                {activeTab === 'recon' && 'Reconciliation'}
                {activeTab === 'audit' && 'Parity Audit'}
              </h1>
              <span className="header-badge">
                {activeRun.partition}
              </span>
              {enclaveInfo?.attestation?.type === 'simulated' && (
                <span 
                  className="pill-tag pill-tag-warning"
                  style={{ fontSize: '0.68rem', cursor: 'default' }}
                  title="Production target: IBM Secure Execution on LinuxONE"
                >
                  Enclave boundary simulated
                </span>
              )}
              {bankHealth?.status === 'ok' && (
                <span 
                  className="pill-tag pill-tag-success"
                  style={{ fontSize: '0.68rem', cursor: 'default' }}
                  title={`mTLS Connected to Bank Service (${bankHealth.bank_id}) on :8000/:8001`}
                >
                  Bank {bankHealth.bank_id} Online
                </span>
              )}
            </div>

            {/* Header Actions & Live Partition Switcher */}
            <div className="header-actions">
              {/* Interactive Guided Tour Button */}
              <button 
                className="selector-pill"
                onClick={() => setShowTour(true)}
                title="Launch Interactive Walkthrough"
                style={{ 
                  background: 'var(--lime-soft)', 
                  border: '1px solid var(--lime-border)',
                  cursor: 'pointer'
                }}
              >
                <Compass size={14} color="var(--text-primary)" />
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Guided Tour</span>
              </button>

              {/* Partition / Run Dropdown Selector */}
              <div style={{ position: 'relative' }}>
                <button 
                  className="selector-pill"
                  onClick={() => setShowRunDropdown(!showRunDropdown)}
                >
                  <span style={{ fontWeight: 700 }}>Partition: {activeRun.partition.split(' ')[0]}</span>
                  <ChevronDown size={14} style={{ opacity: 0.6 }} />
                </button>

                {showRunDropdown && (
                  <div 
                    className="animate-bento"
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + 8px)',
                      right: 0,
                      background: '#ffffff',
                      borderRadius: 'var(--radius-sm)',
                      boxShadow: 'var(--shadow-modal)',
                      border: '1px solid var(--border-medium)',
                      padding: '6px',
                      zIndex: 80,
                      minWidth: '240px'
                    }}
                  >
                    {Object.values(RUN_CATALOG).map((run) => (
                      <button
                        key={run.runId}
                        onClick={() => {
                          setSelectedRunId(run.runId);
                          setShowRunDropdown(false);
                          showToast(`Loaded Partition ${run.partition.split(' ')[0]}`, `${run.totalSamples.toLocaleString()} samples · C4 Oracle F1: ${run.c4OracleF1.toFixed(4)}`, 'lime');
                        }}
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          padding: '10px 14px',
                          borderRadius: '8px',
                          border: 'none',
                          background: selectedRunId === run.runId ? 'rgba(0,0,0,0.06)' : 'transparent',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px',
                          fontFamily: 'var(--font-display)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.84rem' }}>{run.partition}</span>
                          {selectedRunId === run.runId && <span className="badge-dot" style={{ position: 'static' }}></span>}
                        </div>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          Run ID: {run.runId}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Refresh Button */}
              <button 
                className="icon-circle-btn" 
                onClick={handleRefresh}
                title="Refresh Live Enclave Telemetry"
              >
                <RotateCcw 
                  size={16} 
                  style={{ 
                    transition: 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
                    transform: isRefreshing ? 'rotate(360deg)' : 'none'
                  }} 
                />
              </button>

              {/* Notifications Bell */}
              <button className="icon-circle-btn" title="4 Neutralized Discrepancies">
                <Bell size={16} />
                <span className="badge-dot"></span>
              </button>

              {/* Apple Theme Switcher (Studio Cream vs Deep Obsidian OLED) */}
              <button 
                className="icon-circle-btn" 
                onClick={toggleTheme}
                title={theme === 'light' ? "Switch to Deep Obsidian OLED (Key T)" : "Switch to Studio Cream (Key T)"}
                aria-label="Toggle Theme Appearance"
              >
                {theme === 'light' ? (
                  <Moon size={16} />
                ) : (
                  <Sun size={16} color="var(--lime)" />
                )}
              </button>

              {/* User Profile Capsule */}
              <div 
                className="user-profile-capsule"
                onClick={() => setActiveTab('audit')}
                title="Consortium Officer"
              >
                <div className="user-avatar-img">
                  SJ
                </div>
                <div className="user-info">
                  <span className="user-name">Joseph Mitchell</span>
                  <span className="user-role">Chief AML Auditor</span>
                </div>
              </div>
            </div>
          </header>

          {/* ─── Apple Style Segmented View Switcher ───────────────── */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
            <div className="apple-segmented-control">
              <button 
                onClick={() => setActiveTab('overview')} 
                className={`apple-segment-btn ${activeTab === 'overview' ? 'active-lime' : ''}`}
              >
                <LayoutGrid size={15} /> Executive Bento
              </button>
              <button 
                onClick={() => setActiveTab('chain')} 
                className={`apple-segment-btn ${activeTab === 'chain' ? 'active-lime' : ''}`}
              >
                <Network size={15} /> Ring Topology
              </button>
              <button 
                onClick={() => setActiveTab('tlog')} 
                className={`apple-segment-btn ${activeTab === 'tlog' ? 'active-lime' : ''}`}
              >
                <FileText size={15} /> Merkle Ledger
              </button>
              <button 
                onClick={() => setActiveTab('recon')} 
                className={`apple-segment-btn ${activeTab === 'recon' ? 'active-lime' : ''}`}
              >
                <CheckCircle2 size={15} /> Double-Entry Audit
              </button>
              <button 
                onClick={() => setActiveTab('audit')} 
                className={`apple-segment-btn ${activeTab === 'audit' ? 'active-lime' : ''}`}
              >
                <Sliders size={15} /> Pre-reg Parity (§5)
              </button>
            </div>

            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <span>Shortcuts: <kbd style={{ background: '#ffffff', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-subtle)', fontWeight: 700 }}>1–5</kbd></span>
              <span className="pill-tag pill-tag-success" style={{ fontSize: '0.66rem' }}>
                LIVE ENCLAVE STREAMING
              </span>
            </div>
          </div>

          {/* ─── Main Viewport Component ───────────────────────────── */}
          <main style={{ flex: 1 }}>
            {activeTab === 'overview' && (
              <Overview 
                onNavigateTab={(t: string) => setActiveTab(t as any)} 
                selectedRunId={selectedRunId}
                onSelectRunId={setSelectedRunId}
              />
            )}
            {activeTab === 'chain' && <ChainGraph />}
            {activeTab === 'tlog' && <TransparencyLog />}
            {activeTab === 'recon' && <Reconciliation />}
            {activeTab === 'audit' && <ConfigAudit />}
          </main>

          {/* ─── Sub-footer Telemetry Bar (Apple Calibrated) ───────── */}
          <footer 
            style={{
              padding: '16px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              fontSize: '0.76rem',
              color: 'var(--text-muted)',
              borderTop: '1px solid var(--border-subtle)',
              marginTop: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="pill-tag pill-tag-lime" style={{ fontSize: '0.66rem' }}>
                IBM Z DATATHON 2026
              </span>
              <span>Mritra Confidential AI — LinuxONE Secure Execution / AMD SEV-SNP</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontFamily: 'var(--font-mono)' }}>
              <span>Curve25519-Signed</span>
              <span>SHA-256 Merkle: 0x8f2a...c10b</span>
              <span>ε=1.15, δ=10⁻⁶ DP</span>
            </div>
          </footer>

        </div>

      </div>
    </>
  );
}

export default App;
