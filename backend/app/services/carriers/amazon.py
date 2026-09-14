"""Amazon Logistics tracking via Ship24 (ship24.com).

Amazon has no public API for a consumer to check their own packages, and
Amazon Logistics ("TBA"-prefixed tracking numbers) isn't a real carrier with
its own developer portal — it's Amazon's internal last-mile network. Ship24
is a third-party aggregator that tracks it (among 1,500+ couriers) as its
business, so unlike the UPS/FedEx/USPS/DHL modules (which call each
carrier's own official API), this module's tracking data passes through a
third party. (17TRACK was tried first but its signup requires a business
email, which ruled it out for personal use.)

Auth: a single API key sent as `Authorization: Bearer <key>` — no OAuth
exchange.

Uses POST /public/v1/trackers/track, which is idempotent and synchronous:
it creates the tracker on first call if it doesn't exist yet and returns
full tracking results in the same response, so there's no separate
register-then-poll step like the other aggregator-backed integrations
needed. courierCode is omitted so Ship24 auto-detects the carrier from the
tracking number's format. Per Ship24's docs, that very first call for a
tracking number can take up to ~1 minute while it fetches initial results;
every call after that is fast since the tracker already exists.

Response field names follow Ship24's published OpenAPI schema:
data.trackings[].shipment.statusMilestone (overall status) and
data.trackings[].events[] with occurrenceDatetime, status (human-readable
text), location, statusMilestone.
"""

from sqlalchemy.orm import Session

import httpx

from ... import settings_store

_TRACK_URL = "https://api.ship24.com/public/v1/trackers/track"

_MILESTONE_MAP = {
    "delivered": "delivered",
    "exception": "exception",
    "failed_attempt": "exception",
    "info_received": "in_transit",
    "in_transit": "in_transit",
    "out_for_delivery": "in_transit",
    "available_for_pickup": "in_transit",
}


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "amazon_ship24_api_key"))


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"}


def test_credentials(db: Session) -> dict:
    api_key = settings_store.get_setting(db, "amazon_ship24_api_key")
    if not api_key:
        return {"ok": False, "error": "API key not set"}
    try:
        resp = httpx.post(
            _TRACK_URL,
            json={"trackingNumber": "TBA000000000000"},
            headers=_headers(api_key),
            timeout=20,
        )
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    if resp.status_code in (401, 403):
        return {"ok": False, "error": "Ship24 rejected the API key"}
    return {"ok": True}


def get_tracking(db: Session, tracking_number: str) -> dict | None:
    api_key = settings_store.get_setting(db, "amazon_ship24_api_key")
    if not api_key:
        return None

    try:
        resp = httpx.post(
            _TRACK_URL,
            json={"trackingNumber": tracking_number},
            headers=_headers(api_key),
            timeout=65,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        return None

    trackings = ((data.get("data") or {}).get("trackings")) or []
    if not trackings:
        return None
    tracking = trackings[0]

    events = []
    for event in tracking.get("events") or []:
        events.append(
            {
                "time": _normalize_time(event.get("occurrenceDatetime")),
                "location": event.get("location"),
                "description": event.get("status"),
                "raw_status": event.get("statusMilestone"),
            }
        )

    milestone = (tracking.get("shipment") or {}).get("statusMilestone") or ""
    status = _MILESTONE_MAP.get(milestone, "in_transit" if events else "unknown")

    return {"status": status, "events": events}


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    return value[:19]
