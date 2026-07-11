// ---------------------------------------------------------------------------
// Setu — Hero section
// ---------------------------------------------------------------------------

import { Suspense } from 'react';
import { motion } from 'framer-motion';
import BridgeScene from './BridgeScene';
import { useStore } from '../store';

export default function Hero() {
  const setPhase = useStore((s) => s.setPhase);

  return (
    <section
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        padding: '1rem',
      }}
    >
      {/* Background radial gradient */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(45, 212, 191, 0.06) 0%, transparent 60%), ' +
            'radial-gradient(ellipse 60% 40% at 70% 60%, rgba(245, 158, 11, 0.04) 0%, transparent 50%)',
          pointerEvents: 'none',
        }}
      />

      {/* 3D Bridge Scene */}
      <Suspense
        fallback={
          <div
            style={{
              width: '100%',
              height: '400px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div className="shimmer-bg" style={{ width: '100%', height: '100%', borderRadius: '16px' }} />
          </div>
        }
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          style={{ width: '100%', maxWidth: '800px' }}
        >
          <BridgeScene routeState="idle" />
        </motion.div>
      </Suspense>

      {/* Text content */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3 }}
        style={{ textAlign: 'center', maxWidth: '600px', marginTop: '-2rem' }}
      >
        <h1
          className="font-display"
          style={{
            fontSize: 'clamp(3rem, 8vw, 5rem)',
            fontWeight: 700,
            letterSpacing: '-0.03em',
            lineHeight: 1.1,
            marginBottom: '0.75rem',
          }}
        >
          <span className="gradient-text-teal">Se</span>
          <span className="gradient-text-gold">tu</span>
        </h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.8 }}
          className="font-display"
          style={{
            fontSize: 'clamp(1rem, 3vw, 1.25rem)',
            fontWeight: 500,
            color: 'var(--text-primary)',
            marginBottom: '0.5rem',
          }}
        >
          Reason locally. Escalate only when it matters.
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.8 }}
          style={{
            fontSize: 'clamp(0.85rem, 2.5vw, 0.95rem)',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            marginBottom: '2rem',
          }}
        >
          Adaptive AI routing for microfinance credit risk — on-device Gemma by
          default, cloud Gemini when the model isn't confident.
        </motion.p>

        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.6 }}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => setPhase('input')}
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '1rem',
            fontWeight: 600,
            padding: '14px 36px',
            borderRadius: '12px',
            border: 'none',
            cursor: 'pointer',
            background: 'linear-gradient(135deg, #2dd4bf 0%, #14b8a6 100%)',
            color: '#0a0e1a',
            letterSpacing: '0.01em',
            boxShadow:
              '0 0 20px rgba(45, 212, 191, 0.3), 0 4px 20px rgba(0, 0, 0, 0.3)',
          }}
        >
          Start a Case Assessment
        </motion.button>
      </motion.div>
    </section>
  );
}
