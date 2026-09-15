"""Official DHL Shipment Tracking - Unified API (developer.dhl.com).

Auth: a single static API key sent as the DHL-API-Key header — no OAuth
exchange needed.

Response field names follow DHL's published Unified Tracking API schema:
shipments[].events[] (newest first) with timestamp (ISO 8601), description,
and location.address.addressLocality. shipments[].status.statusCode carries
the overall status ("delivered", "failure", etc).
"""

from sqlalchemy.orm import Session

import httpx

from ... import settings_store
from .errors import CarrierError, describe_http_error

_TRACK_URL = "https://api-eu.dhl.com/track/shipments"


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "dhl_api_key"))


def test_credentials(db: Session) -> dict:
    api_key = settings_store.get_setting(db, "dhl_api_key")
    if not api_key:
        return {"ok": False, "error": "API key not set"}
    try:
        resp = httpx.get(
            _TRACK_URL,
            params={"trackingNumber": "000000000000"},
            headers={"DHL-API-Key": api_key},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    if resp.status_code in (401, 403):
        return {"ok": False, "error": "DHL rejected the API key"}
    return {"ok": True}


def get_tracking(db: Session, tracking_number: str) -> dict | None:
    api_key = settings_store.get_setting(db, "dhl_api_key")
    if not api_key:
        return None

    try:
        resp = httpx.get(
            _TRACK_URL,
            params={"trackingNumber": tracking_number},
            headers={"DHL-API-Key": api_key},
            timeout=20,
        )
        if resp.status_code == 404:
            return None  # DHL has no record of this shipment yet, not an error
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise CarrierError(describe_http_error(exc)) from exc

    shipments = data.get("shipments") or []
    if not shipments:
        return None
    shipment = shipments[0]

    events = []
    for event in shipment.get("events") or []:
        address = ((event.get("location") or {}).get("address")) or {}
        events.append(
            {
                "time": _normalize_time(event.get("timestamp")),
                "location": address.get("addressLocality"),
                "description": event.get("description"),
                "raw_status": event.get("statusCode"),
            }
        )

    status_code = ((shipment.get("status") or {}).get("statusCode") or "").lower()
    if status_code == "delivered":
        status = "delivered"
    elif status_code == "failure":
        status = "exception"
    elif events:
        status = "in_transit"
    else:
        status = "unknown"

    return {"status": status, "events": events}


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    return value[:19]
