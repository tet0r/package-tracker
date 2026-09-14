import re

_UPS = re.compile(r"\b1Z[0-9A-Z]{16}\b")
_USPS_LONG = re.compile(r"\b(94|93|92|82|03|70|23)\d{18,20}\b")
_FEDEX_15 = re.compile(r"\b\d{15}\b")
_FEDEX_12 = re.compile(r"\b\d{12}\b")
_DHL = re.compile(r"\b\d{10}\b")

_TRACKING_KEYWORD = re.compile(r"track", re.IGNORECASE)

_SUBJECT_NOISE = [
    r"^(re|fwd):\s*",
    r"^your order (has )?shipped:?\s*",
    r"^shipped:?\s*",
    r"^your package (is )?on (its|the) way:?\s*",
    r"^tracking (info|information|number)s? for:?\s*",
    r"^order confirmation:?\s*",
    r"^out for delivery:?\s*",
    r"^delivered:?\s*",
    r"^shipment (notification|update):?\s*",
]


def _has_context(text: str, match: re.Match, window: int = 200) -> bool:
    """Generic digit-only patterns (FedEx/DHL) are ambiguous with phone numbers,
    order numbers, etc, so only trust them near the word "track"."""
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return bool(_TRACKING_KEYWORD.search(text[start:end]))


def extract_tracking_numbers(text: str) -> list[tuple[str, str]]:
    found: dict[str, str] = {}

    for m in _UPS.finditer(text):
        found.setdefault(m.group(), "UPS")

    for m in _USPS_LONG.finditer(text):
        found.setdefault(m.group(), "USPS")

    for m in _FEDEX_15.finditer(text):
        if m.group() not in found and _has_context(text, m):
            found[m.group()] = "FedEx"

    for m in _FEDEX_12.finditer(text):
        if m.group() not in found and _has_context(text, m):
            found[m.group()] = "FedEx"

    for m in _DHL.finditer(text):
        if m.group() not in found and _has_context(text, m):
            found[m.group()] = "DHL"

    return [(carrier, number) for number, carrier in found.items()]


def clean_item_name(subject: str) -> str:
    cleaned = (subject or "").strip()
    for pattern in _SUBJECT_NOISE:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or subject.strip() or "Unnamed package"
