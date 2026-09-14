"""Amazon Logistics tracking via 17TRACK (17track.net).

Amazon has no public API for a consumer to check their own packages, and
Amazon Logistics ("TBA"-prefixed tracking numbers) isn't a real carrier with
its own developer portal — it's Amazon's internal last-mile network. 17TRACK
is a third-party aggregator that scrapes/monitors Amazon's tracking pages at
scale as its business, so unlike the UPS/FedEx/USPS/DHL modules (which call
each carrier's own official API), this module's tracking data passes through
a third party.

Auth: a single API key sent as the 17token header — no OAuth exchange.

Rather than hardcode a numeric carrier code for Amazon (17TRACK's carrier
list has an ambiguous "Amazon Shipping + Amazon MCF" entry that may not be
the same thing as standard Amazon Logistics deliveries), every tracking
number is registered with auto_detection=true so 17TRACK resolves the
carrier itself from the number's format.

Response field names follow 17TRACK's documented Tracking API v2.2 schema:
data.accepted[].track_info.tracking.providers[].events[], each with
time_iso, description, location, stage (delivered/exception/etc).
"""

from sqlalchemy.orm import Session

import httpx

from ... import settings_store

_BASE_URL = "https://api.17track.net/track/v2.2"

_STAGE_MAP = {
    "delivered": "delivered",
    "exception": "exception",
    "expired": "exception",
    "returned": "exception",
    "notfound": "unknown",
    "inforeceived": "in_transit",
    "intransit": "in_transit",
    "outfordelivery": "in_transit",
    "pickup": "in_transit",
    "alert": "exception",
}


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "amazon_17track_api_key"))


def _headers(api_key: str) -> dict:
    return {"17token": api_key, "Content-Type": "application/json"}


def test_credentials(db: Session) -> dict:
    api_key = settings_store.get_setting(db, "amazon_17track_api_key")
    if not api_key:
        return {"ok": False, "error": "API key not set"}
    try:
        resp = httpx.post(
            f"{_BASE_URL}/register",
            json=[{"number": "TBA000000000000", "auto_detection": True}],
            headers=_headers(api_key),
            timeout=15,
        )
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    if resp.status_code in (401, 403):
        return {"ok": False, "error": "17TRACK rejected the API key"}
    return {"ok": True}


def _register(api_key: str, tracking_number: str) -> None:
    try:
        httpx.post(
            f"{_BASE_URL}/register",
            json=[{"number": tracking_number, "auto_detection": True}],
            headers=_headers(api_key),
            timeout=15,
        )
    except httpx.HTTPError:
        pass


def get_tracking(db: Session, tracking_number: str) -> dict | None:
    api_key = settings_store.get_setting(db, "amazon_17track_api_key")
    if not api_key:
        return None

    _register(api_key, tracking_number)

    try:
        resp = httpx.post(
            f"{_BASE_URL}/gettrackinfo",
            json=[{"number": tracking_number}],
            headers=_headers(api_key),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        return None

    accepted = ((data.get("data") or {}).get("accepted")) or []
    if not accepted:
        return None
    track_info = accepted[0].get("track_info") or {}
    providers = ((track_info.get("tracking") or {}).get("providers")) or []

    events = []
    for provider in providers:
        for event in provider.get("events") or []:
            events.append(
                {
                    "time": _normalize_time(event.get("time_iso") or event.get("time_utc")),
                    "location": event.get("location"),
                    "description": event.get("description"),
                    "raw_status": event.get("sub_status") or event.get("stage"),
                }
            )

    stage = ((track_info.get("latest_status") or {}).get("status") or "").lower()
    status = _STAGE_MAP.get(stage, "in_transit" if events else "unknown")

    return {"status": status, "events": events}


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    return value[:19]
