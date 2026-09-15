import datetime
import logging

from . import models, settings_store
from .db import SessionLocal
from .services import carriers, discord, extractor, geocode, gmail
from .services.carriers.errors import CarrierError

logger = logging.getLogger(__name__)


def run_email_scan() -> None:
    db = SessionLocal()
    try:
        if not gmail.is_configured(db):
            return

        conn = gmail.connect(db)
        if conn is None:
            return

        webhook_url = settings_store.get_setting(db, "discord_webhook_url")
        notify_new_package = settings_store.get_bool_setting(db, "notify_new_package")

        try:
            uids = gmail.search_recent_shipping_messages(conn, days=3, max_results=25)
            for uid in uids:
                message_key = uid.decode()
                if db.get(models.ProcessedEmail, message_key):
                    continue

                message = gmail.get_message(conn, uid)
                if message is None:
                    continue

                text = f"{message['subject']}\n{message['body']}"
                found = extractor.extract_tracking_numbers(text)
                item_name = extractor.clean_item_name(message["subject"])

                for carrier, tracking_number in found:
                    existing = (
                        db.query(models.Package).filter_by(tracking_number=tracking_number).first()
                    )
                    if existing is None:
                        db.add(
                            models.Package(
                                tracking_number=tracking_number,
                                carrier=carrier,
                                item_name=item_name,
                                status="unknown",
                                source_email_subject=message["subject"],
                            )
                        )
                        if notify_new_package and webhook_url:
                            discord.notify_new_package(webhook_url, item_name, tracking_number, carrier)

                db.add(models.ProcessedEmail(gmail_message_id=message_key))
                db.commit()
        finally:
            gmail.disconnect(conn)

        settings_store.set_setting(db, "last_email_scan_at", datetime.datetime.utcnow().isoformat())
    except Exception:
        logger.exception("email scan failed")
    finally:
        db.close()


def run_tracking_refresh() -> None:
    db = SessionLocal()
    try:
        webhook_url = settings_store.get_setting(db, "discord_webhook_url")
        notify_delivered = settings_store.get_bool_setting(db, "notify_delivered")
        notify_exception = settings_store.get_bool_setting(db, "notify_exception")
        notify_out_for_delivery = settings_store.get_bool_setting(db, "notify_out_for_delivery")

        packages = db.query(models.Package).filter_by(archived=False).all()
        for package in packages:
            if package.status == "delivered":
                continue

            if not package.carrier or not carriers.is_configured(db, package.carrier):
                continue

            try:
                result = carriers.get_tracking(db, package.carrier, package.tracking_number)
            except CarrierError as exc:
                package.last_error = str(exc)
                package.last_error_at = datetime.datetime.utcnow()
                db.commit()
                continue

            if result is None:
                continue

            if package.last_error:
                package.last_error = None
                package.last_error_at = None
                db.commit()

            # Dedupe on (time, description, location) rather than time alone: carrier
            # timestamps sometimes fail to parse (→ None for every event in a response),
            # and a time-only key with a stale, loop-external "seen" set let every event
            # in a single batch pass the check, inserting dozens of near-duplicate rows.
            existing_keys = {
                (e.event_time.isoformat() if e.event_time else None, e.description, e.location_text)
                for e in package.events
            }

            # Track the chronologically newest located event explicitly rather than just
            # taking whichever event happens to be processed last — every carrier module
            # returns events newest-first, so a blind overwrite was keeping the OLDEST
            # event of each batch as "latest", not the newest.
            best_time = package.last_update_at
            if best_time is not None and best_time.tzinfo is not None:
                best_time = best_time.replace(tzinfo=None)
            best_location = {
                "lat": package.last_lat,
                "lon": package.last_lon,
                "location": package.last_location_text,
            }
            # A package's stored last-known location can itself be a leftover bad
            # pin from before generic locations were excluded above — don't treat
            # that as a trustworthy baseline. Discard it so the loop below has to
            # re-derive the best AVAILABLE location from the full event history
            # the carrier resends, rather than perpetuating a wrong pin forever.
            discard_stale_baseline = not _is_specific_location(package.last_location_text)
            if discard_stale_baseline:
                best_time = None
                best_location = {"lat": None, "lon": None, "location": None}

            for event in result["events"]:
                event_time = _parse_time(event.get("time"))
                description = event.get("description")
                location = event.get("location")
                key = (event_time.isoformat() if event_time else None, description, location)

                # Carriers generally resend their full event history each cycle, not just
                # new deltas — so re-geocode (cache-backed, cheap) and reconsider this event
                # for "latest" even when it's already stored, rather than only checking
                # newly-inserted rows. That also self-heals a package.last_lat/lon that was
                # set wrong by the pre-fix version of this loop, next refresh after upgrading.
                coords = (
                    geocode.geocode(db, location)
                    if location and _is_specific_location(location)
                    else None
                )
                lat, lon = coords if coords else (None, None)

                if key not in existing_keys:
                    existing_keys.add(key)
                    db.add(
                        models.TrackingEvent(
                            package_id=package.id,
                            event_time=event_time,
                            location_text=location,
                            lat=lat,
                            lon=lon,
                            description=description,
                            raw_status=event.get("raw_status"),
                        )
                    )

                if lat is not None and event_time is not None:
                    if best_time is None or event_time > best_time:
                        best_time = event_time
                        best_location = {"lat": lat, "lon": lon, "location": location}

            if best_time is not None:
                package.last_lat = best_location["lat"]
                package.last_lon = best_location["lon"]
                package.last_location_text = best_location["location"]
                package.last_update_at = best_time
            elif discard_stale_baseline:
                # Nothing specific enough to pin was found anywhere in the carrier's
                # current history either — showing no pin (map falls back to "No
                # location yet") is more honest than leaving the discarded bad one.
                package.last_lat = None
                package.last_lon = None
                package.last_location_text = None
                package.last_update_at = None

            was_delivered = package.status == "delivered"
            was_exception = package.status == "exception"
            package.status = result["status"]
            db.commit()

            if package.status == "delivered" and not was_delivered and not package.delivered_notified_at:
                if notify_delivered and webhook_url:
                    discord.notify_delivered(
                        webhook_url, package.item_name, package.tracking_number, package.last_location_text
                    )
                package.delivered_notified_at = datetime.datetime.utcnow()
                db.commit()

            if package.status == "exception" and not was_exception and not package.exception_notified_at:
                if notify_exception and webhook_url:
                    last_description = package.events[-1].description if package.events else None
                    discord.notify_exception(
                        webhook_url, package.item_name, package.tracking_number, last_description
                    )
                package.exception_notified_at = datetime.datetime.utcnow()
                db.commit()

            if not package.out_for_delivery_notified_at and any(
                _is_out_for_delivery(e.description) for e in package.events
            ):
                if notify_out_for_delivery and webhook_url:
                    discord.notify_out_for_delivery(
                        webhook_url, package.item_name, package.tracking_number, package.last_location_text
                    )
                package.out_for_delivery_notified_at = datetime.datetime.utcnow()
                db.commit()

        settings_store.set_setting(
            db, "last_tracking_refresh_at", datetime.datetime.utcnow().isoformat()
        )
    except Exception:
        logger.exception("tracking refresh failed")
    finally:
        db.close()


_GENERIC_LOCATIONS = {
    "us",
    "usa",
    "u.s.",
    "u.s.a.",
    "united states",
    "united states of america",
}


def _is_specific_location(location: str | None) -> bool:
    """Carriers sometimes report only a bare country name on a checkpoint where
    city/state weren't populated (e.g. UPS's location string collapsing to just
    "US" when address.city/stateProvince are empty). Geocoding that resolves to
    a real coordinate — the country's centroid — which is a valid geocode result
    but nowhere near the package, so these are excluded from ever becoming the
    map pin rather than silently showing a misleading, wildly-off location."""
    if not location:
        return False
    return location.strip().lower() not in _GENERIC_LOCATIONS


def _is_out_for_delivery(description: str | None) -> bool:
    """Carriers don't share a common status code for this sub-state — UPS/DHL
    only ever surface it in free-text event descriptions, so this heuristic is
    used uniformly for all four carriers rather than branching per-carrier."""
    return bool(description) and "out for delivery" in description.lower()


def _parse_time(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
