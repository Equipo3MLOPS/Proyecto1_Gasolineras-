import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import gsap from "gsap";

// ------------------------------------------------------------------ contexto del deck
export const DeckCtx = createContext({ print: false, reduced: false });
export const useDeck = () => useContext(DeckCtx);

// Timeline de entrada de una diapositiva: se construye al activarse y se revierte al salir.
// En modo impresión (o con movimiento reducido) salta directo al estado final.
export function useTL(ref, active, build, deps = []) {
  const { print, reduced } = useDeck();
  useLayoutEffect(() => {
    if (!active && !print) return undefined;
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 0.6 }, delay: 0.12 });
      build(tl);
      if (print || reduced) tl.progress(1);
    }, ref);
    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, print, reduced, ...deps]);
}

// ------------------------------------------------------------------ 7 segmentos
const T = 10; // grosor del segmento
const H = (y, x1, x2) => `${x1},${y} ${x1 + T / 2},${y - T / 2} ${x2 - T / 2},${y - T / 2} ${x2},${y} ${x2 - T / 2},${y + T / 2} ${x1 + T / 2},${y + T / 2}`;
const V = (x, y1, y2) => `${x},${y1} ${x + T / 2},${y1 + T / 2} ${x + T / 2},${y2 - T / 2} ${x},${y2} ${x - T / 2},${y2 - T / 2} ${x - T / 2},${y1 + T / 2}`;
const SEGS = {
  a: H(6, 9, 47), g: H(50, 9, 47), d: H(94, 9, 47),
  f: V(6, 9, 48), b: V(50, 9, 48), e: V(6, 52, 91), c: V(50, 52, 91),
};
const MAP = {
  0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgecd", 7: "abc", 8: "abcdefg",
  9: "abcdfg", "-": "g", " ": "",
};

// Los rótulos de precio reales arman cada segmento con LED redondos en fila: 5 por segmento.
const lin = (a, b, n) => Array.from({ length: n }, (_, k) => a + ((b - a) * k) / (n - 1));
const DOTS = {
  a: lin(12, 44, 5).map((x) => [x, 6]), g: lin(12, 44, 5).map((x) => [x, 50]), d: lin(12, 44, 5).map((x) => [x, 94]),
  f: lin(13, 43, 5).map((y) => [6, y]), b: lin(13, 43, 5).map((y) => [50, y]),
  e: lin(57, 87, 5).map((y) => [6, y]), c: lin(57, 87, 5).map((y) => [50, y]),
};

// Degradado del LED encendido (centro casi blanco, borde naranja); se define una vez en App.
export function LedDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <radialGradient id="ledHot" cx="45%" cy="40%" r="60%">
          <stop offset="0" stopColor="#fff6d8" />
          <stop offset="0.3" stopColor="#ffd060" />
          <stop offset="0.72" stopColor="#ffa200" />
          <stop offset="1" stopColor="#e27400" />
        </radialGradient>
        <filter id="ledGlow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3.2" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <radialGradient id="ledOff" cx="45%" cy="40%" r="60%">
          <stop offset="0" stopColor="#3a2a10" />
          <stop offset="1" stopColor="#1c150a" />
        </radialGradient>
      </defs>
    </svg>
  );
}

export function Seg({ text, h = 80, color, ghost, glow, power = false, delay = 0 }) {
  const chars = [];
  const s = String(text);
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch === ".") continue;
    chars.push({ ch, dot: s[i + 1] === "." });
  }
  const w = (h / 100) * 56;
  const dots = h >= 34; // en tamaños chicos los puntos no se leen: segmentos lisos
  const on = color || (dots ? "url(#ledHot)" : "var(--led)");
  const off = ghost || (dots ? "url(#ledOff)" : "var(--led-off)");
  const style = { ...(glow ? { "--glow": glow } : {}), "--d": `${delay}ms` };
  return (
    <span className={`seg ${power ? "power" : ""} ${dots ? "dots" : ""}`} aria-label={s} role="img" style={style}>
      {chars.map(({ ch, dot }, i) => (
        <svg key={i} width={w + h * 0.16} height={h} viewBox="-2 0 72 100" style={{ "--i": i }}>
          <g transform="skewX(-7) translate(10 0)">
            {dots ? (
              <>
                <g>{Object.entries(DOTS).filter(([k]) => !(MAP[ch] || "").includes(k)).map(([k, pts]) => pts.map(([x, y], j) => <circle key={k + j} cx={x} cy={y} r="3.6" fill={off} />))}
                  {!dot && <circle cx="62" cy="92" r="4" fill={off} />}</g>
                <g className="lit" filter="url(#ledGlow)">{Object.entries(DOTS).filter(([k]) => (MAP[ch] || "").includes(k)).map(([k, pts]) => pts.map(([x, y], j) => <circle key={k + j} cx={x} cy={y} r="3.6" fill={on} />))}
                  {dot && <circle cx="62" cy="92" r="4" fill={on} />}</g>
              </>
            ) : (
              <>
                {Object.entries(SEGS).map(([k, pts]) => (
                  <polygon key={k} points={pts} fill={(MAP[ch] || "").includes(k) ? on : off} />
                ))}
                <circle cx="62" cy="92" r="5.5" fill={dot ? on : off} />
              </>
            )}
          </g>
        </svg>
      ))}
    </span>
  );
}

const fmt = (v, dec, pad) => {
  let s = Number(v).toFixed(dec);
  if (pad && s.replace(".", "").length < pad) s = " ".repeat(pad - s.replace(".", "").length) + s;
  return s;
};

// Módulo LED con conteo animado hasta `to`; al activarse, los segmentos se encienden con parpadeo.
export function Lcd({ to, dec = 0, pad, h = 80, cap, unit, from = 0, delay = 0, dur = 1.4, active, className = "", style, color, glow }) {
  const { print, reduced } = useDeck();
  const [v, setV] = useState(to);
  useEffect(() => {
    if (print || reduced || !active || typeof to !== "number") { setV(to); return undefined; }
    const o = { v: from };
    setV(from);
    const tw = gsap.to(o, { v: to, duration: dur, delay, ease: "power3.out", onUpdate: () => setV(o.v) });
    return () => tw.kill();
  }, [active, to, print, reduced]);
  const text = typeof to === "number" ? fmt(v, dec, pad) : to;
  const power = !!active && !print && !reduced;
  return (
    <span className={`lcd ${cap ? "capped" : ""} ${className}`} style={style}>
      {cap && <span className="cap">{cap}</span>}
      <Seg text={text} h={h} power={power} delay={Math.round(delay * 1000)} color={color} glow={glow} />
      {unit && <span className="unit">{unit}</span>}
    </span>
  );
}

// Escala de un SVG que se dibuja al tamaño real.
export function useSize(ref) {
  const [size, setSize] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);
  return size;
}

export function Bar({ n, total, label }) {
  return (
    <div className="bar">
      <span>Equipo 3 · CC3105 · Predicción del precio de la gasolina en Guatemala</span>
      <span className="count">{label && <span>{label}</span>}<Seg text={`${String(n).padStart(2, "0")}-${String(total).padStart(2, "0")}`} h={20} /></span>
    </div>
  );
}

export const usePrevious = (v) => { const r = useRef(); useEffect(() => { r.current = v; }); return r.current; };
