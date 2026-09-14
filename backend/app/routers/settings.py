from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas, settings_store
from ..db import get_db
from ..services import carriers, discord, gmail

router = APIRouter()


def _build_settings_out(db: Session) -> schemas.SettingsOut:
    return schemas.SettingsOut(
        email_scan_interval_minutes=int(settings_store.get_setting(db, "email_scan_interval_minutes")),
        tracking_refresh_interval_hours=float(
            settings_store.get_setting(db, "tracking_refresh_interval_hours")
        ),
        discord_webhook_url_set=bool(settings_store.get_setting(db, "discord_webhook_url")),
        last_email_scan_at=settings_store.get_setting(db, "last_email_scan_at") or None,
        last_tracking_refresh_at=settings_store.get_setting(db, "last_tracking_refresh_at") or None,
        gmail_configured=gmail.is_configured(db),
        gmail_last_error=settings_store.get_setting(db, "gmail_last_error") or None,
        ups_configured=carriers.is_configured(db, "UPS"),
        fedex_configured=carriers.is_configured(db, "FedEx"),
        usps_configured=carriers.is_configured(db, "USPS"),
        dhl_configured=carriers.is_configured(db, "DHL"),
        amazon_configured=carriers.is_configured(db, "Amazon"),
        theme=settings_store.get_setting(db, "theme"),
        notify_delivered=settings_store.get_bool_setting(db, "notify_delivered"),
        notify_exception=settings_store.get_bool_setting(db, "notify_exception"),
        notify_out_for_delivery=settings_store.get_bool_setting(db, "notify_out_for_delivery"),
        notify_new_package=settings_store.get_bool_setting(db, "notify_new_package"),
        notify_gmail_errors=settings_store.get_bool_setting(db, "notify_gmail_errors"),
    )


@router.get("", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _build_settings_out(db)


@router.put("", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    if payload.email_scan_interval_minutes is not None:
        settings_store.set_setting(
            db, "email_scan_interval_minutes", str(payload.email_scan_interval_minutes)
        )
    if payload.tracking_refresh_interval_hours is not None:
        settings_store.set_setting(
            db, "tracking_refresh_interval_hours", str(payload.tracking_refresh_interval_hours)
        )
    if payload.discord_webhook_url is not None:
        settings_store.set_setting(db, "discord_webhook_url", payload.discord_webhook_url)
    if payload.theme is not None:
        settings_store.set_setting(db, "theme", payload.theme)
    for bool_field in (
        "notify_delivered",
        "notify_exception",
        "notify_out_for_delivery",
        "notify_new_package",
        "notify_gmail_errors",
    ):
        value = getattr(payload, bool_field)
        if value is not None:
            settings_store.set_bool_setting(db, bool_field, value)
    for field in (
        "gmail_address",
        "gmail_app_password",
        "ups_client_id",
        "ups_client_secret",
        "fedex_client_id",
        "fedex_client_secret",
        "usps_consumer_key",
        "usps_consumer_secret",
        "dhl_api_key",
        "amazon_ship24_api_key",
    ):
        value = getattr(payload, field)
        if value is not None:
            settings_store.set_setting(db, field, value)
    return _build_settings_out(db)


@router.post("/discord/test")
def test_discord(db: Session = Depends(get_db)):
    webhook_url = settings_store.get_setting(db, "discord_webhook_url")
    if not webhook_url:
        return {"ok": False, "error": "No Discord webhook URL configured"}
    ok = discord.send_message(
        webhook_url, "🔔 Test notification from Package Tracker — your webhook is working."
    )
    return {"ok": ok}


@router.post("/gmail/test")
def test_gmail(db: Session = Depends(get_db)):
    if not gmail.is_configured(db):
        return {"ok": False, "error": "No Gmail address/app password configured"}
    return gmail.test_connection(db)


@router.post("/carriers/{carrier}/test")
def test_carrier(carrier: str, db: Session = Depends(get_db)):
    if carrier not in ("UPS", "FedEx", "USPS", "DHL", "Amazon"):
        return {"ok": False, "error": f"Unknown carrier {carrier}"}
    return carriers.test_credentials(db, carrier)
