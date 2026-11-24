import { useEffect, useMemo, useRef, useState } from "react";
import QRCode from "qrcode";
import { useDeck, useTL } from "../kit.jsx";
import { API_URL, INTEGRANTES, PRED_SUPER } from "../data.js";
import arquitectura from "../assets/arquitectura.png";
import { Slide } from "./a.jsx";

const BASE = API_URL || "http://<ip>:8003";
const URL_PRED = `${BASE}/prediccion?combustible=super`;
const URL_QR = `${BASE}/`; // la página de la API: precios, predicciones e histórico

// QR dibujado como SVG, sincrónico (sirve también para imprimir)
export function Qr({ text, size = 220, dark = "#16191d" }) {
  const q = useMemo(() => QRCode.create(text, { errorCorrectionLevel: "M" }), [text]);
  const n = q.modules.size;
  const cells = [];
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (q.modules.get(r, c)) cells.push(`M${c + 2},${r + 2}h1v1h-1z`);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${n + 4} ${n + 4}`} role="img" aria-label={`Código QR: ${text}`} shapeRendering="crispEdges">
      <rect width={n + 4} height={n + 4} fill="#fff" />
      <path d={cells.join("")} fill={dark} />
    </svg>
  );
}

function QrBox({ size = 220, onDark }) {
  if (API_URL) {
    return (
      <div className="qr-box">
        <Qr text={URL_QR} size={size} />
        <div className="qr-url">{URL_QR.replace(/^https?:\/\//, "")}</div>
      </div>
    );
  }
  return (
    <div className={`qr-box qr-pend ${onDark ? "on-dark" : ""}`} style={{ width: size + 36, height: size + 36 }}>
      <b>Aquí va el QR</b>
      <span>Falta la IP pública del servidor de la API</span>
    </div>
  );
}

// =================================================================== 11. Automatización
const TAREAS = [
  { k: "bronce", t: "Bronce", s: "ingesta de fotos nuevas", c: "var(--bronce)" },
  { k: "plata", t: "Plata", s: "lectura y reglas de calidad", c: "var(--plata)" },
  { k: "oro", t: "Oro", s: "agregación, modelo y predicción", c: "var(--oro)" },
];
const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

export function Automatizacion(p) {
  const r = useRef();
  const { print, reduced } = useDeck();
  const [paso, setPaso] = useState(print || reduced ? 3 : -1); // -1 sin correr · 0..2 corriendo · 3 terminado
  const timers = useRef([]);
  const correr = () => {
    timers.current.forEach(clearTimeout);
    setPaso(0);
    timers.current = [1, 2, 3].map((k) => setTimeout(() => setPaso(k), k * 1500));
  };
  useEffect(() => {
    if (print || reduced) return undefined;
    if (!p.active) { timers.current.forEach(clearTimeout); setPaso(-1); return undefined; }
    const t = setTimeout(correr, 1800);
    return () => { clearTimeout(t); timers.current.forEach(clearTimeout); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.active, print, reduced]);
  useTL(r, p.active, (tl) => {
    tl.from(".job", { opacity: 0, y: 14, duration: 0.7 })
      .from(".wk", { opacity: 0, duration: 0.45 }, 0.25)
      .from(".au-side > div", { opacity: 0, x: 12, stagger: { each: 0.09, ease: "power2.in" } }, 0.35);
  });
  const estado = (i) => (paso > i ? "ok" : paso === i ? "run" : "wait");
  const ETQ = { ok: "Correcta", run: "Ejecutando", wait: "En espera" };
  return (
    <Slide {...p} innerRef={r}>
      <h2>Cada martes a las 6:00 corre solo</h2>
      <div className="row grow" style={{ marginTop: 34, gap: 52 }}>
        <div className="col" style={{ flex: 1.35, gap: 26 }}>
          <div className="job panel housing">
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 24, fontWeight: 700 }}>Job «Medallón Gasolineras — equipo3»</div>
                <div className="small">Databricks Jobs · tres tareas encadenadas · cómputo serverless</div>
              </div>
              <button className="btn" onClick={correr} disabled={paso >= 0 && paso < 3}>{paso >= 0 && paso < 3 ? "Ejecutando…" : "Ejecutar ahora"}</button>
            </div>
            <div className="dag">
              {TAREAS.map((x, i) => (
                <div key={x.k} style={{ display: "contents" }}>
                  <div className={`task ${estado(i)}`} style={{ "--c": x.c }}>
                    <div className="task-t">{x.t}</div>
                    <div className="small">{x.s}</div>
                    <div className="task-s"><i />{ETQ[estado(i)]}</div>
                  </div>
                  {i < TAREAS.length - 1 && <div className={`dag-wire ${paso > i ? "lit" : ""}`} />}
                </div>
              ))}
            </div>
            <div className="small" style={{ marginTop: 14 }}>
              {paso === 3 ? "Corrida terminada: las tablas de Oro y la API ya tienen la semana nueva." : "Si una tarea falla, las siguientes no corren y la API sigue con los datos de la semana anterior."}
            </div>
          </div>
          <div>
            <div className="small" style={{ marginBottom: 10 }}>Programación en producción (hora de Guatemala)</div>
            <div className="wk">
              {DIAS.map((d) => (
                <div key={d} className={`wk-day ${d === "Mar" ? "on" : ""}`}>
                  <b>{d}</b>
                  {d === "Mar" ? <span>06:00</span> : <span>&nbsp;</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="au-side col" style={{ flex: 1, gap: 22 }}>
          <div className="panel">
            <div className="au-k">Alerta por correo</div>
            <div className="body">Si la corrida falla, Databricks avisa al equipo por correo.</div>
          </div>
          <div className="panel">
            <div className="au-k">Sin clúster que administrar</div>
            <div className="body">Cada tarea usa cómputo serverless: arranca en segundos y solo cuesta mientras corre.</div>
          </div>
          <div className="panel">
            <div className="au-k">Cada entrenamiento queda registrado</div>
            <div className="body">MLflow guarda parámetros y métricas; el modelo elegido queda en Unity Catalog con el alias <code>champion</code>.</div>
          </div>
          <div className="small">Todo el Job se define en código (Databricks Asset Bundle) y se despliega con un comando.</div>
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 12. Demo
const RESP = JSON.stringify(PRED_SUPER, null, 2);
const CMD = `curl "${URL_PRED}"`;

export function Demo(p) {
  const r = useRef();
  const { print, reduced } = useDeck();
  const [nc, setNc] = useState(print || reduced ? CMD.length : 0);
  const [resp, setResp] = useState(print || reduced);
  useEffect(() => {
    if (print || reduced) return undefined;
    if (!p.active) { setNc(0); setResp(false); return undefined; }
    let k = 0;
    let t2;
    const timers = [];
    const t0 = setTimeout(() => {
      const id = setInterval(() => {
        k += 1; setNc(k);
        if (k >= CMD.length) { clearInterval(id); t2 = setTimeout(() => setResp(true), 450); }
      }, 32);
      timers.push(id);
    }, 900);
    return () => { clearTimeout(t0); clearTimeout(t2); timers.forEach(clearInterval); };
  }, [p.active, print, reduced]);
  useTL(r, p.active, (tl) => {
    tl.from(".term", { opacity: 0, y: 14, duration: 0.7 })
      .from(".qr-col", { opacity: 0, scale: 0.97 }, 0.18)
      .from(".demo-steps > div", { opacity: 0, x: 12, stagger: { each: 0.09, ease: "power2.in" } }, 0.3);
  });
  const fecha = PRED_SUPER.semana.split("-").reverse().join("/");
  return (
    <Slide {...p} innerRef={r}>
      <h2>Demo en vivo: pregúntenle a la API</h2>
      <div className="row grow" style={{ marginTop: 32, gap: 48 }}>
        <div className="col" style={{ flex: 1.75, gap: 22 }}>
          <div className="term housing" aria-label="Terminal con la consulta a la API">
            <div className="term-bar"><i /><i /><i /><span>consulta a /prediccion</span></div>
            <pre>
              <span className="pr">$ </span>{CMD.slice(0, nc)}{!resp && <span className="caret">▍</span>}
              {resp && <>{"\n"}<span className="js">{RESP}</span></>}
            </pre>
          </div>
          <div className={`term-say ${resp ? "on" : ""}`}>
            Semana del {fecha}: la súper <b className="baja">baja</b>, con probabilidad {Math.round(PRED_SUPER.probabilidad * 100)} % (la más alta de las tres clases).
          </div>
          <div className="small">Respuesta de la corrida del 24/11/2026. En vivo cambia cuando entran las fotos de la semana nueva.</div>
        </div>
        <div className="col" style={{ flex: 1, gap: 22 }}>
          <div className="qr-col row" style={{ gap: 22, alignItems: "center" }}>
            <QrBox size={200} />
            <div className="body">Escaneen para ver precios y predicciones en su teléfono.</div>
          </div>
          <div className="demo-steps col" style={{ gap: 12 }}>
            {[["Ejecutar el Job", "bronce → plata → oro en Databricks"], ["Ver la capa Oro", "gold.predicciones y su linaje"], ["Consultar la API", "/prediccion, /modelo/metricas y /docs"]].map(([t, s], i) => (
              <div key={t} className="row" style={{ gap: 16, alignItems: "center" }}>
                <span className="num">{i + 1}</span>
                <div className="body"><b>{t}</b> <span style={{ color: "var(--muted)" }}>· {s}</span></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 13. Lecciones
export function Lecciones(p) {
  const r = useRef();
  useTL(r, p.active, (tl) => {
    tl.from(".lc-a", { opacity: 0, y: 12, stagger: { each: 0.12, ease: "power2.in" } })
      .from(".lc-b", { opacity: 0, x: 12, stagger: { each: 0.08, ease: "power2.in" } }, 0.3);
  });
  return (
    <Slide {...p} innerRef={r}>
      <h2>Lo que aprendimos y lo que haríamos con más tiempo</h2>
      <div className="row grow" style={{ marginTop: 40, gap: 64 }}>
        <div className="col" style={{ flex: 1, gap: 22 }}>
          <div className="small">Lo que aprendimos</div>
          {[
            ["La calidad del dato manda", "La revisión a mano encontró el combustible equivocado en la mitad de las fotos: eso pesa más que cambiar de algoritmo."],
            ["Validar en el tiempo cambia la conclusión", "Con una partición aleatoria el modelo parecía mejor de lo que es."],
            ["Automatizar desde el inicio", "Bundle, Job y API en código: la misma corrida se repite sin pasos manuales."],
          ].map(([t, s]) => (
            <div key={t} className="lc-a lc">
              <div className="lc-t">{t}</div>
              <div className="body" style={{ color: "var(--text-2)" }}>{s}</div>
            </div>
          ))}
        </div>
        <div className="col" style={{ flex: 1, gap: 16 }}>
          <div className="small">Con más tiempo</div>
          {[
            ["Asignar bien el combustible", "fue el error más común (10 de 20 fotos); los montos sí se leen bien (18 de 20)."],
            ["Más fotos y más regulares", "al menos una por combustible cada semana."],
            ["Contexto externo", "precio internacional del petróleo y tipo de cambio como variables."],
            ["Plata sin duplicados", "la clave del MERGE debe ser la foto, no la combinación fecha y combustible."],
          ].map(([t, s]) => (
            <div key={t} className="lc-b panel body"><b>{t}:</b> {s}</div>
          ))}
        </div>
      </div>
    </Slide>
  );
}

// =================================================================== 14. Gracias
export function Gracias(p) {
  const r = useRef();
  useTL(r, p.active, (tl) => {
    tl.from(".lightbox", { opacity: 0, y: 16, duration: 0.7 })
      .fromTo(".lightbox", { "--lit": 0 }, { "--lit": 1, duration: 0.45, ease: "steps(5)" }, 0.15)
      .from(".gr-l > div", { opacity: 0, y: 8, stagger: { each: 0.08, ease: "power2.in" } }, 0.45)
      .from(".gr-qr", { opacity: 0, scale: 0.97 }, 0.5);
  });
  return (
    <Slide {...p} innerRef={r}>
      <div className="row grow" style={{ alignItems: "center", gap: 80 }}>
        <div className="col" style={{ flex: 1.4 }}>
          <div className="lightbox"><h1 className="gr-t">Gracias.<br />¿Preguntas?</h1></div>
          <div className="gr-l col" style={{ gap: 12, marginTop: 40 }}>
            <div className="body">API y documentación: <b>{BASE.replace(/^https?:\/\//, "")}/docs</b></div>
            <div className="body">Repositorio: <b>github.com/Equipo3MLOPS/Proyecto1_Gasolineras-</b></div>
            <div className="body">Informe técnico: <b>docs/informe.pdf</b></div>
            <div className="small" style={{ marginTop: 18, fontSize: 19 }}>{INTEGRANTES.join(" · ")}</div>
          </div>
        </div>
        <div className="gr-qr"><QrBox size={240} onDark /></div>
      </div>
    </Slide>
  );
}

// =================================================================== 15. Anexo
export function Anexo(p) {
  return (
    <Slide {...p} label="Anexo">
      <h2 style={{ fontSize: 40 }}>Anexo: arquitectura técnica completa</h2>
      <div className="grow" style={{ marginTop: 20, display: "grid", placeItems: "center" }}>
        <div className="anexo-frame"><img src={arquitectura} alt="Diagrama de arquitectura: S3, capas bronce, plata y oro en Unity Catalog, Job de Databricks, MLflow y API en DigitalOcean" /></div>
      </div>
    </Slide>
  );
}
