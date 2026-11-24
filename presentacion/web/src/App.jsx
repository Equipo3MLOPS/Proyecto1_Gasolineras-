import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DeckCtx, LedDefs } from "./kit.jsx";
import { SLIDES } from "./slides/index.jsx";

const W = 1600, H = 900;
const PRINT = typeof location !== "undefined" && location.hash === "#imprimir";

function readHash() {
  const m = /^#s(\d+)$/.exec(location.hash || "");
  const n = m ? Number(m[1]) - 1 : 0;
  return Math.min(Math.max(n, 0), SLIDES.length - 1);
}

export default function App() {
  const reduced = useMemo(() => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  const [i, setI] = useState(PRINT ? 0 : readHash());
  const prevI = useRef(i);
  const dirRef = useRef(1);
  if (i !== prevI.current) { dirRef.current = i > prevI.current ? 1 : -1; prevI.current = i; }
  const dir = dirRef.current;
  const [scale, setScale] = useState(1);
  const [notes, setNotes] = useState(false);
  const [overview, setOverview] = useState(false);
  const [help, setHelp] = useState(true);
  const touch = useRef(null);

  const go = useCallback((n) => {
    setI((cur) => {
      const nxt = Math.min(Math.max(typeof n === "function" ? n(cur) : n, 0), SLIDES.length - 1);
      try { history.replaceState(null, "", "#s" + (nxt + 1)); } catch { /* sin historial en el marco */ }
      return nxt;
    });
  }, []);

  useEffect(() => {
    if (PRINT) { document.body.classList.add("print"); return undefined; }
    const fit = () => setScale(Math.min(window.innerWidth / W, window.innerHeight / H));
    fit();
    window.addEventListener("resize", fit);
    const onHash = () => setI(readHash());
    window.addEventListener("hashchange", onHash);
    const t = setTimeout(() => setHelp(false), 6000);
    return () => { window.removeEventListener("resize", fit); window.removeEventListener("hashchange", onHash); clearTimeout(t); };
  }, []);

  useEffect(() => {
    if (PRINT) return undefined;
    const onKey = (e) => {
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (["ArrowRight", "PageDown", " ", "Enter"].includes(e.key)) { e.preventDefault(); go((c) => c + 1); }
      else if (["ArrowLeft", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); go((c) => c - 1); }
      else if (e.key === "Home") go(0);
      else if (e.key === "End") go(SLIDES.length - 1);
      else if (e.key.toLowerCase() === "n") setNotes((v) => !v);
      else if (e.key.toLowerCase() === "o" || e.key === "Escape") setOverview((v) => (e.key === "Escape" ? false : !v));
      else if (e.key.toLowerCase() === "f") {
        try {
          if (document.fullscreenElement) document.exitFullscreen();
          else document.documentElement.requestFullscreen().catch(() => {});
        } catch { /* el marco puede no permitir pantalla completa */ }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  const ctx = useMemo(() => ({ print: PRINT, reduced }), [reduced]);


  if (PRINT) {
    return (
      <DeckCtx.Provider value={ctx}>
        <LedDefs />
        {SLIDES.map(({ C }, k) => (
          <div className="viewport" key={k}>
            <div className="stage"><div className="canopy" /><C active n={k + 1} total={SLIDES.length} /></div>
          </div>
        ))}
      </DeckCtx.Provider>
    );
  }

  const S = SLIDES[i];
  return (
    <DeckCtx.Provider value={ctx}>
      <LedDefs />
      <div
        className="viewport"
        onTouchStart={(e) => { touch.current = e.touches[0].clientX; }}
        onTouchEnd={(e) => {
          if (touch.current == null) return;
          const dx = e.changedTouches[0].clientX - touch.current;
          if (Math.abs(dx) > 50) go((c) => c + (dx < 0 ? 1 : -1));
          touch.current = null;
        }}
      >
        <div className="stage" style={{ transform: `translate(-50%, -50%) scale(${scale})` }}>
          <div className="canopy"><i key={i} className={`sweep ${dir < 0 ? "back" : ""}`} /></div>
          {SLIDES.map(({ C }, k) => <C key={k} active={k === i} past={k < i} n={k + 1} total={SLIDES.length} />)}
          <div className="progress" style={{ width: `${((i + 1) / SLIDES.length) * 100}%` }} />
          <button className="navbtn prev" aria-label="Diapositiva anterior" onClick={() => go((c) => c - 1)}>‹</button>
          <button className="navbtn next" aria-label="Diapositiva siguiente" onClick={() => go((c) => c + 1)}>›</button>
        </div>
      </div>
      {help && <div className="help">← → para avanzar · F pantalla completa · O índice · N notas</div>}
      {notes && (
        <div className="notes" role="note">
          <b>{i + 1}. {S.title}</b> · {S.notes}
        </div>
      )}
      {overview && (
        <div className="overview" role="dialog" aria-label="Índice de diapositivas">
          {SLIDES.map((s, k) => (
            <button key={k} className={k === i ? "cur" : ""} onClick={() => { go(k); setOverview(false); }}>
              <b>{k + 1}</b>{s.title}
            </button>
          ))}
        </div>
      )}
    </DeckCtx.Provider>
  );
}
