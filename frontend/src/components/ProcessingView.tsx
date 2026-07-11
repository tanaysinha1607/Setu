// ---------------------------------------------------------------------------
// Setu — Processing View (the "money screen")
// ---------------------------------------------------------------------------
// Shows the 3D bridge with live routing animation, a real ticking latency
// counter, and routing metadata appearing as data becomes available.

import { Suspense } from 'react';
import { motion } from 'framer-motion';
import BridgeScene from './BridgeScene';
import LatencyCounter from './LatencyCounter';
import { useStore } from '../store';

export default function ProcessingView() {
  const { isLoading, routeTaken, result, requestStartTime } = useStore();

  // Map store state to 3D scene route state
  const routeState = isLoading
    ? 'processing'
    : routeTaken === 'local'
      ? 'local'
      : routeTaken === 'escalate'
        ? 'escalate'
        : 'processing';

  const routeColor =
    routeTaken === 'escalate'
      ? 'var(--setu-gold)'
      : 'var(--setu-teal)';

  const routeLabel =
    routeTaken === 'escalate'
      ? 'Cloud — Gemini'
      : routeTaken === 'local'
        ? 'On-Device — Gemma'
        : 'Routing…';

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1rem',
      }}
    >
      <div style={{ width: '100%', maxWidth: '600px' }}>
        {/* 3D Scene */}
        <Suspense
          fallback={
            <div
              className="shimmer-bg"
              style={{ width: '100%', height: '220px', borderRadius: '16px' }}
            />
          }
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
          >
            <BridgeScene routeState={routeState as 'idle' | 'processing' | 'local' | 'escalate'} compact />
          </motion.div>
        </Suspense>

        {/* Status + Latency */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          style={{ textAlign: 'center', marginTop: '0.5rem' }}
        >
          {/* Pulsing status indicator */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginBottom: '0.75rem',
            }}
          >
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: isLoading ? 'var(--setu-teal)' : routeColor,
                boxShadow: `0 0 8px ${isLoading ? 'var(--setu-teal-glow)' : routeColor}`,
                animation: isLoading ? 'pulse-teal 1.5s ease-in-out infinite' : 'none',
              }}
            />
            <span
              className="font-display"
              style={{
                fontSize: '0.85rem',
                fontWeight: 600,
                color: isLoading ? 'var(--text-secondary)' : routeColor,
              }}
            >
              {isLoading ? 'Processing…' : routeLabel}
            </span>
          </div>

          {/* Live latency counter */}
          <div style={{ marginBottom: '1.5rem' }}>
            <LatencyCounter
              startTime={requestStartTime}
              stopped={!isLoading}
              finalMs={result?.latency_ms}
            />
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                marginTop: '0.25rem',
              }}
            >
              {isLoading
                ? 'Measuring real request latency'
                : result?.escalation_method
                  ? `via ${result.escalation_method}`
                  : 'via Local Gemma scoring'}
            </div>
          </div>
        </motion.div>

        {/* Routing metadata cards (appear as data arrives) */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass"
            style={{ padding: '1rem', marginBottom: '1rem' }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '0.75rem',
              }}
            >
              {/* Route */}
              <MetaItem
                label="Route"
                value={result.route.toUpperCase()}
                color={
                  result.route === 'escalate'
                    ? 'var(--setu-gold)'
                    : 'var(--setu-teal)'
                }
              />
              {/* Confidence */}
              <MetaItem
                label="Confidence"
                value={
                  result.confidence_score != null
                    ? `${(result.confidence_score * 100).toFixed(0)}%`
                    : 'N/A'
                }
              />
              {/* Anomaly Flags */}
              {result.anomaly_flags.length > 0 && (
                <div style={{ gridColumn: '1 / -1' }}>
                  <MetaItem
                    label="Anomaly Flags"
                    value={result.anomaly_flags.join(', ')}
                    color="var(--risk-high)"
                  />
                </div>
              )}
            </div>
            {/* Routing reason */}
            {result.routing_reason && (
              <div
                style={{
                  marginTop: '0.75rem',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  background: 'rgba(0,0,0,0.2)',
                  fontSize: '0.78rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                }}
              >
                {result.routing_reason}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </motion.section>
  );
}

function MetaItem({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div
        className="font-display"
        style={{
          fontSize: '0.9rem',
          fontWeight: 600,
          color: color || 'var(--text-primary)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
