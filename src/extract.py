
from __future__ import annotations

from . import config as C, io_layer as io


def run() -> int:
    C.ensure_dirs()
    n = io.write_photos_bronze("bronze.fotos_precios", C.IMAGES_URI)
    print(f"[bronce] {n} fotos -> {io.target_name('bronze.fotos_precios')}")
    return n


if __name__ == "__main__":
    run()
