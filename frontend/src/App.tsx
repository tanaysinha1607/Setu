// ---------------------------------------------------------------------------
// Setu — App Shell
// ---------------------------------------------------------------------------
// Single-page app driven by Zustand phase state.  No router needed.

import { AnimatePresence } from 'framer-motion';
import { useStore } from './store';
import Hero from './components/Hero';
import InputSelector from './components/InputSelector';
import ProcessingView from './components/ProcessingView';
import ResultCard from './components/ResultCard';

export default function App() {
  const phase = useStore((s) => s.phase);

  return (
    <main style={{ minHeight: '100vh', position: 'relative' }}>
      <AnimatePresence mode="wait">
        {phase === 'hero' && <Hero key="hero" />}
        {phase === 'input' && <InputSelector key="input" />}
        {phase === 'processing' && <ProcessingView key="processing" />}
        {phase === 'result' && <ResultCard key="result" />}
      </AnimatePresence>
    </main>
  );
}
