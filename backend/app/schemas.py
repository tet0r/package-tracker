from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TrackingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_time: datetime | None
    location_text: str | None
    lat: float | None
    lon: float | None
    description: str | None
    raw_status: str | None


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_number: str
    carrier: str | None
    item_name: str
    status: str
    last_lat: float | None
    last_lon: float | None
    last_location_text: str | None
    last_update_at: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    archived: bool
    created_at: datetime


class PackageDetailOut(PackageOut):
    events: list[TrackingEventOut] = []


class PackageCreate(BaseModel):
    tracking_number: str
    item_name: str
    carrier: str | None = None


class PackageUpdate(BaseModel):
    item_name: str | None = None
    archived: bool | None = None


class SettingsOut(BaseModel):
    email_scan_interval_minutes: int
    tracking_refresh_interval_hours: float
    discord_webhook_url_set: bool
    last_email_scan_at: str | None
    last_tracking_refresh_at: str | None
    gmail_configured: bool
    gmail_last_error: str | None
    ups_configured: bool
    fedex_configured: bool
    usps_configured: bool
    dhl_configured: bool
    theme: Literal["system", "light", "dark"]
    notify_delivered: bool
    notify_exception: bool
    notify_out_for_delivery: bool
    notify_new_package: bool
    notify_gmail_errors: bool


class SettingsUpdate(BaseModel):
    email_scan_interval_minutes: int | None = None
    tracking_refresh_interval_hours: float | None = None
    discord_webhook_url: str | None = None
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    ups_client_id: str | None = None
    ups_client_secret: str | None = None
    fedex_client_id: str | None = None
    fedex_client_secret: str | None = None
    usps_consumer_key: str | None = None
    usps_consumer_secret: str | None = None
    dhl_api_key: str | None = None
    theme: Literal["system", "light", "dark"] | None = None
    notify_delivered: bool | None = None
    notify_exception: bool | None = None
    notify_out_for_delivery: bool | None = None
    notify_new_package: bool | None = None
    notify_gmail_errors: bool | None = None
