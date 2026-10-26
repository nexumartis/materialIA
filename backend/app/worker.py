"""Worker de tareas de mantenimiento. El estado vive en Postgres: si se reinicia, retoma.

Por ahora libera el stock de pedidos impagos con la reserva vencida (idempotente y seguro con
varias instancias: toma filas con `for update skip locked`).

    python -m app.worker            # bucle cada WORKER_INTERVAL_S segundos (default 60)
    python -m app.worker --once     # una sola vuelta (cron, tests)
"""
from __future__ import annotations

import logging
import os
import sys
import time

from .domain import orders

log = logging.getLogger("app.worker")


def run_once() -> dict[str, int]:
    return {"expired_reservations": orders.expire_reservations()}


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    interval = float(os.environ.get("WORKER_INTERVAL_S", "60"))
    while True:
        try:
            log.info("vuelta: %s", run_once())
        except Exception:  # noqa: BLE001 - el worker sigue; la próxima vuelta reintenta
            log.exception("vuelta fallida")
        if "--once" in argv:
            return
        time.sleep(interval)


if __name__ == "__main__":
    main(sys.argv[1:])
