from sqlalchemy.orm import Session

from . import amazon, dhl, fedex, ups, usps

_MODULES = {
    "UPS": ups,
    "FedEx": fedex,
    "USPS": usps,
    "DHL": dhl,
    "Amazon": amazon,
}


def get_tracking(db: Session, carrier: str, tracking_number: str) -> dict | None:
    module = _MODULES.get(carrier)
    if module is None:
        return None
    return module.get_tracking(db, tracking_number)


def is_configured(db: Session, carrier: str) -> bool:
    module = _MODULES.get(carrier)
    if module is None:
        return False
    return module.is_configured(db)


def test_credentials(db: Session, carrier: str) -> dict:
    module = _MODULES.get(carrier)
    if module is None:
        return {"ok": False, "error": f"Unknown carrier {carrier}"}
    return module.test_credentials(db)
