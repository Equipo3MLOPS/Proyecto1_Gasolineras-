#!/usr/bin/env bash
# Cliente de prueba de la API (equipo3). Consume todos los endpoints.
#   uso:  ./consultas_api.sh                      (contra http://localhost:8003)
#         BASE_URL=http://<ip>:8003 ./consultas_api.sh   (contra el Droplet)
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8003}"

jq_o_cat() { if command -v jq >/dev/null; then jq; else cat; fi; }
titulo() { printf "\n\033[1;36m== %s ==\033[0m\n" "$1"; }

titulo "GET /health"
curl -s "$BASE_URL/health" | jq_o_cat

titulo "GET /precios/actual  (último precio por combustible)"
curl -s "$BASE_URL/precios/actual" | jq_o_cat

titulo "GET /precios?combustible=super&limit=5"
curl -s "$BASE_URL/precios?combustible=super&limit=5" | jq_o_cat

titulo "GET /precios?combustible=diesel&desde=2026-01-01&hasta=2026-12-31&limit=5"
curl -s "$BASE_URL/precios?combustible=diesel&desde=2026-01-01&hasta=2026-12-31&limit=5" | jq_o_cat

titulo "GET /prediccion  (todas las predicciones futuras)"
curl -s "$BASE_URL/prediccion" | jq_o_cat

titulo "GET /prediccion?combustible=super"
curl -s "$BASE_URL/prediccion?combustible=super" | jq_o_cat

titulo "GET /modelo/metricas"
curl -s "$BASE_URL/modelo/metricas" | jq_o_cat

titulo "GET /fotos?combustible=super&limit=3  (lecturas por foto con GPS)"
curl -s "$BASE_URL/fotos?combustible=super&limit=3" | jq_o_cat

titulo "GET /fotos/{image_id}/imagen  (miniatura JPEG de la primera foto)"
PRIMERA=$(curl -s "$BASE_URL/fotos?limit=1" | python3 -c 'import json,sys; f=json.load(sys.stdin)["fotos"]; print(f[0]["image_id"] if f else "")')
if [ -n "$PRIMERA" ]; then
  curl -s -o /dev/null -w "$PRIMERA -> HTTP %{http_code}, %{content_type}, %{size_download} bytes\n" "$BASE_URL/fotos/$PRIMERA/imagen"
fi

printf "\n\033[1;32mListo. Swagger en %s/docs\033[0m\n" "$BASE_URL"
