// ---------------------------------------------------------------------------
// Setu — Live latency counter
// ---------------------------------------------------------------------------
// Displays elapsed time since request started, ticking in real-time via
// requestAnimationFrame.  Reflects true request time, not a canned animation.

import { useRef, useState, useEffect, useCallback } from 'react';

interface LatencyCounterProps {
  /** performance.now() timestamp when the request started */
  startTime: number | null;
  /** If true, counter is frozen at the final value */
  stopped?: boolean;
  /** Final latency value in ms (used when stopped) */
  finalMs?: number;
  className?: string;
}

export default function LatencyCounter({
  startTime,
  stopped = false,
  finalMs,
  className = '',
}: LatencyCounterProps) {
  const [elapsed, setElapsed] = useState(0);
  const rafRef = useRef<number>(0);

  const tick = useCallback(() => {
    if (startTime !== null && !stopped) {
      setElapsed(performance.now() - startTime);
      rafRef.current = requestAnimationFrame(tick);
    }
  }, [startTime, stopped]);

  useEffect(() => {
    if (startTime !== null && !stopped) {
      rafRef.current = requestAnimationFrame(tick);
    }
    return () => cancelAnimationFrame(rafRef.current);
  }, [startTime, stopped, tick]);

  // When stopped, show either the final API-reported latency or the measured one
  const displayMs = stopped && finalMs != null ? finalMs : elapsed;
  const displaySec = (displayMs / 1000).toFixed(1);

  if (startTime === null) return null;

  return (
    <div className={`font-display tabular-nums ${className}`}>
      <span style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
        {displaySec}
      </span>
      <span style={{ fontSize: '0.875rem', opacity: 0.5, marginLeft: '4px' }}>s</span>
    </div>
  );
}
