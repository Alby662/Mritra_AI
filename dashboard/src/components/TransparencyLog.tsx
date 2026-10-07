import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  Check, 
  Copy 
} from 'lucide-react';
import { INITIAL_TLOG_BLOCKS } from '../data/telemetryData';
import type { TLogBlock } from '../data/telemetryData';

export const TransparencyLog: React.FC = () => {
  const [tampered, setTampered] = useState<boolean>(false);
  const [inspectedBlock, setInspectedBlock] = useState<TLogBlock | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  const blocks: TLogBlock[] = INITIAL_TLOG_BLOCKS.map(block => {
    if (tampered && block.seq === 3) {
      return {
        ...block,
        entryHash: 'e999999999999999999999999999999999999999999999999999999999999999',
        tampered: true,
      };
    }
    return block;
  });

  const handleCopy = (text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ─── Apple Style Header Panel ───────────────────────────── */}
      <div 
        className="bento-card animate-bento" 
        style={{ padding: '24px 28px', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="pill-tag pill-tag-dark" style={{ fontSize: '0.68rem' }}>
              IMMUTABLE AUDIT LOG
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              SHA-256 Merkle Chaining
            </span>
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.025em' }}>
            Append-Only Transparency Ledger
          </h2>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '2px', maxWidth: '640px' }}>
            Every round window submission, Curve25519 key exchange, and topological query is cryptographically hash-chained inside the enclave SQLite database.
          </p>
        </div>

        {/* Apple Segmented Tamper Simulation Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setTampered(!tampered)}
            className={`selector-pill ${tampered ? 'pill-tag-danger' : ''}`}
            style={{ 
              padding: '8px 18px', 
              fontSize: '0.8rem',
              background: tampered ? 'rgba(255, 59, 48, 0.12)' : '#ffffff',
              color: tampered ? 'var(--apple-red)' : 'var(--text-primary)',
              border: tampered ? '1px solid rgba(255, 59, 48, 0.3)' : '1px solid var(--border-subtle)'
            }}
          >
            <RefreshCw size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            {tampered ? 'Restore Valid Ledger' : 'Simulate Tamper Attack'}
          </button>
        </div>
      </div>

      {/* ─── Cryptographic Verification Banner ──────────────────── */}
      <div 
        className="animate-bento"
        style={{
          padding: '16px 22px',
          borderRadius: 'var(--radius-md)',
          background: tampered ? 'rgba(255, 59, 48, 0.1)' : 'rgba(52, 199, 89, 0.12)',
          border: tampered ? '1.5px solid rgba(255, 59, 48, 0.3)' : '1.5px solid rgba(52, 199, 89, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {tampered ? (
            <ShieldAlert size={24} color="var(--apple-red)" />
          ) : (
            <ShieldCheck size={24} color="var(--apple-green)" />
          )}
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.92rem', color: tampered ? 'var(--apple-red)' : 'var(--apple-green)' }}>
              {tampered 
                ? 'CRITICAL TAMPER DETECTED — MERKLE CHAIN BROKEN AT SEQ #3' 
                : 'TRANSPARENCY LEDGER AUDIT PASSED — 5/5 BLOCKS CRYPTOGRAPHICALLY VALID'}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {tampered
                ? 'Block #3 entry hash does not match previous hash pointer in Block #4. Lying bank attack neutralized.'
                : 'Sequential root consistency verified. All hardware quotes signed with AMD SEV-SNP VCEK.'}
            </div>
          </div>
        </div>

        <span className="code-font" style={{ fontSize: '0.74rem', background: '#ffffff', padding: '6px 12px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-subtle)', fontWeight: 700 }}>
          Latest Merkle Root: 0x7390...24ef
        </span>
      </div>

      {/* ─── Blocks Table (Apple Table Card) ────────────────────── */}
      <div className="apple-table-card animate-bento bento-delay-1">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 className="bento-card-title">Sequenced Event Blocks</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Showing 5 latest cryptographically committed transactions
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Seq #</th>
                <th>Timestamp (UTC)</th>
                <th>Requesting Entity</th>
                <th>Query Operation</th>
                <th>Entry Hash</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((block) => (
                <tr 
                  key={block.seq}
                  style={{
                    background: block.tampered ? 'rgba(255, 59, 48, 0.06)' : undefined
                  }}
                >
                  <td className="tabular-nums" style={{ fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                    #{block.seq}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {block.ts.replace('T', ' ').replace('Z', '')}
                  </td>
                  <td style={{ fontWeight: 700 }}>
                    {block.requester}
                  </td>
                  <td>
                    <span className="code-font" style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.04)', padding: '3px 8px', borderRadius: '6px' }}>
                      {block.queryType}
                    </span>
                  </td>
                  <td className="code-font" style={{ fontSize: '0.75rem', color: block.tampered ? 'var(--apple-red)' : 'var(--text-muted)' }}>
                    {block.entryHash.slice(0, 14)}...{block.entryHash.slice(-6)}
                  </td>
                  <td>
                    {block.tampered ? (
                      <span className="pill-tag pill-tag-danger">
                        Tampered
                      </span>
                    ) : (
                      <span className="pill-tag pill-tag-success">
                        Verified
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      onClick={() => setInspectedBlock(block)}
                      className="selector-pill"
                      style={{ padding: '4px 12px', fontSize: '0.72rem' }}
                    >
                      Inspect &gt;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── Apple Style Block Inspection Sheet ─────────────────── */}
      {inspectedBlock && (
        <div className="apple-sheet-backdrop" onClick={() => setInspectedBlock(null)}>
          <div className="apple-sheet animate-bento" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="pill-tag pill-tag-dark">
                  BLOCK #{inspectedBlock.seq}
                </span>
                <span className={inspectedBlock.tampered ? 'pill-tag pill-tag-danger' : 'pill-tag pill-tag-success'}>
                  {inspectedBlock.tampered ? 'INVALID CHECKSUM' : 'ATTESTED & SIGNED'}
                </span>
              </div>
              <button 
                onClick={() => setInspectedBlock(null)}
                style={{ border: 'none', background: 'rgba(0,0,0,0.06)', width: '28px', height: '28px', borderRadius: '50%', cursor: 'pointer', fontWeight: 800 }}
              >
                ✕
              </button>
            </div>

            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', marginBottom: '12px' }}>
              Submitted by <strong style={{ color: '#000' }}>{inspectedBlock.requester}</strong> at {inspectedBlock.ts} UTC.
            </p>

            {inspectedBlock.details && (
              <div style={{ background: '#f5f5f7', padding: '12px 14px', borderRadius: 'var(--radius-sm)', marginBottom: '16px', fontSize: '0.82rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                <strong>Execution Record:</strong> {inspectedBlock.details}
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Audited Volume: {inspectedBlock.recordsCount.toLocaleString()} items committed
                </div>
              </div>
            )}

            {/* Hashes Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              <div style={{ background: '#f5f5f7', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>BLOCK ENTRY SHA-256 HASH</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 700, wordBreak: 'break-all', marginTop: '2px', color: inspectedBlock.tampered ? 'var(--apple-red)' : '#000' }}>
                  {inspectedBlock.entryHash}
                </div>
              </div>

              <div style={{ background: '#f5f5f7', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>PARENT BLOCK HASH (POINTER)</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 700, wordBreak: 'break-all', marginTop: '2px' }}>
                  {inspectedBlock.prevHash}
                </div>
              </div>

              <div style={{ background: '#f5f5f7', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>CRYPTOGRAPHIC SIGNATURE</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 700, wordBreak: 'break-all', marginTop: '2px' }}>
                  {inspectedBlock.signature}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                onClick={() => handleCopy(inspectedBlock.entryHash)}
                className="selector-pill"
                style={{ flex: 1, justifyContent: 'center', padding: '12px 18px', fontWeight: 700 }}
              >
                {copiedHash ? <Check size={14} color="var(--apple-green)" /> : <Copy size={14} />}
                {copiedHash ? 'Hash Copied' : 'Copy Hash'}
              </button>
              <button 
                onClick={() => setInspectedBlock(null)}
                className="btn-pill-dark"
                style={{ flex: 1 }}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
