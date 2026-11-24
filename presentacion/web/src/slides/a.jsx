import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { Bar, Lcd, Seg, useDeck, useTL } from "../kit.jsx";
import { FOTO, FUELS, INTEGRANTES, PLATA, REV, REVISION, SERIE } from "../data.js";
import foto from "../assets/surtidor.jpg";

export function Slide({ active, past, n, total, dark, cls = "", label, innerRef, children }) {
  return (
    <section ref={innerRef} className={`slide ${dark ? "dark" : ""} ${active ? "on" : past ? "past" : ""} ${cls}`} aria-hidden={!active}>
      {children}
      <Bar n={n} total={total} label={label} />
    </section>
  );
}

// =================================================================== 1. Portada
const PY_DELAYS = [420, 560, 650, 715]; // encendido de cada fila: huecos que se acortan, como un rótulo que arranca

export function Portada(p) {
  const r = useRef();
  const { print, reduced } = useDeck();
  const on = !!p.active && !print && !reduced;
  useTL(r, p.active, (tl) => {
    tl.from(".p-title", { y: 28, opacity: 0, duration: 0.7 })
      .from(".pylon", { y: 36, opacity: 0, duration: 0.7 }, 0.06)
      .fromTo(".py-crown", { "--lit": 0 }, { "--lit": 1, duration: 0.4, ease: "steps(5)" }, 0.3)
      .from(".p-lead", { y: 10, opacity: 0 }, 0.2)
      .from(".p-names", { opacity: 0, duration: 0.5 }, 0.32)
      .from(".p-hl", { opacity: 0, scale: 0.97, duration: 0.4 }, 1.25)
      .from(".py-note", { opacity: 0, y: 8, duration: 0.45 }, 1.32);
  });
  return (
    <Slide {...p} innerRef={r} cls="s-portada">
      <div className="row grow" style={{ alignItems: "center", gap: 80 }}>
        <div className="col" style={{ flex: 1.15 }}>
          <h1 className="p-title">¿Sube o baja la gasolina la próxima semana?</h1>
          <p className="lead p-lead">Un pipeline que lee fotos de surtidores, ordena los precios por semana y predice la dirección del precio de cada combustible.</p>
          <div className="small p-names">CC3105 · Equipo 3 · {INTEGRANTES.join(" · ")}</div>
        </div>
        <div className="pylon">
          <div className="py-crown lightbox"><span>Equipo 3</span><i /></div>
          <div className="py-sign housing">
            <div className="py-head"><span>Precio por galón</span><span>quetzales</span></div>
            {FUELS.map((f, i) => (
              <div key={f.k} className={`py-row ${f.k}`}>
                <span className={`plate ${f.k === "regular" || f.k === "diesel" ? "dark-ink" : ""}`} style={{ "--c": f.color }}>{f.name}</span>
                <Seg text={FOTO.precios[f.k].toFixed(2)} h={62} power={on} delay={PY_DELAYS[i]} />
              </div>
            ))}
            <div className="p-hl" aria-hidden="true" />
            <div className="py-note">Esta venta Q{FOTO.venta.toFixed(2)} ÷ {FOTO.galones.toFixed(3)} galones = <b>Q38.09</b>: la foto es de súper</div>
          </div>
          <div className="py-pole" />
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 2. Problema
const ICONS = {
  camion: <svg viewBox="0 0 64 40" width="64" height="40"><rect x="2" y="6" width="36" height="22" rx="3" /><path d="M40 12h12l8 9v7H40z" /><circle cx="14" cy="32" r="6" fill="var(--ico-bg)" stroke="currentColor" strokeWidth="4" /><circle cx="50" cy="32" r="6" fill="var(--ico-bg)" stroke="currentColor" strokeWidth="4" /></svg>,
  tienda: <svg viewBox="0 0 64 40" width="64" height="40"><path d="M6 4h52l4 12H2z" /><rect x="8" y="18" width="48" height="20" rx="2" /><rect x="26" y="24" width="12" height="14" fill="var(--ico-bg)" /></svg>,
  carro: <svg viewBox="0 0 64 40" width="64" height="40"><path d="M6 22l8-12h30l10 12h4v8H4v-8z" /><circle cx="16" cy="32" r="6" fill="var(--ico-bg)" stroke="currentColor" strokeWidth="4" /><circle cx="48" cy="32" r="6" fill="var(--ico-bg)" stroke="currentColor" strokeWidth="4" /></svg>,
};
const SEMANAS_2026 = SERIE.super.filter(([s]) => s >= "2026-01-01");
const fecha = (s) => { const [y, m, d] = s.split("-"); return `${d}/${m}/${y.slice(2)}`; };

export function Problema(p) {
  const r = useRef();
  const { print } = useDeck();
  const [k, setK] = useState(SEMANAS_2026.length - 1);
  useEffect(() => {
    if (!p.active || print) return undefined;
    setK(0);
    let j = 0;
    const id = setInterval(() => { j += 1; if (j >= SEMANAS_2026.length) { clearInterval(id); return; } setK(j); }, 520);
    return () => clearInterval(id);
  }, [p.active, print]);
  const [sem, precio] = SEMANAS_2026[k];
  const prev = k > 0 ? SEMANAS_2026[k - 1][1] : null;
  const d = prev == null ? 0 : precio - prev;
  const dir = prev == null ? "" : d > 0.1 ? "sube" : d < -0.1 ? "baja" : "se mantiene";
  useTL(r, p.active, (tl) => {
    tl.from(".pb-board", { y: 18, opacity: 0, duration: 0.7 })
      .from(".who > div", { x: 16, opacity: 0, stagger: { each: 0.09, ease: "power2.in" } }, 0.12)
      .from(".question", { opacity: 0, duration: 0.5 }, 0.5)
      .fromTo(".question", { "--lit": 0 }, { "--lit": 1, duration: 0.4, ease: "steps(5)" }, 0.55);
  });
  return (
    <Slide {...p} innerRef={r}>
      <h2>Cada martes hay un precio nuevo</h2>
      <p className="lead">El Ministerio de Energía y Minas publica cada martes precios de referencia que valen de martes a lunes.</p>
      <div className="row grow" style={{ marginTop: 34, gap: 56 }}>
        <div className="pb-board">
          <div className="small" style={{ marginBottom: 10 }}>Súper en las fotos de 2026, semana por semana</div>
          <div className="board housing">
            <div className="board-week">Semana del {fecha(sem)}</div>
            <div className="row" style={{ alignItems: "flex-end", gap: 20 }}>
              <Lcd to={precio.toFixed(2)} h={120} unit="Q/gal" />
              <div className={`board-dir ${dir.replace(" ", "-")}`}>{dir === "sube" ? "▲ sube" : dir === "baja" ? "▼ baja" : dir ? "= se mantiene" : ""}</div>
            </div>
            <div className="spark">
              {SEMANAS_2026.map(([s, v], j) => (
                <i key={s} style={{ height: `${(v - 26) * 7}px`, opacity: j <= k ? 1 : 0.18 }} />
              ))}
            </div>
          </div>
        </div>
        <div className="col" style={{ flex: 1, gap: 22 }}>
          <div className="who col" style={{ gap: 20 }}>
            {[["camion", "Transportistas y flotillas", "compran cientos de galones por semana"],
              ["tienda", "Pequeñas empresas", "deciden si adelantar o posponer una compra grande"],
              ["carro", "Cualquier conductor", "¿llenar el tanque hoy o esperar?"]].map(([ic, t, s]) => (
              <div key={t} className="row" style={{ gap: 22, alignItems: "center" }}>
                <span className="ico">{ICONS[ic]}</span>
                <div className="body"><b>{t}</b><br /><span style={{ color: "var(--muted)" }}>{s}</span></div>
              </div>
            ))}
          </div>
          <div className="question">
            Nuestra pregunta: para cada combustible, ¿el precio de la semana siguiente <b>sube</b>, <b>baja</b> o <b>se mantiene</b>?
          </div>
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 3. Arquitectura simple
const NODOS = [
  { k: "fotos", t: "Fotos", b: "var(--text-3)", q: "El catedrático sube fotos de surtidores a la nube.", d: "AWS S3 · cc3105-raw/img/ · solo lectura" },
  { k: "bronce", t: "Bronce", b: "var(--bronce)", q: "Guarda cada foto tal como llegó, con fecha de carga y origen. No repite fotos.", d: "bronze.fotos_precios · bucket cusn" },
  { k: "plata", t: "Plata", b: "var(--plata)", q: "Un modelo de visión lee la venta y los galones; tres reglas validan el precio.", d: "silver.precios y precios_rejected · bucket ag" },
  { k: "oro", t: "Oro", b: "var(--oro)", q: "Precio semanal, variación, etiqueta y la predicción del modelo.", d: "gold.precio_semanal, predicciones, metricas_modelo · bucket au" },
  { k: "api", t: "API", b: "var(--baja)", q: "Responde por internet: precio actual, histórico y predicción.", d: "FastAPI en Docker · Droplet de DigitalOcean · puerto 8003" },
];

export function Arquitectura(p) {
  const r = useRef();
  const { print } = useDeck();
  const [sel, setSel] = useState(0);
  const [auto, setAuto] = useState(true);
  useEffect(() => {
    if (!p.active || print || !auto) return undefined;
    setSel(0);
    const id = setInterval(() => setSel((s) => (s + 1) % NODOS.length), 2600);
    return () => clearInterval(id);
  }, [p.active, print, auto]);
  useTL(r, p.active, (tl) => {
    tl.from(".node", { y: 16, opacity: 0, stagger: { each: 0.07, ease: "power2.in" } })
      .from(".wire", { scaleX: 0, transformOrigin: "left center", stagger: 0.07, duration: 0.45, ease: "power2.inOut" }, 0.1)
      .from(".arch-detail", { opacity: 0, y: 10 }, 0.3)
      .from(".arch-strip", { opacity: 0, duration: 0.5 }, 0.45);
    tl.add(() => {
      gsap.utils.toArray(".pulse").forEach((el, i) => {
        gsap.fromTo(el, { left: "0%" }, { left: "100%", duration: 1.1, repeat: -1, ease: "none", delay: i * 0.22 });
      });
    });
  });
  const n = NODOS[sel];
  return (
    <Slide {...p} innerRef={r}>
      <h2>De la foto a la respuesta en cuatro pasos</h2>
      <div className="arch" style={{ marginTop: 44 }}>
        {NODOS.map((x, i) => (
          <div key={x.k} style={{ display: "contents" }}>
            <button className={`node ${i === sel ? "sel" : ""}`} style={{ "--c": x.b }}
              onClick={() => { setAuto(false); setSel(i); }} aria-pressed={i === sel}>
              <span className="node-n">{i === 0 ? "Origen" : `Paso ${i}`}</span>
              <span className="node-t">{x.t}</span>
            </button>
            {i < NODOS.length - 1 && <div className="wire"><span className="pulse" /></div>}
          </div>
        ))}
      </div>
      <div className="arch-detail panel">
        <div className="arch-t" style={{ "--c": n.b }}>{n.t}</div>
        <div className="body" style={{ marginTop: 6 }}>{n.q}</div>
        <div className="small" style={{ marginTop: 8 }}>{n.d}</div>
      </div>
      <div className="arch-strip row" style={{ marginTop: "auto", gap: 24 }}>
        <div className="panel body" style={{ flex: 1.4 }}><b>Databricks</b> ejecuta los pasos 1 a 3 cada martes, sin que nadie toque un notebook, y registra cada entrenamiento del modelo.</div>
        <div className="panel body" style={{ flex: 1 }}><b>Un servidor en DigitalOcean</b> publica la API; solo lee la capa Oro.</div>
      </div>
    </Slide>
  );
}

// =================================================================== 4. De la foto al dato
export function FotoDato(p) {
  const r = useRef();
  useTL(r, p.active, (tl) => {
    tl.from(".fd-photo", { opacity: 0, x: -20, duration: 0.7 })
      .from(".hl-main", { strokeDashoffset: 900, duration: 0.9, ease: "power2.inOut" }, 0.35)
      .from(".fd-step", { opacity: 0, x: 14, stagger: { each: 0.45 } }, 0.5)
      .from(".hl-panels", { strokeDashoffset: 1400, duration: 0.9, ease: "power2.inOut" }, 1.25)
      .from(".fd-stats", { opacity: 0, y: 10 }, 1.6);
  });
  return (
    <Slide {...p} innerRef={r}>
      <h2>De la foto al dato</h2>
      <div className="row grow" style={{ marginTop: 26, gap: 56 }}>
        <div className="fd-photo" style={{ position: "relative", width: 452, flex: "none", alignSelf: "flex-start" }}>
          <img src={foto} alt="Surtidor: esta venta Q150.00, 3.938 galones y el precio por galón de cada combustible" style={{ width: 452, borderRadius: 16, display: "block" }} />
          <svg viewBox="0 0 684 888" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
            <rect className="hl-main" x="236" y="20" width="226" height="128" rx="10" fill="none" stroke="#FFB000" strokeWidth="8" strokeDasharray="900" strokeDashoffset="0" />
            <rect className="hl-panels" x="108" y="712" width="420" height="72" rx="10" fill="none" stroke="#23B25A" strokeWidth="8" strokeDasharray="1400" strokeDashoffset="0" />
          </svg>
        </div>
        <div className="col grow" style={{ gap: 22 }}>
          <div className="fd-step">
            <div className="step-t"><span className="num">1</span>Leer los números grandes</div>
            <div className="row" style={{ gap: 18, marginTop: 10, alignItems: "flex-end" }}>
              <Lcd to={150} dec={2} h={56} cap="Esta venta (Q)" active={p.active} delay={1.4} />
              <Lcd to={3.938} dec={3} h={56} cap="Galones" active={p.active} delay={1.4} />
            </div>
            <div className="small" style={{ marginTop: 8 }}>Un modelo de visión (Llama 4 Maverick en Databricks) devuelve los números en JSON. El OCR clásico falla con dígitos de 7 segmentos.</div>
          </div>
          <div className="fd-step">
            <div className="step-t"><span className="num">2</span>Calcular el precio efectivo</div>
            <div className="row body" style={{ gap: 16, marginTop: 10, alignItems: "center" }}>
              150.00 ÷ 3.938 = <Lcd to={38.09} dec={2} h={56} active={p.active} delay={2.4} from={30} unit="Q/gal" />
            </div>
          </div>
          <div className="fd-step">
            <div className="step-t"><span className="num">3</span>Asignar el combustible</div>
            <div className="small" style={{ marginTop: 6 }}>El de la pantallita con el precio más cercano: <b style={{ color: "var(--super)" }}>súper, Q38.09</b>.</div>
          </div>
          <div className="fd-stats row" style={{ gap: 18, marginTop: "auto" }}>
            <div className="panel stat"><Seg text={String(PLATA.fotos)} h={48} /><span>fotos procesadas</span></div>
            <div className="panel stat"><Seg text={PLATA.pct.toFixed(1)} h={48} /><span>% pasan los controles ({PLATA.aceptadas} de {PLATA.fotos})</span></div>
            <div className="panel stat">{REVISION ? <Seg text={REVISION} h={48} /> : <span className="pend">pendiente</span>}<span>% sin ningún error en la revisión a mano ({REV.correctas} de {REV.fotos}); los montos, bien en {REV.montos}</span></div>
          </div>
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 5. Reglas (interactiva)
const PRESETS = [
  { t: "Foto real", venta: 150, galones: 3.938, comb: "super", futura: false },
  { t: "Galones mal leídos", venta: 150, galones: 39.38, comb: "super", futura: false },
  { t: "Sin combustible", venta: 200, galones: 6.2, comb: "", futura: false },
  { t: "Fecha del EXIF en el futuro", venta: 100, galones: 2.9, comb: "regular", futura: true },
];

export function Reglas(p) {
  const r = useRef();
  const [st, setSt] = useState(PRESETS[0]);
  const precio = st.galones > 0 ? st.venta / st.galones : 0;
  const reglas = [
    ["Precio entre Q20 y Q60 por galón", precio >= 20 && precio <= 60, "precio_fuera_de_rango"],
    ["Combustible dentro del catálogo", !!st.comb, "combustible_no_identificado"],
    ["Fecha conocida y no futura", !st.futura, "fecha_futura"],
  ];
  const fallas = reglas.filter((x) => !x[1]);
  useTL(r, p.active, (tl) => {
    tl.from(".rg-in", { opacity: 0, x: -16 }).from(".rg-rule", { opacity: 0, x: 12, stagger: { each: 0.08, ease: "power2.in" } }, 0.1)
      .from(".rg-out", { opacity: 0, y: 8 }, 0.4);
  });
  const set = (k, v) => setSt((s) => ({ ...s, t: "", [k]: v }));
  return (
    <Slide {...p} innerRef={r}>
      <h2>Tres reglas deciden qué precio se guarda</h2>
      <p className="lead">Pruébenlo: cambien la lectura y vean qué pasa con la foto.</p>
      <div className="row grow" style={{ marginTop: 28, gap: 48 }}>
        <div className="rg-in panel col" style={{ width: 600, gap: 18 }}>
          <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
            {PRESETS.map((x) => (
              <button key={x.t} className="chip" aria-pressed={st.t === x.t} onClick={() => setSt(x)}>{x.t}</button>
            ))}
          </div>
          <label className="field">Esta venta (Q) <b>{st.venta.toFixed(2)}</b>
            <input type="range" min="10" max="400" step="1" value={st.venta} onChange={(e) => set("venta", Number(e.target.value))} />
          </label>
          <label className="field">Galones <b>{st.galones.toFixed(3)}</b>
            <input type="range" min="0.5" max="45" step="0.001" value={st.galones} onChange={(e) => set("galones", Number(e.target.value))} />
          </label>
          <div className="row" style={{ gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <span className="small">Combustible leído:</span>
            {[...FUELS.map((f) => [f.k, f.name]), ["", "ninguno"]].map(([k, name]) => (
              <button key={name} className="chip" aria-pressed={st.comb === k} onClick={() => set("comb", k)}>{name}</button>
            ))}
          </div>
          <label className="row small" style={{ gap: 10, alignItems: "center" }}>
            <input type="checkbox" checked={st.futura} onChange={(e) => set("futura", e.target.checked)} style={{ width: 24, height: 24 }} />
            La fecha de la foto es futura
          </label>
        </div>
        <div className="col grow" style={{ gap: 14 }}>
          <Lcd to={precio > 999 ? "999.99" : precio.toFixed(2)} h={84} unit="Q/gal" cap="Precio efectivo = venta ÷ galones" />
          {reglas.map(([t, ok]) => (
            <div key={t} className={`rg-rule ${ok ? "ok" : "ko"}`}>
              <span className="mark">{ok ? "✓" : "✕"}</span>{t}
            </div>
          ))}
          <div className={`rg-out ${fallas.length ? "ko" : "ok"}`}>
            {fallas.length
              ? <>Va a <b>silver.precios_rejected</b> con el motivo <code>{fallas.map((x) => x[2]).join(";")}</code></>
              : <>Entra a <b>silver.precios</b> como precio de la {FUELS.find((f) => f.k === st.comb)?.name.toLowerCase()}</>}
          </div>
          <div className="small">En las 109 fotos: 3 fuera de rango, 1 sin combustible y 1 con montos ilegibles.</div>
        </div>
      </div>
    </Slide>
  );
}
