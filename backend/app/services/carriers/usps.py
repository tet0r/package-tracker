"""Official USPS Tracking API v3 (developer.usps.com / apis.usps.com).

Auth: OAuth2 client_credentials against /oauth2/v3/token, then a bearer-token
GET against /tracking/v3/tracking/{trackingNumber}?expand=DETAIL.

Response field names follow USPS's published Tracking API v3 schema:
trackingEvents[] (newest first) with eventTimestamp (ISO 8601), eventType,
eventCity, eventState, eventCountry. Top-level statusCategory carries the
overall status.
"""

from sqlalchemy.orm import Session

import httpx

from ... import settings_store
from .errors import CarrierError, describe_http_error

_TOKEN_URL = "https://apis.usps.com/oauth2/v3/token"
_TRACK_URL = "https://apis.usps.com/tracking/v3/tracking/{tracking_number}"


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "usps_consumer_key")) and bool(
        settings_store.get_setting(db, "usps_consumer_secret")
    )


def _get_token(consumer_key: str, consumer_secret: str) -> str | None:
    try:
        resp = httpx.post(
            _TOKEN_URL,
            json={
                "client_id": consumer_key,
                "client_secret": consumer_secret,
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except httpx.HTTPError:
        return None


def test_credentials(db: Session) -> dict:
    consumer_key = settings_store.get_setting(db, "usps_consumer_key")
    consumer_secret = settings_store.get_setting(db, "usps_consumer_secret")
    if not consumer_key or not consumer_secret:
        return {"ok": False, "error": "Consumer key/secret not set"}
    token = _get_token(consumer_key, consumer_secret)
    if token is None:
        return {"ok": False, "error": "USPS rejected the consumer key/secret"}
    return {"ok": True}


def get_tracking(db: Session, tracking_number: str) -> dict | None:
    consumer_key = settings_store.get_setting(db, "usps_consumer_key")
    consumer_secret = settings_store.get_setting(db, "usps_consumer_secret")
    if not consumer_key or not consumer_secret:
        return None

    token = _get_token(consumer_key, consumer_secret)
    if token is None:
        raise CarrierError("Could not authenticate with USPS — check the consumer key/secret")

    try:
        resp = httpx.get(
            _TRACK_URL.format(tracking_number=tracking_number),
            params={"expand": "DETAIL"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise CarrierError(describe_http_error(exc)) from exc

    events = []
    for event in data.get("trackingEvents") or []:
        location_parts = [event.get("eventCity"), event.get("eventState"), event.get("eventCountry")]
        location = ", ".join(p for p in location_parts if p) or None
        events.append(
            {
                "time": _normalize_time(event.get("eventTimestamp")),
                "location": location,
                "description": event.get("eventType"),
                "raw_status": event.get("eventCode"),
            }
        )

    status_category = (data.get("statusCategory") or "").lower()
    if "delivered" in status_category:
        status = "delivered"
    elif "alert" in status_category or "exception" in status_category:
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
