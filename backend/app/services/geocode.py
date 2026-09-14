import threading
import time

import httpx
from sqlalchemy.orm import Session

from .. import models
from ..config import settings as app_settings

_lock = threading.Lock()
_last_call = 0.0
_MIN_INTERVAL_SECONDS = 1.1  # Nominatim's usage policy caps free requests at ~1/sec.


def geocode(db: Session, location_text: str | None) -> tuple[float, float] | None:
    if not location_text:
        return None
    location_text = location_text.strip()
    if not location_text:
        return None

    cached = db.get(models.GeocodeCache, location_text)
    if cached:
        return cached.lat, cached.lon

    global _last_call
    with _lock:
        wait = _MIN_INTERVAL_SECONDS - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": location_text, "format": "json", "limit": 1},
                headers={"User-Agent": app_settings.NOMINATIM_USER_AGENT},
                timeout=15,
            )
            _last_call = time.time()
            resp.raise_for_status()
            results = resp.json()
        except httpx.HTTPError:
            return None

    if not results:
        return None

    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    db.add(models.GeocodeCache(location_text=location_text, lat=lat, lon=lon))
    db.commit()
    return lat, lon
