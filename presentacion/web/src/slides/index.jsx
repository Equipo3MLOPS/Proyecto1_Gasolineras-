import { Arquitectura, FotoDato, Portada, Problema, Reglas } from "./a.jsx";
import { Etiqueta, Limitaciones, Oro, Resultados, Validacion } from "./b.jsx";
import { Anexo, Automatizacion, Demo, Gracias, Lecciones } from "./c.jsx";

// Las notas del orador viven en notas.js, que no se sube al repositorio. Si el archivo no existe,
// o si se compila con VITE_SIN_NOTAS=1, la presentación sale sin notas.
const ARCHIVOS = import.meta.env.VITE_SIN_NOTAS ? {} : import.meta.glob("./notas.js", { eager: true });
const NOTAS = Object.values(ARCHIVOS)[0]?.default || {};

export const HAY_NOTAS = Object.keys(NOTAS).length > 0;

export const SLIDES = [
  { C: Portada, title: "¿Sube o baja la gasolina la próxima semana?", notes: NOTAS[1] || "" },
  { C: Problema, title: "Cada martes hay un precio nuevo", notes: NOTAS[2] || "" },
  { C: Arquitectura, title: "De la foto a la respuesta en cuatro pasos", notes: NOTAS[3] || "" },
  { C: FotoDato, title: "De la foto al dato", notes: NOTAS[4] || "" },
  { C: Reglas, title: "Tres reglas deciden qué precio se guarda", notes: NOTAS[5] || "" },
  { C: Oro, title: "En 2026 la súper pasó de Q28 a Q45 por galón", notes: NOTAS[6] || "" },
  { C: Etiqueta, title: "Cada semana recibe una etiqueta", notes: NOTAS[7] || "" },
  { C: Validacion, title: "Lo evaluamos con semanas que nunca vio", notes: NOTAS[8] || "" },
  { C: Resultados, title: "El modelo supera a la línea base por un acierto", notes: NOTAS[9] || "" },
  { C: Limitaciones, title: "Los datos ponen el techo, no el algoritmo", notes: NOTAS[10] || "" },
  { C: Automatizacion, title: "Cada martes a las 6:00 corre solo", notes: NOTAS[11] || "" },
  { C: Demo, title: "Demo en vivo: pregúntenle a la API", notes: NOTAS[12] || "" },
  { C: Lecciones, title: "Lo que aprendimos y lo que haríamos con más tiempo", notes: NOTAS[13] || "" },
  { C: Gracias, title: "Gracias. ¿Preguntas?", notes: NOTAS[14] || "" },
  { C: Anexo, title: "Anexo: arquitectura técnica completa", notes: NOTAS[15] || "" },
];
