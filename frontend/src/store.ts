// ---------------------------------------------------------------------------
// Setu — Zustand global state store
// ---------------------------------------------------------------------------

import { create } from 'zustand';
import { submitAssessment } from './api/client';
import type { AppState, ProcessRequest } from './api/types';

export const useStore = create<AppState>((set) => ({
  // ── Navigation ──
  phase: 'hero',
  setPhase: (p) => set({ phase: p }),

  // ── Input ──
  inputType: null,
  setInputType: (t) => set({ inputType: t }),

  // ── Processing & results ──
  isLoading: false,
  routeTaken: null,
  result: null,
  error: null,
  requestStartTime: null,

  // ── Actions ──
  startAssessment: async (req: ProcessRequest) => {
    set({
      phase: 'processing',
      isLoading: true,
      routeTaken: null,
      result: null,
      error: null,
      requestStartTime: performance.now(),
    });

    try {
      const response = await submitAssessment(req);
      set({
        isLoading: false,
        routeTaken: response.route,
        result: response,
        phase: 'result',
      });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Unknown error',
        phase: 'result',
      });
    }
  },

  reset: () =>
    set({
      phase: 'input',
      inputType: null,
      isLoading: false,
      routeTaken: null,
      result: null,
      error: null,
      requestStartTime: null,
    }),
}));
