import asyncio
import logging
import time
from typing import Callable

from . import pipeline, settings_store
from .db import SessionLocal

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 60


async def _run_loop(
    interval_setting_key: str, default_value: str, unit_seconds: float, run_fn: Callable[[], None], name: str
) -> None:
    last_run = 0.0
    while True:
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

        db = SessionLocal()
        try:
            raw = settings_store.get_setting(db, interval_setting_key) or default_value
        finally:
            db.close()

        try:
            interval_seconds = float(raw) * unit_seconds
        except ValueError:
            interval_seconds = float(default_value) * unit_seconds

        if time.time() - last_run >= interval_seconds:
            logger.info("running %s", name)
            await asyncio.to_thread(run_fn)
            last_run = time.time()


def start_background_loops() -> None:
    asyncio.create_task(
        _run_loop("email_scan_interval_minutes", "30", 60, pipeline.run_email_scan, "email scan")
    )
    asyncio.create_task(
        _run_loop(
            "tracking_refresh_interval_hours", "5", 3600, pipeline.run_tracking_refresh, "tracking refresh"
        )
    )
