# Reporte de Analisis Exploratorio (EDA)

## 1. Panorama general

- Imagenes analizadas: **5**
- Moneda: **GTQ**, volumen en **gallon**
- Combustibles: diesel, regular, super, v_power

## 2. Calidad de lectura y valores faltantes

Las lecturas con confianza < **0.7** se consideran faltantes (nulos) y se imputaran en la etapa de transformacion, marcadas como tal.

## 3. Reconciliacion  venta = galones x precio

Identidad fisica del surtidor. El **precio efectivo = Esta_Venta / Galones** identifica el combustible surtido y valida su precio leido.

```
image_id  esta_venta  galones  precio_efectivo  price_super  residual_super
IMG_8271       150.0    3.938          38.0904        38.09          0.0004
IMG_8286       150.0    3.789          39.5883        39.59         -0.0017
IMG_8304       150.0    3.651          41.0846        41.09         -0.0054
IMG_8322       150.0    3.564          42.0875        42.09         -0.0025
IMG_8325       150.0    3.564          42.0875        42.09         -0.0025
```

## 4. Orden de precios 

Regla de dominio para gasolinas: `regular <= super <= v_power`.

- Sin violaciones: las gasolinas respetan el orden en todas las imagenes.

## 5. Atipicos por rango de dominio

Rango plausible de precio: [20.0, 60.0] GTQ/galon.

- Ningun precio cae fuera del rango plausible.

## 6. Resumen estadistico de precios

```
       price_diesel  price_regular  price_super  price_v_power
count          5.00           5.00         5.00           5.00
mean          40.37          39.59        40.59          41.09
std            3.14           1.73         1.73           1.73
min           35.59          37.09        38.09          38.59
25%           39.59          38.59        39.59          40.09
50%           40.29          40.09        41.09          41.59
75%           43.19          41.09        42.09          42.59
max           43.19          41.09        42.09          42.59
```

## 7. Analisis orientado al pronostico

**Cambio total en el periodo**:

- `diesel`: +7.6 GTQ/galon
- `regular`: +4.0 GTQ/galon
- `super`: +4.0 GTQ/galon
- `v_power`: +4.0 GTQ/galon

**Correlacion entre combustibles**:

```
         diesel  regular  super  v_power
diesel    1.000    0.973  0.973    0.973
regular   0.973    1.000  1.000    1.000
super     0.973    1.000  1.000    1.000
v_power   0.973    1.000  1.000    1.000
```

## 8. Decisiones para la etapa de transformacion (silver)

A partir de lo anterior, la limpieza aplicara:

1. **Nulos**: toda lectura con confianza < 0.7 se vuelve NaN y se
   imputa, marcando
   `is_imputed = True`. Nunca se sobrescribe en silencio.
2. **Reconciliacion**: se recalcula `precio_efectivo = venta/galones`; si un
   precio leido difiere > 0.15 del derivado para el combustible
   surtido, se corrige con el derivado  y se marca.
3. **Atipicos**: reglas de dominio + orden
   `regular<=super<=v_power`. Se **marcan** para trazabilidad.
4. **Estandarizacion**: se unifican unidades (GTQ/galon), se agrega
   columna opcional GTQ/litro, y se redondea a 2 decimales.
   La normalizacion z-score para ML se deja para la etapa de modelado.
