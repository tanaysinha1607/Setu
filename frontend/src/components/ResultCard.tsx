// ---------------------------------------------------------------------------
// Setu — Result Card
// ---------------------------------------------------------------------------
// Animated radial gauge for risk score, explanation card, escalation badge,
// latency display, and "Run Another Case" reset button.

import { motion } from 'framer-motion';
import { useStore } from '../store';

// ── Radial gauge (SVG arc) ──────────────────────────────────────────────────
function RadialGauge({
  score,
  category,
}: {
  score: number | null;
  category: string;
}) {
  const size = 180;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Map risk_category to colors
  const colorMap: Record<string, string> = {
    low: 'var(--risk-low)',
    medium: 'var(--risk-medium)',
    high: 'var(--risk-high)',
    pending_review: 'var(--risk-pending)',
  };
  const color = colorMap[category] || colorMap.pending_review;

  // Score percentage (0-100)
  const pct = score != null ? Math.max(0, Math.min(100, score)) / 100 : 0;
  const dashOffset = circumference * (1 - pct * 0.75); // 270-degree arc

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-225deg)' }}
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
        />
        {/* Filled arc */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          initial={{ strokeDashoffset: circumference * 0.75 }}
          animate={{ strokeDashoffset: dashOffset }}
          transition={{ duration: 1.5, ease: 'easeOut', delay: 0.3 }}
          style={{
            filter: `drop-shadow(0 0 8px ${color})`,
          }}
        />
      </svg>
      {/* Center label */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <motion.span
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.6, ease: 'easeOut' }}
          className="font-display"
          style={{
            fontSize: '2.5rem',
            fontWeight: 700,
            color: color,
            lineHeight: 1,
          }}
        >
          {score != null ? Math.round(score) : '—'}
        </motion.span>
        <span
          style={{
            fontSize: '0.7rem',
            color: 'var(--text-muted)',
            marginTop: '2px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          Risk Score
        </span>
      </div>
    </div>
  );
}

// ── Category badge ──────────────────────────────────────────────────────────
function CategoryBadge({ category }: { category: string }) {
  const config: Record<string, { bg: string; color: string; label: string }> = {
    low: { bg: 'var(--setu-teal-dim)', color: 'var(--setu-teal)', label: 'LOW RISK' },
    medium: { bg: 'var(--setu-gold-dim)', color: 'var(--setu-gold)', label: 'MEDIUM RISK' },
    high: { bg: 'rgba(239,68,68,0.15)', color: '#ef4444', label: 'HIGH RISK' },
    pending_review: { bg: 'rgba(107,114,128,0.15)', color: '#9ca3af', label: 'PENDING REVIEW' },
  };
  const c = config[category] || config.pending_review;

  return (
    <motion.span
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.8 }}
      style={{
        display: 'inline-block',
        padding: '4px 14px',
        borderRadius: '99px',
        background: c.bg,
        color: c.color,
        fontSize: '0.7rem',
        fontWeight: 700,
        letterSpacing: '0.08em',
        fontFamily: 'var(--font-display)',
      }}
    >
      {c.label}
    </motion.span>
  );
}

// ── Main component ──────────────────────────────────────────────────────────
export default function ResultCard() {
  const { result, error, reset } = useStore();

  if (error) {
    return (
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem 1rem',
        }}
      >
        <div className="glass" style={{ padding: '2rem', maxWidth: '480px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
          <h3 className="font-display" style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
            Assessment Error
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
            {error}
          </p>
          <button
            onClick={reset}
            style={{
              padding: '10px 24px',
              borderRadius: '10px',
              border: '1px solid var(--setu-border)',
              background: 'var(--setu-surface)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            Try Again
          </button>
        </div>
      </motion.section>
    );
  }

  if (!result) return null;

  const isEscalated = result.route === 'escalate';
  const latencySec = (result.latency_ms / 1000).toFixed(1);
  const viaLabel = result.escalation_method
    ? `via ${result.escalation_method}`
    : 'via Local Gemma';

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1rem',
      }}
    >
      <div style={{ width: '100%', maxWidth: '480px' }}>
        {/* Gauge + category */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            marginBottom: '1.5rem',
          }}
        >
          <RadialGauge score={result.risk_score} category={result.risk_category} />
          <div style={{ marginTop: '0.75rem' }}>
            <CategoryBadge category={result.risk_category} />
          </div>
        </motion.div>

        {/* Latency display */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          style={{
            textAlign: 'center',
            marginBottom: '1.5rem',
          }}
        >
          <div
            className="font-display"
            style={{
              fontSize: '1.1rem',
              fontWeight: 600,
              color: isEscalated ? 'var(--setu-gold)' : 'var(--setu-teal)',
            }}
          >
            {latencySec}s {isEscalated ? 'Cloud' : 'On-Device'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {viaLabel}
          </div>
        </motion.div>

        {/* Escalation method badge */}
        {result.escalation_method && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            style={{
              display: 'flex',
              justifyContent: 'center',
              marginBottom: '1rem',
            }}
          >
            <div
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                background: 'var(--setu-gold-dim)',
                border: '1px solid rgba(245,158,11,0.2)',
                fontSize: '0.7rem',
                color: 'var(--setu-gold)',
                fontFamily: 'var(--font-body)',
                fontWeight: 500,
                textAlign: 'center',
                maxWidth: '100%',
                wordBreak: 'break-word',
              }}
            >
              🚀 {result.escalation_method}
            </div>
          </motion.div>
        )}

        {/* Explanation card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="glass"
          style={{ padding: '1.25rem', marginBottom: '1rem' }}
        >
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: '0.5rem',
              fontWeight: 600,
            }}
          >
            Analysis
          </div>
          <p
            style={{
              fontSize: '0.88rem',
              color: 'var(--text-primary)',
              lineHeight: 1.7,
            }}
          >
            {result.explanation}
          </p>
        </motion.div>

        {/* Route & confidence metadata */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="glass"
          style={{
            padding: '1rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.5rem',
            textAlign: 'center',
          }}
        >
          <div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Route
            </div>
            <div
              className="font-display"
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: isEscalated ? 'var(--setu-gold)' : 'var(--setu-teal)',
                marginTop: '2px',
              }}
            >
              {result.route.toUpperCase()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Confidence
            </div>
            <div className="font-display" style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '2px' }}>
              {result.confidence_score != null
                ? `${(result.confidence_score * 100).toFixed(0)}%`
                : 'N/A'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Flags
            </div>
            <div
              className="font-display"
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                marginTop: '2px',
                color: result.anomaly_flags.length > 0 ? 'var(--risk-high)' : 'var(--text-primary)',
              }}
            >
              {result.anomaly_flags.length > 0
                ? result.anomaly_flags.join(', ')
                : 'None'}
            </div>
          </div>
        </motion.div>

        {/* Reset button */}
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={reset}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '12px',
            border: '1px solid var(--setu-border)',
            background: 'var(--setu-surface)',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: '0.95rem',
          }}
        >
          Run Another Case
        </motion.button>
      </div>
    </motion.section>
  );
}
