"""Official FedEx Track API (developer.fedex.com).

Auth: OAuth2 client_credentials against /oauth/token, then a bearer-token
POST against /track/v1/trackingnumbers with includeDetailedScans=true.

Response field names follow FedEx's published Track API v1 schema:
output.completeTrackResults[].trackResults[].scanEvents[], each with
date (ISO 8601), eventDescription, eventType, and scanLocation.{city,
stateOrProvinceCode, countryCode}. latestStatusDetail.code carries the
overall status (DL=delivered, DE/SE=exception, else in transit).
"""

from sqlalchemy.orm import Session

import httpx

from ... import settings_store

_TOKEN_URL = "https://apis.fedex.com/oauth/token"
_TRACK_URL = "https://apis.fedex.com/track/v1/trackingnumbers"

_EXCEPTION_CODES = {"DE", "SE", "CA"}


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "fedex_client_id")) and bool(
        settings_store.get_setting(db, "fedex_client_secret")
    )


def _get_token(client_id: str, client_secret: str) -> str | None:
    try:
        resp = httpx.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except httpx.HTTPError:
        return None


def test_credentials(db: Session) -> dict:
    client_id = settings_store.get_setting(db, "fedex_client_id")
    client_secret = settings_store.get_setting(db, "fedex_client_secret")
    if not client_id or not client_secret:
        return {"ok": False, "error": "API key/secret key not set"}
    token = _get_token(client_id, client_secret)
    if token is None:
        return {"ok": False, "error": "FedEx rejected the API key/secret key"}
    return {"ok": True}


def get_tracking(db: Session, tracking_number: str) -> dict | None:
    client_id = settings_store.get_setting(db, "fedex_client_id")
    client_secret = settings_store.get_setting(db, "fedex_client_secret")
    if not client_id or not client_secret:
        return None

    token = _get_token(client_id, client_secret)
    if token is None:
        return None

    try:
        resp = httpx.post(
            _TRACK_URL,
            json={
                "includeDetailedScans": True,
                "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": tracking_number}}],
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-locale": "en_US",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        return None

    complete_results = ((data.get("output") or {}).get("completeTrackResults")) or []
    if not complete_results:
        return None
    track_results = complete_results[0].get("trackResults") or []
    if not track_results:
        return None
    result = track_results[0]

    events = []
    for scan in result.get("scanEvents") or []:
        location_obj = scan.get("scanLocation") or {}
        location_parts = [
            location_obj.get("city"),
            location_obj.get("stateOrProvinceCode"),
            location_obj.get("countryCode"),
        ]
        location = ", ".join(p for p in location_parts if p) or None
        events.append(
            {
                "time": _normalize_time(scan.get("date")),
                "location": location,
                "description": scan.get("eventDescription"),
                "raw_status": scan.get("eventType"),
            }
        )

    status_code = (result.get("latestStatusDetail") or {}).get("code")
    if status_code == "DL":
        status = "delivered"
    elif status_code in _EXCEPTION_CODES:
        status = "exception"
    elif status_code:
        status = "in_transit"
    else:
        status = "unknown"

    return {"status": status, "events": events}


def _normalize_time(value: str | None) -> str | None:
    """FedEx returns ISO 8601 with a timezone offset (e.g. 2024-01-15T14:30:00-05:00);
    trim to the naive "YYYY-MM-DDTHH:MM:SS" prefix that pipeline._parse_time expects."""
    if not value:
        return None
    return value[:19]
