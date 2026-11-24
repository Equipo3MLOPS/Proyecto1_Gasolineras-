import { Arquitectura, FotoDato, Portada, Problema, Reglas } from "./a.jsx";
import { Etiqueta, Limitaciones, Oro, Resultados, Validacion } from "./b.jsx";
import { Anexo, Automatizacion, Demo, Gracias, Lecciones } from "./c.jsx";

// Notas del orador (tecla N). Tiempos para 10 min de exposición + 5 de demo + 5 de preguntas.
export const SLIDES = [
  { C: Portada, title: "¿Sube o baja la gasolina la próxima semana?",
    notes: "0:00 · P4 (Hugo). Presentar al equipo y la pregunta. El display de la derecha es una foto real: Q150.00 entre 3.938 galones da Q38.09, el precio de la súper." },
  { C: Problema, title: "Cada martes hay un precio nuevo",
    notes: "0:40 · P4. El tablero recorre las semanas de 2026 con foto. Decir para quién sirve saber si sube o baja: flotillas, pequeñas empresas, cualquier conductor. Cerrar con la pregunta del recuadro." },
  { C: Arquitectura, title: "De la foto a la respuesta en cuatro pasos",
    notes: "1:40 · P3. Sin jerga: fotos → bronce (guardar) → plata (leer y validar) → oro (resumir y predecir) → API. Se puede tocar cada caja. Databricks corre los pasos 1 a 3; DigitalOcean solo publica la API." },
  { C: FotoDato, title: "De la foto al dato",
    notes: "2:50 · P2. El modelo de visión lee la venta y los galones; el precio efectivo es venta ÷ galones y se asigna el combustible con el precio más cercano. 104 de 109 fotos pasan los controles. Revisión a mano de 20 fotos al azar: 9 sin errores (45 %); los montos bien en 18, pero 10 fotos de súper quedaron en otro combustible." },
  { C: Reglas, title: "Tres reglas deciden qué precio se guarda",
    notes: "3:50 · P2. Mostrar «Galones mal leídos» (Q3.81/gal, fuera de rango) y volver a «Foto real». Rechazadas: 3 fuera de rango, 1 sin combustible, 1 ilegible." },
  { C: Oro, title: "En 2026 la súper pasó de Q28 a Q45 por galón",
    notes: "4:30 · P1. Capa Oro: un precio promedio por semana y combustible. Activar diésel o regular si preguntan. Los huecos son semanas sin foto." },
  { C: Etiqueta, title: "Cada semana recibe una etiqueta",
    notes: "5:10 · P1. Mover el control: menos de ±Q0.10 cuenta como «se mantiene». 49 subidas, 41 bajadas y solo 9 «se mantiene»." },
  { C: Validacion, title: "Lo evaluamos con semanas que nunca vio",
    notes: "5:50 · P1. 71 semanas para entrenar, las 28 más recientes para probar, y 4 cortes de validación cruzada en el tiempo para elegir el modelo." },
  { C: Resultados, title: "El modelo supera a la línea base por un acierto",
    notes: "6:30 · P1. Bosque aleatorio 42.9 % contra 39.3 % de la línea base: 12 contra 11 aciertos, no es una mejora demostrada. Decir siempre «sube» da 57.1 %. Lo decimos abiertamente. La matriz muestra que predice «baja» de más." },
  { C: Limitaciones, title: "Los datos ponen el techo, no el algoritmo",
    notes: "7:40 · Quinto integrante. Fotos irregulares (la semana siguiente a veces está a meses), pocos ejemplos, combustible mal asignado en 10 de 20 fotos revisadas y sin variables externas." },
  { C: Automatizacion, title: "Cada martes a las 6:00 corre solo",
    notes: "8:40 · P1. El Job encadena bronce → plata → oro; en producción corre los martes 06:00 hora de Guatemala, avisa por correo si falla, usa serverless y registra cada entrenamiento en MLflow." },
  { C: Demo, title: "Demo en vivo: pregúntenle a la API",
    notes: "9:40 · P2 y P3 (5 min). Seguir presentacion/guion_demo.md: Run now del Job, gold.predicciones con su linaje y consultas_api.sh. Si falla la conexión, plan B: video y planb_respuestas.txt." },
  { C: Lecciones, title: "Lo que aprendimos y lo que haríamos con más tiempo",
    notes: "14:40 · P4. Una frase por lección. La mejora más concreta: asignar bien el combustible." },
  { C: Gracias, title: "Gracias. ¿Preguntas?",
    notes: "15:00 · Todos. Cualquiera puede responder. El anexo (siguiente) tiene el diagrama técnico completo." },
  { C: Anexo, title: "Anexo: arquitectura técnica completa",
    notes: "Solo si preguntan por detalles: buckets S3, external locations, tablas de Unity Catalog, Job, MLflow y la API en Docker." },
];
