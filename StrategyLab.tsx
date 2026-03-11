import { motion } from 'motion/react';
import { useFetch } from '../hooks/useApi';
import { FlaskConical, Activity, TrendingUp, Zap, BarChart3, Brain } from 'lucide-react';

function cardStyle(isDark: boolean) {
  return {
    background: isDark ? 'rgba(24,24,27,0.65)' : 'rgba(255,255,255,0.75)',
    border: `1px solid ${isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'}`,
    boxShadow: isDark ? '0 4px 24px rgba(0,0,0,0.3)' : '0 4px 24px rgba(0,0,0,0.06)',
    backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderRadius: 16,
  };
}

const CATEGORY_META: Record<string, { color: string; icon: any; desc: string; alloc: string }> = {
  trend:          { color:'#10b981', icon:TrendingUp,  desc:'Momentum and directional strategies',   alloc:'35%' },
  mean_reversion: { color:'#8b5cf6', icon:Activity,    desc:'Pullback and reversion strategies',     alloc:'20%' },
  stat_arb:       { color:'#3b82f6', icon:BarChart3,   desc:'Statistical arbitrage & Kalman pairs',  alloc:'20%' },
  volatility:     { color:'#f59e0b', icon:Zap,         desc:'Volatility expansion & compression',    alloc:'15%' },
  scalping:       { color:'#ef4444', icon:FlaskConical, desc:'High-frequency price action signals',  alloc:'10%' },
  ml:             { color:'#a78bfa', icon:Brain,       desc:'XGBoost, RandomForest, LSTM models',    alloc:'–' },
  composite:      { color:'#06b6d4', icon:Activity,    desc:'Multi-signal composite strategies',     alloc:'–' },
  microstructure: { color:'#f43f5e', icon:Zap,         desc:'Order flow & liquidity detection',      alloc:'–' },
  macro:          { color:'#84cc16', icon:TrendingUp,  desc:'Interest rate & macro differential',    alloc:'–' },
};

const DEMO_CATS = [
  { category:'trend',          total:7,  enabled:7,  win_rate:61.2, avg_confidence:0.72 },
  { category:'mean_reversion', total:6,  enabled:5,  win_rate:58.4, avg_confidence:0.67 },
  { category:'stat_arb',       total:3,  enabled:3,  win_rate:63.1, avg_confidence:0.74 },
  { category:'volatility',     total:4,  enabled:4,  win_rate:56.8, avg_confidence:0.65 },
  { category:'scalping',       total:15, enabled:13, win_rate:54.2, avg_confidence:0.61 },
  { category:'ml',             total:3,  enabled:3,  win_rate:68.5, avg_confidence:0.81 },
  { category:'composite',      total:3,  enabled:3,  win_rate:65.3, avg_confidence:0.76 },
  { category:'microstructure', total:2,  enabled:2,  win_rate:59.0, avg_confidence:0.69 },
  { category:'macro',          total:1,  enabled:1,  win_rate:62.0, avg_confidence:0.70 },
];

export default function StrategyLab({ isDark }: { isDark: boolean }) {
  const { data } = useFetch<any>('/strategies/categories', 30000);
  const cats = data?.categories ?? DEMO_CATS;
  const total_strategies = cats.reduce((s: number, c: any) => s + (c.total ?? 0), 0);
  const total_enabled    = cats.reduce((s: number, c: any) => s + (c.enabled ?? 0), 0);
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };

  return (
    <div style={{ display:'flex',flexDirection:'column',height:'100%',overflow:'hidden' }}>
      <div style={{ padding:'18px 24px 14px',borderBottom:`1px solid ${C.border}`,display:'flex',justifyContent:'space-between',alignItems:'flex-end' }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:700,letterSpacing:'-0.03em',color:C.text }}>
            Strategy Lab<span style={{ color:C.muted }}>.</span>
          </h1>
          <p style={{ fontSize:12.5,color:C.sub,marginTop:3 }}>43 strategies across 9 categories · Regime-gated · Confidence-calibrated</p>
        </div>
        <div style={{ display:'flex',gap:16 }}>
          <div style={{ textAlign:'right' }}>
            <div style={{ fontSize:22,fontWeight:700,color:'#10b981',fontFamily:'JetBrains Mono,monospace' }}>{total_enabled}</div>
            <div style={{ fontSize:10.5,color:C.muted,letterSpacing:'0.06em',textTransform:'uppercase' }}>Active</div>
          </div>
          <div style={{ textAlign:'right' }}>
            <div style={{ fontSize:22,fontWeight:700,color:C.text,fontFamily:'JetBrains Mono,monospace' }}>{total_strategies}</div>
            <div style={{ fontSize:10.5,color:C.muted,letterSpacing:'0.06em',textTransform:'uppercase' }}>Total</div>
          </div>
        </div>
      </div>

      <div style={{ flex:1,overflowY:'auto',padding:'18px 24px' }}>

        {/* Regime gate info */}
        <motion.div initial={{ opacity:0,y:12 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.4 }}
          style={{ ...cardStyle(isDark),padding:16,marginBottom:14,display:'flex',gap:20,alignItems:'center',
            background:isDark?'rgba(16,185,129,0.06)':'rgba(16,185,129,0.04)',border:'1px solid rgba(16,185,129,0.15)' }}>
          <div style={{ width:8,height:8,borderRadius:'50%',background:'#10b981',flexShrink:0,animation:'pulse-dot 2s infinite' }}/>
          <div>
            <span style={{ fontSize:12.5,fontWeight:600,color:'#10b981' }}>Market Regime Enforcement Active</span>
            <span style={{ fontSize:12,color:isDark?'#52525b':'#a1a1aa',marginLeft:8 }}>
              Trend strategies → Trending market · Mean reversion → Ranging · Volatility → Breakout
            </span>
          </div>
        </motion.div>

        {/* Category grid */}
        <div style={{ display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12 }}>
          {cats.map((cat: any, i: number) => {
            const meta = CATEGORY_META[cat.category] ?? { color:'#71717a', icon:Activity, desc:'', alloc:'–' };
            const Icon = meta.icon;
            const allEnabled = (cat.enabled ?? cat.total) === cat.total;
            return (
              <motion.div key={cat.category}
                initial={{ opacity:0,y:20 }} animate={{ opacity:1,y:0 }}
                whileHover={{ y:-3,scale:1.005 }}
                transition={{ duration:0.45,delay:i*0.05,ease:[0.22,1,0.36,1] }}
                style={{ ...cardStyle(isDark),padding:18,cursor:'default' }}>
                <div style={{ display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:12 }}>
                  <div style={{ display:'flex',alignItems:'center',gap:8 }}>
                    <div style={{ width:30,height:30,borderRadius:8,background:`${meta.color}15`,display:'flex',alignItems:'center',justifyContent:'center' }}>
                      <Icon size={14} color={meta.color}/>
                    </div>
                    <div>
                      <div style={{ fontSize:12.5,fontWeight:600,color:isDark?'#e4e4e7':'#18181b',textTransform:'capitalize' }}>
                        {cat.category.replace('_',' ')}
                      </div>
                      <div style={{ fontSize:10,color:isDark?'#52525b':'#a1a1aa',marginTop:1 }}>Alloc: {meta.alloc}</div>
                    </div>
                  </div>
                  <span style={{ padding:'2px 7px',borderRadius:5,fontSize:10,fontWeight:700,letterSpacing:'0.04em',
                    color:allEnabled?'#10b981':'#f59e0b',background:allEnabled?'rgba(16,185,129,0.1)':'rgba(245,158,11,0.1)' }}>
                    {cat.enabled ?? cat.total}/{cat.total}
                  </span>
                </div>
                <p style={{ fontSize:11,color:isDark?'#52525b':'#a1a1aa',marginBottom:12,lineHeight:1.4 }}>{meta.desc}</p>
                <div style={{ display:'flex',justifyContent:'space-between',paddingTop:10,borderTop:`1px solid ${isDark?'rgba(255,255,255,0.05)':'rgba(0,0,0,0.05)'}` }}>
                  <div>
                    <div style={{ fontSize:16,fontWeight:700,color:meta.color,fontFamily:'JetBrains Mono,monospace' }}>
                      {(cat.win_rate ?? 60).toFixed(1)}%
                    </div>
                    <div style={{ fontSize:10,color:isDark?'#52525b':'#a1a1aa' }}>Win rate</div>
                  </div>
                  <div style={{ textAlign:'right' }}>
                    <div style={{ fontSize:16,fontWeight:700,color:isDark?'#e4e4e7':'#18181b',fontFamily:'JetBrains Mono,monospace' }}>
                      {((cat.avg_confidence ?? 0.7)*100).toFixed(0)}%
                    </div>
                    <div style={{ fontSize:10,color:isDark?'#52525b':'#a1a1aa' }}>Avg confidence</div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
        <div style={{ height:16 }}/>
      </div>
    </div>
  );
}
