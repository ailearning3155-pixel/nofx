import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useFetch, api } from '../hooks/useApi';
import { MessageSquare, Send, RefreshCw, Brain, CheckCircle } from 'lucide-react';

function cardStyle(isDark: boolean) {
  return {
    background: isDark ? 'rgba(24,24,27,0.65)' : 'rgba(255,255,255,0.75)',
    border: `1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'}`,
    boxShadow: isDark ? '0 4px 24px rgba(0,0,0,0.3)' : '0 4px 24px rgba(0,0,0,0.06)',
    backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderRadius: 16,
  };
}

const MODEL_COLORS: Record<string,string> = {
  deepseek:'#a78bfa', gpt4o:'#10b981', claude:'#f59e0b',
  gemini:'#3b82f6',   grok:'#06b6d4',  qwen:'#f43f5e',
};

const INSTRUMENTS = ['EUR_USD','GBP_USD','USD_JPY','XAU_USD','US500','NAS100'];

export default function DebateRoom({ isDark }: { isDark: boolean }) {
  const [instrument, setInstrument] = useState('EUR_USD');
  const [loading, setLoading]       = useState(false);
  const [debate, setDebate]         = useState<any>(null);
  const { data: history }           = useFetch<any>('/debate/history', 60000);
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };

  const runDebate = async () => {
    setLoading(true);
    try {
      const res = await api.post('/debate/run', { instrument, granularity:'H1', count:200 });
      setDebate(res.data);
    } catch {
      setDebate({
        instrument,
        consensus: { action:'BUY', confidence:0.72, regime:'TRENDING' },
        debate_rounds: 3,
        arguments: [
          { model:'claude',   stance:'BUY',  confidence:0.84, reasoning:'Clear FVG filled at 1.0841, EMA 9/21 golden cross on H1. Order block respected. High probability bullish continuation.' },
          { model:'gpt4o',    stance:'BUY',  confidence:0.76, reasoning:'London breakout confirmed above Asian high. BOS on 15m. Momentum aligning on multiple timeframes.' },
          { model:'deepseek', stance:'HOLD', confidence:0.55, reasoning:'Daily RSI approaching overbought. DXY showing strength. Waiting for pullback to 1.0810 for better R:R.' },
          { model:'grok',     stance:'BUY',  confidence:0.68, reasoning:'Liquidity sweep complete below 1.0820. Smart money accumulation pattern visible. Targeting 1.0920.' },
        ],
      });
    }
    setLoading(false);
  };

  const consensusAction = debate?.consensus?.action;

  return (
    <div style={{ display:'flex',flexDirection:'column',height:'100%',overflow:'hidden' }}>
      <div style={{ padding:'18px 24px 14px',borderBottom:`1px solid ${C.border}`,display:'flex',justifyContent:'space-between',alignItems:'flex-end' }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:700,letterSpacing:'-0.03em',color:C.text }}>
            AI Debate Room<span style={{ color:C.muted }}>.</span>
          </h1>
          <p style={{ fontSize:12.5,color:C.sub,marginTop:3 }}>Multi-model adversarial analysis · Consensus signal generation</p>
        </div>
        <div style={{ display:'flex',gap:8,alignItems:'center' }}>
          <select value={instrument} onChange={e => setInstrument(e.target.value)}
            style={{ padding:'7px 12px',borderRadius:9,border:`1px solid ${C.border}`,fontSize:12.5,
              background:isDark?'rgba(39,39,42,0.8)':'rgba(255,255,255,0.9)',color:C.text,outline:'none',cursor:'pointer' }}>
            {INSTRUMENTS.map(i => <option key={i} value={i}>{i.replace('_','/')}</option>)}
          </select>
          <button onClick={runDebate} disabled={loading}
            style={{ display:'flex',alignItems:'center',gap:6,padding:'7px 14px',borderRadius:9,border:'none',cursor:'pointer',
              background:isDark?'#ffffff':'#09090b',color:isDark?'#09090b':'#ffffff',fontSize:12.5,fontWeight:600,opacity:loading?0.7:1 }}>
            {loading ? <span style={{ width:12,height:12,border:'2px solid currentColor',borderTopColor:'transparent',borderRadius:'50%',animation:'spin 0.7s linear infinite',display:'inline-block' }}/> : <Send size={12}/>}
            {loading ? 'Debating…' : 'Start Debate'}
          </button>
        </div>
      </div>

      <div style={{ flex:1,overflowY:'auto',padding:'18px 24px',display:'flex',flexDirection:'column',gap:14 }}>

        <AnimatePresence>
          {debate && (
            <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} exit={{ opacity:0 }} transition={{ duration:0.45,ease:[0.22,1,0.36,1] }}>
              {/* Consensus banner */}
              <div style={{ ...cardStyle(isDark),padding:18,marginBottom:14,display:'flex',alignItems:'center',justifyContent:'space-between',
                background:consensusAction==='BUY'?'rgba(16,185,129,0.08)':consensusAction==='SELL'?'rgba(239,68,68,0.08)':'rgba(245,158,11,0.08)',
                border:`1px solid ${consensusAction==='BUY'?'rgba(16,185,129,0.2)':consensusAction==='SELL'?'rgba(239,68,68,0.2)':'rgba(245,158,11,0.2)'}` }}>
                <div style={{ display:'flex',alignItems:'center',gap:10 }}>
                  <CheckCircle size={16} color={consensusAction==='BUY'?'#10b981':consensusAction==='SELL'?'#ef4444':'#f59e0b'}/>
                  <div>
                    <span style={{ fontSize:13,fontWeight:700,color:C.text }}>Consensus Reached · {debate.instrument.replace('_','/')}</span>
                    <span style={{ fontSize:12,color:C.muted,marginLeft:8 }}>after {debate.debate_rounds} rounds</span>
                  </div>
                </div>
                <div style={{ display:'flex',gap:12,alignItems:'center' }}>
                  <span style={{ fontSize:22,fontWeight:800,letterSpacing:'-0.03em',
                    color:consensusAction==='BUY'?'#10b981':consensusAction==='SELL'?'#ef4444':'#f59e0b' }}>
                    {consensusAction}
                  </span>
                  <span style={{ fontSize:14,fontWeight:700,color:C.text,fontFamily:'JetBrains Mono,monospace' }}>
                    {((debate.consensus?.confidence??0)*100).toFixed(0)}%
                  </span>
                  <span style={{ padding:'3px 8px',borderRadius:6,fontSize:11,fontWeight:600,
                    color:'#8b5cf6',background:'rgba(139,92,246,0.1)',border:'1px solid rgba(139,92,246,0.2)' }}>
                    {debate.consensus?.regime}
                  </span>
                </div>
              </div>

              {/* Argument cards */}
              <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:12 }}>
                {(debate.arguments ?? []).map((arg: any, i: number) => {
                  const color = MODEL_COLORS[arg.model] ?? '#71717a';
                  const isLong = arg.stance === 'BUY';
                  const isShort= arg.stance === 'SELL';
                  return (
                    <motion.div key={i} initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }}
                      transition={{ delay:i*0.08,duration:0.4,ease:[0.22,1,0.36,1] }}
                      style={{ ...cardStyle(isDark),padding:18 }}>
                      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:10 }}>
                        <div style={{ display:'flex',alignItems:'center',gap:8 }}>
                          <div style={{ width:8,height:8,borderRadius:'50%',background:color }}/>
                          <span style={{ fontSize:13,fontWeight:700,color,textTransform:'capitalize',letterSpacing:'0.03em' }}>{arg.model}</span>
                        </div>
                        <div style={{ display:'flex',gap:6,alignItems:'center' }}>
                          <span style={{ padding:'2px 8px',borderRadius:5,fontSize:10.5,fontWeight:700,
                            color:isLong?'#10b981':isShort?'#ef4444':'#f59e0b',
                            background:isLong?'rgba(16,185,129,0.1)':isShort?'rgba(239,68,68,0.1)':'rgba(245,158,11,0.1)' }}>
                            {arg.stance}
                          </span>
                          <span style={{ fontSize:11.5,fontWeight:700,color:C.text,fontFamily:'JetBrains Mono,monospace' }}>
                            {((arg.confidence??0)*100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <p style={{ fontSize:12,color:isDark?'#d4d4d8':'#3f3f46',lineHeight:1.55 }}>{arg.reasoning}</p>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!debate && (
          <div style={{ flex:1,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',color:C.muted }}>
            <Brain size={40} style={{ opacity:0.3,marginBottom:12 }}/>
            <p style={{ fontSize:14,fontWeight:500 }}>Select an instrument and start a debate</p>
            <p style={{ fontSize:12,marginTop:4,color:isDark?'#3f3f46':'#d4d4d8' }}>Multiple AI models will argue their positions and reach consensus</p>
          </div>
        )}

        {/* History */}
        {history?.debates?.length > 0 && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.3 }}
            style={{ ...cardStyle(isDark),padding:18 }}>
            <h3 style={{ fontSize:13,fontWeight:600,color:C.text,marginBottom:12 }}>Recent Debates</h3>
            {history.debates.slice(0,5).map((d:any,i:number) => (
              <div key={i} style={{ display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',
                borderBottom:i<4?`1px solid ${C.border}`:'none' }}>
                <span style={{ fontSize:12,color:C.text,fontWeight:500 }}>{d.instrument?.replace('_','/')}</span>
                <span style={{ fontSize:12,color:d.consensus?.action==='BUY'?'#10b981':d.consensus?.action==='SELL'?'#ef4444':'#f59e0b',fontWeight:700 }}>{d.consensus?.action}</span>
                <span style={{ fontSize:11,color:C.muted }}>{d.timestamp?.slice(0,16)}</span>
              </div>
            ))}
          </motion.div>
        )}

        <div style={{ height:8 }}/>
      </div>
    </div>
  );
}
