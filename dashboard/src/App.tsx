import { useState } from 'react';
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
  Shield
} from 'lucide-react';
import { Overview } from './components/Overview';
import { ChainGraph } from './components/ChainGraph';
import { TransparencyLog } from './components/TransparencyLog';
import { Reconciliation } from './components/Reconciliation';
import { ConfigAudit } from './components/ConfigAudit';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'chain' | 'tlog' | 'recon' | 'audit'>('overview');
  const [selectedPartition, setSelectedPartition] = useState<'P1' | 'P2'>('P1');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 800);
  };

  return (
    <>
      {/* ─── Ambient Organic Backdrop ─────────────────────────────── */}
      <div className="ambient-bg">
        <div className="ambient-blob-1"></div>
        <div className="ambient-blob-2"></div>
        <div className="ambient-blob-3"></div>
      </div>

      {/* ─── Main Outer Container ─────────────────────────────────── */}
      <div className="app-container">
        
        {/* ─── Left Slim Obsidian Sidebar ─────────────────────────── */}
        <aside className="nav-sidebar">
          {/* Brand Mark */}
          <button 
            className="nav-logo-btn" 
            title="Mritra AI Engine"
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
              <span className="nav-tooltip">Dashboard Bento</span>
            </button>

            {/* Topology Graph */}
            <button
              onClick={() => setActiveTab('chain')}
              className={`nav-icon-btn ${activeTab === 'chain' ? 'active' : ''}`}
              aria-label="Topology Graph"
            >
              <Network size={20} />
              <span className="nav-tooltip">Laundering Topology</span>
            </button>

            {/* Transparency Log */}
            <button
              onClick={() => setActiveTab('tlog')}
              className={`nav-icon-btn ${activeTab === 'tlog' ? 'active' : ''}`}
              aria-label="Transparency Log"
            >
              <FileText size={20} />
              <span className="nav-tooltip">Transparency Log</span>
            </button>

            {/* Double-Entry Audit */}
            <button
              onClick={() => setActiveTab('recon')}
              className={`nav-icon-btn ${activeTab === 'recon' ? 'active' : ''}`}
              aria-label="Double-Entry Audit"
            >
              <CheckCircle2 size={20} />
              <span className="nav-tooltip">Reconciliation Audit</span>
            </button>

            {/* Parity Audit */}
            <button
              onClick={() => setActiveTab('audit')}
              className={`nav-icon-btn ${activeTab === 'audit' ? 'active' : ''}`}
              aria-label="Parity & Tests"
            >
              <Sliders size={20} />
              <span className="nav-tooltip">Parity Audit §5</span>
            </button>
          </div>

          {/* Bottom Nav Icons */}
          <div className="nav-icon-group">
            <button 
              className="nav-icon-btn" 
              onClick={() => setActiveTab('audit')}
              aria-label="System Documentation"
            >
              <HelpCircle size={19} />
              <span className="nav-tooltip">Documentation</span>
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
                {selectedPartition === 'P1' ? 'Partition P1 (Volume Balanced)' : 'Partition P2 (Random Partitions)'}
              </span>
            </div>

            {/* Actions & Filters matching inspiration */}
            <div className="header-actions">
              {/* Partition / Filter Dropdown Pill */}
              <button 
                className="selector-pill"
                onClick={() => setSelectedPartition(p => p === 'P1' ? 'P2' : 'P1')}
              >
                <span>Financial · {selectedPartition}</span>
                <ChevronDown size={14} style={{ opacity: 0.6 }} />
              </button>

              {/* Refresh Button */}
              <button 
                className="icon-circle-btn" 
                onClick={handleRefresh}
                title="Refresh Live Enclave Stream"
              >
                <RotateCcw 
                  size={16} 
                  style={{ 
                    transition: 'transform 0.6s ease',
                    transform: isRefreshing ? 'rotate(360deg)' : 'none'
                  }} 
                />
              </button>

              {/* Notifications Bell */}
              <button className="icon-circle-btn" title="3 Critical Alerts">
                <Bell size={16} />
                <span className="badge-dot"></span>
              </button>

              {/* User Profile Capsule (Joseph Mitchell / Chief AML Officer) */}
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
                  <span className="user-role">Lead AML Auditor</span>
                </div>
              </div>
            </div>
          </header>

          {/* ─── Secondary View Switcher Tabs ─────────────────────── */}
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '2px' }}>
            <button 
              onClick={() => setActiveTab('overview')} 
              className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            >
              <LayoutGrid size={15} /> Executive Bento
            </button>
            <button 
              onClick={() => setActiveTab('chain')} 
              className={`tab-btn ${activeTab === 'chain' ? 'active' : ''}`}
            >
              <Network size={15} /> Ring Topology
            </button>
            <button 
              onClick={() => setActiveTab('tlog')} 
              className={`tab-btn ${activeTab === 'tlog' ? 'active' : ''}`}
            >
              <FileText size={15} /> Merkle Log
            </button>
            <button 
              onClick={() => setActiveTab('recon')} 
              className={`tab-btn ${activeTab === 'recon' ? 'active' : ''}`}
            >
              <CheckCircle2 size={15} /> Double-Entry Audit
            </button>
            <button 
              onClick={() => setActiveTab('audit')} 
              className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
            >
              <Sliders size={15} /> Pre-reg Parity (§5)
            </button>
          </div>

          {/* ─── Main Viewport Component ───────────────────────────── */}
          <main style={{ flex: 1 }}>
            {activeTab === 'overview' && <Overview onNavigateTab={(t: string) => setActiveTab(t as any)} />}
            {activeTab === 'chain' && <ChainGraph />}
            {activeTab === 'tlog' && <TransparencyLog />}
            {activeTab === 'recon' && <Reconciliation />}
            {activeTab === 'audit' && <ConfigAudit />}
          </main>

          {/* ─── Sub-footer Telemetry Bar ──────────────────────────── */}
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
