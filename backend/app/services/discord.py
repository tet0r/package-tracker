import httpx


def send_message(webhook_url: str, content: str) -> bool:
    if not webhook_url:
        return False
    try:
        resp = httpx.post(webhook_url, json={"content": content}, timeout=10)
        return resp.status_code in (200, 204)
    except httpx.HTTPError:
        return False


def notify_delivered(webhook_url: str, item_name: str, tracking_number: str, location: str | None) -> bool:
    location_part = f" — last seen at {location}" if location else ""
    content = f"📦 **Delivered:** {item_name} ({tracking_number}){location_part}"
    return send_message(webhook_url, content)


def notify_out_for_delivery(
    webhook_url: str, item_name: str, tracking_number: str, location: str | None
) -> bool:
    location_part = f" — {location}" if location else ""
    content = f"🚚 **Out for delivery:** {item_name} ({tracking_number}){location_part}"
    return send_message(webhook_url, content)


def notify_exception(
    webhook_url: str, item_name: str, tracking_number: str, description: str | None
) -> bool:
    detail = f" — {description}" if description else ""
    content = f"⚠️ **Delivery problem:** {item_name} ({tracking_number}){detail}"
    return send_message(webhook_url, content)


def notify_new_package(webhook_url: str, item_name: str, tracking_number: str, carrier: str | None) -> bool:
    carrier_part = f" via {carrier}" if carrier else ""
    content = f"🆕 **New package found:** {item_name} ({tracking_number}){carrier_part}"
    return send_message(webhook_url, content)
