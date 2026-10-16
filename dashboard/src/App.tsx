import React, { useState, useEffect, useCallback } from 'react';
import { 
  LayoutGrid, 
  Network, 
  FileText, 
  CheckCircle2, 
  Sliders, 
  Building2,
  Shield, 
  Moon, 
  Sun
} from 'lucide-react';
import { Overview } from './components/Overview';
import { ChainGraph } from './components/ChainGraph';
import { TransparencyLog } from './components/TransparencyLog';
import { Reconciliation } from './components/Reconciliation';
import { ConfigAudit } from './components/ConfigAudit';
import { EntityIntelligence } from './components/EntityIntelligence';
import { IBMHardwareModal } from './components/IBMHardwareModal';
import { getEnclaveInfo, getBankHealth } from './api/mritraApi';
import type { EnclaveInfo, BankHealth } from './api/mritraApi';

type TabType = 'overview' | 'chain' | 'tlog' | 'recon' | 'audit' | 'entity';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [enclaveInfo, setEnclaveInfo] = useState<EnclaveInfo | null>(null);
  const [bankHealth, setBankHealth] = useState<BankHealth | null>(null);

  // Synchronize system health on boot
  useEffect(() => {
    getEnclaveInfo().then((res) => {
      if (res) setEnclaveInfo(res);
    });
    getBankHealth().then((res) => {
      if (res) setBankHealth(res);
    });
  }, []);

  // Theme Initializer
  useEffect(() => {
    const saved = localStorage.getItem('mritra-theme') as 'light' | 'dark' | null;
    const prefDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = saved || (prefDark ? 'dark' : 'light');
    setTheme(initialTheme);
    document.documentElement.setAttribute('data-theme', initialTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('mritra-theme', next);
      document.documentElement.setAttribute('data-theme', next);
      return next;
    });
  }, []);

  // Keyboard Shortcuts (1-6 for tabs, T for theme)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === '1') setActiveTab('overview');
      if (e.key === '2') setActiveTab('chain');
      if (e.key === '3') setActiveTab('recon');
      if (e.key === '4') setActiveTab('tlog');
      if (e.key === '5') setActiveTab('audit');
      if (e.key === '6') setActiveTab('entity');
      if (e.key === 't' || e.key === 'T') toggleTheme();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleTheme]);

  return (
    <>
      {/* ─── Ambient Subtle Backdrop ──────────────────────────────── */}
      <div className="ambient-bg">
        <div className="ambient-blob-1"></div>
        <div className="ambient-blob-2"></div>
        <div className="ambient-blob-3"></div>
      </div>

      {/* ─── Main Outer Container ──────────────────────────────────── */}
      <div className="app-container">
        
        {/* ─── Unified Minimalist Header Bar ────────────────────────── */}
        <header className="minimal-header animate-bento">
          
          {/* Brand & Hardware Attestation */}
          <div 
            className="brand-group" 
            onClick={() => setActiveTab('overview')} 
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}
          >
            <div style={{ padding: '7px', background: '#000000', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Shield size={18} color="#c6ef4e" />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                Mritra
              </span>
              <span 
                className="pill-tag pill-tag-success" 
                style={{ fontSize: '0.62rem', padding: '2px 7px', fontWeight: 700 }}
                title={`Attestation: ${enclaveInfo?.attestation?.hardware_target || 'IBM Secure Execution on LinuxONE (s390x)'}`}
              >
                s390x Enclave
              </span>
            </div>
          </div>

          {/* Clean Segmented Tab Navigation */}
          <nav className="apple-segmented-control" style={{ padding: '3px', flexShrink: 0 }}>
            <button 
              onClick={() => setActiveTab('overview')} 
              className={`apple-segment-btn ${activeTab === 'overview' ? 'active-lime' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              <LayoutGrid size={13} /> Alerts
            </button>
            <button 
              onClick={() => setActiveTab('chain')} 
              className={`apple-segment-btn ${activeTab === 'chain' ? 'active-lime' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              <Network size={13} /> Money Flow
            </button>
            <button 
              onClick={() => setActiveTab('recon')} 
              className={`apple-segment-btn ${activeTab === 'recon' ? 'active-lime' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              <CheckCircle2 size={13} /> Settlement
            </button>
            <button 
              onClick={() => setActiveTab('tlog')} 
              className={`apple-segment-btn ${activeTab === 'tlog' ? 'active-lime' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              <FileText size={13} /> Audit Log
            </button>
            <button 
              onClick={() => setActiveTab('audit')} 
              className={`apple-segment-btn ${activeTab === 'audit' ? 'active-lime' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              <Sliders size={13} /> Compliance
            </button>
            <button 
              onClick={() => setActiveTab('entity')} 
              className={`apple-segment-btn ${activeTab === 'entity' ? 'active-lime' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
            >
              <Building2 size={13} /> Entity Intel
            </button>
          </nav>

          {/* Right Status & Appearance Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {/* Live IBM LinuxONE Hardware Coprocessor Pill */}
            <IBMHardwareModal />

            {/* Live Bank Network Status */}
            <div 
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px', 
                fontSize: '0.74rem', 
                fontWeight: 600, 
                color: 'var(--text-secondary)',
                padding: '4px 10px',
                background: 'var(--bg-card-subtle)',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--border-subtle)'
              }}
              title={`Consortium status: 5 banks connected (${bankHealth?.status === 'ok' ? 'Bank ' + bankHealth.bank_id : 'All Nodes'} Active)`}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--apple-green)', boxShadow: '0 0 6px var(--apple-green)' }}></span>
              5 Banks Online
            </div>

            {/* Dark / Light Appearance Switcher */}
            <button 
              className="icon-circle-btn" 
              onClick={toggleTheme}
              title={theme === 'light' ? "Switch to OLED Dark Mode (Key T)" : "Switch to Clean Light Mode (Key T)"}
              aria-label="Toggle Theme Appearance"
              style={{ width: '32px', height: '32px' }}
            >
              {theme === 'light' ? <Moon size={14} /> : <Sun size={14} color="var(--lime)" />}
            </button>

            {/* Clean User Avatar */}
            <div 
              className="user-avatar-img" 
              title="Joseph Mitchell · Chief AML Auditor"
              style={{ width: '30px', height: '30px', fontSize: '0.72rem', fontWeight: 700, cursor: 'default' }}
            >
              JM
            </div>
          </div>
        </header>

        {/* ─── Main Content Canvas ──────────────────────────────────── */}
        <main style={{ minHeight: '600px' }}>
          {activeTab === 'overview' && (
            <Overview 
              onNavigateTab={(tab) => setActiveTab(tab as TabType)}
            />
          )}

          {activeTab === 'chain' && (
            <ChainGraph />
          )}

          {activeTab === 'tlog' && (
            <TransparencyLog />
          )}

          {activeTab === 'recon' && (
            <Reconciliation />
          )}

          {activeTab === 'audit' && (
            <ConfigAudit />
          )}

          {activeTab === 'entity' && (
            <EntityIntelligence 
              onNavigateTab={(tab) => setActiveTab(tab as TabType)}
            />
          )}
        </main>

        {/* ─── Minimal Footnote ────────────────────────────────────── */}
        <footer style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          padding: '16px 4px 8px', 
          fontSize: '0.72rem', 
          color: 'var(--text-muted)',
          borderTop: '1px solid var(--border-subtle)',
          marginTop: '24px'
        }}>
          <div>
            <strong>Mritra AI</strong> · IBM Z Datathon 2026 · Confidential Multi-Bank AML Interception
          </div>
          <div>
            Curve25519 Encrypted · Zero-Knowledge Boundary GFP · Differential Privacy ε=1.15
          </div>
        </footer>

      </div>
    </>
  );
};

export default App;
