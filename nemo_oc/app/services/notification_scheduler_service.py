"""
Scheduler liviano para resumenes email mientras la app esta encendida.
Se inicia tanto en desktop como en web.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

POLL_SECONDS = 45
STARTUP_DELAY_SECONDS = 60

_instance: Optional["NotificationSchedulerService"] = None


def get_notification_scheduler() -> "NotificationSchedulerService":
    global _instance
    if _instance is None:
        _instance = NotificationSchedulerService()
    return _instance


def start_notification_scheduler() -> None:
    get_notification_scheduler().start()


def stop_notification_scheduler() -> None:
    get_notification_scheduler().stop()


class NotificationSchedulerService:

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.info("Scheduler de notificaciones ya estaba en ejecucion.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="NotificationScheduler",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        from app.services.email_service import get_email_service

        logger.info("Scheduler de resumenes email iniciado.")
        if self._stop_event.wait(STARTUP_DELAY_SECONDS):
            logger.info("Scheduler de resumenes email detenido.")
            return

        self._run_once(get_email_service())

        while not self._stop_event.wait(POLL_SECONDS):
            self._run_once(get_email_service())

        logger.info("Scheduler de resumenes email detenido.")

    def _run_once(self, email_service) -> None:
        try:
            enviados = email_service.enviar_resumenes_programados()
            if enviados:
                logger.info(f"Scheduler email: {enviados} resumen(es) enviados.")
        except Exception as e:
            logger.warning(f"Scheduler email: no se pudieron enviar resumenes: {e}")
