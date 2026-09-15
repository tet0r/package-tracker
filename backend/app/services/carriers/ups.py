"""Official UPS Tracking API (developer.ups.com).

Auth: OAuth2 client_credentials against /security/v1/oauth/token, then a
bearer-token GET against /api/track/v1/details/{trackingNumber}.

Response field names below follow UPS's published Track API schema
(trackResponse.shipment[].package[].activity[], each with status.type/
description, location.address.{city,stateProvince,country}, date (YYYYMMDD),
time (HHMMSS)). UPS returns activity most-recent-first.
"""

import datetime

from sqlalchemy.orm import Session

import httpx

from ... import settings_store
from .errors import CarrierError, describe_http_error

_TOKEN_URL = "https://onlinetools.ups.com/security/v1/oauth/token"
_TRACK_URL = "https://onlinetools.ups.com/api/track/v1/details/{tracking_number}"

_STATUS_TYPE_MAP = {
    "D": "delivered",
    "X": "exception",
    "RS": "exception",
}


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "ups_client_id")) and bool(
        settings_store.get_setting(db, "ups_client_secret")
    )


def _get_token(client_id: str, client_secret: str) -> str | None:
    try:
        resp = httpx.post(
            _TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except httpx.HTTPError:
        return None


def test_credentials(db: Session) -> dict:
    client_id = settings_store.get_setting(db, "ups_client_id")
    client_secret = settings_store.get_setting(db, "ups_client_secret")
    if not client_id or not client_secret:
        return {"ok": False, "error": "Client ID/secret not set"}
    token = _get_token(client_id, client_secret)
    if token is None:
        return {"ok": False, "error": "UPS rejected the Client ID/secret"}
    return {"ok": True}


def get_tracking(db: Session, tracking_number: str) -> dict | None:
    client_id = settings_store.get_setting(db, "ups_client_id")
    client_secret = settings_store.get_setting(db, "ups_client_secret")
    if not client_id or not client_secret:
        return None

    token = _get_token(client_id, client_secret)
    if token is None:
        raise CarrierError("Could not authenticate with UPS — check the Client ID/secret")

    try:
        resp = httpx.get(
            _TRACK_URL.format(tracking_number=tracking_number),
            headers={
                "Authorization": f"Bearer {token}",
                "transId": f"pkgtracker-{tracking_number}",
                "transactionSrc": "self-hosted-package-tracker",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise CarrierError(describe_http_error(exc)) from exc

    shipments = (data.get("trackResponse") or {}).get("shipment") or []
    if not shipments:
        return None
    packages = shipments[0].get("package") or []
    if not packages:
        return None
    activities = packages[0].get("activity") or []

    events = []
    for activity in activities:
        address = ((activity.get("location") or {}).get("address")) or {}
        location_parts = [
            address.get("city"),
            address.get("stateProvince"),
            address.get("country"),
        ]
        location = ", ".join(p for p in location_parts if p) or None
        status = activity.get("status") or {}
        events.append(
            {
                "time": _parse_datetime(activity.get("date"), activity.get("time")),
                "location": location,
                "description": status.get("description"),
                "raw_status": status.get("type"),
            }
        )

    status_type = (activities[0].get("status") or {}).get("type") if activities else None
    status = _STATUS_TYPE_MAP.get(status_type, "in_transit" if activities else "unknown")

    return {"status": status, "events": events}


def _parse_datetime(date_str: str | None, time_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        dt = datetime.datetime.strptime(date_str + (time_str or "000000"), "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
