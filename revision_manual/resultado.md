# Revisión manual de 20 fotos (capa Plata)

Revisión hecha por Hugo Rivas el 24 de noviembre de 2026 con la hoja que genera `pipelines/revision_fotos_hoja.py`
(20 fotos elegidas al azar entre las 109 de `workspace.bronze.fotos_precios`, semilla 42).

Una foto cuenta como correcta si la venta, los galones y el combustible asignado coinciden con el display.

| Resultado | Fotos | % |
|---|---:|---:|
| Sin ningún error | 9 de 20 | 45.0 % |
| Montos (venta y galones) correctos | 18 de 20 | 90.0 % |
| Combustible correcto | 10 de 20 | 50.0 % |
| Ilegibles | 0 | |

Errores encontrados:

- **Combustible:** IMG_8354, IMG_5697, IMG_5269, IMG_4201, IMG_6820, IMG_5181, IMG_5311, IMG_7185, IMG_7997 e
  IMG_7549 eran súper y quedaron asignadas a otro combustible. El precio efectivo de esas filas es correcto, pero
  entra a la serie de otro combustible.
- **Venta:** IMG_3605, el display dice Q190.02.
- **Galones:** IMG_7185, el display dice 3.391.

Las correcciones en formato de diccionario están en `correcciones_20_fotos.json`.
