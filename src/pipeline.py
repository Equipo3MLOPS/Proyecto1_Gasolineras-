from __future__ import annotations

import argparse
import time

from . import extract, eda, transform, load

STAGES = {
    "extract": extract.run,
    "eda": eda.run,
    "transform": transform.run,
    "load": load.run,
}
DEFAULT_ORDER = ["extract", "eda", "transform", "load"]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Pipeline ETL de gasolineras")
    ap.add_argument("stages", nargs="*", help="etapas a correr")
    ap.add_argument("--no-eda", action="store_true", help="omitir la etapa de EDA")
    args = ap.parse_args(argv)

    order = args.stages or DEFAULT_ORDER
    if args.no_eda and "eda" in order:
        order = [s for s in order if s != "eda"]

    t0 = time.time()
    for stage in order:
        if stage not in STAGES:
            raise SystemExit(f"Etapa desconocida: {stage}. Validas: {list(STAGES)}")
        print(f"\n--- {stage.upper()} ---")
        STAGES[stage]()


if __name__ == "__main__":
    main()
