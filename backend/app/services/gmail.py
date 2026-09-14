"""Gmail access over IMAP with an App Password.

Deliberately not OAuth: Google forces personal (non-Workspace) OAuth apps
requesting the gmail.readonly scope to stay in "Testing" publishing status
unless they pass a paid third-party CASA security audit, and Testing-status
refresh tokens expire every 7 days. App Passwords have no such expiry and
need no Google Cloud project at all.

Uses Gmail's IMAP X-GM-RAW extension to reuse the same search syntax as
Gmail's own search box.
"""

import email
import imaplib
from email.header import decode_header

from sqlalchemy.orm import Session

from .. import settings_store
from . import discord as discord_service

_IMAP_HOST = "imap.gmail.com"
_IMAP_PORT = 993

_SEARCH_QUERY = (
    'newer_than:{days}d (tracking OR "tracking number" OR shipped OR shipment OR '
    '"out for delivery" OR ups OR fedex OR usps OR dhl OR amazon)'
)


def is_configured(db: Session) -> bool:
    return bool(settings_store.get_setting(db, "gmail_address")) and bool(
        settings_store.get_setting(db, "gmail_app_password")
    )


def connect(db: Session) -> imaplib.IMAP4_SSL | None:
    address = settings_store.get_setting(db, "gmail_address")
    app_password = settings_store.get_setting(db, "gmail_app_password")
    if not address or not app_password:
        return None
    try:
        conn = imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT)
        conn.login(address, app_password)
        conn.select("INBOX", readonly=True)
        settings_store.set_setting(db, "gmail_last_error", "")
        return conn
    except (imaplib.IMAP4.error, OSError) as exc:
        message = str(exc)
        settings_store.set_setting(db, "gmail_last_error", message)
        webhook = settings_store.get_setting(db, "discord_webhook_url")
        if webhook:
            discord_service.send_message(
                webhook, f"⚠️ Gmail connection failed — check your app password in Settings. ({message})"
            )
        return None


def disconnect(conn: imaplib.IMAP4_SSL | None) -> None:
    if conn is None:
        return
    try:
        conn.logout()
    except Exception:
        pass


def test_connection(db: Session) -> dict:
    conn = connect(db)
    if conn is None:
        return {"ok": False, "error": settings_store.get_setting(db, "gmail_last_error") or "Could not connect"}
    disconnect(conn)
    return {"ok": True}


def search_recent_shipping_messages(
    conn: imaplib.IMAP4_SSL, days: int = 3, max_results: int = 25
) -> list[bytes]:
    query = _SEARCH_QUERY.format(days=days).replace('"', '\\"')
    try:
        status, data = conn.uid("search", None, "X-GM-RAW", f'"{query}"')
    except imaplib.IMAP4.error:
        return []
    if status != "OK" or not data or data[0] is None:
        return []
    uids = data[0].split()
    return uids[-max_results:]


def get_message(conn: imaplib.IMAP4_SSL, uid: bytes) -> dict | None:
    try:
        status, data = conn.uid("fetch", uid, "(RFC822)")
    except imaplib.IMAP4.error:
        return None
    if status != "OK" or not data or data[0] is None:
        return None
    raw = data[0][1]
    msg = email.message_from_bytes(raw)
    subject = _decode_header_value(msg.get("Subject", ""))
    body = _extract_body(msg)
    return {"id": uid.decode(), "subject": subject, "body": body}


def _decode_header_value(value: str) -> str:
    decoded = ""
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            decoded += part.decode(encoding or "utf-8", errors="ignore")
        else:
            decoded += part
    return decoded


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload is not None:
                    return payload.decode(charset, errors="ignore")
        return ""
    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True)
    return payload.decode(charset, errors="ignore") if payload is not None else ""
