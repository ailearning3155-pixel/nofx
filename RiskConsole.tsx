import { useState } from 'react';
import { motion } from 'motion/react';
import { useFetch, api } from '../hooks/useApi';
import { ShieldAlert, AlertTriangle, CheckCircle, Zap, TrendingUp, TrendingDown } from 'lucide-react';

function cardStyle(isDark: boolean) {
  return {
    background:    isDark ? 'rgba(24,24,27,0.65)' : 'rgba(255,255,255,0.75)',
    border:        `1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'}`,
    boxShadow:     isDark ? '0 4px 24px rgba(0,0,0,0.3)' : '0 4px 24px rgba(0,0,0,0.06)',
    backdropFilter:'blur(20px)',
    WebkitBackdropFilter:'blur(20px)',
    borderRadius:  16,
  };
}

export default function RiskConsole({ isDark }: { isDark: boolean }) {
  const { data, refresh } = useFetch<any>('/risk/status');
  const { data: eng }     = useFetch<any>('/v2/risk-engine/status', 5000);
  const { data: exp }     = useFetch<any>('/v2/exposure/summary',  10000);
  const { data: corr }    = useFetch<any>('/v2/correlation/matrix', 10000);
  const { data: orders }  = useFetch<any>('/v2/orders/summary',    10000);
  const { data: perf }    = useFetch<any>('/v2/risk/strategy-performance', 30000);
  const [confirming, setConfirming] = useState(false);

  const activateKS = async () => {
    if (!confirming) { setConfirming(true); return; }
    try { await api.post('/v2/risk-engine/kill-switch/activate'); } catch {}
    setConfirming(false); refresh();
  };
  const deactivateKS = async () => {
    try { await api.post('/v2/risk-engine/kill-switch/deactivate'); } catch {}
    refresh();
  };

  const ks = eng?.kill_switch_active ?? data?.kill_switch_active ?? false;
  const drawdown = eng?.current_drawdown_pct ?? 0;
  const dailyPnl = eng?.daily_pnl ?? 0;

  const RULES = [
    `Max ${eng?.max_daily_loss_pct ?? 3}% daily loss — auto kill switch`,
    `Max ${eng?.max_drawdown_pct ?? 15}% drawdown — halts all trading`,
    `Max ${eng?.max_open_trades ?? 3} concurrent open positions`,
    `${eng?.risk_per_trade_pct ?? 1}% risk per trade (ATR-based sizing)`,
    'Correlation control — blocks correlated pairs (|r| > 0.8)',
    'Currency exposure limit — max 40% per single currency',
    '30-min blackout around high-impact news events',
  ];

  const strategies = perf?.strategies ?? [];

  const C = {
    text:  isDark ? '#fafafa'  : '#09090b',
    sub:   isDark ? '#71717a'  : '#71717a',
    muted: isDark ? '#52525b'  : '#a1a1aa',
    row:   isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
    border:isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
  };

  return (
    <div style={{ display:'flex',flexDirection:'column',height:'100%',overflow:'hidden' }}>
      {/* Header */}
      <div style={{ padding:'18px 24px 14px',borderBottom:`1px solid ${C.border}`,display:'flex',justifyContent:'space-between',alignItems:'flex-end' }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:700,letterSpacing:'-0.03em',color:C.text }}>
            Risk Console<span style={{ color:C.muted }}>.</span>
          </h1>
          <p style={{ fontSize:12.5,color:C.sub,marginTop:3 }}>Position limits · Drawdown monitor · Emergency controls</p>
        </div>
        {ks ? (
          <button onClick={deactivateKS} style={{ padding:'8px 16px',borderRadius:10,border:'none',cursor:'pointer',
            background:'#ef4444',color:'#fff',fontSize:12,fontWeight:700,letterSpacing:'0.04em' }}>
            🔴 KILL SWITCH ACTIVE — CLICK TO DEACTIVATE
          </button>
        ) : (
          <button onClick={activateKS} style={{ padding:'8px 16px',borderRadius:10,cursor:'pointer',
            border:'1px solid rgba(239,68,68,0.35)',background:confirming?'rgba(239,68,68,0.15)':'rgba(239,68,68,0.07)',
            color:'#ef4444',fontSize:12,fontWeight:700,letterSpacing:'0.04em',transition:'all 0.2s' }}>
            {confirming ? '⚠️ CLICK AGAIN TO CONFIRM' : '🚨 ACTIVATE KILL SWITCH'}
          </button>
        )}
      </div>

      <div style={{ flex:1,overflowY:'auto',padding:'18px 24px',display:'flex',flexDirection:'column',gap:14 }}>

        {/* Status metrics */}
        <div style={{ display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12 }}>
          {[
            { l:'Kill Switch', v:ks?'ACTIVE':'SAFE',   c:ks?'#ef4444':'#10b981' },
            { l:'Daily P&L',   v:`${dailyPnl>=0?'+':''}$${dailyPnl.toFixed(2)}`, c:dailyPnl>=0?'#10b981':'#ef4444' },
            { l:'Drawdown',    v:`${drawdown.toFixed(1)}%`, c:drawdown>10?'#ef4444':drawdown>5?'#f59e0b':'#10b981' },
            { l:'Open Trades', v:`${eng?.open_trade_count??0} / ${eng?.max_open_trades??3}`, c:C.text },
          ].map((m,i) => (
            <motion.div key={m.l} initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ delay:i*0.06,duration:0.45,ease:[0.22,1,0.36,1] }}
              style={{ ...cardStyle(isDark),padding:18 }}>
              <div style={{ fontSize:10.5,fontWeight:600,letterSpacing:'0.07em',textTransform:'uppercase',color:C.muted,marginBottom:8 }}>{m.l}</div>
              <div style={{ fontSize:24,fontWeight:800,color:m.c,fontFamily:'JetBrains Mono,monospace',letterSpacing:'-0.02em' }}>{m.v}</div>
            </motion.div>
          ))}
        </div>

        {/* Risk rules + Exposure + Correlation */}
        <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:12 }}>

          {/* Risk rules */}
          <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.25,duration:0.45,ease:[0.22,1,0.36,1] }}
            style={{ ...cardStyle(isDark),padding:20 }}>
            <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:14 }}>
              <ShieldAlert size={14} color="#8b5cf6"/>
              <h3 style={{ fontSize:14,fontWeight:600,color:C.text }}>Risk Rules</h3>
            </div>
            {RULES.map((r,i) => (
              <div key={i} style={{ display:'flex',alignItems:'flex-start',gap:8,padding:'7px 0',
                borderBottom:i<RULES.length-1?`1px solid ${C.border}`:'none' }}>
                <CheckCircle size={11} color="#10b981" style={{ marginTop:1,flexShrink:0 }}/>
                <span style={{ fontSize:12,color:isDark?'#d4d4d8':'#3f3f46' }}>{r}</span>
              </div>
            ))}
          </motion.div>

          {/* Exposure + Orders */}
          <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
            <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.3,duration:0.45,ease:[0.22,1,0.36,1] }}
              style={{ ...cardStyle(isDark),padding:18 }}>
              <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:12 }}>
                <Zap size={13} color="#f59e0b"/>
                <h3 style={{ fontSize:13,fontWeight:600,color:C.text }}>Currency Exposure</h3>
              </div>
              {exp?.net_exposure && Object.keys(exp.net_exposure).length > 0 ? (
                Object.entries(exp.net_exposure).slice(0,5).map(([k,v]:any) => (
                  <div key={k} style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6 }}>
                    <span style={{ fontSize:12,fontWeight:500,color:C.sub }}>{k}</span>
                    <span style={{ fontSize:12,fontWeight:700,fontFamily:'JetBrains Mono,monospace',
                      color:Math.abs(v)>0.35?'#ef4444':'#10b981' }}>{(v*100).toFixed(0)}%</span>
                  </div>
                ))
              ) : (
                <p style={{ fontSize:12,color:C.muted }}>No open positions — exposure clear</p>
              )}
              {exp?.limit_breaches?.length>0 && (
                <div style={{ marginTop:8,padding:'6px 10px',borderRadius:8,background:'rgba(239,68,68,0.08)',border:'1px solid rgba(239,68,68,0.2)' }}>
                  <span style={{ fontSize:11,color:'#ef4444',fontWeight:600 }}>⚠ Breach: {exp.limit_breaches.join(', ')}</span>
                </div>
              )}
            </motion.div>

            <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.35,duration:0.45,ease:[0.22,1,0.36,1] }}
              style={{ ...cardStyle(isDark),padding:18 }}>
              <div style={{ display:'flex',alignItems:'center',gap:8,marginBottom:12 }}>
                <AlertTriangle size={13} color="#06b6d4"/>
                <h3 style={{ fontSize:13,fontWeight:600,color:C.text }}>Order Lifecycle</h3>
              </div>
              {[
                { l:'Active Orders',    v:orders?.active_orders  ?? 0 },
                { l:'Filled',          v:orders?.filled_orders  ?? 0 },
                { l:'Rejected',        v:orders?.rejected_orders?? 0 },
                { l:'Total P&L',       v:`$${(orders?.total_pnl??0).toFixed(0)}` },
              ].map(r => (
                <div key={r.l} style={{ display:'flex',justifyContent:'space-between',marginBottom:6 }}>
                  <span style={{ fontSize:12,color:C.sub }}>{r.l}</span>
                  <span style={{ fontSize:12,fontWeight:700,color:C.text,fontFamily:'JetBrains Mono,monospace' }}>{r.v}</span>
                </div>
              ))}
            </motion.div>
          </div>
        </div>

        {/* Strategy performance table */}
        {strategies.length > 0 && (
          <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ delay:0.4,duration:0.45,ease:[0.22,1,0.36,1] }}
            style={{ ...cardStyle(isDark),padding:20 }}>
            <h3 style={{ fontSize:14,fontWeight:600,color:C.text,marginBottom:14 }}>Strategy Performance</h3>
            <div style={{ overflowX:'auto' }}>
              <table style={{ width:'100%',borderCollapse:'collapse',fontSize:12 }}>
                <thead>
                  <tr style={{ borderBottom:`1px solid ${C.border}` }}>
                    {['Strategy','Category','Win Rate','Trades','Sharpe','P&L','Status'].map(h => (
                      <th key={h} style={{ padding:'6px 10px',textAlign:'left',fontSize:10.5,fontWeight:600,letterSpacing:'0.06em',textTransform:'uppercase',color:C.muted }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {strategies.map((s:any,i:number) => (
                    <tr key={i} style={{ borderBottom:`1px solid ${C.border}`,background:i%2===0?C.row:'transparent' }}>
                      <td style={{ padding:'8px 10px',fontWeight:500,color:C.text }}>{s.name}</td>
                      <td style={{ padding:'8px 10px',color:C.sub }}>{s.category}</td>
                      <td style={{ padding:'8px 10px',fontFamily:'JetBrains Mono,monospace',color:s.win_rate>=55?'#10b981':s.win_rate>=45?'#f59e0b':'#ef4444' }}>{s.win_rate?.toFixed(1)}%</td>
                      <td style={{ padding:'8px 10px',fontFamily:'JetBrains Mono,monospace',color:C.text }}>{s.total_trades}</td>
                      <td style={{ padding:'8px 10px',fontFamily:'JetBrains Mono,monospace',color:C.text }}>{s.sharpe_ratio?.toFixed(2)}</td>
                      <td style={{ padding:'8px 10px',fontFamily:'JetBrains Mono,monospace',color:s.total_pnl>=0?'#10b981':'#ef4444' }}>{s.total_pnl>=0?'+':''}${s.total_pnl?.toFixed(0)}</td>
                      <td style={{ padding:'8px 10px' }}>
                        <span style={{ padding:'2px 7px',borderRadius:5,fontSize:10,fontWeight:700,
                          color:s.enabled?'#10b981':'#ef4444',background:s.enabled?'rgba(16,185,129,0.1)':'rgba(239,68,68,0.1)' }}>
                          {s.enabled?'ON':'OFF'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        <div style={{ height:8 }}/>
      </div>
    </div>
  );
}
