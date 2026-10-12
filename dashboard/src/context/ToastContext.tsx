import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, ShieldCheck, Copy } from 'lucide-react';

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  type?: 'success' | 'danger' | 'info' | 'lime' | 'copy';
}

interface ToastContextType {
  showToast: (title: string, description?: string, type?: ToastMessage['type']) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((title: string, description?: string, type: ToastMessage['type'] = 'lime') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, title, description, type }]);

    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3800);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}

      {/* Floating Apple Dynamic Island Capsule */}
      <div 
        style={{
          position: 'fixed',
          top: '22px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          alignItems: 'center',
          pointerEvents: 'none',
        }}
      >
        {toasts.map(toast => (
          <div
            key={toast.id}
            className="apple-toast-capsule animate-toast"
            style={{
              pointerEvents: 'auto',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '10px 20px',
              borderRadius: '9999px',
              background: 'rgba(18, 18, 22, 0.92)',
              backdropFilter: 'blur(24px) saturate(180%)',
              WebkitBackdropFilter: 'blur(24px) saturate(180%)',
              color: '#ffffff',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.35), 0 2px 8px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              fontFamily: 'var(--font-display)',
              maxWidth: '90vw',
            }}
          >
            {/* Icon */}
            <div style={{ display: 'flex', alignItems: 'center' }}>
              {toast.type === 'lime' && <ShieldCheck size={18} color="var(--lime)" />}
              {toast.type === 'success' && <CheckCircle2 size={18} color="var(--apple-green)" />}
              {toast.type === 'danger' && <AlertCircle size={18} color="var(--apple-red)" />}
              {toast.type === 'copy' && <Copy size={16} color="var(--lime)" />}
              {toast.type === 'info' && <Info size={18} color="var(--apple-blue)" />}
            </div>

            {/* Content */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.84rem', fontWeight: 700, letterSpacing: '-0.01em' }}>
                {toast.title}
              </span>
              {toast.description && (
                <span style={{ fontSize: '0.74rem', color: '#a1a1a6', fontWeight: 500 }}>
                  {toast.description}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// oxlint-disable-next-line react/only-export-components
export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
