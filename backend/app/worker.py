"""Worker de tareas de mantenimiento. El estado vive en Postgres: si se reinicia, retoma.

Cada vuelta (todas idempotentes; el estado vive en la base):
- libera el stock de pedidos impagos con la reserva vencida (`for update skip locked`);
- destila la memoria de clientes cuya conversación quedó inactiva (fuera de la respuesta);
- resume la parte vieja de las conversaciones largas;
- lee con OCR local los comprobantes de pago recibidos (nunca acreditan el pago);
- borra conversaciones de prueba abandonadas (vistas previas del asistente).

    python -m app.worker            # bucle cada WORKER_INTERVAL_S segundos (default 60)
    python -m app.worker --once     # una sola vuelta (cron, tests)
"""
from __future__ import annotations

import logging
import os
import sys
import time

from .agent import compaction
from .documents import store as documents
from .domain import customer_memory, evals, orders

log = logging.getLogger("app.worker")


def run_once() -> dict[str, int]:
    return {"expired_reservations": orders.expire_reservations(),
            "customer_memories": customer_memory.refresh_due(),
            "compacted_conversations": compaction.compact_due(),
            "payment_documents_read": documents.process_pending(),
            "stale_previews": evals.cleanup_stale()}


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
