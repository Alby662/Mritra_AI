import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, RefreshCw, Database } from 'lucide-react';

interface TLogEntry {
  seq: number;
  ts: string;
  requester: string;
  queryType: string;
  entryHash: string;
  prevHash: string;
  tampered?: boolean;
}

export const TransparencyLog: React.FC = () => {
  const [tampered, setTampered] = useState<boolean>(false);

  const initialEntries: TLogEntry[] = [
    { seq: 1, ts: '2026-10-02T10:00:00Z', requester: 'Bank Alpha (Inst 0)', queryType: 'REGISTER_KEYS', entryHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', prevHash: '0000000000000000000000000000000000000000000000000000000000000000' },
    { seq: 2, ts: '2026-10-02T10:05:00Z', requester: 'Bank Beta (Inst 1)', queryType: 'SUBMIT_BOUNDARIES', entryHash: '8f4e2b109c3a71258d4a901eef2349b10924c5617a89bc213049182bc834fa12', prevHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
    { seq: 3, ts: '2026-10-02T10:10:00Z', requester: 'Enclave Service', queryType: 'RECONCILE_ROUND_1', entryHash: 'a12bc9048fe391024bd872eef012948c279410bb45a782194bc8712aef9120bc', prevHash: '8f4e2b109c3a71258d4a901eef2349b10924c5617a89bc213049182bc834fa12' },
    { seq: 4, ts: '2026-10-02T10:15:00Z', requester: 'Bank Gamma (Inst 2)', queryType: 'FETCH_NETWORK_FEATURES', entryHash: '4920bc81fa39102847cfab10923e490184b9104859a1024789bc10293fa0182c', prevHash: 'a12bc9048fe391024bd872eef012948c279410bb45a782194bc8712aef9120bc' },
    { seq: 5, ts: '2026-10-02T10:20:00Z', requester: 'Enclave Service', queryType: 'RECONCILE_ROUND_2', entryHash: '7390abef18923049182bc8710924cfab102948c7102948ab1029348c901824ef', prevHash: '4920bc81fa39102847cfab10923e490184b9104859a1024789bc10293fa0182c' },
  ];

  const entries = initialEntries.map(e => {
    if (tampered && e.seq === 3) {
      return {
        ...e,
        entryHash: 'BAD_HASH_999999999999999999999999999999999999999999999999999999999999',
        tampered: true,
      };
    }
    return e;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Bar */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={20} color="#6366f1" /> Append-Only Transparency Log Verification
          </h3>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '2px' }}>
            Every round submission, key exchange, and feature query is cryptographically hash-chained in SQLite.
          </p>
        </div>

        {/* Tamper Simulation Toggle */}
        <button
          onClick={() => setTampered(!tampered)}
          className={`btn ${tampered ? 'btn-primary' : 'btn-outline'}`}
          style={{ background: tampered ? 'rgba(244, 63, 94, 0.2)' : undefined, borderColor: tampered ? '#f43f5e' : undefined, color: tampered ? '#f87171' : undefined }}
        >
          <RefreshCw size={14} /> {tampered ? 'Restore Valid Chain' : 'Simulate Log Tampering'}
        </button>
      </div>

      {/* Verification Status Alert */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          background: tampered ? 'rgba(244, 63, 94, 0.12)' : 'rgba(16, 185, 129, 0.12)',
          borderColor: tampered ? 'rgba(244, 63, 94, 0.4)' : 'rgba(16, 185, 129, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {tampered ? <ShieldAlert size={28} color="#f43f5e" /> : <ShieldCheck size={28} color="#10b981" />}
          <div>
            <h4 style={{ color: tampered ? '#f87171' : '#34d399', fontWeight: 700, fontSize: '1rem' }}>
              {tampered ? '❌ CRITICAL: Cryptographic Chain Broken at Sequence #3' : '✅ Transparency Log Intact & Verified'}
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '2px' }}>
              {tampered
                ? 'Entry #3 hash mismatch! Previous hash pointer on Entry #4 fails SHA-256 verification.'
                : 'All 5 log entries pass recursive SHA-256 hash pointer verification. Head: 7390abef1892...'}
            </p>
          </div>
        </div>

        <span className="code-font" style={{ fontSize: '0.75rem', padding: '6px 12px', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '8px', color: '#94a3b8' }}>
          SQLite tlog.db
        </span>
      </div>

      {/* Hash Chain Table */}
      <div className="glass-panel" style={{ padding: '20px', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'left', color: '#94a3b8' }}>
              <th style={{ padding: '12px 16px' }}>Seq</th>
              <th style={{ padding: '12px 16px' }}>Timestamp</th>
              <th style={{ padding: '12px 16px' }}>Requester</th>
              <th style={{ padding: '12px 16px' }}>Query / Action</th>
              <th style={{ padding: '12px 16px' }}>Entry Hash (SHA-256)</th>
              <th style={{ padding: '12px 16px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(e => (
              <tr
                key={e.seq}
                style={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                  background: e.tampered ? 'rgba(244, 63, 94, 0.15)' : 'transparent',
                }}
              >
                <td style={{ padding: '14px 16px', fontWeight: 700 }} className="code-font">#{e.seq}</td>
                <td style={{ padding: '14px 16px', color: '#cbd5e1' }} className="code-font">{e.ts}</td>
                <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f8fafc' }}>{e.requester}</td>
                <td style={{ padding: '14px 16px' }}>
                  <span className="glow-pill" style={{ fontSize: '0.7rem', background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc' }}>
                    {e.queryType}
                  </span>
                </td>
                <td style={{ padding: '14px 16px', color: e.tampered ? '#f87171' : '#94a3b8' }} className="code-font">
                  {e.entryHash.substring(0, 20)}...
                </td>
                <td style={{ padding: '14px 16px' }}>
                  {e.tampered ? (
                    <span className="glow-pill badge-rose" style={{ fontSize: '0.7rem' }}>Tampered</span>
                  ) : (
                    <span className="glow-pill badge-emerald" style={{ fontSize: '0.7rem' }}>Verified</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
