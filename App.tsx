import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Canvas } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Environment, ContactShadows, Sphere } from '@react-three/drei';
import {
  LayoutGrid, ShieldAlert, FlaskConical, Swords,
  MessageSquare, BarChart3, Sun, Moon, Bell, TrendingUp, Cpu, Settings, BrainCircuit,
} from 'lucide-react';

import Dashboard   from './pages/Dashboard';
import AIControl   from './pages/AIControl';
import Arena       from './pages/Arena';
import DebateRoom  from './pages/DebateRoom';
import Backtest    from './pages/Backtest';
import StrategyLab from './pages/StrategyLab';
import RiskConsole from './pages/RiskConsole';
import PriceStrip  from './components/PriceStrip';

// ─── Noise overlay ────────────────────────────────────────────────────────────
function NoiseLayer() {
  return (
    <div style={{ position:'fixed',inset:0,zIndex:100,pointerEvents:'none',opacity:0.025,mixBlendMode:'overlay' as any }}>
      <svg viewBox="0 0 200 200" style={{ width:'100%',height:'100%' }}>
        <filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch"/></filter>
        <rect width="100%" height="100%" filter="url(#n)"/>
      </svg>
    </div>
  );
}

// ─── 3D Intro orb ────────────────────────────────────────────────────────────
function IntroOrb({ isDark }: { isDark: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div ref={ref} style={{ width:'100%',height:'100%' }}>
      <Canvas camera={{ position:[0,0,4.5], fov:45 }} eventSource={ref}>
        <ambientLight intensity={0.5}/>
        <directionalLight position={[10,10,5]} intensity={1.5}/>
        <Environment preset={isDark ? 'city' : 'studio'}/>
        <Float speed={4} rotationIntensity={1.5} floatIntensity={2}>
          <Sphere args={[1.2,64,64]}>
            <MeshDistortMaterial
              color={isDark ? '#ffffff' : '#18181b'}
              envMapIntensity={2} clearcoat={1} clearcoatRoughness={0.1}
              metalness={0.9} roughness={0.1} distort={0.4} speed={2}
            />
          </Sphere>
        </Float>
        <ContactShadows position={[0,-2,0]} opacity={0.4} scale={10} blur={2} far={4}/>
      </Canvas>
    </div>
  );
}

// ─── Intro screen ─────────────────────────────────────────────────────────────
function IntroScreen({ onComplete, isDark }: { onComplete: ()=>void; isDark: boolean }) {
  useEffect(() => { const t = setTimeout(onComplete, 3400); return () => clearTimeout(t); }, [onComplete]);
  const bg = isDark ? '#09090b' : '#FAFAFA';
  return (
    <motion.div
      initial={{ opacity:1 }} exit={{ opacity:0, filter:'blur(20px)', scale:1.05 }}
      transition={{ duration:1.2, ease:[0.22,1,0.36,1] }}
      style={{ position:'fixed',inset:0,zIndex:200,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',overflow:'hidden',background:bg }}
    >
      <div style={{ position:'absolute',inset:0 }}><IntroOrb isDark={isDark}/></div>
      <NoiseLayer/>
      <motion.div
        initial={{ opacity:0,y:20 }} animate={{ opacity:1,y:0 }}
        transition={{ delay:0.5,duration:1,ease:[0.22,1,0.36,1] }}
        style={{ position:'relative',zIndex:10,display:'flex',flexDirection:'column',alignItems:'center',marginTop:'30vh',pointerEvents:'none' }}
      >
        <h1 style={{ fontSize:72,fontWeight:800,letterSpacing:'-0.04em',color:isDark?'#fafafa':'#09090b',lineHeight:1 }}>
          APEX<span style={{ color:isDark?'#52525b':'#a1a1aa' }}>.</span>
        </h1>
        <motion.div
          initial={{ scaleX:0 }} animate={{ scaleX:1 }}
          transition={{ delay:1.4,duration:1.2,ease:'easeInOut' }}
          style={{ transformOrigin:'left',height:1,width:260,marginTop:20,background:isDark?'#27272a':'#e4e4e7' }}
        />
        <motion.p
          initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:1.8 }}
          style={{ marginTop:16,fontSize:11,fontWeight:600,letterSpacing:'0.22em',textTransform:'uppercase',color:isDark?'#52525b':'#a1a1aa' }}
        >
          AI-Powered Forex Trading System
        </motion.p>
        <motion.div initial={{ opacity:0,y:8 }} animate={{ opacity:1,y:0 }} transition={{ delay:2.5 }} style={{ marginTop:20 }}>
          <span style={{ display:'inline-flex',alignItems:'center',gap:6,padding:'5px 14px',borderRadius:99,fontSize:11,fontWeight:600,letterSpacing:'0.06em',textTransform:'uppercase',
            color:'#10b981',background:'rgba(16,185,129,0.1)',border:'1px solid rgba(16,185,129,0.25)' }}>
            <span style={{ width:6,height:6,borderRadius:'50%',background:'#10b981',animation:'pulse-dot 2s infinite' }}/>
            40+ Strategies · ML Active · OANDA Live
          </span>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

// ─── Navigation items ─────────────────────────────────────────────────────────
const NAV = [
  { icon: LayoutGrid,    label: 'Dashboard',    path: '/' },
  { icon: BrainCircuit,  label: 'AI Control',   path: '/ai-control' },
  { icon: Swords,        label: 'AI Arena',     path: '/arena' },
  { icon: MessageSquare, label: 'Debate Room',  path: '/debate' },
  { icon: BarChart3,     label: 'Backtest',     path: '/backtest' },
  { icon: FlaskConical,  label: 'Strategy Lab', path: '/strategies' },
  { icon: ShieldAlert,   label: 'Risk Console', path: '/risk' },
];

function NavItem({ icon: Icon, label, active, onClick, isDark }: any) {
  const activeStyle = isDark
    ? { background:'#ffffff',color:'#09090b' }
    : { background:'#09090b',color:'#ffffff' };
  const inactiveStyle = isDark
    ? { background:'transparent',color:'#71717a' }
    : { background:'transparent',color:'#71717a' };

  return (
    <button
      onClick={onClick}
      style={{ position:'relative',width:'100%',display:'flex',alignItems:'center',gap:10,padding:'9px 12px',
        borderRadius:12,border:'none',cursor:'pointer',transition:'all 0.2s',
        fontSize:13,fontWeight:500,overflow:'hidden',
        ...(active ? activeStyle : inactiveStyle) }}
      onMouseEnter={e => { if(!active) e.currentTarget.style.background = isDark?'rgba(255,255,255,0.07)':'rgba(0,0,0,0.05)'; }}
      onMouseLeave={e => { if(!active) e.currentTarget.style.background = 'transparent'; }}
    >
      {active && (
        <motion.div
          layoutId="nav-indicator"
          style={{ position:'absolute',inset:0,borderRadius:12,background:isDark?'#ffffff':'#09090b' }}
          transition={{ type:'spring',stiffness:320,damping:30 }}
        />
      )}
      <Icon size={14} style={{ position:'relative',zIndex:1,flexShrink:0 }}/>
      <span style={{ position:'relative',zIndex:1 }}>{label}</span>
    </button>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [showIntro, setShowIntro] = useState(true);
  const [isDark,    setIsDark]    = useState(true);
  const navigate  = useNavigate();
  const location  = useLocation();

  useEffect(() => {
    document.body.style.backgroundColor = isDark ? '#09090b' : '#FAFAFA';
  }, [isDark]);

  const page = NAV.find(n => n.path === location.pathname)?.label || 'Overview';

  const C = {
    bg:     isDark ? '#09090b'                   : '#FAFAFA',
    card:   isDark ? 'rgba(24,24,27,0.7)'        : 'rgba(255,255,255,0.8)',
    border: isDark ? 'rgba(255,255,255,0.07)'    : 'rgba(0,0,0,0.06)',
    text:   isDark ? '#fafafa'                   : '#09090b',
    sub:    isDark ? '#71717a'                   : '#71717a',
    sidebar:isDark ? 'rgba(18,18,20,0.8)'        : 'rgba(255,255,255,0.85)',
    header: isDark ? 'rgba(9,9,11,0.7)'          : 'rgba(250,250,250,0.7)',
  };

  return (
    <>
      <NoiseLayer/>
      <AnimatePresence>
        {showIntro && <IntroScreen onComplete={() => setShowIntro(false)} isDark={isDark}/>}
      </AnimatePresence>

      <div style={{ display:'flex',flexDirection:'column',height:'100vh',background:C.bg,color:C.text,transition:'background 0.4s,color 0.4s',fontFamily:"'Inter',-apple-system,sans-serif" }}>
        {/* Price ticker */}
        <PriceStrip isDark={isDark}/>

        <div style={{ display:'flex',flex:1,overflow:'hidden' }}>

          {/* ── Sidebar ─────────────────────────────────────────── */}
          <aside style={{ width:220,flexShrink:0,display:'flex',flexDirection:'column',justifyContent:'space-between',
            background:C.sidebar,borderRight:`1px solid ${C.border}`,backdropFilter:'blur(24px)',
            WebkitBackdropFilter:'blur(24px)',zIndex:20,transition:'background 0.4s' }}>
            <div>
              {/* Logo */}
              <div style={{ height:56,display:'flex',alignItems:'center',gap:10,padding:'0 16px',borderBottom:`1px solid ${C.border}` }}>
                <div style={{ width:26,height:26,borderRadius:7,background:isDark?'#fafafa':'#09090b',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
                  <TrendingUp size={12} color={isDark?'#09090b':'#fafafa'}/>
                </div>
                <span style={{ fontSize:15,fontWeight:800,letterSpacing:'-0.04em',color:C.text }}>
                  APEX<span style={{ color:C.sub }}>.</span>
                </span>
              </div>

              {/* Navigation */}
              <nav style={{ padding:'10px 8px',display:'flex',flexDirection:'column',gap:2 }}>
                {NAV.map(item => (
                  <NavItem key={item.path} icon={item.icon} label={item.label}
                    active={location.pathname === item.path}
                    onClick={() => navigate(item.path)} isDark={isDark}
                  />
                ))}
              </nav>
            </div>

            {/* Bottom */}
            <div style={{ padding:'8px',borderTop:`1px solid ${C.border}` }}>
              <div style={{ display:'flex',alignItems:'center',gap:6,padding:'7px 10px',borderRadius:9,marginBottom:4,
                background:'rgba(16,185,129,0.08)',border:'1px solid rgba(16,185,129,0.15)' }}>
                <span style={{ width:5,height:5,borderRadius:'50%',background:'#10b981',flexShrink:0,animation:'pulse-dot 2s infinite' }}/>
                <span style={{ fontSize:10.5,fontWeight:600,color:'#10b981',letterSpacing:'0.04em' }}>OANDA Live · ML Active</span>
              </div>
              <button
                onClick={() => setIsDark(!isDark)}
                style={{ width:'100%',display:'flex',alignItems:'center',gap:8,padding:'8px 10px',borderRadius:9,border:'none',cursor:'pointer',
                  background:'transparent',color:C.sub,fontSize:12.5,fontWeight:500,transition:'background 0.2s' }}
                onMouseEnter={e => e.currentTarget.style.background = isDark?'rgba(255,255,255,0.05)':'rgba(0,0,0,0.04)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                {isDark ? <Sun size={13}/> : <Moon size={13}/>}
                {isDark ? 'Light mode' : 'Dark mode'}
              </button>
            </div>
          </aside>

          {/* ── Main content ─────────────────────────────────────── */}
          <main style={{ flex:1,display:'flex',flexDirection:'column',overflow:'hidden' }}>

            {/* Header */}
            <header style={{ height:56,flexShrink:0,display:'flex',alignItems:'center',justifyContent:'space-between',
              padding:'0 24px',background:C.header,borderBottom:`1px solid ${C.border}`,
              backdropFilter:'blur(24px)',WebkitBackdropFilter:'blur(24px)',transition:'background 0.4s',position:'sticky',top:0,zIndex:10 }}>
              <div style={{ display:'flex',alignItems:'center',gap:6,fontSize:13 }}>
                <span style={{ color:C.sub }}>APEX</span>
                <span style={{ color:isDark?'#3f3f46':'#d4d4d8' }}>/</span>
                <span style={{ color:C.text,fontWeight:500 }}>{page}</span>
              </div>
              <div style={{ display:'flex',gap:8,alignItems:'center' }}>
                <div style={{ display:'flex',alignItems:'center',gap:5,padding:'4px 10px',borderRadius:8,
                  background:'rgba(139,92,246,0.08)',border:'1px solid rgba(139,92,246,0.18)',
                  fontSize:10.5,fontWeight:600,color:'#8b5cf6',letterSpacing:'0.04em' }}>
                  <Cpu size={10}/>40+ Strategies · ML Gate Active
                </div>
                <button style={{ padding:'6px',borderRadius:8,border:'none',cursor:'pointer',background:'transparent',color:C.sub }}>
                  <Bell size={14}/>
                </button>
                <button style={{ padding:'6px',borderRadius:8,border:'none',cursor:'pointer',background:'transparent',color:C.sub }}>
                  <Settings size={14}/>
                </button>
              </div>
            </header>

            {/* Page content with transitions */}
            <div style={{ flex:1,overflow:'hidden' }}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  initial={{ opacity:0,y:8 }} animate={{ opacity:1,y:0 }}
                  exit={{ opacity:0,y:-6 }} transition={{ duration:0.2,ease:[0.22,1,0.36,1] }}
                  style={{ height:'100%',overflow:'hidden' }}
                >
                  <Routes>
                    <Route path="/"           element={<Dashboard   isDark={isDark}/>}/>
                    <Route path="/ai-control" element={<AIControl   isDark={isDark}/>}/>
                    <Route path="/arena"      element={<Arena        isDark={isDark}/>}/>
                    <Route path="/debate"     element={<DebateRoom   isDark={isDark}/>}/>
                    <Route path="/backtest"   element={<Backtest     isDark={isDark}/>}/>
                    <Route path="/strategies" element={<StrategyLab  isDark={isDark}/>}/>
                    <Route path="/risk"       element={<RiskConsole  isDark={isDark}/>}/>
                  </Routes>
                </motion.div>
              </AnimatePresence>
            </div>
          </main>
        </div>
      </div>
    </>
  );
}
