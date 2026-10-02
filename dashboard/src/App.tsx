import { useState } from 'react';
import { Shield, TrendingUp, Network, FileText, CheckCircle, Sliders, Server } from 'lucide-react';
import { Overview } from './components/Overview';
import { ChainGraph } from './components/ChainGraph';
import { TransparencyLog } from './components/TransparencyLog';
import { Reconciliation } from './components/Reconciliation';
import { ConfigAudit } from './components/ConfigAudit';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'chain' | 'tlog' | 'recon' | 'audit'>('overview');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Header */}
      <header
        style={{
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(11, 15, 25, 0.8)',
          backdropFilter: 'blur(16px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          padding: '16px 32px',
        }}
      >
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
              }}
            >
              <Shield size={24} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.01em' }}>
                  MRITRA
                </h1>
                <span className="glow-pill" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                  v0.1.0
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                Privacy-Preserving Cross-Bank AML Engine
              </p>
            </div>
          </div>

          {/* LinuxONE Hardware Target Badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '10px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.8rem' }}>
              <Server size={16} color="#38bdf8" />
              <span style={{ color: '#94a3b8' }}>Target:</span>
              <span style={{ color: '#f8fafc', fontWeight: 600 }}>IBM Secure Execution (LinuxONE)</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ flex: 1, maxWidth: '1400px', width: '100%', margin: '0 auto', padding: '24px 32px' }}>
        {/* Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', overflowX: 'auto', paddingBottom: '4px' }}>
          <button
            onClick={() => setActiveTab('overview')}
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          >
            <TrendingUp size={16} /> Overview & Gap ($G$)
          </button>
          <button
            onClick={() => setActiveTab('chain')}
            className={`tab-btn ${activeTab === 'chain' ? 'active' : ''}`}
          >
            <Network size={16} /> Laundering Topology
          </button>
          <button
            onClick={() => setActiveTab('tlog')}
            className={`tab-btn ${activeTab === 'tlog' ? 'active' : ''}`}
          >
            <FileText size={16} /> Transparency Log
          </button>
          <button
            onClick={() => setActiveTab('recon')}
            className={`tab-btn ${activeTab === 'recon' ? 'active' : ''}`}
          >
            <CheckCircle size={16} /> Double-Entry Audit
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          >
            <Sliders size={16} /> Parity Audit
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && <Overview />}
        {activeTab === 'chain' && <ChainGraph />}
        {activeTab === 'tlog' && <TransparencyLog />}
        {activeTab === 'recon' && <Reconciliation />}
        {activeTab === 'audit' && <ConfigAudit />}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border-color)', padding: '20px 32px', background: 'rgba(11, 15, 25, 0.6)', marginTop: '40px' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', fontSize: '0.8rem', color: '#64748b' }}>
          <div>
            IBM Z Datathon 2026 — Mritra Cross-Bank Confidential Compute
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <span>PREREGISTRATION.md §5 Verified</span>
            <span>|</span>
            <span>PyNaCl Curve25519 Encryption</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
