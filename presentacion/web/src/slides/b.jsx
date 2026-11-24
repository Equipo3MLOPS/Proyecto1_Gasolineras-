import { useMemo, useRef, useState } from "react";
import { Lcd, useSize, useTL } from "../kit.jsx";
import { CLASES, CONF, ETIQUETAS, FUELS, MODELOS, SERIE } from "../data.js";
import { Slide } from "./a.jsx";

const T0 = Date.parse("2022-12-01"), T1 = Date.parse("2026-12-01");
const tx = (s, w) => ((Date.parse(s) - T0) / (T1 - T0)) * w;
const YEARS = ["2023", "2024", "2025", "2026"];

// =================================================================== 6. Capa Oro: la serie semanal
export function Oro(p) {
  const r = useRef();
  const box = useRef();
  const { w, h } = useSize(box);
  const [on, setOn] = useState({ super: true, regular: false, diesel: false, v_power: false });
  const [hover, setHover] = useState(null);
  const pad = { l: 64, r: 24, t: 16, b: 44 };
  const W = Math.max(w - pad.l - pad.r, 10), Hh = Math.max(h - pad.t - pad.b, 10);
  const y = (v) => pad.t + Hh - ((v - 20) / (48 - 20)) * Hh;
  const x = (s) => pad.l + tx(s, W);
  useTL(r, p.active, (tl) => {
    tl.from(".oro-line", { strokeDashoffset: 4000, duration: 1.8, ease: "power2.inOut" })
      .from(".oro-dot", { opacity: 0, duration: 0.25, stagger: 0.018 }, 0.3)
      .from(".oro-note", { opacity: 0, y: 6, duration: 0.45 }, 1.6);
  }, [w > 0]);
  const peak = SERIE.super.reduce((a, b) => (b[1] > a[1] ? b : a));
  return (
    <Slide {...p} innerRef={r}>
      <h2>En 2026 la súper pasó de Q28 a Q45 por galón</h2>
      <div className="row" style={{ gap: 12, marginTop: 22, alignItems: "center" }}>
        <span className="small">Capa Oro · precio promedio semanal (martes a lunes):</span>
        {FUELS.map((f) => (
          <button key={f.k} className="chip" aria-pressed={on[f.k]} onClick={() => setOn((o) => ({ ...o, [f.k]: !o[f.k] }))}>
            <i style={{ background: f.color }} />{f.name} ({SERIE[f.k].length})
          </button>
        ))}
      </div>
      <div ref={box} className="grow" style={{ position: "relative", marginTop: 14 }}>
        {w > 0 && (
          <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
            {[20, 25, 30, 35, 40, 45].map((v) => (
              <g key={v}>
                <line x1={pad.l} x2={w - pad.r} y1={y(v)} y2={y(v)} stroke="var(--grid)" />
                <text x={pad.l - 12} y={y(v) + 6} textAnchor="end" fontSize="17" fill="var(--text-3)">Q{v}</text>
              </g>
            ))}
            {YEARS.map((yr) => (
              <text key={yr} x={x(`${yr}-07-01`)} y={h - 10} textAnchor="middle" fontSize="18" fill="var(--text-3)">{yr}</text>
            ))}
            {YEARS.map((yr) => <line key={yr} x1={x(`${yr}-01-01`)} x2={x(`${yr}-01-01`)} y1={pad.t} y2={pad.t + Hh} stroke="var(--grid)" />)}
            {FUELS.filter((f) => on[f.k]).map((f) => {
              const pts = SERIE[f.k];
              const d = pts.map(([s, v], i) => `${i ? "L" : "M"}${x(s).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
              return (
                <g key={f.k}>
                  <path className="oro-line" d={d} fill="none" stroke={f.color} style={{ color: f.color }} strokeWidth="3" strokeDasharray="4000" strokeLinejoin="round" />
                  {pts.map(([s, v]) => (
                    <circle key={s} className="oro-dot" cx={x(s)} cy={y(v)} r="6" fill="var(--asfalto)" stroke={f.color} strokeWidth="3"
                      onMouseEnter={() => setHover({ s, v, f: f.name, c: f.color })} onMouseLeave={() => setHover(null)} />
                  ))}
                </g>
              );
            })}
            {on.super && (
              <g className="oro-note">
                <line x1={x(peak[0])} x2={x(peak[0]) - 90} y1={y(peak[1])} y2={y(peak[1]) + 10} stroke="var(--text-2)" />
                <text x={x(peak[0]) - 96} y={y(peak[1]) + 16} textAnchor="end" fontSize="19" fontWeight="600" fill="var(--text)">
                  Q{peak[1].toFixed(2)} · semana del 29/09/26
                </text>
              </g>
            )}
          </svg>
        )}
        {hover && (
          <div className="tip" style={{ left: x(hover.s), top: y(hover.v) - 64 }}>
            <b style={{ color: hover.c }}>{hover.f}</b> · {hover.s.split("-").reverse().join("/")} · Q{hover.v.toFixed(2)}
          </div>
        )}
      </div>
      <div className="small oro-note">Cada punto es una semana con foto. Los huecos entre puntos son semanas sin foto: eso importa para el modelo.</div>
    </Slide>
  );
}

// =================================================================== 7. Etiqueta
export function Etiqueta(p) {
  const r = useRef();
  const [d, setD] = useState(0.45);
  const base = 38.09;
  const lab = d > 0.1 ? "sube" : d < -0.1 ? "baja" : "se mantiene";
  const total = ETIQUETAS.sube + ETIQUETAS.baja + ETIQUETAS.se_mantiene;
  useTL(r, p.active, (tl) => {
    tl.from(".et-left", { opacity: 0, x: -16 })
      .from(".et-bar span", { scaleX: 0, transformOrigin: "left center", stagger: { each: 0.1, ease: "power2.in" }, duration: 0.8 }, 0.15)
      .from(".et-goal", { opacity: 0, y: 8 }, 0.6);
  });
  const pos = (v) => `${((v + 1) / 2) * 100}%`;
  return (
    <Slide {...p} innerRef={r}>
      <h2>Cada semana recibe una etiqueta: sube, baja o se mantiene</h2>
      <div className="row grow" style={{ marginTop: 36, gap: 64 }}>
        <div className="et-left col" style={{ flex: 1.15, gap: 26 }}>
          <div className="row" style={{ gap: 22, alignItems: "flex-end" }}>
            <Lcd to={base.toFixed(2)} h={70} cap="Semana anterior" />
            <span style={{ fontSize: 40, paddingBottom: 18 }}>→</span>
            <Lcd to={(base + d).toFixed(2)} h={70} cap="Esta semana" />
            <div className={`et-lab ${lab.replace(" ", "-")}`}>{lab === "sube" ? "▲ " : lab === "baja" ? "▼ " : "= "}{lab}</div>
          </div>
          <div className="scale">
            <div className="zone" style={{ left: pos(-0.1), width: `${(0.2 / 2) * 100}%` }}>±Q0.10</div>
            <div className="knob" style={{ left: pos(d) }} />
            <span style={{ left: 0 }}>−Q1.00</span><span style={{ left: "50%" }}>Q0</span><span style={{ left: "100%" }}>+Q1.00</span>
          </div>
          <label className="field" style={{ fontSize: 20 }}>Muevan el cambio de precio: <b>{d >= 0 ? "+" : "−"}Q{Math.abs(d).toFixed(2)}</b>
            <input type="range" min="-1" max="1" step="0.01" value={d} onChange={(e) => setD(Number(e.target.value))} aria-label="Cambio de precio contra la semana anterior" />
          </label>
          <div className="small">Un cambio menor a 10 centavos no cuenta: absorbe el redondeo del precio efectivo y las diferencias entre estaciones.</div>
        </div>
        <div className="col" style={{ flex: 1, gap: 20 }}>
          <div className="small">Etiquetas de las {total} semanas que sirven para entrenar (los cuatro combustibles)</div>
          {[["Sube", ETIQUETAS.sube, "var(--sube)"], ["Baja", ETIQUETAS.baja, "var(--baja)"], ["Se mantiene", ETIQUETAS.se_mantiene, "var(--igual)"]].map(([t, n, c]) => (
            <div key={t} className="et-bar">
              <div className="row" style={{ justifyContent: "space-between", fontSize: 22 }}><b>{t}</b><span>{n}</span></div>
              <div className="track"><span style={{ width: `${(n / ETIQUETAS.sube) * 100}%`, background: c }} /></div>
            </div>
          ))}
          <div className="et-goal panel body" style={{ marginTop: "auto" }}>
            El modelo recibe la semana actual y debe adivinar la etiqueta de la <b>semana siguiente</b>. Solo 9 semanas «se mantienen»: es la clase más difícil.
          </div>
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 8. Validación temporal
export function Validacion(p) {
  const r = useRef();
  useTL(r, p.active, (tl) => {
    tl.from(".vt-cell", { opacity: 0, scale: 0.9, stagger: { each: 0.006, ease: "power1.in" }, duration: 0.2 })
      .from(".vt-test", { backgroundColor: "rgba(255,176,0,0.32)", boxShadow: "0 0 0 rgba(234,244,255,0)", stagger: { each: 0.025, ease: "power1.in" }, duration: 0.25 }, 0.75)
      .from(".vt-lbl", { opacity: 0, y: 6, stagger: 0.08 }, 1.2)
      .from(".cv-row", { opacity: 0, x: -12, stagger: { each: 0.08, ease: "power2.in" } }, 1.35);
  });
  const cells = Array.from({ length: 99 }, (_, i) => i >= 71);
  return (
    <Slide {...p} innerRef={r}>
      <h2>Lo evaluamos con semanas que nunca vio</h2>
      <p className="lead">Las 99 semanas etiquetadas, ordenadas en el tiempo. El modelo aprende del pasado y se prueba con lo más reciente, como pasaría en la vida real.</p>
      <div className="vt" style={{ marginTop: 34 }}>
        {cells.map((t, i) => <span key={i} className={`vt-cell ${t ? "vt-test" : ""}`} />)}
      </div>
      <div className="row" style={{ marginTop: 14, justifyContent: "space-between" }}>
        <div className="vt-lbl body"><b>71 semanas para entrenar</b> · dic 2022 a ene 2026</div>
        <div className="vt-lbl body" style={{ color: "var(--luz)" }}><b>28 para probar</b> · 27 ene a 27 oct 2026</div>
      </div>
      <div className="col" style={{ marginTop: 40, gap: 12 }}>
        <div className="small">Además, validación cruzada en el tiempo: cuatro cortes con ventana creciente (esquema)</div>
        {[1, 2, 3, 4].map((k) => (
          <div key={k} className="cv-row">
            <span className="small" style={{ width: 90 }}>Corte {k}</span>
            <div className="cv-track">
              <span className="cv-train" style={{ width: `${(k / 5) * 100}%` }} />
              <span className="cv-test" style={{ width: "20%" }} />
            </div>
          </div>
        ))}
      </div>
      <div className="small" style={{ marginTop: 16 }}>Con una validación aleatoria el modelo habría visto el futuro y su exactitud saldría inflada.</div>
    </Slide>
  );
}

// =================================================================== 9. Resultados
export function Resultados(p) {
  const r = useRef();
  const [vista, setVista] = useState("barras");
  useTL(r, p.active, (tl) => {
    if (vista === "matriz") {
      tl.from(".cm-c", { opacity: 0, scale: 0.94, stagger: { each: 0.035, from: "start" }, duration: 0.3 });
      return;
    }
    tl.from(".rs-row:not(.ref) .rs-fill", { scaleX: 0, transformOrigin: "left center", duration: 0.9, stagger: { each: 0.12, ease: "power2.in" } })
      .from(".rs-row:not(.ref) .rs-v", { opacity: 0, stagger: 0.12 }, 0.35)
      .from(".rs-row.ref", { opacity: 0 }, 1.3)
      .from(".rs-row.ref .rs-fill", { scaleX: 0, transformOrigin: "left center", duration: 0.8 }, 1.35)
      .from(".rs-side > div", { opacity: 0, x: 12, stagger: { each: 0.1, ease: "power2.in" } }, 1.7);
  }, [vista]);
  const max = 60;
  return (
    <Slide {...p} innerRef={r}>
      <h2>El modelo supera a la línea base por un acierto</h2>
      <div className="row" style={{ gap: 10, marginTop: 20 }}>
        <button className="chip" aria-pressed={vista === "barras"} onClick={() => setVista("barras")}>Exactitud por modelo</button>
        <button className="chip" aria-pressed={vista === "matriz"} onClick={() => setVista("matriz")}>Aciertos del bosque por clase</button>
      </div>
      <div className="row grow" style={{ marginTop: 26, gap: 56 }}>
        {vista === "barras" ? (
          <div className="col" style={{ flex: 1.35, gap: 16 }}>
            <div className="small">Exactitud en las 28 semanas de prueba</div>
            {MODELOS.map((m) => (
              <div key={m.m} className={`rs-row ${m.ref ? "ref" : ""} ${m.sel ? "sel" : ""} ${m.base ? "base" : ""}`}>
                <div className="rs-name">{m.m}</div>
                <div className="rs-track"><span className="rs-fill" style={{ width: `${(m.acc / max) * 100}%` }} /></div>
                <div className="rs-v">{m.acc.toFixed(1)} %</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="col" style={{ flex: 1.35 }}>
            <div className="small" style={{ marginBottom: 12 }}>Bosque aleatorio en las 28 semanas de prueba: filas = lo que pasó, columnas = lo que predijo</div>
            <div className="cm">
              <span /> {CLASES.map((c) => <span key={c} className="cm-h">predijo {c.toLowerCase()}</span>)}
              {CONF.map((row, i) => [
                <span key={`h${i}`} className="cm-h" style={{ textAlign: "right" }}>{CLASES[i].toLowerCase()} ({row.reduce((a, b) => a + b, 0)})</span>,
                ...row.map((n, j) => (
                  <span key={`${i}${j}`} className={`cm-c ${i === j ? "diag" : ""}`} style={{ "--a": n / 10 }}>{n}</span>
                )),
              ])}
            </div>
            <div className="body" style={{ marginTop: 18 }}>Acierta 7 de 11 bajas pero solo 5 de 16 subidas: tiende a predecir «baja» de más.</div>
          </div>
        )}
        <div className="rs-side col" style={{ flex: 1, gap: 26 }}>
          <div><div className="rs-k">12 contra 11</div><div className="body">aciertos del bosque frente a la línea base. Con 28 casos no es una mejora demostrada.</div></div>
          <div><div className="rs-k">57.1 %</div><div className="body">acierta decir siempre «sube»: el precio subió 16 de las 28 semanas.</div></div>
          <div><div className="rs-k">46 % ± 3 %</div><div className="body">promedio del bosque en los cuatro cortes; el más estable, por eso es el elegido.</div></div>
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 10. Limitaciones
export function Limitaciones(p) {
  const r = useRef();
  const box = useRef();
  const { w } = useSize(box);
  useTL(r, p.active, (tl) => {
    tl.from(".lm-dot", { opacity: 0, stagger: { each: 0.006, ease: "power1.in" }, duration: 0.2 })
      .from(".lm-ring", { opacity: 0, scale: 1.6, transformOrigin: "center", stagger: 0.2, duration: 0.5 }, 1.0)
      .from(".lm-item", { opacity: 0, y: 8, stagger: { each: 0.08, ease: "power2.in" } }, 1.3);
  }, [w > 0]);
  const L = 150, R = 20;
  const xx = (s) => L + tx(s, Math.max(w - L - R, 10));
  const outliers = [["diesel", "2022-12-27"], ["regular", "2025-08-26"]];
  const gaps = useMemo(() => Object.fromEntries(FUELS.map((f) => {
    const s = SERIE[f.k]; let g = 0;
    for (let i = 1; i < s.length; i++) g += (Date.parse(s[i][0]) - Date.parse(s[i - 1][0])) / 864e5;
    return [f.k, Math.round(g / (s.length - 1))];
  })), []);
  return (
    <Slide {...p} innerRef={r}>
      <h2>Los datos ponen el techo, no el algoritmo</h2>
      <div ref={box} style={{ marginTop: 34, height: 330, position: "relative" }}>
        {w > 0 && (
          <svg width={w} height={330}>
            {FUELS.map((f, i) => {
              const yy = 34 + i * 72;
              return (
                <g key={f.k}>
                  <text x={0} y={yy + 7} fontSize="21" fill="var(--text)" fontWeight="600">{f.name}</text>
                  <line x1={L} x2={w - R} y1={yy} y2={yy} stroke="var(--grid)" strokeWidth="2" />
                  {SERIE[f.k].map(([s]) => <circle key={s} className="lm-dot" cx={xx(s)} cy={yy} r="8" fill={f.color} />)}
                  {outliers.filter(([k]) => k === f.k).map(([, s]) => (
                    <circle key={s} className="lm-ring" cx={xx(s)} cy={yy} r="17" fill="none" stroke="var(--text)" strokeWidth="3" strokeDasharray="5 4" />
                  ))}
                </g>
              );
            })}
            {YEARS.map((yr) => <text key={yr} x={xx(`${yr}-07-01`)} y={322} textAnchor="middle" fontSize="18" fill="var(--text-3)">{yr}</text>)}
          </svg>
        )}
      </div>
      <div className="small" style={{ marginTop: 2 }}>Cada punto es una semana con foto. Con círculo punteado, dos precios que no encajan con sus vecinos: probables errores de lectura.</div>
      <div className="row" style={{ gap: 22, marginTop: "auto" }}>
        {[
          ["Fotos irregulares", `En promedio ${gaps.super} días entre fotos de súper y ${gaps.v_power} en V-Power: la «semana siguiente» a veces está a meses.`],
          ["Pocos ejemplos", "99 semanas etiquetadas en cuatro años; solo 9 de «se mantiene»."],
          ["Combustible mal asignado", "En la revisión a mano, 10 de 20 fotos eran súper y quedaron en otro combustible. Además, dos atípicos pasan las reglas."],
          ["Sin contexto externo", "El modelo solo ve el precio local; falta el precio internacional del petróleo."],
        ].map(([t, s]) => (
          <div key={t} className="lm-item panel" style={{ flex: 1 }}>
            <div style={{ fontSize: 23, fontWeight: 700 }}>{t}</div>
            <div className="small" style={{ marginTop: 6, color: "var(--text-2)" }}>{s}</div>
          </div>
        ))}
      </div>
    </Slide>
  );
}
