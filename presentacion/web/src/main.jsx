import { createRoot } from "react-dom/client";
import bc600 from "@fontsource/barlow-condensed/files/barlow-condensed-latin-600-normal.woff2?url";
import bc700 from "@fontsource/barlow-condensed/files/barlow-condensed-latin-700-normal.woff2?url";
import bc800 from "@fontsource/barlow-condensed/files/barlow-condensed-latin-800-normal.woff2?url";
import b400 from "@fontsource/barlow/files/barlow-latin-400-normal.woff2?url";
import b500 from "@fontsource/barlow/files/barlow-latin-500-normal.woff2?url";
import b600 from "@fontsource/barlow/files/barlow-latin-600-normal.woff2?url";
import b700 from "@fontsource/barlow/files/barlow-latin-700-normal.woff2?url";
import "./styles.css";
import "./slides.css";
import App from "./App.jsx";

// Barlow nace de las placas y rótulos de carretera: es la letra del mundo de la gasolinera.
const face = (fam, w, src) => `@font-face{font-family:"${fam}";font-style:normal;font-display:block;font-weight:${w};src:url(${src}) format("woff2");}`;
const f = document.createElement("style");
f.textContent = [
  face("Barlow Condensed", 600, bc600), face("Barlow Condensed", 700, bc700), face("Barlow Condensed", 800, bc800),
  face("Barlow", 400, b400), face("Barlow", 500, b500), face("Barlow", 600, b600), face("Barlow", 700, b700),
].join("");
document.head.appendChild(f);

createRoot(document.getElementById("root")).render(<App />);
