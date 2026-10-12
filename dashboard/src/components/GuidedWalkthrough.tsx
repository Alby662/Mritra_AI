import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Network, 
  FileText, 
  CheckCircle2, 
  LayoutGrid, 
  ArrowRight, 
  ArrowLeft, 
  X, 
  Sparkles, 
  Eye, 
  Lock, 
  Cpu
} from 'lucide-react';

interface GuidedWalkthroughProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateTab: (tab: 'overview' | 'chain' | 'tlog' | 'recon' | 'audit') => void;
}

interface Step {
  id: string;
  tabTarget: 'overview' | 'chain' | 'tlog' | 'recon' | 'audit';
  badge: string;
  title: string;
  subtitle: string;
  description: string;
  icon: React.ReactNode;
  highlights: { title: string; desc: string; icon: React.ReactNode }[];
  takeaway: string;
}

export function GuidedWalkthrough({ isOpen, onClose, onNavigateTab }: GuidedWalkthroughProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps: Step[] = [
    {
      id: 'welcome',
      tabTarget: 'overview',
      badge: 'Architecture & Mission',
      title: 'Welcome to Mritra AI',
      subtitle: 'The Cross-Institutional Money Mule Blindspot',
      description: 
        'Organized fraud syndicates move money through rented mule accounts spread across multiple banks. Over 50% of illicit funds leave a mule account in under one hour.',
      icon: <Shield size={28} color="#c6ef4e" />,
      highlights: [
        {
          title: 'The Silo Problem',
          desc: 'Each bank only sees its isolated fraction of the transactions. A 5-bank laundering chain looks completely harmless to every individual bank.',
          icon: <Eye size={16} color="#ff9500" />
        },
        {
          title: 'Legal Bar to Data Pooling',
          desc: 'Banks cannot legally pool raw customer transaction data under banking secrecy, GDPR, and DPDP laws.',
          icon: <Lock size={16} color="#ff3b30" />
        },
        {
          title: 'The Enclave Solution',
          desc: 'Mritra enables banks to submit encrypted boundary summaries into an IBM LinuxONE Secure Execution enclave to reconcile networks with zero raw data exposure.',
          icon: <Cpu size={16} color="#c6ef4e" />
        }
      ],
      takeaway: 'Result: Participating banks catch cross-institution mule chains without ever sharing raw ledgers or KYC data.'
    },
    {
      id: 'bento',
      tabTarget: 'overview',
      badge: 'Tab 1 · Executive Bento',
      title: 'Operations & Zero-Exposure Proof',
      subtitle: 'Real-Time Model Uplift & Telemetric Compliance',
      description:
        'The Executive Bento provides the compliance team and risk officers with live performance metrics and cryptographic telemetry.',
      icon: <LayoutGrid size={28} color="#0071e3" />,
      highlights: [
        {
          title: 'C1 vs C3 F1 Uplift',
          desc: 'Compares Siloed local models (C1) against Enclave-reconciled models (C3), demonstrating significant detection improvement on cross-bank fraud.',
          icon: <Sparkles size={16} color="#c6ef4e" />
        },
        {
          title: 'Prioritized AML Cases',
          desc: 'Surfaces highest-risk accounts identified by the bank’s internal scoring model with full audit metadata.',
          icon: <Shield size={16} color="#0071e3" />
        },
        {
          title: 'Data Boundary Telemetry',
          desc: 'Audits every enclave round, confirming that only aggregated degree statistics leave the bank and zero raw internal ledger transactions are leaked.',
          icon: <Lock size={16} color="#34c759" />
        }
      ],
      takeaway: 'Auditors can verify that joining the network yields superior detection while strictly preserving regulatory data boundaries.'
    },
    {
      id: 'chain',
      tabTarget: 'chain',
      badge: 'Tab 2 · Topology Graph',
      title: 'Multi-Bank Mule Ring (Pattern #268)',
      subtitle: 'See the Enclave Illuminate Hidden Syndicates',
      description:
        'This interactive graph maps a real scatter-gather laundering ring spanning 30 transactions, 15 accounts, and 5 independent banking institutions.',
      icon: <Network size={28} color="#c6ef4e" />,
      highlights: [
        {
          title: 'C1 Siloed View (Blind)',
          desc: 'Toggle the switch in this tab to "C1 Siloed". Notice how individual banks only see 1–2 transfers each and assign low risk scores (grey edges).',
          icon: <Eye size={16} color="#ff9500" />
        },
        {
          title: 'C3 Enclave View (Illuminated)',
          desc: 'Switch to "C3 Enclave". The enclave’s cross-bank graph reconciliation connects the multi-hop transfers and flags the entire ring in red.',
          icon: <Sparkles size={16} color="#ff3b30" />
        },
        {
          title: 'Interactive Node Inspection',
          desc: 'Click on any account node to inspect its institution ID, transfer velocity, and transaction hop breakdown.',
          icon: <Network size={16} color="#c6ef4e" />
        }
      ],
      takeaway: 'This view proves visually why isolated bank models fail and how enclave graph synthesis catches the full criminal chain.'
    },
    {
      id: 'tlog',
      tabTarget: 'tlog',
      badge: 'Tab 3 · Merkle Ledger',
      title: 'Tamper-Evident Transparency Log',
      subtitle: 'Cryptographic Guarantees Over Human Promises',
      description:
        'Every enclave round, code hash, input commitment, and reconciliation output is signed with Curve25519 and recorded in an immutable ledger (tlog.db).',
      icon: <FileText size={28} color="#5856d6" />,
      highlights: [
        {
          title: 'SHA-256 Hash Chaining',
          desc: 'Each block commits to the previous block’s hash. If an operator or rogue insider modifies a single past record, the hash chain breaks.',
          icon: <Lock size={16} color="#5856d6" />
        },
        {
          title: 'Hardware Attestation',
          desc: 'Validates enclave authenticity (simulated locally, target: IBM LinuxONE Secure Execution ultra-secure memory isolation).',
          icon: <Cpu size={16} color="#c6ef4e" />
        },
        {
          title: 'Zero Reversibility',
          desc: 'Entries store irreversible SHA-256 hashes of inputs and outputs, allowing public verification without exposing transaction details.',
          icon: <CheckCircle2 size={16} color="#34c759" />
        }
      ],
      takeaway: 'Regulators and member banks can independently verify system execution integrity without seeing raw transaction data.'
    },
    {
      id: 'recon',
      tabTarget: 'recon',
      badge: 'Tab 4 · Double-Entry Audit',
      title: 'Two-Sided Settlement Reconciliation',
      subtitle: 'Defending the Network Against Malicious or Lying Banks',
      description:
        'The enclave cross-examines sender and recipient settlement reports. A bank cannot poison the network or secretly hide its mule accounts.',
      icon: <CheckCircle2 size={28} color="#34c759" />,
      highlights: [
        {
          title: 'Counterparty Matching',
          desc: 'Every outgoing transfer reported by Bank A must match an incoming transfer reported by Bank B with the exact amount and timestamp window.',
          icon: <CheckCircle2 size={16} color="#34c759" />
        },
        {
          title: 'Adversary Injection Defense',
          desc: 'Under automated tests where Bank 3 injects fraudulent transactions or withholds records, the enclave detects 100% of the discrepancies.',
          icon: <Shield size={16} color="#ff3b30" />
        },
        {
          title: 'Automated Discrepancy Quarantine',
          desc: 'Mismatched transactions are flagged and isolated before they can skew the graph feature calculations.',
          icon: <Lock size={16} color="#ff9500" />
        }
      ],
      takeaway: 'Ensures data integrity across the consortium so that dishonest participants cannot manipulate network risk scores.'
    }
  ];

  const current = steps[currentStep];

  const handleDismiss = React.useCallback(() => {
    localStorage.setItem('mritra_walkthrough_completed', 'true');
    onClose();
  }, [onClose]);

  // Auto-switch background tab as the user steps through the tour
  useEffect(() => {
    if (isOpen) {
      onNavigateTab(current.tabTarget);
    }
  }, [currentStep, isOpen, current.tabTarget, onNavigateTab]);

  // Keyboard navigation: Escape closes, Arrow keys navigate
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleDismiss();
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        if (currentStep < steps.length - 1) {
          setCurrentStep(s => s + 1);
        } else {
          handleDismiss();
        }
      } else if (e.key === 'ArrowLeft') {
        if (currentStep > 0) {
          setCurrentStep(s => s - 1);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentStep, steps.length, handleDismiss]);

  if (!isOpen) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(5, 5, 8, 0.72)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        animation: 'fadeIn 0.25s ease-out'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleDismiss();
      }}
    >
      <div 
        style={{
          width: '100%',
          maxWidth: '680px',
          background: 'var(--bg-card-solid)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-medium)',
          boxShadow: '0 28px 80px -12px rgba(0, 0, 0, 0.45)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        {/* Top Header Bar */}
        <div 
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-canvas-subtle)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span 
              className="pill-tag pill-tag-lime" 
              style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.5px' }}
            >
              MRITRA INTERACTIVE TOUR
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Step {currentStep + 1} of {steps.length}
            </span>
          </div>

          <button 
            onClick={handleDismiss}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.75rem',
              padding: '6px 10px',
              borderRadius: '6px',
              transition: 'all 0.2s ease'
            }}
            title="Skip and do not show again"
          >
            <span>Skip Tour</span>
            <X size={15} />
          </button>
        </div>

        {/* Modal Main Body */}
        <div style={{ padding: '28px 30px' }}>
          {/* Badge & Step Icon */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px' }}>
            <div 
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '16px',
                background: 'var(--bg-card-subtle)',
                border: '1px solid var(--border-medium)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-subtle)'
              }}
            >
              {current.icon}
            </div>

            <div>
              <span 
                style={{ 
                  fontSize: '0.72rem', 
                  color: 'var(--lime)', 
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  display: 'block',
                  marginBottom: '2px'
                }}
              >
                {current.badge}
              </span>
              <h2 
                style={{ 
                  fontSize: '1.45rem', 
                  fontWeight: 800, 
                  letterSpacing: '-0.02em',
                  color: 'var(--text-primary)',
                  margin: 0
                }}
              >
                {current.title}
              </h2>
            </div>
          </div>

          <p 
            style={{ 
              fontSize: '0.98rem', 
              fontWeight: 600, 
              color: 'var(--text-secondary)',
              marginTop: '4px',
              marginBottom: '10px'
            }}
          >
            {current.subtitle}
          </p>

          <p 
            style={{ 
              fontSize: '0.88rem', 
              color: 'var(--text-muted)',
              lineHeight: 1.55,
              marginBottom: '20px'
            }}
          >
            {current.description}
          </p>

          {/* Key Architectural Highlights */}
          <div 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '10px', 
              marginBottom: '20px'
            }}
          >
            {current.highlights.map((item, idx) => (
              <div 
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  padding: '12px 14px',
                  borderRadius: '12px',
                  background: 'var(--bg-canvas-subtle)',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <div style={{ marginTop: '2px', flexShrink: 0 }}>
                  {item.icon}
                </div>
                <div>
                  <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2px' }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: '0.79rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                    {item.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom Takeaway Box */}
          <div 
            style={{
              padding: '12px 16px',
              borderRadius: '10px',
              background: 'var(--lime-soft)',
              border: '1px solid var(--lime-border)',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <Sparkles size={16} color="var(--lime)" style={{ flexShrink: 0 }} />
            <span>{current.takeaway}</span>
          </div>
        </div>

        {/* Footer Actions & Progress Indicator */}
        <div 
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--border-subtle)',
            background: 'var(--bg-canvas-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}
        >
          {/* Step Dots */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {steps.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                style={{
                  width: idx === currentStep ? '24px' : '8px',
                  height: '8px',
                  borderRadius: '4px',
                  background: idx === currentStep ? 'var(--lime)' : 'var(--border-medium)',
                  border: 'none',
                  padding: 0,
                  cursor: 'pointer',
                  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
                }}
                title={`Go to Step ${idx + 1}`}
              />
            ))}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep(s => s - 1)}
                className="apple-segment-btn"
                style={{ padding: '8px 14px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <ArrowLeft size={14} /> Back
              </button>
            )}

            {currentStep < steps.length - 1 ? (
              <button
                onClick={() => setCurrentStep(s => s + 1)}
                className="apple-segment-btn active-lime"
                style={{ padding: '8px 18px', fontSize: '0.84rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Next Step <ArrowRight size={14} />
              </button>
            ) : (
              <button
                onClick={handleDismiss}
                className="apple-segment-btn active-lime"
                style={{ padding: '8px 20px', fontSize: '0.84rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <CheckCircle2 size={15} /> Complete & Explore
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
export default GuidedWalkthrough;
