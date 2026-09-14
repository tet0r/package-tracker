import datetime
import logging

from . import models, settings_store
from .db import SessionLocal
from .services import carriers, discord, extractor, geocode, gmail

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

            result = carriers.get_tracking(db, package.carrier, package.tracking_number)
            if result is None:
                continue

            existing_times = {
                e.event_time.isoformat() if e.event_time else None for e in package.events
            }

            latest_event = None
            for event in result["events"]:
                event_time = _parse_time(event.get("time"))
                key = event_time.isoformat() if event_time else None
                if key in existing_times:
                    continue

                location = event.get("location")
                coords = geocode.geocode(db, location) if location else None
                lat, lon = coords if coords else (None, None)

                db.add(
                    models.TrackingEvent(
                        package_id=package.id,
                        event_time=event_time,
                        location_text=location,
                        lat=lat,
                        lon=lon,
                        description=event.get("description"),
                        raw_status=event.get("raw_status"),
                    )
                )
                if lat is not None:
                    latest_event = {"lat": lat, "lon": lon, "location": location, "time": event_time}

            if latest_event:
                package.last_lat = latest_event["lat"]
                package.last_lon = latest_event["lon"]
                package.last_location_text = latest_event["location"]
                package.last_update_at = latest_event["time"]

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
