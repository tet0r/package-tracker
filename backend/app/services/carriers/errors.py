import httpx


class CarrierError(Exception):
    """Raised by a carrier module's get_tracking() on an actual failure
    (auth rejected, network error, unexpected response) so the pipeline can
    surface a real reason on the package. A plain `None` return from
    get_tracking() still means something different: "no data yet" — not
    an error worth showing the user."""


def describe_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return f"Authentication failed (HTTP {code}) — check the credentials in Settings"
        if code == 429:
            return "Rate limited (HTTP 429) — too many requests, will retry next cycle"
        return f"HTTP {code} from carrier API"
    if isinstance(exc, httpx.TimeoutException):
        return "Carrier API request timed out"
    return f"Network error contacting carrier API ({exc.__class__.__name__})"
