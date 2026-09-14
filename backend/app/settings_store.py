from sqlalchemy.orm import Session

from . import models
from .crypto import decrypt, encrypt

SENSITIVE_KEYS = {
    "discord_webhook_url",
    "gmail_app_password",
    "ups_client_id",
    "ups_client_secret",
    "fedex_client_id",
    "fedex_client_secret",
    "usps_consumer_key",
    "usps_consumer_secret",
    "dhl_api_key",
    "amazon_17track_api_key",
}

DEFAULTS = {
    "email_scan_interval_minutes": "30",
    "tracking_refresh_interval_hours": "5",
    "discord_webhook_url": "",
    "gmail_address": "",
    "gmail_app_password": "",
    "gmail_last_error": "",
    "last_email_scan_at": "",
    "last_tracking_refresh_at": "",
    "ups_client_id": "",
    "ups_client_secret": "",
    "fedex_client_id": "",
    "fedex_client_secret": "",
    "usps_consumer_key": "",
    "usps_consumer_secret": "",
    "dhl_api_key": "",
    "amazon_17track_api_key": "",
    "theme": "system",
    "notify_delivered": "true",
    "notify_exception": "true",
    "notify_out_for_delivery": "true",
    "notify_new_package": "true",
    "notify_gmail_errors": "true",
}


def get_setting(db: Session, key: str) -> str:
    row = db.get(models.Setting, key)
    if row is None or row.value is None:
        return DEFAULTS.get(key, "")
    if key in SENSITIVE_KEYS and row.value:
        try:
            return decrypt(row.value)
        except Exception:
            return ""
    return row.value


def set_setting(db: Session, key: str, value: str) -> None:
    stored = encrypt(value) if (key in SENSITIVE_KEYS and value) else value
    row = db.get(models.Setting, key)
    if row is None:
        row = models.Setting(key=key, value=stored)
        db.add(row)
    else:
        row.value = stored
    db.commit()


def get_bool_setting(db: Session, key: str) -> bool:
    return get_setting(db, key) == "true"


def set_bool_setting(db: Session, key: str, value: bool) -> None:
    set_setting(db, key, "true" if value else "false")
