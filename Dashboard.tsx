import { useRef } from 'react';
import { motion } from 'motion/react';
import { ArrowUpRight, ArrowDownRight, RefreshCw, Sparkles, MoreHorizontal, Activity } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Canvas } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Environment, Sphere } from '@react-three/drei';
import { useFetch } from '../hooks/useApi';

const DEMO_EQUITY = [
  {t:'Jan',v:100000},{t:'Feb',v:102400},{t:'Mar',v:101100},{t:'Apr',v:105800},
  {t:'May',v:108200},{t:'Jun',v:106900},{t:'Jul',v:112300},{t:'Aug',v:116100},
  {t:'Sep',v:113400},{t:'Oct',v:118200},{t:'Nov',v:122100},{t:'Dec',v:127800},
];
const DEMO_SIGNALS = [
  {ai_model:'claude',   instrument:'EUR/USD',action:'BUY',  confidence:0.84,reasoning:'FVG filled at 1.0841. EMA 9/21 golden cross H1. Order block respected.'},
  {ai_model:'deepseek', instrument:'XAU/USD',action:'SELL', confidence:0.77,reasoning:'Overbought D1 RSI (76). Supply zone 2345. Supertrend flipping bearish.'},
  {ai_model:'gpt4o',    instrument:'GBP/USD',action:'BUY',  confidence:0.71,reasoning:'London breakout above Asian high 1.2682. Volume 2.3x. BOS confirmed.'},
  {ai_model:'grok',     instrument:'US500',  action:'HOLD', confidence:0.55,reasoning:'Mixed signals. Waiting for 5287. No high-conviction setup yet.'},
];
const MODEL_COLORS: Record<string,string> = {
  deepseek:'#a78bfa', gpt4o:'#10b981', claude:'#f59e0b',
  gemini:'#3b82f6',   grok:'#06b6d4',  qwen:'#f43f5e',
};

// ─── Shared card style ────────────────────────────────────────────────────────
function cardStyle(isDark: boolean, extra: any = {}) {
  return {
    background:    isDark ? 'rgba(24,24,27,0.65)' : 'rgba(255,255,255,0.75)',
    border:        `1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'}`,
    boxShadow:     isDark ? '0 4px 24px rgba(0,0,0,0.3)' : '0 4px 24px rgba(0,0,0,0.06)',
    backdropFilter:'blur(20px)',
    WebkitBackdropFilter:'blur(20px)',
    borderRadius:  20,
    ...extra,
  };
}

// ─── 3D Neural Engine orb ────────────────────────────────────────────────────
function NeuralOrb({ isDark }: { isDark: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div ref={ref} style={{ width:'100%',height:'100%' }}>
      <Canvas camera={{ position:[0,0,3] }} eventSource={ref}>
        <ambientLight intensity={1}/>
        <directionalLight position={[2,2,2]} intensity={2}/>
        <Environment preset={isDark?'city':'studio'}/>
        <Float speed={3} rotationIntensity={1} floatIntensity={2}>
          <Sphere args={[1,64,64]}>
            <MeshDistortMaterial
              color={isDark?'#10b981':'#059669'}
              envMapIntensity={2} metalness={0.8} roughness={0.2}
              distort={0.4} speed={3}
            />
          </Sphere>
        </Float>
      </Canvas>
    </div>
  );
}

// ─── Metric card ─────────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, trend, isDark, delay }: any) {
  const positive = trend === null || trend >= 0;
  return (
    <motion.div
      initial={{ opacity:0,y:20 }} animate={{ opacity:1,y:0 }}
      whileHover={{ y:-3,scale:1.005 }}
      transition={{ duration:0.5,delay,ease:[0.22,1,0.36,1] }}
      style={{ ...cardStyle(isDark),padding:20,position:'relative',overflow:'hidden' }}
    >
      <div style={{ position:'absolute',inset:0,borderRadius:20,background:'linear-gradient(135deg,rgba(255,255,255,0.04),transparent)',opacity:0,transition:'opacity 0.4s' }}
        onMouseEnter={e => (e.currentTarget as HTMLElement).style.opacity='1'}
        onMouseLeave={e => (e.currentTarget as HTMLElement).style.opacity='0'}
      />
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:12,position:'relative',zIndex:1 }}>
        <p style={{ fontSize:11,fontWeight:600,letterSpacing:'0.07em',textTransform:'uppercase',color:isDark?'#71717a':'#a1a1aa' }}>{label}</p>
        {trend !== null && (
          <span style={{ display:'inline-flex',alignItems:'center',gap:3,padding:'2px 7px',borderRadius:6,fontSize:10,fontWeight:700,letterSpacing:'0.04em',
            color:positive?'#10b981':'#ef4444',background:positive?'rgba(16,185,129,0.1)':'rgba(239,68,68,0.1)' }}>
            {positive ? <ArrowUpRight size={9}/> : <ArrowDownRight size={9}/>}{Math.abs(trend)}%
          </span>
        )}
      </div>
      <div style={{ fontSize:28,fontWeight:700,letterSpacing:'-0.03em',color:isDark?'#fafafa':'#09090b',position:'relative',zIndex:1,fontVariantNumeric:'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize:11.5,color:isDark?'#52525b':'#a1a1aa',marginTop:4,position:'relative',zIndex:1 }}>{sub}</div>}
    </motion.div>
  );
}

// ─── Custom chart tooltip ────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label, isDark }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ padding:'10px 14px',borderRadius:12,border:`1px solid ${isDark?'rgba(255,255,255,0.1)':'rgba(0,0,0,0.08)'}`,
      background:isDark?'rgba(24,24,27,0.95)':'rgba(255,255,255,0.95)',backdropFilter:'blur(16px)',boxShadow:'0 8px 32px rgba(0,0,0,0.2)' }}>
      <p style={{ fontSize:11,color:isDark?'#71717a':'#a1a1aa',marginBottom:4 }}>{label}</p>
      <p style={{ fontSize:14,fontWeight:600,color:isDark?'#fafafa':'#09090b',fontFamily:'JetBrains Mono,monospace' }}>
        ${payload[0].value.toLocaleString()}
      </p>
    </div>
  );
}

// ─── Signal row ────────────────────────────────────────────────────────────
function SignalRow({ sig, isDark }: { sig: any; isDark: boolean }) {
  const color = MODEL_COLORS[sig.ai_model] || '#71717a';
  const isLong  = sig.action === 'BUY';
  const isShort = sig.action === 'SELL';
  return (
    <div style={{ display:'flex',alignItems:'center',gap:12,padding:'12px 0',
      borderBottom:`1px solid ${isDark?'rgba(255,255,255,0.04)':'rgba(0,0,0,0.04)'}` }}>
      <div style={{ width:7,height:7,borderRadius:'50%',background:color,flexShrink:0 }}/>
      <div style={{ flex:1,minWidth:0 }}>
        <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:3 }}>
          <span style={{ fontSize:12,fontWeight:700,color,letterSpacing:'0.04em',textTransform:'uppercase' }}>{sig.ai_model}</span>
          <span style={{ fontSize:12,fontWeight:600,color:isDark?'#e4e4e7':'#18181b' }}>{sig.instrument}</span>
          <span style={{ padding:'1px 7px',borderRadius:5,fontSize:10,fontWeight:700,letterSpacing:'0.06em',
            color:isLong?'#10b981':isShort?'#ef4444':'#f59e0b',
            background:isLong?'rgba(16,185,129,0.1)':isShort?'rgba(239,68,68,0.1)':'rgba(245,158,11,0.1)' }}>
            {sig.action}
          </span>
        </div>
        <p style={{ fontSize:11,color:isDark?'#52525b':'#a1a1aa',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>{sig.reasoning}</p>
      </div>
      <div style={{ textAlign:'right',flexShrink:0 }}>
        <div style={{ fontSize:11,fontWeight:700,color:isDark?'#e4e4e7':'#18181b',fontFamily:'JetBrains Mono,monospace' }}>
          {(sig.confidence*100).toFixed(0)}%
        </div>
        <div style={{ fontSize:10,color:isDark?'#52525b':'#a1a1aa' }}>confidence</div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard({ isDark }: { isDark: boolean }) {
  const { data: acct,   refresh } = useFetch<any>('/account/summary', 10000);
  const { data: sigs }            = useFetch<any>('/ai/signals',       15000);
  const { data: equity }          = useFetch<any>('/account/equity-history', 60000);

  const nav      = acct?.NAV              ?? 127_800;
  const pnl      = acct?.total_pnl       ?? 27_800;
  const pnlPct   = acct?.total_pnl_pct   ?? 27.8;
  const winRate  = acct?.win_rate         ?? 62;
  const sharpe   = acct?.sharpe_ratio     ?? 2.1;
  const drawdown = acct?.max_drawdown_pct ?? 4.2;

  const chartData    = equity?.data    ?? DEMO_EQUITY;
  const recentSigs   = sigs?.signals   ?? DEMO_SIGNALS;
  const lineColor    = isDark ? '#ffffff' : '#09090b';

  return (
    <div style={{ display:'flex',flexDirection:'column',height:'100%',overflow:'hidden' }}>
      {/* ── Page header ─────────────────────────────────────────────── */}
      <div style={{ padding:'18px 24px 14px',borderBottom:`1px solid ${isDark?'rgba(255,255,255,0.05)':'rgba(0,0,0,0.05)'}`,
        display:'flex',justifyContent:'space-between',alignItems:'flex-end' }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:700,letterSpacing:'-0.03em',color:isDark?'#fafafa':'#09090b' }}>
            Executive Overview<span style={{ color:isDark?'#3f3f46':'#d4d4d8' }}>.</span>
          </h1>
          <p style={{ fontSize:12.5,color:isDark?'#71717a':'#a1a1aa',marginTop:3 }}>
            Live OANDA account · AI signal feed · Portfolio metrics
          </p>
        </div>
        <button
          onClick={refresh}
          style={{ display:'flex',alignItems:'center',gap:6,padding:'7px 13px',borderRadius:10,
            border:`1px solid ${isDark?'rgba(255,255,255,0.08)':'rgba(0,0,0,0.08)'}`,
            background:'transparent',cursor:'pointer',fontSize:12,fontWeight:500,color:isDark?'#71717a':'#71717a',
            transition:'all 0.2s' }}>
          <RefreshCw size={11}/>Live
        </button>
      </div>

      {/* ── Scrollable content ──────────────────────────────────────── */}
      <div style={{ flex:1,overflowY:'auto',padding:'18px 24px',display:'flex',flexDirection:'column',gap:16 }}>

        {/* Metric cards */}
        <div style={{ display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12 }}>
          <MetricCard label="Portfolio Value" value={`$${nav.toLocaleString()}`}     sub="Net Asset Value"            trend={pnlPct}   isDark={isDark} delay={0}    />
          <MetricCard label="Total P&L"       value={`${pnl>=0?'+':''}$${pnl.toFixed(0)}`} sub={`${pnlPct>=0?'+':''}${pnlPct.toFixed(1)}% all-time`} trend={pnlPct} isDark={isDark} delay={0.06} />
          <MetricCard label="Win Rate"        value={`${winRate}%`}                  sub="Across all strategies"      trend={3.2}      isDark={isDark} delay={0.12} />
          <MetricCard label="Sharpe Ratio"    value={sharpe.toFixed(2)}              sub={`Max DD: ${drawdown.toFixed(1)}%`} trend={null} isDark={isDark} delay={0.18} />
        </div>

        {/* Chart + Neural Engine */}
        <div style={{ display:'grid',gridTemplateColumns:'1fr 300px',gap:12 }}>

          {/* Area chart */}
          <motion.div initial={{ opacity:0,y:20 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.55,delay:0.24,ease:[0.22,1,0.36,1] }}
            style={{ ...cardStyle(isDark),padding:'22px 22px 16px',position:'relative',overflow:'hidden' }}>
            {/* Glow */}
            <div style={{ position:'absolute',top:0,left:'50%',transform:'translateX(-50%)',width:500,height:220,
              borderRadius:'50%',filter:'blur(90px)',opacity:0.07,background:lineColor,pointerEvents:'none' }}/>
            <div style={{ display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:20,position:'relative',zIndex:1 }}>
              <div>
                <h2 style={{ fontSize:15,fontWeight:600,letterSpacing:'-0.02em',color:isDark?'#fafafa':'#09090b' }}>Equity Growth</h2>
                <p style={{ fontSize:11.5,color:isDark?'#71717a':'#a1a1aa',marginTop:2 }}>Portfolio performance over 12 months</p>
              </div>
              <select style={{ border:`1px solid ${isDark?'rgba(255,255,255,0.1)':'rgba(0,0,0,0.08)'}`,borderRadius:8,padding:'5px 10px',fontSize:11.5,
                background:isDark?'rgba(39,39,42,0.8)':'rgba(255,255,255,0.8)',color:isDark?'#e4e4e7':'#3f3f46',cursor:'pointer',outline:'none' }}>
                <option>Last 12 Months</option><option>Year to Date</option><option>All Time</option>
              </select>
            </div>
            <div style={{ height:240,position:'relative',zIndex:1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top:5,right:0,left:-12,bottom:0 }}>
                  <defs>
                    <linearGradient id="grad-equity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={lineColor} stopOpacity={0.18}/>
                      <stop offset="95%" stopColor={lineColor} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark?'rgba(255,255,255,0.05)':'rgba(0,0,0,0.06)'}/>
                  <XAxis dataKey="t" axisLine={false} tickLine={false} tick={{ fill:isDark?'#52525b':'#a1a1aa',fontSize:11 }} dy={8}/>
                  <YAxis axisLine={false} tickLine={false} tick={{ fill:isDark?'#52525b':'#a1a1aa',fontSize:11 }} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`}/>
                  <Tooltip content={<ChartTooltip isDark={isDark}/>}/>
                  <Area type="monotone" dataKey="v" stroke={lineColor} strokeWidth={1.5} fill="url(#grad-equity)"
                    activeDot={{ r:5,fill:lineColor,strokeWidth:0 }}/>
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Neural Engine 3D card */}
          <motion.div initial={{ opacity:0,y:20 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.55,delay:0.3,ease:[0.22,1,0.36,1] }}
            style={{ ...cardStyle(isDark),padding:22,position:'relative',overflow:'hidden',display:'flex',flexDirection:'column' }}>
            <div style={{ position:'relative',zIndex:10 }}>
              <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:5 }}>
                <Sparkles size={14} color="#10b981"/>
                <h2 style={{ fontSize:15,fontWeight:600,letterSpacing:'-0.02em',color:isDark?'#fafafa':'#09090b' }}>Neural Engine</h2>
              </div>
              <p style={{ fontSize:11.5,color:isDark?'#71717a':'#a1a1aa' }}>ML ensemble actively filtering signals</p>
              <div style={{ marginTop:20,display:'flex',flexDirection:'column',gap:13 }}>
                {[
                  { k:'Status',        v:'Active',      c:'#10b981' },
                  { k:'ML Threshold',  v:'65%',         c:isDark?'#e4e4e7':'#18181b' },
                  { k:'Regime',        v:'Trending',    c:'#f59e0b' },
                  { k:'Active Strats', v:'40 / 43',     c:isDark?'#e4e4e7':'#18181b' },
                  { k:'Last Retrain',  v:'3 days ago',  c:isDark?'#e4e4e7':'#18181b' },
                ].map(row => (
                  <div key={row.k} style={{ display:'flex',justifyContent:'space-between',alignItems:'center',fontSize:12 }}>
                    <span style={{ color:isDark?'#71717a':'#a1a1aa' }}>{row.k}</span>
                    <span style={{ fontWeight:600,color:row.c,fontFamily:'JetBrains Mono,monospace',fontSize:12 }}>{row.v}</span>
                  </div>
                ))}
              </div>
            </div>
            {/* 3D orb background */}
            <div style={{ position:'absolute',right:-60,bottom:-60,width:200,height:200,opacity:0.55,pointerEvents:'none' }}>
              <NeuralOrb isDark={isDark}/>
            </div>
          </motion.div>
        </div>

        {/* Recent AI Signals */}
        <motion.div initial={{ opacity:0,y:20 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.55,delay:0.36,ease:[0.22,1,0.36,1] }}
          style={{ ...cardStyle(isDark),padding:22 }}>
          <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:2 }}>
            <div style={{ display:'flex',alignItems:'center',gap:8 }}>
              <Activity size={14} color={isDark?'#71717a':'#a1a1aa'}/>
              <h2 style={{ fontSize:15,fontWeight:600,letterSpacing:'-0.02em',color:isDark?'#fafafa':'#09090b' }}>Recent AI Signals</h2>
            </div>
            <button style={{ padding:4,borderRadius:6,border:'none',background:'transparent',cursor:'pointer',color:isDark?'#52525b':'#a1a1aa' }}>
              <MoreHorizontal size={16}/>
            </button>
          </div>
          <div>
            {recentSigs.map((sig: any, i: number) => <SignalRow key={i} sig={sig} isDark={isDark}/>)}
          </div>
        </motion.div>

        <div style={{ height:8 }}/>
      </div>
    </div>
  );
}
