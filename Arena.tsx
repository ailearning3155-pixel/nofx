import { motion } from 'motion/react';
import { useFetch } from '../hooks/useApi';
import { Swords, Trophy, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

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

const DEMO_MODELS = [
  { model:'claude',   win_rate:68.4, total_signals:142, avg_confidence:0.81, total_pnl:4820, current_streak:5,  rank:1 },
  { model:'gpt4o',    win_rate:65.2, total_signals:138, avg_confidence:0.77, total_pnl:3640, current_streak:3,  rank:2 },
  { model:'deepseek', win_rate:62.8, total_signals:156, avg_confidence:0.74, total_pnl:2980, current_streak:-2, rank:3 },
  { model:'gemini',   win_rate:60.1, total_signals:127, avg_confidence:0.71, total_pnl:2140, current_streak:1,  rank:4 },
  { model:'grok',     win_rate:57.3, total_signals:119, avg_confidence:0.68, total_pnl:1520, current_streak:4,  rank:5 },
  { model:'qwen',     win_rate:54.6, total_signals:98,  avg_confidence:0.64, total_pnl:860,  current_streak:-1, rank:6 },
];

export default function Arena({ isDark }: { isDark: boolean }) {
  const { data } = useFetch<any>('/competition/leaderboard', 30000);
  const models = data?.models ?? DEMO_MODELS;
  const C = { text:isDark?'#fafafa':'#09090b', sub:isDark?'#71717a':'#71717a', muted:isDark?'#52525b':'#a1a1aa', border:isDark?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)' };

  const chartData = models.map((m:any) => ({ name:m.model, wr:parseFloat(m.win_rate.toFixed(1)), fill:MODEL_COLORS[m.model]??'#71717a' }));

  return (
    <div style={{ display:'flex',flexDirection:'column',height:'100%',overflow:'hidden' }}>
      <div style={{ padding:'18px 24px 14px',borderBottom:`1px solid ${C.border}`,display:'flex',justifyContent:'space-between',alignItems:'flex-end' }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:700,letterSpacing:'-0.03em',color:C.text }}>
            AI Arena<span style={{ color:C.muted }}>.</span>
          </h1>
          <p style={{ fontSize:12.5,color:C.sub,marginTop:3 }}>Live model competition · Win rate leaderboard · Signal performance tracking</p>
        </div>
        <div style={{ display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:9,
          background:'rgba(245,158,11,0.1)',border:'1px solid rgba(245,158,11,0.2)' }}>
          <Trophy size={12} color="#f59e0b"/>
          <span style={{ fontSize:11.5,fontWeight:600,color:'#f59e0b' }}>Season Active</span>
        </div>
      </div>

      <div style={{ flex:1,overflowY:'auto',padding:'18px 24px',display:'flex',flexDirection:'column',gap:14 }}>

        {/* Bar chart */}
        <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.45,ease:[0.22,1,0.36,1] }}
          style={{ ...cardStyle(isDark),padding:22 }}>
          <h3 style={{ fontSize:14,fontWeight:600,color:C.text,marginBottom:16 }}>Win Rate Comparison</h3>
          <div style={{ height:180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top:0,right:0,left:-20,bottom:0 }}>
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill:isDark?'#52525b':'#a1a1aa',fontSize:11,textTransform:'capitalize' }}/>
                <YAxis axisLine={false} tickLine={false} tick={{ fill:isDark?'#52525b':'#a1a1aa',fontSize:11 }} domain={[45,75]} tickFormatter={v=>`${v}%`}/>
                <Tooltip formatter={(v:any) => [`${v}%`, 'Win Rate']} contentStyle={{ background:isDark?'rgba(24,24,27,0.95)':'rgba(255,255,255,0.95)',border:`1px solid ${C.border}`,borderRadius:10,fontSize:12 }}/>
                <Bar dataKey="wr" radius={[6,6,0,0]} fill="#10b981"
                  label={{ position:'top',formatter:(v:any)=>`${v}%`,fontSize:10,fill:isDark?'#71717a':'#a1a1aa' }}/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Leaderboard */}
        <motion.div initial={{ opacity:0,y:16 }} animate={{ opacity:1,y:0 }} transition={{ duration:0.45,delay:0.1,ease:[0.22,1,0.36,1] }}
          style={{ ...cardStyle(isDark),padding:20 }}>
          <h3 style={{ fontSize:14,fontWeight:600,color:C.text,marginBottom:14 }}>Model Leaderboard</h3>
          {models.map((m: any, i: number) => {
            const color = MODEL_COLORS[m.model] ?? '#71717a';
            const streak = m.current_streak ?? 0;
            return (
              <motion.div key={m.model}
                initial={{ opacity:0,x:-16 }} animate={{ opacity:1,x:0 }}
                transition={{ delay:i*0.06,duration:0.35,ease:[0.22,1,0.36,1] }}
                style={{ display:'flex',alignItems:'center',gap:14,padding:'12px 0',
                  borderBottom:i<models.length-1?`1px solid ${C.border}`:'none' }}>
                {/* Rank */}
                <div style={{ width:24,textAlign:'center',fontSize:13,fontWeight:700,
                  color:i===0?'#f59e0b':i===1?'#a1a1aa':i===2?'#b87333':C.muted }}>
                  {i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1}
                </div>
                {/* Color dot */}
                <div style={{ width:8,height:8,borderRadius:'50%',background:color,flexShrink:0 }}/>
                {/* Name */}
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:13,fontWeight:600,color,textTransform:'capitalize',letterSpacing:'0.02em' }}>{m.model}</div>
                  <div style={{ fontSize:11,color:C.muted }}>{m.total_signals} signals</div>
                </div>
                {/* Win rate */}
                <div style={{ textAlign:'right' }}>
                  <div style={{ fontSize:15,fontWeight:700,color:C.text,fontFamily:'JetBrains Mono,monospace' }}>
                    {m.win_rate.toFixed(1)}%
                  </div>
                  <div style={{ fontSize:10,color:C.muted }}>win rate</div>
                </div>
                {/* P&L */}
                <div style={{ textAlign:'right',minWidth:70 }}>
                  <div style={{ fontSize:13,fontWeight:700,fontFamily:'JetBrains Mono,monospace',color:m.total_pnl>=0?'#10b981':'#ef4444' }}>
                    {m.total_pnl>=0?'+':''}${m.total_pnl.toLocaleString()}
                  </div>
                  <div style={{ fontSize:10,color:C.muted }}>total P&L</div>
                </div>
                {/* Streak */}
                <div style={{ display:'flex',alignItems:'center',gap:3,padding:'3px 8px',borderRadius:6,
                  background:streak>0?'rgba(16,185,129,0.1)':streak<0?'rgba(239,68,68,0.1)':'rgba(113,113,122,0.1)',
                  color:streak>0?'#10b981':streak<0?'#ef4444':'#71717a' }}>
                  {streak>0?<ArrowUpRight size={11}/>:streak<0?<ArrowDownRight size={11}/>:<Minus size={11}/>}
                  <span style={{ fontSize:11,fontWeight:700 }}>{Math.abs(streak)}</span>
                </div>
              </motion.div>
            );
          })}
        </motion.div>

        <div style={{ height:8 }}/>
      </div>
    </div>
  );
}
