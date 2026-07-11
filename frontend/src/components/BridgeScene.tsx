// ---------------------------------------------------------------------------
// Setu — 3D Bridge Scene (React Three Fiber)
// ---------------------------------------------------------------------------
// Lightweight 3D hero: two glowing nodes (Gemma ↔ Gemini) connected by an
// arc/bridge.  Accepts a `routeState` prop to animate routing decisions.
// Performance budget: ~20 draw calls, no postprocessing, no shadows.

import { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Html } from '@react-three/drei';
import * as THREE from 'three';

type RouteState = 'idle' | 'processing' | 'local' | 'escalate';

interface BridgeSceneProps {
  routeState?: RouteState;
  compact?: boolean;
}

// ── Colors ──────────────────────────────────────────────────────────────────
const TEAL = new THREE.Color('#2dd4bf');
const GOLD = new THREE.Color('#f59e0b');
const DIM_WHITE = new THREE.Color('#334155');
const BRIDGE_COLOR = new THREE.Color('#1e293b');

// ── Bridge curve ────────────────────────────────────────────────────────────
function useBridgeCurve() {
  return useMemo(() => {
    const points = [
      new THREE.Vector3(-3, 0, 0),
      new THREE.Vector3(-1.5, 1.2, 0),
      new THREE.Vector3(0, 1.6, 0),
      new THREE.Vector3(1.5, 1.2, 0),
      new THREE.Vector3(3, 0, 0),
    ];
    return new THREE.CatmullRomCurve3(points);
  }, []);
}

// ── Glowing node ────────────────────────────────────────────────────────────
function GlowNode({
  position,
  color,
  label,
  sublabel,
  active,
}: {
  position: [number, number, number];
  color: THREE.Color;
  label: string;
  sublabel: string;
  active: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.3;
    }
    if (glowRef.current) {
      const scale = active ? 1.8 + Math.sin(Date.now() * 0.003) * 0.3 : 1.4;
      glowRef.current.scale.setScalar(scale);
    }
  });

  return (
    <group position={position}>
      {/* Outer glow sphere */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={active ? 0.15 : 0.06}
        />
      </mesh>
      {/* Core sphere */}
      <Float speed={2} rotationIntensity={0.2} floatIntensity={0.3}>
        <mesh ref={meshRef}>
          <icosahedronGeometry args={[0.35, 1]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={active ? 1.5 : 0.4}
            roughness={0.3}
            metalness={0.7}
          />
        </mesh>
      </Float>
      {/* Label */}
      <Html
        position={[0, -1, 0]}
        center
        distanceFactor={8}
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        <div style={{ textAlign: 'center', whiteSpace: 'nowrap' }}>
          <div
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: '14px',
              color: `#${color.getHexString()}`,
              letterSpacing: '0.05em',
            }}
          >
            {label}
          </div>
          <div
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '11px',
              color: 'rgba(255,255,255,0.45)',
              marginTop: '2px',
            }}
          >
            {sublabel}
          </div>
        </div>
      </Html>
    </group>
  );
}

// ── Bridge arc ──────────────────────────────────────────────────────────────
function BridgeArc() {
  const curve = useBridgeCurve();
  const tubeGeom = useMemo(
    () => new THREE.TubeGeometry(curve, 32, 0.04, 8, false),
    [curve],
  );

  return (
    <mesh geometry={tubeGeom}>
      <meshStandardMaterial
        color={BRIDGE_COLOR}
        emissive={BRIDGE_COLOR}
        emissiveIntensity={0.3}
        transparent
        opacity={0.5}
        roughness={0.5}
      />
    </mesh>
  );
}

// ── Travelling packet (the "money animation") ───────────────────────────────
function TravellingPacket({ routeState }: { routeState: RouteState }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const curve = useBridgeCurve();
  const progressRef = useRef(0);
  const [packetColor, setPacketColor] = useState(TEAL);

  useEffect(() => {
    if (routeState === 'processing') {
      progressRef.current = 0;
    }
  }, [routeState]);

  useFrame((_, delta) => {
    if (!meshRef.current) return;

    if (routeState === 'idle') {
      meshRef.current.visible = false;
      return;
    }

    meshRef.current.visible = true;

    if (routeState === 'processing') {
      // Travel from left (0) toward midpoint (0.5)
      progressRef.current = Math.min(progressRef.current + delta * 0.3, 0.5);
      setPacketColor(TEAL);
    } else if (routeState === 'local') {
      // Retreat back toward left node
      progressRef.current = Math.max(progressRef.current - delta * 0.5, 0.05);
      setPacketColor(TEAL);
    } else if (routeState === 'escalate') {
      // Continue to right node
      progressRef.current = Math.min(progressRef.current + delta * 0.4, 0.95);
      setPacketColor(GOLD);
    }

    const point = curve.getPoint(progressRef.current);
    meshRef.current.position.copy(point);
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.12, 12, 12]} />
      <meshStandardMaterial
        color={packetColor}
        emissive={packetColor}
        emissiveIntensity={2}
        toneMapped={false}
      />
    </mesh>
  );
}

// ── Particle field (subtle background depth) ────────────────────────────────
function Particles() {
  const points = useMemo(() => {
    const positions = new Float32Array(60 * 3);
    for (let i = 0; i < 60; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 8;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 6;
    }
    return positions;
  }, []);

  const ref = useRef<THREE.Points>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.02;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[points, 3]}
          count={60}
        />
      </bufferGeometry>
      <pointsMaterial
        color={DIM_WHITE}
        size={0.03}
        transparent
        opacity={0.4}
        sizeAttenuation
      />
    </points>
  );
}

// ── Scene internals ─────────────────────────────────────────────────────────
function SceneContent({ routeState }: { routeState: RouteState }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.05;
    }
  });

  const isGemmaActive =
    routeState === 'processing' || routeState === 'local';
  const isGeminiActive = routeState === 'escalate';

  return (
    <group ref={groupRef}>
      <GlowNode
        position={[-3, 0, 0]}
        color={TEAL}
        label="Gemma"
        sublabel="On-Device"
        active={isGemmaActive}
      />
      <GlowNode
        position={[3, 0, 0]}
        color={GOLD}
        label="Gemini"
        sublabel="Cloud"
        active={isGeminiActive}
      />
      <BridgeArc />
      <TravellingPacket routeState={routeState} />
      <Particles />
    </group>
  );
}

// ── Exported component ──────────────────────────────────────────────────────
export default function BridgeScene({
  routeState = 'idle',
  compact = false,
}: BridgeSceneProps) {
  return (
    <div
      style={{
        width: '100%',
        height: compact ? '220px' : '400px',
        position: 'relative',
      }}
    >
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 1, 7], fov: 45 }}
        style={{ background: 'transparent' }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={0.6} color="#ffffff" />
        <pointLight position={[-5, 3, 3]} intensity={0.3} color="#2dd4bf" />
        <pointLight position={[5, 3, 3]} intensity={0.3} color="#f59e0b" />

        <SceneContent routeState={routeState} />
      </Canvas>

      {/* Gradient fade at bottom for seamless blend into content */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '80px',
          background:
            'linear-gradient(transparent, var(--setu-bg, #0a0e1a))',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
}
