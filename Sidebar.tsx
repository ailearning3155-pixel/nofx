import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useWebSocket } from "../hooks/useWebSocket";

const NAV = [
  { section: "TRADING", items: [
    { path:"/",         icon:"◈", label:"Live Dashboard" },
    { path:"/arena",    icon:"⬡", label:"AI Arena",     badge:"6 AI" },
    { path:"/debate",   icon:"◎", label:"Debate Room"   },
  ]},
  { section: "RESEARCH", items: [
    { path:"/backtest",    icon:"◷", label:"Backtest Engine" },
    { path:"/strategies",  icon:"◆", label:"Strategy Lab",   badge:"45" },
  ]},
  { section: "SYSTEM", items: [
    { path:"/risk",  icon:"⬢", label:"Risk Console" },
  ]},
];

function useClock() {
  const [t, setT] = useState(new Date());
  useEffect(()=>{ const id=setInterval(()=>setT(new Date()),1000); return()=>clearInterval(id); },[]);
  const d = t.toUTCString();
  return d.slice(5,16) + " · " + d.slice(17,25);
}

export default function Sidebar() {
  const {status}    = useSystemStatus();
  const {connected} = useWebSocket();
  const clock       = useClock();
  const mode        = status?.trading?.mode?.toUpperCase() || "BACKTEST";

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">N</div>
        <div className="brand-info">
          <div className="brand-name">NOFX</div>
          <div className="brand-ver">TRADING OS  v2.0</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({section, items}) => (
          <div key={section}>
            <div className="nav-section">{section}</div>
            {items.map(({path,icon,label,badge})=>(
              <NavLink key={path} to={path} end={path==="/"} className={({isActive})=>`nav-item${isActive?" active":""}`}>
                <span className="nav-icon">{icon}</span>
                <span className="nav-label">{label}</span>
                {badge && <span className="nav-badge">{badge}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="status-item">
          <span className={`dot ${status?.oanda?.connected?"dot-on":"dot-off"}`}/>
          <span>OANDA {status?.oanda?.connected?"Connected":"Offline"}</span>
        </div>
        <div className="status-item">
          <span className={`dot ${connected?"dot-on":"dot-warn"}`}/>
          <span>WS {connected?"Live":"Reconnecting"}</span>
        </div>
        <div className="status-item">
          <span className={`dot ${(status?.ai?.count||0)>0?"dot-on":"dot-off"}`}/>
          <span>{status?.ai?.count||0} AI models active</span>
        </div>
        <div className={`mode-pill ${mode==="LIVE"?"mode-live":mode==="PAPER"?"mode-paper":"mode-bt"}`}>
          <span style={{width:5,height:5,borderRadius:"50%",background:"currentColor",display:"inline-block"}}/>
          {mode} MODE
        </div>
        <div className="sidebar-clock">{clock} UTC</div>
      </div>
    </aside>
  );
}
