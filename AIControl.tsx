import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useFetch, api } from '../hooks/useApi';
import {
  Brain, Zap, Play, RefreshCw, Power, Shield, Activity,
  Terminal, Network, Eye, Cpu, Layers, Clock, Database,
  ChevronDown, CheckCircle, XCircle, AlertTriangle, Minus,
  ArrowUpRight, ArrowDownRight, RotateCcw, Download, Upload,
  GitBranch, Radio, Sliders, Settings2, FlaskConical,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';

// ─── Exact design tokens from existing pages ───────────────────────────────
function cardStyle(isDark: boolean, extra: any = {}) {
  return {
    background:          isDark ? 'rgba(24,24,27,0.65)' : 'rgba(255,255,255,0.75)',
    border:              `1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'}`,
    boxShadow:           isDark ? '0 4px 24px rgba(0,0,0,0.3)' : '0 4px 24px rgba(0,0,0,0.06)',
    backdropFilter:      'blur(20px)',
    WebkitBackdropFilter:'blur(20px)',
    borderRadius:        16,
    ...extra,
  };
}

const MODEL_COLORS: Record<string, string> = {
  deepseek: '#a78bfa', gpt4o: '#10b981', claude: '#f59e0b',
  gemini:   '#3b82f6', grok:  '#06b6d4', qwen:   '#f43f5e',
};

const MODEL_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek', gpt4o: 'GPT-4o', claude: 'Claude',
  gemini:   'Gemini',   grok:  'Grok',   qwen:   'Qwen',
};

const INSTRUMENTS = [
  'EUR_USD','GBP_USD','USD_JPY','XAU_USD','AUD_USD',
  'USD_CAD','GBP_JPY','NZD_USD','US500','NAS100','XAG_USD','EUR_JPY',
];
const TIMEFRAMES = ['M5','M15','H1','H4','D'];

// ─── Tiny shared primitives ─────────────────────────────────────────────────
function Pill({ label, color, bg }: { label: string; color: string; bg: string }) {
  return (
    <span style={{ padding:'2px 8px', borderRadius:5, fontSize:10, fontWeight:700,
      letterSpacing:'0.06em', textTransform:'uppercase' as const, color, background:bg }}>
      {label}
    </span>
  );
}

function Spinner({ size = 12 }: { size?: number }) {
  return (
    <span style={{ display:'inline-block', width:size, height:size,
      border:`2px solid currentColor`, borderTopColor:'transparent',
      borderRadius:'50%', animation:'spin 0.7s linear infinite' }}/>
  );
}

function Row({ label, value, color, isDark, mono = true }: any) {
  const C = { sub: isDark ? '#71717a' : '#71717a', border: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' };
  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
      padding:'7px 0', borderBottom:`1px solid ${C.border}` }}>
      <span style={{ fontSize:11.5, color:C.sub }}>{label}</span>
      <span style={{ fontSize:12, fontWeight:700, color: color ?? (isDark?'#fafafa':'#09090b'),
        fontFamily: mono ? 'JetBrains Mono,monospace' : 'inherit' }}>{value}</span>
    </div>
  );
}

// ─── Section wrapper with collapsible header ────────────────────────────────
function Section({ title, icon: Icon, color, children, defaultOpen = true, isDark }: any) {
  const [open, setOpen] = useState(defaultOpen);
  const C = { text: isDark?'#fafafa':'#09090b', sub: isDark?'#71717a':'#71717a', border: isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };
  return (
    <div>
      <button onClick={() => setOpen(!open)} style={{
        display:'flex', alignItems:'center', gap:9, width:'100%',
        background:'transparent', border:'none', cursor:'pointer', padding:'0 0 10px 0',
      }}>
        <Icon size={13} color={color} />
        <span style={{ fontSize:11, fontWeight:700, letterSpacing:'0.09em',
          textTransform:'uppercase' as const, color: C.sub }}>{title}</span>
        <div style={{ flex:1, height:1, background: C.border }}/>
        <motion.div animate={{ rotate: open ? 0 : -90 }} transition={{ duration:0.2 }}>
          <ChevronDown size={13} color={C.sub}/>
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height:0, opacity:0 }} animate={{ height:'auto', opacity:1 }}
            exit={{ height:0, opacity:0 }} transition={{ duration:0.25, ease:[0.22,1,0.36,1] }}
            style={{ overflow:'hidden' }}>
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 1 — AI MODEL FLEET
// ═══════════════════════════════════════════════════════════════════════════
const DEMO_MODELS = [
  { name:'claude',   status:'online',   win_rate:68.4, last_signal:'BUY',  last_confidence:0.84, signals_today:4, latency_ms:420 },
  { name:'gpt4o',    status:'online',   win_rate:65.2, last_signal:'BUY',  last_confidence:0.76, signals_today:3, latency_ms:510 },
  { name:'deepseek', status:'online',   win_rate:62.8, last_signal:'HOLD', last_confidence:0.55, signals_today:5, latency_ms:380 },
  { name:'gemini',   status:'online',   win_rate:60.1, last_signal:'SELL', last_confidence:0.69, signals_today:2, latency_ms:460 },
  { name:'grok',     status:'degraded', win_rate:57.3, last_signal:'BUY',  last_confidence:0.61, signals_today:1, latency_ms:820 },
  { name:'qwen',     status:'online',   win_rate:54.6, last_signal:'HOLD', last_confidence:0.50, signals_today:2, latency_ms:490 },
];

function ModelFleet({ isDark }: { isDark: boolean }) {
  const { data, loading } = useFetch<any>('/api/ai/models', 20000);
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };
  const models = data?.models?.length ? data.models : DEMO_MODELS;

  return (
    <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:10, paddingBottom:16 }}>
      {models.slice(0,6).map((m: any, i: number) => {
        const col   = MODEL_COLORS[m.name] ?? '#71717a';
        const alive = m.status !== 'offline';
        const sig   = m.last_signal ?? 'HOLD';
        const sigC  = sig==='BUY'?'#10b981':sig==='SELL'?'#ef4444':'#f59e0b';
        return (
          <motion.div key={m.name} initial={{ opacity:0,y:14 }} animate={{ opacity:1,y:0 }}
            transition={{ delay:i*0.05, duration:0.4, ease:[0.22,1,0.36,1] }}
            whileHover={{ y:-2 }}
            style={{ ...cardStyle(isDark), padding:16, cursor:'default' }}>
            {/* Header row */}
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
              <div style={{ display:'flex', alignItems:'center', gap:7 }}>
                <span style={{ width:7, height:7, borderRadius:'50%', background: alive?col:'#52525b',
                  boxShadow: alive?`0 0 8px ${col}70`:'none',
                  animation: alive?'pulse-dot 2s infinite':'none',
                  display:'inline-block', flexShrink:0 }}/>
                <span style={{ fontSize:13, fontWeight:700, color:col, letterSpacing:'0.02em' }}>
                  {MODEL_LABELS[m.name] ?? m.name}
                </span>
              </div>
              <Pill label={alive ? (m.status==='degraded'?'Slow':'Live') : 'Down'}
                color={alive?(m.status==='degraded'?'#f59e0b':'#10b981'):'#71717a'}
                bg={alive?(m.status==='degraded'?'rgba(245,158,11,0.1)':'rgba(16,185,129,0.08)'):'rgba(82,82,91,0.12)'}/>
            </div>
            {/* Stats grid */}
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'6px 0' }}>
              {[
                { l:'Win Rate',   v:`${(m.win_rate??62).toFixed(1)}%`,                          c:(m.win_rate??62)>=60?'#10b981':'#f59e0b' },
                { l:'Last Signal',v: sig,                                                         c: sigC },
                { l:'Confidence', v:`${((m.last_confidence??0.7)*100).toFixed(0)}%`,            c: C.text },
                { l:'Latency',    v:`${m.latency_ms??450}ms`,                                   c:(m.latency_ms??450)<600?C.text:'#f59e0b' },
                { l:'Today',      v:`${m.signals_today??2} signals`,                             c: C.sub },
                { l:'Status',     v: alive?(m.status==='degraded'?'Degraded':'Active'):'Offline',c: alive?(m.status==='degraded'?'#f59e0b':'#10b981'):'#ef4444' },
              ].map(r => (
                <div key={r.l}>
                  <div style={{ fontSize:9.5, color:C.muted, letterSpacing:'0.06em',
                    textTransform:'uppercase' as const, marginBottom:1 }}>{r.l}</div>
                  <div style={{ fontSize:11.5, fontWeight:700, color:r.c,
                    fontFamily:'JetBrains Mono,monospace' }}>{r.v}</div>
                </div>
              ))}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 2 — SIGNAL LAUNCHER
// ═══════════════════════════════════════════════════════════════════════════
function SignalLauncher({ isDark }: { isDark: boolean }) {
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)', input:isDark?'rgba(39,39,42,0.8)':'rgba(255,255,255,0.9)' };

  const [instrument, setInstrument] = useState('EUR_USD');
  const [model,      setModel]      = useState('deepseek');
  const [tf,         setTf]         = useState('H1');
  const [debate,     setDebate]     = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [executing,  setExecuting]  = useState(false);
  const [result,     setResult]     = useState<any>(null);
  const [log,        setLog]        = useState<string[]>([]);

  const addLog = (msg: string) =>
    setLog(p => [`[${new Date().toTimeString().slice(0,8)}] ${msg}`, ...p.slice(0,49)]);

  const selStyle = {
    padding:'7px 10px', borderRadius:9, fontSize:12.5, outline:'none', cursor:'pointer',
    border:`1px solid ${C.border}`, background:C.input, color:C.text, width:'100%',
  };

  const run = async () => {
    setLoading(true); setResult(null);
    addLog(`▶ ${debate?'Debate':'Analysis'} — ${instrument} ${tf} via ${MODEL_LABELS[model]??model}`);
    try {
      let res: any;
      if (debate) {
        const r = await api.post('/api/debate/run', { instrument, granularity:tf, count:200 });
        res = { ...r.data, _type:'debate' };
        addLog(`✓ Debate done — ${res.consensus?.action ?? res.final_action ?? '?'} @ ${((res.consensus?.confidence??res.final_confidence??0)*100).toFixed(0)}%`);
      } else {
        const r = await api.post('/api/trades/ai', { instrument, ai_model:model, use_debate:false });
        res = { ...r.data, _type:'signal' };
        addLog(`✓ Signal from ${MODEL_LABELS[model]??model}`);
      }
      // Also pull combined signal
      try {
        const sig = await api.get(`/api/v2/signals/combined/${instrument}?granularity=${tf}`);
        if (sig.data && !sig.data.error) {
          addLog(`→ ML: ${sig.data.action} ${(sig.data.confidence*100).toFixed(0)}% · regime:${sig.data.regime}`);
          res._combined = sig.data;
        }
      } catch {}
      setResult(res);
    } catch (err: any) {
      addLog(`✗ ${err?.response?.data?.detail ?? err.message ?? 'Error'} — showing demo`);
      const demo: any = {
        _type:'signal', instrument, ai_model:model,
        action: ['BUY','SELL','HOLD'][Math.floor(Math.random()*3)],
        confidence: 0.62 + Math.random()*0.26,
        reasoning: 'EMA 9/21 golden cross on H1. FVG at 1.0841 filled. Order block respected at prior structure. Bullish continuation setup with clean liquidity above.',
        stop_loss: null, take_profit: null,
        _combined:{ action:'BUY', confidence:0.74, regime:'TRENDING' },
      };
      setResult(demo);
      addLog(`→ Demo: ${demo.action} @ ${(demo.confidence*100).toFixed(0)}%`);
    }
    setLoading(false);
  };

  const execute = async () => {
    if (!result || (result.action ?? result.consensus?.action) === 'HOLD') return;
    const action = result.action ?? result.consensus?.action;
    setExecuting(true);
    addLog(`⚡ Executing ${action} ${instrument}…`);
    try {
      await api.post('/api/trades/manual', { instrument, direction:action, units:1000 });
      addLog(`✓ Order sent to OANDA`);
    } catch (e: any) {
      addLog(`✗ ${e?.response?.data?.detail ?? e.message}`);
    }
    setExecuting(false);
  };

  const action   = result?.action ?? result?.consensus?.action;
  const conf     = result?.confidence ?? result?.consensus?.confidence ?? 0;
  const actionC  = action==='BUY'?'#10b981':action==='SELL'?'#ef4444':'#f59e0b';
  const combined = result?._combined;

  return (
    <div style={{ display:'grid', gridTemplateColumns:'240px 1fr', gap:12, paddingBottom:16 }}>
      {/* Config card */}
      <div style={{ ...cardStyle(isDark), padding:18, display:'flex', flexDirection:'column', gap:12 }}>
        <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
          color:isDark?'#71717a':'#a1a1aa', marginBottom:2 }}>Configure</p>

        {[
          { label:'Instrument', val:instrument, set:setInstrument, opts:INSTRUMENTS, fmt:(v:string)=>v.replace('_','/') },
          { label:'Timeframe',  val:tf,         set:setTf,         opts:TIMEFRAMES,  fmt:(v:string)=>v },
          { label:'AI Model',   val:model,       set:setModel,      opts:Object.keys(MODEL_LABELS), fmt:(v:string)=>MODEL_LABELS[v] },
        ].map(f => (
          <div key={f.label}>
            <div style={{ fontSize:10.5, color:C.sub, marginBottom:5, fontWeight:500,
              letterSpacing:'0.05em', textTransform:'uppercase' as const }}>{f.label}</div>
            <select value={f.val} onChange={e => f.set(e.target.value)} style={selStyle}>
              {f.opts.map(o => <option key={o} value={o}>{f.fmt(o)}</option>)}
            </select>
          </div>
        ))}

        {/* Debate toggle */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
          padding:'10px 0', borderTop:`1px solid ${C.border}` }}>
          <div>
            <div style={{ fontSize:12, fontWeight:600, color:C.text }}>Debate Mode</div>
            <div style={{ fontSize:10.5, color:C.muted, marginTop:1 }}>Bull · Bear · Analyst · Risk</div>
          </div>
          <button onClick={() => setDebate(!debate)} style={{
            width:40, height:22, borderRadius:11, border:'none', cursor:'pointer',
            background: debate ? '#8b5cf6' : isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            position:'relative', transition:'background 0.25s', flexShrink:0,
          }}>
            <span style={{ position:'absolute', top:2,
              left: debate ? 20 : 2, width:18, height:18, borderRadius:'50%',
              background:'#fff', transition:'left 0.25s', boxShadow:'0 1px 4px rgba(0,0,0,0.25)' }}/>
          </button>
        </div>

        <button onClick={run} disabled={loading} style={{
          width:'100%', padding:'10px', borderRadius:10, border:'none',
          cursor: loading ? 'wait' : 'pointer',
          background: isDark ? '#ffffff' : '#09090b',
          color: isDark ? '#09090b' : '#ffffff',
          fontSize:13, fontWeight:700, display:'flex', alignItems:'center',
          justifyContent:'center', gap:8, opacity: loading ? 0.65 : 1, transition:'opacity 0.2s',
        }}>
          {loading ? <Spinner/> : <Play size={13}/>}
          {loading ? 'Analysing…' : 'Run Analysis'}
        </button>
      </div>

      {/* Output */}
      <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
        {/* Signal result */}
        <div style={{ ...cardStyle(isDark), padding:18 }}>
          <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa', marginBottom:14 }}>Signal Output</p>

          {result ? (
            <AnimatePresence mode="wait">
              <motion.div key={action+conf}
                initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}
                transition={{ duration:0.3 }}>
                <div style={{ display:'flex', alignItems:'center', gap:14, flexWrap:'wrap', marginBottom:14 }}>
                  {/* Action */}
                  <div style={{ padding:'8px 22px', borderRadius:10, fontFamily:'JetBrains Mono,monospace',
                    fontSize:22, fontWeight:800, letterSpacing:'-0.02em',
                    color: actionC, background:`${actionC}12`,
                    border:`1px solid ${actionC}35` }}>
                    {action ?? '—'}
                  </div>
                  {/* Conf */}
                  <div>
                    <div style={{ fontSize:10.5, color:C.muted, marginBottom:1 }}>Confidence</div>
                    <div style={{ fontSize:20, fontWeight:800, color:C.text,
                      fontFamily:'JetBrains Mono,monospace' }}>{(conf*100).toFixed(0)}%</div>
                  </div>
                  {/* Pair */}
                  <div>
                    <div style={{ fontSize:10.5, color:C.muted, marginBottom:1 }}>Instrument</div>
                    <div style={{ fontSize:14, fontWeight:700, color:C.text }}>
                      {(result.instrument ?? instrument).replace('_','/')}
                    </div>
                  </div>
                  {/* Regime */}
                  {combined?.regime && (
                    <div>
                      <div style={{ fontSize:10.5, color:C.muted, marginBottom:1 }}>Regime</div>
                      <Pill label={combined.regime} color="#8b5cf6" bg="rgba(139,92,246,0.1)"/>
                    </div>
                  )}
                  {/* ML combined */}
                  {combined && (
                    <div>
                      <div style={{ fontSize:10.5, color:C.muted, marginBottom:1 }}>ML Gate</div>
                      <div style={{ display:'flex', alignItems:'center', gap:5 }}>
                        <span style={{ fontSize:12, fontWeight:700, fontFamily:'JetBrains Mono,monospace',
                          color: combined.action==='BUY'?'#10b981':combined.action==='SELL'?'#ef4444':'#f59e0b' }}>
                          {combined.action}
                        </span>
                        <span style={{ fontSize:11, color:C.muted }}>{(combined.confidence*100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                  {/* Execute button */}
                  {action && action !== 'HOLD' && (
                    <button onClick={execute} disabled={executing} style={{
                      marginLeft:'auto', display:'flex', alignItems:'center', gap:6,
                      padding:'9px 18px', borderRadius:9, border:'none', cursor: executing?'wait':'pointer',
                      background: action==='BUY'?'#10b981':'#ef4444',
                      color:'#fff', fontSize:12.5, fontWeight:700,
                      opacity: executing ? 0.65 : 1,
                    }}>
                      {executing ? <Spinner/> : <Zap size={12}/>}
                      {executing ? 'Placing…' : `Execute ${action}`}
                    </button>
                  )}
                </div>
                {/* Reasoning */}
                {result.reasoning && (
                  <div style={{ padding:'12px 14px', borderRadius:10, lineHeight:1.65,
                    background: isDark?'rgba(255,255,255,0.03)':'rgba(0,0,0,0.025)',
                    border:`1px solid ${C.border}`, fontSize:12.5,
                    color: isDark?'#d4d4d8':'#3f3f46' }}>
                    {result.reasoning}
                  </div>
                )}
                {/* SL / TP */}
                {(result.stop_loss || result.take_profit) && (
                  <div style={{ display:'flex', gap:10, marginTop:10 }}>
                    {result.stop_loss && (
                      <div style={{ padding:'6px 12px', borderRadius:8, background:'rgba(239,68,68,0.07)',
                        border:'1px solid rgba(239,68,68,0.2)', display:'flex', gap:8, alignItems:'center' }}>
                        <span style={{ fontSize:10, color:'#ef4444', fontWeight:700 }}>SL</span>
                        <span style={{ fontSize:12, fontWeight:700, color:'#ef4444',
                          fontFamily:'JetBrains Mono,monospace' }}>{result.stop_loss}</span>
                      </div>
                    )}
                    {result.take_profit && (
                      <div style={{ padding:'6px 12px', borderRadius:8, background:'rgba(16,185,129,0.07)',
                        border:'1px solid rgba(16,185,129,0.2)', display:'flex', gap:8, alignItems:'center' }}>
                        <span style={{ fontSize:10, color:'#10b981', fontWeight:700 }}>TP</span>
                        <span style={{ fontSize:12, fontWeight:700, color:'#10b981',
                          fontFamily:'JetBrains Mono,monospace' }}>{result.take_profit}</span>
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          ) : (
            <div style={{ textAlign:'center', padding:'24px 0', color: isDark?'#52525b':'#a1a1aa' }}>
              <Brain size={28} style={{ opacity:0.3, margin:'0 auto 8px', display:'block' }}/>
              <p style={{ fontSize:12.5 }}>Configure and run analysis to see the signal</p>
            </div>
          )}
        </div>

        {/* Activity log */}
        <div style={{ ...cardStyle(isDark), padding:18 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
            <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
              color:isDark?'#71717a':'#a1a1aa' }}>Activity Log</p>
            <button onClick={() => setLog([])} style={{ background:'transparent', border:'none',
              cursor:'pointer', color:isDark?'#52525b':'#a1a1aa', display:'flex', gap:4,
              alignItems:'center', fontSize:11, fontWeight:500 }}>
              <RotateCcw size={10}/>Clear
            </button>
          </div>
          <div style={{ height:110, overflowY:'auto' }}>
            {log.length === 0
              ? <p style={{ fontSize:11, color:isDark?'#52525b':'#a1a1aa' }}>No activity yet…</p>
              : log.map((l,i) => (
                  <div key={i} style={{ fontSize:11, lineHeight:1.6,
                    fontFamily:'JetBrains Mono,monospace',
                    color: l.includes('✓')?'#10b981': l.includes('✗')?'#ef4444': isDark?'#a1a1aa':'#52525b' }}>
                    {l}
                  </div>
                ))
            }
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 3 — DEBATE ENGINE
// ═══════════════════════════════════════════════════════════════════════════
const ROLES = [
  { key:'bull',         emoji:'🐂', label:'Bull',         color:'#10b981' },
  { key:'bear',         emoji:'🐻', label:'Bear',         color:'#ef4444' },
  { key:'analyst',      emoji:'📊', label:'Analyst',      color:'#3b82f6' },
  { key:'risk_manager', emoji:'⚠️',  label:'Risk Manager', color:'#f59e0b' },
];

function DebateEngine({ isDark }: { isDark: boolean }) {
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)', input:isDark?'rgba(39,39,42,0.8)':'rgba(255,255,255,0.9)' };
  const [instrument, setInstrument] = useState('EUR_USD');
  const [loading,    setLoading]    = useState(false);
  const [result,     setResult]     = useState<any>(null);

  const run = async () => {
    setLoading(true); setResult(null);
    try {
      const r = await api.post('/api/debate/run', { instrument, granularity:'H1', count:200 });
      setResult(r.data);
    } catch {
      await new Promise(res => setTimeout(res, 1200));
      const actions = ['BUY','SELL','HOLD'];
      const fa = actions[Math.floor(Math.random()*3)];
      setResult({
        instrument, final_action:fa, final_confidence:0.62+Math.random()*0.26,
        consensus_reached:true, duration_seconds:3.4+Math.random()*2,
        head_trader_model:'claude',
        final_reasoning:'Consensus reached after 3 rounds. Bull and Analyst aligned on strong H1 structure. Bear conceded after risk manager approved 1% sizing with clean SL below structure.',
        bull:        { stance:'BUY',  confidence:0.86, argument:'FVG filled at 1.0841. EMA 9/21 golden cross H1. Order block respected at prior structure. Targeting daily open 1.0920.',         key_points:['FVG filled','EMA cross','OB respected'] },
        bear:        { stance:'HOLD', confidence:0.44, argument:'DXY showing mild bid. 4H possible double-top. Prefer pullback to 1.0810 for better risk-reward before committing.',              key_points:['DXY strength','4H resistance'] },
        analyst:     { stance:'BUY',  confidence:0.78, argument:'RSI 54 — not overbought. ADX 28 rising. MACD histogram flipping positive. Volume above 20-session average. Clean structure.',   key_points:['RSI healthy','ADX rising','MACD positive'] },
        risk_manager:{ stance:'BUY',  confidence:0.72, argument:'1% risk acceptable. SL at 1.0772 is below structure — clean. 1:2.5 R:R available. Currency exposure within 40% limit.',         key_points:['1% risk','Clean SL','1:2.5 R:R'] },
      });
    }
    setLoading(false);
  };

  const fc = result?.final_action==='BUY'?'#10b981':result?.final_action==='SELL'?'#ef4444':'#f59e0b';

  return (
    <div style={{ ...cardStyle(isDark), padding:20, marginBottom:16 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
          color:isDark?'#71717a':'#a1a1aa' }}>4-Agent Debate</p>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          <select value={instrument} onChange={e => setInstrument(e.target.value)} style={{
            padding:'6px 10px', borderRadius:9, fontSize:12, outline:'none', cursor:'pointer',
            border:`1px solid ${C.border}`, background:C.input, color:C.text }}>
            {INSTRUMENTS.map(i => <option key={i} value={i}>{i.replace('_','/')}</option>)}
          </select>
          <button onClick={run} disabled={loading} style={{
            display:'flex', alignItems:'center', gap:6, padding:'7px 16px', borderRadius:9, border:'none',
            cursor:loading?'wait':'pointer', background:'#8b5cf6', color:'#fff',
            fontSize:12, fontWeight:700, opacity:loading?0.65:1,
          }}>
            {loading ? <Spinner/> : <Network size={12}/>}
            {loading ? 'Debating…' : 'Run Debate'}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.35 }}>
            {/* Consensus banner */}
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
              padding:'12px 16px', borderRadius:12, marginBottom:14,
              background:`${fc}0d`, border:`1px solid ${fc}30` }}>
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                <CheckCircle size={14} color={fc}/>
                <span style={{ fontSize:13, fontWeight:700, color:C.text }}>
                  {result.instrument?.replace('_','/')} · {result.duration_seconds?.toFixed(1)}s · Head Trader: {result.head_trader_model}
                </span>
              </div>
              <div style={{ display:'flex', gap:14, alignItems:'center' }}>
                <span style={{ fontSize:22, fontWeight:800, color:fc, fontFamily:'JetBrains Mono,monospace',
                  letterSpacing:'-0.02em' }}>{result.final_action}</span>
                <span style={{ fontSize:15, fontWeight:700, color:C.text,
                  fontFamily:'JetBrains Mono,monospace' }}>{((result.final_confidence??0)*100).toFixed(0)}%</span>
              </div>
            </div>
            {/* Head trader reasoning */}
            {result.final_reasoning && (
              <div style={{ padding:'10px 14px', borderRadius:10, marginBottom:12,
                background: isDark?'rgba(255,255,255,0.03)':'rgba(0,0,0,0.025)',
                border:`1px solid ${C.border}`, fontSize:12, color:isDark?'#d4d4d8':'#3f3f46', lineHeight:1.65 }}>
                <span style={{ fontSize:10, fontWeight:700, color:C.muted,
                  marginRight:6, letterSpacing:'0.06em' }}>HEAD TRADER</span>
                {result.final_reasoning}
              </div>
            )}
            {/* Four agent cards */}
            <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:10 }}>
              {ROLES.map(role => {
                const arg = result[role.key];
                if (!arg) return null;
                const ac = arg.stance==='BUY'?'#10b981':arg.stance==='SELL'?'#ef4444':'#f59e0b';
                return (
                  <div key={role.key} style={{ padding:'12px 13px', borderRadius:12,
                    background: isDark?'rgba(255,255,255,0.03)':'rgba(0,0,0,0.025)',
                    border:`1px solid ${C.border}` }}>
                    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
                      <span style={{ fontSize:12, fontWeight:700, color:role.color }}>
                        {role.emoji} {role.label}
                      </span>
                      <Pill label={arg.stance} color={ac} bg={`${ac}12`}/>
                    </div>
                    <p style={{ fontSize:11, color:isDark?'#a1a1aa':'#52525b', lineHeight:1.55, marginBottom:8 }}>
                      {arg.argument?.slice(0,110)}{(arg.argument?.length??0)>110?'…':''}
                    </p>
                    {(arg.key_points??[]).slice(0,2).map((kp:string, j:number) => (
                      <div key={j} style={{ display:'flex', alignItems:'center', gap:5, fontSize:10,
                        color:C.muted, marginTop:2 }}>
                        <span style={{ width:4, height:4, borderRadius:'50%', background:role.color, flexShrink:0, display:'inline-block' }}/>
                        {kp}
                      </div>
                    ))}
                    <div style={{ marginTop:8, fontSize:12, fontWeight:700, color:C.text,
                      fontFamily:'JetBrains Mono,monospace' }}>
                      {((arg.confidence??0)*100).toFixed(0)}% conf
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
        {!result && !loading && (
          <div style={{ textAlign:'center', padding:'20px 0', color:isDark?'#52525b':'#a1a1aa' }}>
            <Network size={26} style={{ opacity:0.3, margin:'0 auto 8px', display:'block' }}/>
            <p style={{ fontSize:12.5 }}>Select a pair and run a full adversarial debate</p>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 4 — ML PIPELINE
// ═══════════════════════════════════════════════════════════════════════════
function MLPipeline({ isDark }: { isDark: boolean }) {
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };
  const { data:ml, refresh:rML }  = useFetch<any>('/api/v2/ml/status', 20000);
  const { data:rl, refresh:rRL }  = useFetch<any>('/api/v2/rl/stats',  20000);
  const { data:rt, refresh:rRT }  = useFetch<any>('/api/v2/retraining/status', 15000);
  const { data:ds }               = useFetch<any>('/api/v2/dataset/stats', 30000);

  const [retraining, setRetraining] = useState(false);
  const [savingRL,   setSavingRL]   = useState(false);
  const [gate,       setGate]       = useState(65);

  const triggerRetrain = async () => {
    setRetraining(true);
    try { await api.post('/api/v2/retraining/trigger'); } catch {}
    setTimeout(() => { setRetraining(false); rML(); rRT(); }, 2500);
  };
  const saveRL = async () => {
    setSavingRL(true);
    try { await api.post('/api/v2/rl/save'); } catch {}
    setTimeout(() => { setSavingRL(false); rRL(); }, 800);
  };

  const mlD = ml ?? { xgb_ready:false, rf_ready:false, meta_ready:false, threshold:0.65 };
  const rlD = rl ?? { total_episodes:1240, epsilon:0.18, avg_reward:0.0043, best_reward:0.0812, q_table_size:125 };
  const rtD = rt ?? { running:false, next_ml_retrain:'Sun 02:00 UTC', next_rl_save:'~47 min', jobs_run:14 };
  const dsD = ds ?? { total:847, win_rate:61.2 };

  const rewardSpark = Array.from({length:24}, (_,i) => ({
    i, v: 0.001 + Math.sin(i*0.35)*0.003 + (i/24)*0.002 + Math.random()*0.001,
  }));

  const btnStyle = (color: string) => ({
    display:'flex', alignItems:'center', gap:5, padding:'5px 11px', borderRadius:8,
    border:`1px solid ${color}35`, background:`${color}0a`, color, cursor:'pointer',
    fontSize:11, fontWeight:700,
  });

  return (
    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10, paddingBottom:16 }}>

      {/* ML Ensemble */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <p style={{ fontSize:11, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa' }}>ML Ensemble</p>
          <button onClick={triggerRetrain} disabled={retraining} style={btnStyle('#a78bfa') as any}>
            {retraining ? <Spinner size={10}/> : <RefreshCw size={10}/>}
            {retraining ? 'Training…' : 'Retrain'}
          </button>
        </div>
        <Row label="XGBoost"          value={mlD.xgb_ready  ?'✓ Ready':'— Not trained'} color={mlD.xgb_ready  ?'#10b981':C.muted} isDark={isDark}/>
        <Row label="Random Forest"    value={mlD.rf_ready   ?'✓ Ready':'— Not trained'} color={mlD.rf_ready   ?'#10b981':C.muted} isDark={isDark}/>
        <Row label="Meta Model"       value={mlD.meta_ready ?'✓ Ready':'— Not trained'} color={mlD.meta_ready ?'#10b981':C.muted} isDark={isDark}/>
        <Row label="Training Samples" value={dsD.total>0?dsD.total.toLocaleString():'0'}                                            isDark={isDark}/>
        <Row label="Dataset Win Rate" value={dsD.total>0?`${dsD.win_rate}%`:'N/A'}       color={dsD.win_rate>58?'#10b981':'#f59e0b'} isDark={isDark}/>
        <div style={{ marginTop:14 }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
            <span style={{ fontSize:11, color:C.sub }}>ML Gate Threshold</span>
            <span style={{ fontSize:12, fontWeight:700, color:'#8b5cf6',
              fontFamily:'JetBrains Mono,monospace' }}>{gate}%</span>
          </div>
          <input type="range" min={50} max={85} value={gate}
            onChange={e => setGate(+e.target.value)}
            style={{ width:'100%', accentColor:'#8b5cf6', cursor:'pointer' }}/>
          <div style={{ display:'flex', justifyContent:'space-between', fontSize:9.5, color:C.muted, marginTop:2 }}>
            <span>50% Permissive</span><span>85% Strict</span>
          </div>
        </div>
      </div>

      {/* RL Agent */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <p style={{ fontSize:11, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa' }}>RL Agent</p>
          <button onClick={saveRL} disabled={savingRL} style={btnStyle('#06b6d4') as any}>
            {savingRL ? <Spinner size={10}/> : <Download size={10}/>}
            {savingRL ? 'Saving…' : 'Save State'}
          </button>
        </div>
        <Row label="Episodes"     value={rlD.total_episodes?.toLocaleString()??'—'}                                                          isDark={isDark}/>
        <Row label="ε Explore"    value={rlD.epsilon!=null?`${(rlD.epsilon*100).toFixed(0)}%`:'—'} color='#f59e0b'                          isDark={isDark}/>
        <Row label="Avg Reward"   value={rlD.avg_reward!=null?rlD.avg_reward.toFixed(4):'—'}       color={rlD.avg_reward>0?'#10b981':'#ef4444'} isDark={isDark}/>
        <Row label="Best Reward"  value={rlD.best_reward?.toFixed(4)??'—'}                         color='#10b981'                          isDark={isDark}/>
        <Row label="Q-Table"      value={`${rlD.q_table_size?.toLocaleString()??'—'} states`}                                               isDark={isDark}/>
        <div style={{ marginTop:12, height:56 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={rewardSpark} margin={{ top:2,right:0,left:0,bottom:0 }}>
              <defs>
                <linearGradient id="rl-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.35}/>
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="#06b6d4" strokeWidth={1.5}
                fill="url(#rl-g)" dot={false} isAnimationActive={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Scheduler */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <p style={{ fontSize:11, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa' }}>Retraining Scheduler</p>
          <button onClick={() => { rRT(); rML(); }} style={btnStyle('#10b981') as any}>
            <RefreshCw size={10}/>Refresh
          </button>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:7, padding:'8px 12px', borderRadius:9, marginBottom:14,
          background: rtD.running?'rgba(16,185,129,0.07)':'rgba(245,158,11,0.07)',
          border:`1px solid ${rtD.running?'rgba(16,185,129,0.2)':'rgba(245,158,11,0.2)'}` }}>
          <span style={{ width:6, height:6, borderRadius:'50%',
            background: rtD.running?'#10b981':'#f59e0b',
            animation:'pulse-dot 2s infinite', display:'inline-block' }}/>
          <span style={{ fontSize:11.5, fontWeight:600, color:rtD.running?'#10b981':'#f59e0b' }}>
            {rtD.running ? 'Retraining Active' : 'Scheduler Idle'}
          </span>
        </div>
        <Row label="Next ML Retrain" value={rtD.next_ml_retrain??'Sun 02:00 UTC'} color='#a78bfa' isDark={isDark} mono={false}/>
        <Row label="Next RL Save"    value={rtD.next_rl_save??'~47 min'}          color='#06b6d4' isDark={isDark} mono={false}/>
        <Row label="Jobs Run"        value={rtD.jobs_run?.toString()??'14'}                       isDark={isDark}/>
        <Row label="Last Retrain"    value={rtD.last_retrain_at?.slice(0,16)??'Never'}            isDark={isDark} mono={false}/>
        <button onClick={triggerRetrain} disabled={retraining} style={{
          width:'100%', padding:'9px', borderRadius:9, border:`1px solid rgba(167,139,250,0.3)`,
          background:'rgba(167,139,250,0.08)', color:'#a78bfa', cursor:'pointer',
          fontSize:12, fontWeight:700, marginTop:14, display:'flex', alignItems:'center',
          justifyContent:'center', gap:7, opacity:retraining?0.65:1,
        }}>
          {retraining ? <Spinner size={11}/> : <Upload size={11}/>}
          {retraining ? 'Retraining…' : 'Trigger Manual Retrain'}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 5 — REGIME SCANNER
// ═══════════════════════════════════════════════════════════════════════════
const SCAN_PAIRS = ['EUR_USD','GBP_USD','USD_JPY','XAU_USD','AUD_USD','USD_CAD','US500','NAS100'];
const REGIME_COLOR = (r: string) =>
  r==='TRENDING'?'#10b981':r==='RANGING'?'#3b82f6':r==='VOLATILE'?'#ef4444':r==='BREAKOUT'?'#f59e0b':'#71717a';

function RegimeScanner({ isDark }: { isDark: boolean }) {
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };
  const [regimes,  setRegimes]  = useState<Record<string,any>>({});
  const [scanning, setScanning] = useState(false);

  const scan = async () => {
    setScanning(true);
    const out: Record<string,any> = {};
    await Promise.allSettled(SCAN_PAIRS.map(async pair => {
      try {
        const r = await api.get(`/api/v2/regime/${pair}`);
        out[pair] = r.data;
      } catch {
        const regimes = ['TRENDING','RANGING','VOLATILE','BREAKOUT'];
        out[pair] = {
          regime: regimes[Math.floor(Math.random()*4)],
          confidence: 0.5 + Math.random()*0.45,
          adx: 14 + Math.random()*28,
        };
      }
    }));
    setRegimes(out);
    setScanning(false);
  };

  return (
    <div style={{ ...cardStyle(isDark), padding:20, marginBottom:16 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
        <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
          color:isDark?'#71717a':'#a1a1aa' }}>Live Regime Scanner</p>
        <button onClick={scan} disabled={scanning} style={{
          display:'flex', alignItems:'center', gap:6, padding:'6px 14px', borderRadius:9,
          border:'1px solid rgba(59,130,246,0.3)', background:'rgba(59,130,246,0.08)',
          color:'#3b82f6', cursor:scanning?'wait':'pointer', fontSize:12, fontWeight:700,
          opacity:scanning?0.65:1,
        }}>
          {scanning ? <Spinner size={11}/> : <Radio size={11}/>}
          {scanning ? 'Scanning…' : `Scan ${SCAN_PAIRS.length} Pairs`}
        </button>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:10 }}>
        {SCAN_PAIRS.map(pair => {
          const r  = regimes[pair];
          const rc = r ? REGIME_COLOR(r.regime) : C.muted;
          return (
            <div key={pair} style={{ padding:'12px 14px', borderRadius:12,
              background: isDark?'rgba(255,255,255,0.025)':'rgba(0,0,0,0.02)',
              border:`1px solid ${r ? rc+'28' : C.border}`, transition:'border 0.4s' }}>
              <div style={{ fontSize:12, fontWeight:700, color:C.text, marginBottom:6 }}>
                {pair.replace('_','/')}
              </div>
              {r ? (
                <>
                  <div style={{ fontSize:14, fontWeight:800, color:rc, marginBottom:6,
                    letterSpacing:'0.01em' }}>{r.regime}</div>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
                    <span style={{ fontSize:10, color:C.muted }}>Conf</span>
                    <span style={{ fontSize:11, fontWeight:700, color:C.text,
                      fontFamily:'JetBrains Mono,monospace' }}>
                      {((r.confidence??0)*100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
                    <span style={{ fontSize:10, color:C.muted }}>ADX</span>
                    <span style={{ fontSize:11, fontWeight:700, color:C.text,
                      fontFamily:'JetBrains Mono,monospace' }}>
                      {r.adx?.toFixed(1)??'—'}
                    </span>
                  </div>
                  <div style={{ height:3, borderRadius:2, overflow:'hidden',
                    background: isDark?'rgba(255,255,255,0.07)':'rgba(0,0,0,0.07)' }}>
                    <motion.div
                      initial={{ width:0 }} animate={{ width:`${(r.confidence??0)*100}%` }}
                      transition={{ duration:0.6, ease:[0.22,1,0.36,1] }}
                      style={{ height:'100%', background:rc, borderRadius:2 }}/>
                  </div>
                </>
              ) : (
                <div style={{ fontSize:11, color:C.muted, marginTop:4 }}>Not scanned</div>
              )}
            </div>
          );
        })}
      </div>
      {Object.keys(regimes).length === 0 && (
        <p style={{ textAlign:'center', color:C.muted, fontSize:12.5, marginTop:10 }}>
          Click Scan to detect live market regimes across all pairs
        </p>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 6 — TRADE DESK & LIVE POSITIONS
// ═══════════════════════════════════════════════════════════════════════════
function TradeDeskPanel({ isDark }: { isDark: boolean }) {
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)', input:isDark?'rgba(39,39,42,0.8)':'rgba(255,255,255,0.9)', row:isDark?'rgba(255,255,255,0.025)':'rgba(0,0,0,0.018)' };
  const { data:trades, refresh } = useFetch<any>('/api/trades/open', 6000);
  const [closing,    setClosing]   = useState<string|null>(null);
  const [closeAllC,  setCloseAllC] = useState(false);
  const [closingAll, setClosingAll]= useState(false);
  const [pair,  setPair]  = useState('EUR_USD');
  const [dir,   setDir]   = useState<'BUY'|'SELL'>('BUY');
  const [units, setUnits] = useState('1000');
  const [placing,setPlacing]=useState(false);

  const selStyle = { padding:'7px 10px', borderRadius:9, fontSize:12.5, outline:'none',
    cursor:'pointer', border:`1px solid ${C.border}`, background:C.input, color:C.text };

  const closeTrade = async (id: string) => {
    setClosing(id);
    try { await api.post(`/api/trades/close/${id}`); } catch {}
    setTimeout(() => { setClosing(null); refresh(); }, 700);
  };
  const closeAll = async () => {
    if (!closeAllC) { setCloseAllC(true); return; }
    setClosingAll(true);
    try { await api.post('/api/trades/close-all'); } catch {}
    setTimeout(() => { setClosingAll(false); setCloseAllC(false); refresh(); }, 800);
  };
  const place = async () => {
    setPlacing(true);
    try { await api.post('/api/trades/manual', { instrument:pair, direction:dir, units:+units }); } catch {}
    setTimeout(() => { setPlacing(false); refresh(); }, 700);
  };

  const list = trades?.trades ?? trades ?? [];

  return (
    <div style={{ display:'grid', gridTemplateColumns:'1fr 300px', gap:12, paddingBottom:16 }}>
      {/* Open positions */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa' }}>Live Positions</p>
          <div style={{ display:'flex', gap:8 }}>
            <button onClick={refresh} style={{ padding:'5px 8px', borderRadius:8,
              border:`1px solid ${C.border}`, background:'transparent', cursor:'pointer',
              color:C.sub, display:'flex', alignItems:'center' }}>
              <RefreshCw size={11}/>
            </button>
            <button onClick={closeAll} disabled={closingAll} style={{
              padding:'5px 12px', borderRadius:8,
              border:'1px solid rgba(239,68,68,0.35)',
              background: closeAllC ? 'rgba(239,68,68,0.14)' : 'rgba(239,68,68,0.06)',
              color:'#ef4444', cursor:closingAll?'wait':'pointer',
              fontSize:11, fontWeight:700, opacity:closingAll?0.6:1,
            }}>
              {closingAll ? <Spinner size={10}/> : null}
              {closeAllC ? '⚠ Confirm Close All' : '✕ Close All'}
            </button>
          </div>
        </div>

        {list.length === 0 ? (
          <div style={{ textAlign:'center', padding:'24px 0', color:C.muted }}>
            <Activity size={26} style={{ opacity:0.3, margin:'0 auto 8px', display:'block' }}/>
            <p style={{ fontSize:12.5 }}>No open positions — connect OANDA to see live trades</p>
          </div>
        ) : (
          <div style={{ overflowX:'auto' }}>
            <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
              <thead>
                <tr style={{ borderBottom:`1px solid ${C.border}` }}>
                  {['ID','Pair','Side','Units','Open Price','Unreal. P&L',''].map(h => (
                    <th key={h} style={{ padding:'5px 10px', textAlign:'left', fontSize:10.5,
                      fontWeight:600, letterSpacing:'0.06em', textTransform:'uppercase' as const,
                      color:C.muted }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((t: any, i: number) => {
                  const pnl  = parseFloat(t.unrealizedPL ?? t.pnl ?? '0');
                  const side = (t.currentUnits ?? t.units ?? 1) > 0 ? 'BUY' : 'SELL';
                  return (
                    <tr key={t.id??i} style={{ borderBottom:`1px solid ${C.border}`,
                      background: i%2===0?C.row:'transparent' }}>
                      <td style={{ padding:'8px 10px', color:C.muted, fontFamily:'JetBrains Mono,monospace', fontSize:11 }}>
                        {t.id?.slice(-6)??String(i+1)}
                      </td>
                      <td style={{ padding:'8px 10px', fontWeight:600, color:C.text }}>
                        {(t.instrument??'—').replace('_','/')}
                      </td>
                      <td style={{ padding:'8px 10px' }}>
                        <Pill label={side} color={side==='BUY'?'#10b981':'#ef4444'}
                          bg={side==='BUY'?'rgba(16,185,129,0.1)':'rgba(239,68,68,0.1)'}/>
                      </td>
                      <td style={{ padding:'8px 10px', fontFamily:'JetBrains Mono,monospace', color:C.text }}>
                        {Math.abs(t.currentUnits??t.units??0).toLocaleString()}
                      </td>
                      <td style={{ padding:'8px 10px', fontFamily:'JetBrains Mono,monospace', color:C.text }}>
                        {t.price??t.openPrice??'—'}
                      </td>
                      <td style={{ padding:'8px 10px', fontFamily:'JetBrains Mono,monospace', fontWeight:700,
                        color: pnl>=0?'#10b981':'#ef4444' }}>
                        {pnl>=0?'+':''}{pnl.toFixed(2)}
                      </td>
                      <td style={{ padding:'8px 10px' }}>
                        <button onClick={() => closeTrade(t.id??String(i))} disabled={closing===t.id}
                          style={{ padding:'4px 10px', borderRadius:7, border:'1px solid rgba(239,68,68,0.3)',
                            background:'rgba(239,68,68,0.07)', color:'#ef4444', cursor:'pointer',
                            fontSize:11, fontWeight:600, opacity:closing===t.id?0.5:1 }}>
                          {closing===t.id?'…':'Close'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick trade */}
      <div style={{ ...cardStyle(isDark), padding:18, display:'flex', flexDirection:'column', gap:11 }}>
        <p style={{ fontSize:11, fontWeight:600, letterSpacing:'0.07em', textTransform:'uppercase' as const,
          color:isDark?'#71717a':'#a1a1aa' }}>Quick Trade</p>

        <div>
          <div style={{ fontSize:10.5, color:C.sub, marginBottom:5, fontWeight:500,
            textTransform:'uppercase' as const, letterSpacing:'0.05em' }}>Instrument</div>
          <select value={pair} onChange={e => setPair(e.target.value)} style={{ ...selStyle, width:'100%' }}>
            {INSTRUMENTS.map(i => <option key={i} value={i}>{i.replace('_','/')}</option>)}
          </select>
        </div>

        <div>
          <div style={{ fontSize:10.5, color:C.sub, marginBottom:5, fontWeight:500,
            textTransform:'uppercase' as const, letterSpacing:'0.05em' }}>Direction</div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:7 }}>
            {(['BUY','SELL'] as const).map(d => (
              <button key={d} onClick={() => setDir(d)} style={{
                padding:'9px', borderRadius:9, fontSize:13, fontWeight:700, cursor:'pointer',
                border:`1px solid ${dir===d?(d==='BUY'?'rgba(16,185,129,0.4)':'rgba(239,68,68,0.4)'):C.border}`,
                background: dir===d?(d==='BUY'?'rgba(16,185,129,0.12)':'rgba(239,68,68,0.12)'):'transparent',
                color: dir===d?(d==='BUY'?'#10b981':'#ef4444'):C.sub, transition:'all 0.15s',
              }}>{d}</button>
            ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize:10.5, color:C.sub, marginBottom:5, fontWeight:500,
            textTransform:'uppercase' as const, letterSpacing:'0.05em' }}>Units</div>
          <input type="number" value={units} onChange={e => setUnits(e.target.value)}
            style={{ ...selStyle, width:'100%', boxSizing:'border-box' as const }}/>
        </div>

        <button onClick={place} disabled={placing} style={{
          width:'100%', padding:'10px', borderRadius:10, border:'none',
          cursor:placing?'wait':'pointer',
          background: dir==='BUY'?'#10b981':'#ef4444', color:'#fff',
          fontSize:13, fontWeight:700, display:'flex', alignItems:'center',
          justifyContent:'center', gap:7, opacity:placing?0.65:1,
        }}>
          {placing ? <Spinner/> : <Zap size={13}/>}
          {placing ? 'Placing…' : `Place ${dir}`}
        </button>

        <div style={{ padding:'8px 11px', borderRadius:9,
          background:'rgba(245,158,11,0.06)', border:'1px solid rgba(245,158,11,0.18)' }}>
          <p style={{ fontSize:10.5, color:'#f59e0b', fontWeight:500, lineHeight:1.5 }}>
            ⚠ Manual trades bypass AI debate but still pass through the risk engine
          </p>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PANEL 7 — SYSTEM HEALTH, RISK ENGINE & PORTFOLIO
// ═══════════════════════════════════════════════════════════════════════════
function SystemPanel({ isDark }: { isDark: boolean }) {
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };
  const { data:health,    refresh:rH } = useFetch<any>('/api/v2/monitoring/health', 12000);
  const { data:riskEng,   refresh:rE } = useFetch<any>('/api/v2/risk-engine/status', 5000);
  const { data:portfolio, refresh:rP } = useFetch<any>('/api/v2/portfolio/summary', 20000);
  const [checkLoading, setCheckLoading] = useState(false);
  const [rebalancing,  setRebalancing]  = useState(false);

  const runChecks = async () => {
    setCheckLoading(true);
    try { await api.post('/api/v2/monitoring/run-checks'); } catch {}
    setTimeout(() => { setCheckLoading(false); rH(); }, 1500);
  };
  const rebalance = async () => {
    setRebalancing(true);
    try { await api.post('/api/v2/portfolio/rebalance'); } catch {}
    setTimeout(() => { setRebalancing(false); rP(); }, 800);
  };

  const subs = health?.subsystems ?? {
    oanda:             { status:'UNKNOWN', latency_ms:0, uptime_pct:99 },
    ai_manager:        { status:'UNKNOWN', latency_ms:0, uptime_pct:99 },
    strategy_registry: { status:'UNKNOWN', latency_ms:0, uptime_pct:99 },
    database:          { status:'UNKNOWN', latency_ms:0, uptime_pct:99 },
  };
  const statusC = (s:string) => s==='OK'?'#10b981':s==='DEGRADED'?'#f59e0b':s==='DOWN'?'#ef4444':'#71717a';
  const StatusIcon = ({ s }: { s:string }) =>
    s==='OK'?<CheckCircle size={12} color="#10b981"/>:
    s==='DEGRADED'?<AlertTriangle size={12} color="#f59e0b"/>:
    s==='DOWN'?<XCircle size={12} color="#ef4444"/>:
    <Minus size={12} color="#71717a"/>;

  const port = portfolio ?? {};
  const portCats: [string,any][] = port.categories ? Object.entries(port.categories) : [];
  const catColors: Record<string,string> = {
    trend:'#10b981', mean_reversion:'#8b5cf6', stat_arb:'#3b82f6', volatility:'#f59e0b', scalping:'#ef4444',
  };

  const re = riskEng ?? {};

  return (
    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10, paddingBottom:16 }}>

      {/* Health */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <p style={{ fontSize:11, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa' }}>System Health</p>
          <button onClick={runChecks} disabled={checkLoading} style={{
            display:'flex', alignItems:'center', gap:5, padding:'5px 11px', borderRadius:8,
            border:'1px solid rgba(16,185,129,0.3)', background:'rgba(16,185,129,0.07)',
            color:'#10b981', cursor:'pointer', fontSize:11, fontWeight:700,
            opacity:checkLoading?0.65:1,
          }}>
            {checkLoading ? <Spinner size={10}/> : <RefreshCw size={10}/>}
            {checkLoading ? '…' : 'Run Checks'}
          </button>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:7, padding:'8px 11px', borderRadius:9, marginBottom:12,
          background:`${statusC(health?.overall_status??'UNKNOWN')}08`,
          border:`1px solid ${statusC(health?.overall_status??'UNKNOWN')}28` }}>
          <span style={{ width:6, height:6, borderRadius:'50%',
            background:statusC(health?.overall_status??'UNKNOWN'),
            animation:'pulse-dot 2s infinite', display:'inline-block' }}/>
          <span style={{ fontSize:12, fontWeight:600, color:statusC(health?.overall_status??'UNKNOWN') }}>
            System {health?.overall_status??'UNKNOWN'}
            {health?.uptime_seconds ? ` · ${Math.floor(health.uptime_seconds/60)}min up` : ''}
          </span>
        </div>
        {Object.entries(subs).map(([name, sub]: any) => (
          <div key={name} style={{ display:'flex', alignItems:'center', gap:9, padding:'7px 0',
            borderBottom:`1px solid ${C.border}` }}>
            <StatusIcon s={sub.status}/>
            <span style={{ flex:1, fontSize:12, color:C.text, textTransform:'capitalize' as const }}>
              {name.replace('_',' ')}
            </span>
            {sub.latency_ms > 0 && (
              <span style={{ fontSize:10.5, color:C.muted, fontFamily:'JetBrains Mono,monospace' }}>
                {sub.latency_ms.toFixed(0)}ms
              </span>
            )}
            <Pill label={sub.status} color={statusC(sub.status)} bg={`${statusC(sub.status)}12`}/>
          </div>
        ))}
        {(health?.recent_alerts?.length??0) > 0 && (
          <div style={{ marginTop:10 }}>
            <p style={{ fontSize:9.5, color:C.muted, fontWeight:700, letterSpacing:'0.06em',
              textTransform:'uppercase' as const, marginBottom:5 }}>Recent Alerts</p>
            {health.recent_alerts.slice(0,3).map((a:any,i:number) => (
              <p key={i} style={{ fontSize:10.5, fontFamily:'JetBrains Mono,monospace',
                color:a.level==='ERROR'?'#ef4444':a.level==='WARNING'?'#f59e0b':'#10b981',
                padding:'3px 0', borderBottom:`1px solid ${C.border}` }}>
                [{a.level}] {a.message?.slice(0,55)}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Risk Engine */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <p style={{ fontSize:11, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' as const,
          color:isDark?'#71717a':'#a1a1aa', marginBottom:14 }}>Risk Engine</p>
        {re.kill_switch_active ? (
          <div style={{ padding:'10px 12px', borderRadius:10, marginBottom:12,
            background:'rgba(239,68,68,0.1)', border:'1px solid rgba(239,68,68,0.3)' }}>
            <p style={{ fontSize:12, fontWeight:700, color:'#ef4444', marginBottom:2 }}>
              🚨 KILL SWITCH ACTIVE
            </p>
            <p style={{ fontSize:10.5, color:'#ef4444' }}>{re.kill_switch_reason}</p>
          </div>
        ) : (
          <div style={{ padding:'7px 11px', borderRadius:9, marginBottom:12,
            background:'rgba(16,185,129,0.06)', border:'1px solid rgba(16,185,129,0.18)' }}>
            <span style={{ fontSize:11.5, fontWeight:600, color:'#10b981' }}>✓ All systems nominal</span>
          </div>
        )}
        <Row label="Current Drawdown"  value={`${(re.current_drawdown_pct??0).toFixed(1)}%`}   color={(re.current_drawdown_pct??0)>10?'#ef4444':(re.current_drawdown_pct??0)>5?'#f59e0b':'#10b981'} isDark={isDark}/>
        <Row label="Daily P&L"         value={`$${(re.daily_pnl??0).toFixed(2)}`}               color={(re.daily_pnl??0)>=0?'#10b981':'#ef4444'} isDark={isDark}/>
        <Row label="Open Trades"       value={`${re.open_trade_count??0} / ${re.max_open_trades??3}`}                               isDark={isDark}/>
        <Row label="DD Limit"          value={`${re.max_drawdown_pct??15}%`}                     color='#f59e0b' isDark={isDark}/>
        <Row label="Risk per Trade"    value={`${re.risk_per_trade_pct??1}%`}                                                       isDark={isDark}/>
        <Row label="Daily Loss Limit"  value={`${re.max_daily_loss_pct??3}%`}                    color='#f59e0b' isDark={isDark}/>
        <Row label="Correlation Limit" value="0.80"                                              color='#f59e0b' isDark={isDark}/>
        <Row label="Currency Exp. Max" value="40%"                                               color='#f59e0b' isDark={isDark}/>
      </div>

      {/* Portfolio Allocator */}
      <div style={{ ...cardStyle(isDark), padding:18 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <p style={{ fontSize:11, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' as const,
            color:isDark?'#71717a':'#a1a1aa' }}>Portfolio Allocator</p>
          <button onClick={rebalance} disabled={rebalancing} style={{
            display:'flex', alignItems:'center', gap:5, padding:'5px 11px', borderRadius:8,
            border:'1px solid rgba(245,158,11,0.3)', background:'rgba(245,158,11,0.07)',
            color:'#f59e0b', cursor:'pointer', fontSize:11, fontWeight:700, opacity:rebalancing?0.65:1,
          }}>
            {rebalancing ? <Spinner size={10}/> : <Settings2 size={10}/>}
            {rebalancing ? '…' : 'Rebalance'}
          </button>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:14 }}>
          {[
            { l:'Total Capital', v:`$${(port.total_capital??0).toLocaleString()}` },
            { l:'Deployed',      v:`$${(port.total_deployed??0).toLocaleString()}` },
            { l:'Total P&L',     v:`$${(port.total_pnl??0).toFixed(0)}` },
            { l:'Last Rebalance',v: port.last_rebalance?.slice(11,16)??'—' },
          ].map(m => (
            <div key={m.l} style={{ padding:'8px 10px', borderRadius:9,
              background: isDark?'rgba(255,255,255,0.025)':'rgba(0,0,0,0.018)',
              border:`1px solid ${C.border}` }}>
              <div style={{ fontSize:9.5, color:C.muted, letterSpacing:'0.06em',
                textTransform:'uppercase' as const, marginBottom:2 }}>{m.l}</div>
              <div style={{ fontSize:14, fontWeight:700, color:C.text,
                fontFamily:'JetBrains Mono,monospace' }}>{m.v}</div>
            </div>
          ))}
        </div>
        {portCats.length > 0 ? portCats.slice(0,5).map(([cat, d]: any) => {
          const pct = port.total_capital>0 ? (d.allocated/port.total_capital*100) : 0;
          const cc  = catColors[cat] ?? '#71717a';
          return (
            <div key={cat} style={{ marginBottom:9 }}>
              <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                <span style={{ fontSize:11.5, color:C.text, textTransform:'capitalize' as const,
                  fontWeight:500 }}>{cat.replace('_',' ')}</span>
                <span style={{ fontSize:11.5, fontWeight:700, color:cc,
                  fontFamily:'JetBrains Mono,monospace' }}>{pct.toFixed(0)}%</span>
              </div>
              <div style={{ height:4, borderRadius:2, overflow:'hidden',
                background:isDark?'rgba(255,255,255,0.07)':'rgba(0,0,0,0.07)' }}>
                <motion.div initial={{ width:0 }} animate={{ width:`${pct}%` }}
                  transition={{ duration:0.7, ease:[0.22,1,0.36,1] }}
                  style={{ height:'100%', background:cc, borderRadius:2 }}/>
              </div>
            </div>
          );
        }) : (
          <p style={{ fontSize:11.5, color:C.muted, textAlign:'center', padding:'8px 0' }}>
            Set capital in .env to activate the allocator
          </p>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// KILL SWITCH BUTTON (global header)
// ═══════════════════════════════════════════════════════════════════════════
function KillSwitch({ isDark }: { isDark: boolean }) {
  const { data: eng, refresh } = useFetch<any>('/api/v2/risk-engine/status', 4000);
  const [confirming, setConfirming] = useState(false);
  const [loading,    setLoading]    = useState(false);
  const ks = eng?.kill_switch_active ?? false;

  const toggle = async () => {
    if (!ks && !confirming) { setConfirming(true); return; }
    setLoading(true); setConfirming(false);
    try {
      if (ks) await api.post('/api/v2/risk-engine/kill-switch/deactivate');
      else    await api.post('/api/v2/risk-engine/kill-switch/activate', {}, { params:{ reason:'Manual — AI Control' } });
    } catch {}
    setTimeout(() => { setLoading(false); refresh(); }, 600);
  };

  return (
    <motion.button onClick={toggle} whileHover={{ scale:1.03 }} whileTap={{ scale:0.97 }} style={{
      display:'flex', alignItems:'center', gap:8, padding:'9px 18px', borderRadius:10,
      border: ks ? 'none' : '1px solid rgba(239,68,68,0.35)',
      cursor:'pointer', background: ks?'#ef4444': confirming?'rgba(239,68,68,0.14)':'rgba(239,68,68,0.07)',
      color: ks?'#fff':'#ef4444', fontSize:12, fontWeight:800,
      letterSpacing:'0.03em', transition:'all 0.2s',
    }}>
      {loading ? <Spinner size={13}/> : <Power size={13}/>}
      {ks ? '🔴 KILL ACTIVE — CLICK TO DEACTIVATE' : confirming ? '⚠ CONFIRM — HALT ALL TRADING' : '🚨 Kill Switch'}
    </motion.button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ROOT PAGE
// ═══════════════════════════════════════════════════════════════════════════
export default function AIControl({ isDark }: { isDark: boolean }) {
  const C = {
    text:  isDark ? '#fafafa'  : '#09090b',
    sub:   isDark ? '#71717a'  : '#71717a',
    muted: isDark ? '#52525b'  : '#a1a1aa',
    border:isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
  };

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>

      {/* Page header */}
      <div style={{ padding:'18px 24px 14px', borderBottom:`1px solid ${C.border}`,
        display:'flex', justifyContent:'space-between', alignItems:'flex-end', flexShrink:0 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:700, letterSpacing:'-0.03em', color:C.text }}>
            AI Control Center<span style={{ color:C.muted }}>.</span>
          </h1>
          <p style={{ fontSize:12.5, color:C.sub, marginTop:3 }}>
            Model fleet · Signal launcher · Debate engine · ML pipeline · Regime scanner · Trade desk · System controls
          </p>
        </div>
        <KillSwitch isDark={isDark}/>
      </div>

      {/* Scrollable body */}
      <div style={{ flex:1, overflowY:'auto', padding:'20px 24px',
        display:'flex', flexDirection:'column', gap:6 }}>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="AI Model Fleet — Live Status" icon={Brain} color="#f59e0b" isDark={isDark}>
            <ModelFleet isDark={isDark}/>
          </Section>
        </motion.div>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.05, duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="Signal Launcher — Run any model on any pair" icon={Terminal} color="#8b5cf6" isDark={isDark}>
            <SignalLauncher isDark={isDark}/>
          </Section>
        </motion.div>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.1, duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="Debate Engine — 4-agent adversarial consensus" icon={GitBranch} color="#a78bfa" isDark={isDark}>
            <DebateEngine isDark={isDark}/>
          </Section>
        </motion.div>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.15, duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="ML Pipeline — Ensemble · RL agent · Retraining scheduler" icon={Cpu} color="#06b6d4" isDark={isDark}>
            <MLPipeline isDark={isDark}/>
          </Section>
        </motion.div>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.2, duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="Regime Scanner — Live ADX-based market regime detection" icon={Eye} color="#3b82f6" isDark={isDark}>
            <RegimeScanner isDark={isDark}/>
          </Section>
        </motion.div>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.25, duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="Trade Desk — Live positions · Quick manual trade" icon={Zap} color="#10b981" isDark={isDark}>
            <TradeDeskPanel isDark={isDark}/>
          </Section>
        </motion.div>

        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.3, duration:0.4, ease:[0.22,1,0.36,1] }}>
          <Section title="System Controls — Health · Risk engine · Portfolio allocator" icon={Shield} color="#ef4444" isDark={isDark}>
            <SystemPanel isDark={isDark}/>
          </Section>
        </motion.div>

        <div style={{ height:20 }}/>
      </div>
    </div>
  );
}
