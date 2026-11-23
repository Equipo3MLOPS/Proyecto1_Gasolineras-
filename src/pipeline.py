
from __future__ import annotations

import argparse
import time

from . import extract, transform, load
from . import config as C

STAGES = {
    "bronce": extract.run,
    "plata": transform.run,
    "oro": load.run,
}
DEFAULT_ORDER = ["bronce", "plata", "oro"]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Pipeline de datos (medallón) de gasolineras")
    ap.add_argument("stages", nargs="*", help="etapas a correr (bronce, plata, oro)")
    args = ap.parse_args(argv)

    order = args.stages or DEFAULT_ORDER
    print(f"[pipeline] backend={C.BACKEND} | equipo={C.TEAM} | etapas={order}")
    t0 = time.time()
    for stage in order:
        if stage not in STAGES:
            raise SystemExit(f"Etapa desconocida: {stage}. Validas: {list(STAGES)}")
        print(f"\n--- {stage.upper()} ---")
        STAGES[stage]()
    print(f"\n[pipeline] completado en {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
