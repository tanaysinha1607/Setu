// ---------------------------------------------------------------------------
// Setu — Input Selector
// ---------------------------------------------------------------------------
// Three mode cards (SMS, Ledger Photo, Voice Note) + sub-panels for data
// entry and pre-loaded demo samples.

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import type { ProcessRequest } from '../api/types';

// ── SMS samples (same 5 from extract_sms.py) ───────────────────────────────
const SMS_SAMPLES = [
  {
    label: 'Sample 1 — Clean (Consistent)',
    text:
      '10-07-26 09:30: Received INR 800.00 from Suresh K via UPI Ref 6293049102.\n' +
      '10-07-26 12:15: Received INR 1,100.00 from Priya M via UPI Ref 6293049221.\n' +
      '10-07-26 16:45: Received INR 950.00 from Ramesh S via UPI Ref 6293049381.\n' +
      '10-07-26 20:00: Received INR 1,050.00 from Amit B via UPI Ref 6293049442.\n' +
      'Summary: Payments are stable and recurring at similar times.',
  },
  {
    label: 'Sample 2 — Clean (Stable)',
    text:
      '11-07-26 09:45: Received INR 900.00 from Vikram L via UPI Ref 6293050110.\n' +
      '11-07-26 11:30: Received INR 1,000.00 from Priya M via UPI Ref 6293050201.\n' +
      '11-07-26 17:00: Received INR 850.00 from Suresh K via UPI Ref 6293050392.\n' +
      '11-07-26 19:30: Received INR 1,200.00 from Nitin P via UPI Ref 6293050410.\n' +
      'Summary: Stable transactions, consistent daily revenue.',
  },
  {
    label: 'Sample 3 — Natural Variance',
    text:
      '12-07-26 10:00: Received INR 500.00 from Joy D via UPI Ref 6293060123.\n' +
      '12-07-26 13:00: Received INR 2,500.00 from Rohit G via UPI Ref 6293060341.\n' +
      '12-07-26 18:30: Received INR 700.00 from Sneha V via UPI Ref 6293060592.\n' +
      'Summary: Fluctuation in transaction sizes, typical for weekend sales.',
  },
  {
    label: 'Sample 4 — Natural Variance',
    text:
      '13-07-26 08:30: Received INR 3,000.00 from Anand R via UPI Ref 6293070001.\n' +
      '13-07-26 14:15: Received INR 600.00 from Divya K via UPI Ref 6293070192.\n' +
      '13-07-26 21:00: Received INR 500.00 from Rahul P via UPI Ref 6293070441.\n' +
      'Summary: Moderate daily fluctuations, transaction amounts vary from INR 500 to INR 3000.',
  },
  {
    label: 'Sample 5 — Anomalous Spike',
    text:
      '14-07-26 09:00: Received INR 900.00 from Suresh K via UPI Ref 6293080101.\n' +
      '14-07-26 11:00: Received INR 18,500.00 from Corporate Corp via UPI Ref 6293080392.\n' +
      '14-07-26 15:30: Received INR 1,000.00 from Priya M via UPI Ref 6293080512.\n' +
      '14-07-26 19:00: Received INR 800.00 from Ramesh S via UPI Ref 6293080641.\n' +
      'Summary: A single massive transaction of INR 18500 occurs, which is ~20x the typical transaction size.',
  },
];

// ── Ledger demo samples ─────────────────────────────────────────────────────
const LEDGER_SAMPLES = [
  { label: 'Hariom Traders', file: '/samples/hariom_traders.jpeg', id: 'hariom' },
  { label: 'Shiva Builder', file: '/samples/shiva_builder.jpeg', id: 'shiva' },
  { label: 'Shree Ram Enterprises', file: '/samples/shree_ram_enterprises.jpeg', id: 'shree' },
];

// ── Mode card ───────────────────────────────────────────────────────────────
function ModeCard({
  icon,
  title,
  description,
  active,
  disabled,
  badge,
  onClick,
}: {
  icon: string;
  title: string;
  description: string;
  active: boolean;
  disabled?: boolean;
  badge?: string;
  onClick: () => void;
}) {
  return (
    <motion.button
      whileHover={disabled ? {} : { scale: 1.02, y: -2 }}
      whileTap={disabled ? {} : { scale: 0.98 }}
      onClick={disabled ? undefined : onClick}
      className={disabled ? '' : 'glass'}
      style={{
        position: 'relative',
        padding: '1.25rem 1rem',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: active
          ? '1px solid var(--setu-teal)'
          : '1px solid var(--setu-border)',
        borderRadius: '16px',
        background: disabled
          ? 'rgba(255,255,255,0.02)'
          : active
            ? 'var(--setu-teal-dim)'
            : 'var(--setu-surface)',
        opacity: disabled ? 0.4 : 1,
        width: '100%',
        fontFamily: 'var(--font-body)',
      }}
    >
      {badge && (
        <span
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            fontSize: '0.65rem',
            padding: '2px 8px',
            borderRadius: '99px',
            background: 'rgba(245, 158, 11, 0.15)',
            color: 'var(--setu-gold)',
            fontWeight: 600,
            letterSpacing: '0.03em',
          }}
        >
          {badge}
        </span>
      )}
      <div style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>{icon}</div>
      <div
        className="font-display"
        style={{
          fontWeight: 600,
          fontSize: '0.9rem',
          color: active ? 'var(--setu-teal)' : 'var(--text-primary)',
          marginBottom: '0.25rem',
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        {description}
      </div>
    </motion.button>
  );
}

// ── Main component ──────────────────────────────────────────────────────────
export default function InputSelector() {
  const { inputType, setInputType, startAssessment, setPhase } = useStore();
  const [smsText, setSmsText] = useState('');
  const [selectedSample, setSelectedSample] = useState<number | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [selectedLedger, setSelectedLedger] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSmsSubmit = () => {
    if (!smsText.trim()) return;
    const sampleIdx = selectedSample ?? 0;
    const req: ProcessRequest = {
      source_type: 'sms',
      raw_text: smsText,
      borrower_session_id: `demo_sample_${sampleIdx + 1}_${Date.now()}`,
    };
    startAssessment(req);
  };

  const handlePhotoSubmit = () => {
    if (!imageBase64) return;
    const req: ProcessRequest = {
      source_type: 'ledger_photo',
      image_data_base64: imageBase64,
      borrower_session_id: `demo_${selectedLedger || 'upload'}_${Date.now()}`,
    };
    startAssessment(req);
  };

  const loadDemoLedger = useCallback(async (sample: typeof LEDGER_SAMPLES[0]) => {
    setSelectedLedger(sample.id);
    setImagePreview(sample.file);
    try {
      const res = await fetch(sample.file);
      const blob = await res.blob();
      const reader = new FileReader();
      reader.onload = () => {
        setImageBase64(reader.result as string);
      };
      reader.readAsDataURL(blob);
    } catch {
      console.warn('Failed to load demo ledger image');
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedLedger(null);
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setImagePreview(result);
      setImageBase64(result);
    };
    reader.readAsDataURL(file);
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1rem',
      }}
    >
      <div style={{ width: '100%', maxWidth: '520px' }}>
        {/* Back button */}
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => setPhase('hero')}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: '0.85rem',
            marginBottom: '1.5rem',
            fontFamily: 'var(--font-body)',
          }}
        >
          ← Back
        </motion.button>

        <h2
          className="font-display"
          style={{
            fontSize: 'clamp(1.5rem, 4vw, 2rem)',
            fontWeight: 700,
            marginBottom: '0.5rem',
          }}
        >
          Choose Input Type
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
          Select the data source for credit risk assessment.
        </p>

        {/* Mode cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.75rem',
            marginBottom: '1.5rem',
          }}
        >
          <ModeCard
            icon="💬"
            title="SMS Text"
            description="Transaction messages"
            active={inputType === 'sms'}
            onClick={() => setInputType('sms')}
          />
          <ModeCard
            icon="📒"
            title="Ledger Photo"
            description="Daybook / notebook"
            active={inputType === 'photo'}
            onClick={() => setInputType('photo')}
          />
          <ModeCard
            icon="🎙️"
            title="Voice Note"
            description="Field officer Q&A"
            active={false}
            disabled
            badge="In Progress"
            onClick={() => {}}
          />
        </div>

        {/* ── SMS sub-panel ─────────────────────────────────────────────── */}
        <AnimatePresence mode="wait">
          {inputType === 'sms' && (
            <motion.div
              key="sms-panel"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="glass" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
                <label
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.5rem',
                    display: 'block',
                  }}
                >
                  Quick Demo Samples
                </label>
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.4rem',
                    marginBottom: '0.75rem',
                  }}
                >
                  {SMS_SAMPLES.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setSelectedSample(i);
                        setSmsText(s.text);
                      }}
                      style={{
                        fontSize: '0.7rem',
                        padding: '4px 10px',
                        borderRadius: '8px',
                        border:
                          selectedSample === i
                            ? '1px solid var(--setu-teal)'
                            : '1px solid var(--setu-border)',
                        background:
                          selectedSample === i
                            ? 'var(--setu-teal-dim)'
                            : 'var(--setu-surface)',
                        color:
                          selectedSample === i
                            ? 'var(--setu-teal)'
                            : 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontFamily: 'var(--font-body)',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>

                <textarea
                  value={smsText}
                  onChange={(e) => {
                    setSmsText(e.target.value);
                    setSelectedSample(null);
                  }}
                  placeholder="Paste SMS transaction text here..."
                  rows={6}
                  style={{
                    width: '100%',
                    background: 'rgba(0, 0, 0, 0.3)',
                    border: '1px solid var(--setu-border)',
                    borderRadius: '10px',
                    padding: '0.75rem',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.8rem',
                    lineHeight: 1.5,
                    resize: 'vertical',
                  }}
                />
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSmsSubmit}
                disabled={!smsText.trim()}
                style={{
                  width: '100%',
                  padding: '14px',
                  borderRadius: '12px',
                  border: 'none',
                  cursor: smsText.trim() ? 'pointer' : 'not-allowed',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  background: smsText.trim()
                    ? 'linear-gradient(135deg, #2dd4bf, #14b8a6)'
                    : 'rgba(255,255,255,0.05)',
                  color: smsText.trim() ? '#0a0e1a' : 'var(--text-muted)',
                  boxShadow: smsText.trim()
                    ? '0 0 20px rgba(45,212,191,0.25)'
                    : 'none',
                }}
              >
                Run Gemma Extraction →
              </motion.button>
            </motion.div>
          )}

          {/* ── Photo sub-panel ──────────────────────────────────────────── */}
          {inputType === 'photo' && (
            <motion.div
              key="photo-panel"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="glass" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
                <label
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.5rem',
                    display: 'block',
                  }}
                >
                  Demo Ledger Samples
                </label>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '0.5rem',
                    marginBottom: '0.75rem',
                  }}
                >
                  {LEDGER_SAMPLES.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => loadDemoLedger(s)}
                      style={{
                        padding: '0.6rem 0.5rem',
                        borderRadius: '10px',
                        border:
                          selectedLedger === s.id
                            ? '1px solid var(--setu-gold)'
                            : '1px solid var(--setu-border)',
                        background:
                          selectedLedger === s.id
                            ? 'var(--setu-gold-dim)'
                            : 'var(--setu-surface)',
                        color:
                          selectedLedger === s.id
                            ? 'var(--setu-gold)'
                            : 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontSize: '0.7rem',
                        fontFamily: 'var(--font-body)',
                        fontWeight: 500,
                        textAlign: 'center',
                      }}
                    >
                      📒 {s.label}
                    </button>
                  ))}
                </div>

                {/* File upload area */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const file = e.dataTransfer.files?.[0];
                    if (file) {
                      setSelectedLedger(null);
                      const reader = new FileReader();
                      reader.onload = () => {
                        const result = reader.result as string;
                        setImagePreview(result);
                        setImageBase64(result);
                      };
                      reader.readAsDataURL(file);
                    }
                  }}
                  style={{
                    border: '2px dashed var(--setu-border)',
                    borderRadius: '12px',
                    padding: '1.5rem 1rem',
                    textAlign: 'center',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    fontSize: '0.8rem',
                    transition: 'border-color 0.2s',
                  }}
                >
                  {imagePreview ? (
                    <img
                      src={imagePreview}
                      alt="Ledger preview"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '180px',
                        borderRadius: '8px',
                        objectFit: 'contain',
                      }}
                    />
                  ) : (
                    <>
                      <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📸</div>
                      <div>Drop a ledger image or tap to upload</div>
                    </>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handlePhotoSubmit}
                disabled={!imageBase64}
                style={{
                  width: '100%',
                  padding: '14px',
                  borderRadius: '12px',
                  border: 'none',
                  cursor: imageBase64 ? 'pointer' : 'not-allowed',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  background: imageBase64
                    ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                    : 'rgba(255,255,255,0.05)',
                  color: imageBase64 ? '#0a0e1a' : 'var(--text-muted)',
                  boxShadow: imageBase64
                    ? '0 0 20px rgba(245,158,11,0.25)'
                    : 'none',
                }}
              >
                Escalate to Cloud Vision →
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}
