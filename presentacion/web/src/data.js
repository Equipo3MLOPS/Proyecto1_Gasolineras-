import serie from "./serie.json";

export const SERIE = serie; // { super: [[semana, precio], ...], ... } desde gold.precio_semanal (24-nov-2026)

export const FUELS = [
  { k: "super", name: "Súper", color: "var(--super)" },
  { k: "regular", name: "Regular", color: "var(--regular)" },
  { k: "diesel", name: "Diésel", color: "var(--diesel)" },
  { k: "v_power", name: "V-Power", color: "var(--vpower)" },
];

// Foto IMG_8271: lo que se ve en el display
export const FOTO = { venta: 150.0, galones: 3.938, precios: { diesel: 35.59, regular: 37.09, super: 38.09, v_power: 38.59 } };

export const PLATA = { fotos: 109, aceptadas: 104, rechazadas: 5, pct: 95.4,
  motivos: [["Precio fuera de Q20–Q60", 3], ["Combustible no identificado", 1], ["Venta o galones ilegibles", 1]] };

export const ETIQUETAS = { sube: 49, baja: 41, se_mantiene: 9 };

// gold.metricas_modelo (corrida del 24-nov-2026, 28 semanas de prueba)
export const MODELOS = [
  { m: "Árbol de decisión", acc: 35.7, cv: 44.5 },
  { m: "Regresión logística", acc: 39.3, cv: 43.4 },
  { m: "Línea base: repetir la semana anterior", acc: 39.3, base: true },
  { m: "Bosque aleatorio (elegido)", acc: 42.9, cv: 46.0, sel: true },
  { m: "Decir siempre «sube»", acc: 57.1, ref: true },
];

// Matriz de confusión del bosque en prueba: filas = real, columnas = predicho [baja, se mantiene, sube]
export const CONF = [[7, 0, 4], [0, 0, 1], [10, 1, 5]];
export const CLASES = ["Baja", "Se mantiene", "Sube"];

// gold.predicciones, tipo = futura
export const PRED_SUPER = { combustible: "super", semana: "2026-11-10", prediccion: "baja", probabilidad: 0.3679, modelo: "bosque_aleatorio" };

export const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
export const REVISION = import.meta.env.VITE_REVISION || "45.0";
// Revisión manual de 20 fotos (semilla 42, 24-nov-2026): 9 sin errores; montos bien en 18; combustible bien en 10
export const REV = { fotos: 20, correctas: 9, montos: 18, combustible: 10 };
export const INTEGRANTES = ["Jose Santiago Pereira", "Nancy Mazariegos", "Hugo Rivas", "Giovanni Santos", "Alexis Mesias"];
