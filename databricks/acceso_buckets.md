# Guía para la llamada con el profe — acceso de escritura a los buckets

## El problema en una frase
Los 4 external locations (`xloc-raw`, `xloc-cusn`, `xloc-ag`, `xloc-au`) están en
**`read_only = true`** y son propiedad de **`arodriguezo@uvg.edu.gt`**. Con eso puedo
**leer** de los buckets pero **no escribir** vía Unity Catalog. Por eso la medallón no
se puede poblar todavía. Otro equipo (equipo2) sí logró escribir, pero por **S3 directo
con credenciales AWS**, no por Unity Catalog.

---

## Demostración en vivo (comandos seguros: no crean nada)

Corré estos en la terminal con el perfil `uvg-mlops` mientras compartís pantalla.

### 1) Mostrar que el bucket es de solo lectura
```bash
databricks external-locations get xloc-cusn -p uvg-mlops
```
Fijate en los campos **`owner: arodriguezo@uvg.edu.gt`** y **`read_only: true`**.

### 2) Intentar crear un schema que escriba ahí → **FALLA**
```bash
databricks schemas create ztest workspace --storage-root s3://cc3105-cusn-869227452861-us-east-2-an/equipo3/_probe -p uvg-mlops
```
Respuesta esperada:
```
Error: Creating a schema with a read-only storage location is not supported.
```

### 3) Intentar crear un volumen externo → **FALLA**
```bash
databricks volumes create workspace bronze ztest EXTERNAL --storage-location s3://cc3105-raw-869227452861-us-east-2-an/equipo3/_probe -p uvg-mlops
```
Respuesta esperada:
```
Error: User does not have CREATE EXTERNAL VOLUME on External Location 'xloc-raw'.
```

> Los comandos 2 y 3 **fallan a propósito**: no crean nada, solo prueban que la
> escritura está bloqueada. (Si por casualidad alguno llegara a crear algo, se borra con
> `databricks schemas delete workspace.ztest -p uvg-mlops` o
> `databricks volumes delete workspace.bronze.ztest -p uvg-mlops`.)

### 4) (Opcional) Mostrar que LEER sí funciona y que equipo2 ya escribió
Con un SQL warehouse encendido podés listar la carpeta de otro equipo:
```bash
databricks api post /api/2.0/sql/statements -p uvg-mlops --json '{"warehouse_id":"<ID_DE_TU_WAREHOUSE>","statement":"LIST \"s3://cc3105-cusn-869227452861-us-east-2-an/equipo2/fotos_precios/\"","wait_timeout":"30s"}'
```
Verás un `_delta_log/` y archivos `.parquet`: equipo2 **sí escribió** una tabla Delta en
su carpeta. Conclusión: el bucket permite escritura por carpeta de equipo, pero **no por
Unity Catalog** (que está en read-only) sino por **S3 directo con credenciales AWS**.

---

## Las 2 preguntas clave para el profe

1. **¿El `read_only` de los external locations es a propósito, o se puede cambiar?**
2. **¿Cómo quiere que cada equipo escriba su medallón?** Hay dos caminos (cualquiera sirve):

### Camino A — Unity Catalog (lo más limpio y gobernado) ⭐
Que el profe, sobre los 3 buckets de capa (`xloc-cusn`, `xloc-ag`, `xloc-au`):
- Los ponga en **modo escritura** — en la UI: *Catalog → External Locations → (cada uno)
  → Edit → desmarcar "Limit to read-only use"*.
- Me dé el permiso de usarlos como almacenamiento de tablas:
```sql
GRANT CREATE MANAGED STORAGE ON EXTERNAL LOCATION `xloc-cusn` TO `jspereira0402@gmail.com`;
GRANT CREATE MANAGED STORAGE ON EXTERNAL LOCATION `xloc-ag`   TO `jspereira0402@gmail.com`;
GRANT CREATE MANAGED STORAGE ON EXTERNAL LOCATION `xloc-au`   TO `jspereira0402@gmail.com`;
```
→ Yo despliego con `backend=uc` y las tablas quedan como `workspace.bronze/silver/gold.*`.

> El bucket **raw** (imágenes) puede quedarse en read-only: solo lo leemos, y además las
> imágenes ya están cargadas en el Volume `workspace.bronze.raw_images`. Así que el
> pedido al profe es solo por los **3 buckets de capa**.

### Camino B — S3 directo (como lo hizo equipo2)
Que el profe nos pase las **credenciales AWS** del equipo (access key + secret con
permiso sobre la carpeta `equipo3/`), o nos explique cómo las obtuvo equipo2.
→ Yo despliego con `backend=s3` y escribo Delta a `s3a://cc3105-.../equipo3/...`.

---

## Qué me pasás después de la llamada
- Si eligen **Camino A**: avisame *"ya está en modo escritura y me dieron el permiso"*.
- Si eligen **Camino B**: pasame las **credenciales AWS** (o el método de equipo2).

Con cualquiera de las dos, el código ya está listo: **solo cambio una variable**
(`backend=uc` o `backend=s3`) y corremos el Job. Nada más que reescribir.
