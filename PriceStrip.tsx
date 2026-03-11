import { useFetch } from '../hooks/useApi';

const DEMO = [
  {instrument:'EUR_USD',bid:1.08415,change:0.12},
  {instrument:'GBP_USD',bid:1.27210,change:-0.08},
  {instrument:'USD_JPY',bid:151.845,change:0.22},
  {instrument:'XAU_USD',bid:2341.50,change:0.45},
  {instrument:'USD_CHF',bid:0.90210,change:-0.05},
  {instrument:'AUD_USD',bid:0.65410,change:0.08},
  {instrument:'USD_CAD',bid:1.35640,change:-0.14},
  {instrument:'US500',  bid:5287.4, change:0.32},
  {instrument:'NAS100', bid:18420.5,change:0.58},
  {instrument:'XAG_USD',bid:27.340, change:-0.22},
];

export default function PriceStrip({ isDark }: { isDark: boolean }) {
  const { data } = useFetch<any>('/account/prices', 15000);
  const prices = data?.prices?.length ? data.prices : DEMO;
  const doubled = [...prices, ...prices];
  return (
    <div style={{ height:32,flexShrink:0,overflow:'hidden',display:'flex',alignItems:'center',
      background:isDark?'rgba(9,9,11,0.9)':'rgba(255,255,255,0.9)',
      borderBottom:`1px solid ${isDark?'rgba(255,255,255,0.05)':'rgba(0,0,0,0.05)'}`,
      backdropFilter:'blur(16px)' }}>
      <style>{`@keyframes ticker{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}`}</style>
      <div style={{ display:'flex',animation:'ticker 60s linear infinite',whiteSpace:'nowrap' }}>
        {doubled.map((p:any,i:number) => (
          <div key={i} style={{ display:'flex',alignItems:'center',gap:6,padding:'0 16px',
            borderRight:`1px solid ${isDark?'rgba(255,255,255,0.04)':'rgba(0,0,0,0.04)'}` }}>
            <span style={{ fontSize:10,fontWeight:500,color:isDark?'#52525b':'#a1a1aa',fontFamily:'JetBrains Mono,monospace',letterSpacing:'0.04em' }}>
              {p.instrument.replace('_','/')}
            </span>
            <span style={{ fontSize:10.5,fontWeight:600,color:isDark?'#e4e4e7':'#18181b',fontFamily:'JetBrains Mono,monospace' }}>
              {p.bid>=100?p.bid.toFixed(2):p.bid.toFixed(5)}
            </span>
            <span style={{ fontSize:9.5,fontWeight:600,padding:'1px 5px',borderRadius:4,
              color:p.change>=0?'#10b981':'#ef4444',
              background:p.change>=0?'rgba(16,185,129,0.1)':'rgba(239,68,68,0.1)' }}>
              {p.change>=0?'+':''}{p.change.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
