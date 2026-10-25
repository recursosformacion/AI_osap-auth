from __future__ import annotations

from urllib.parse import urlsplit


def is_allowed_return_url(value: str | None, origins: list[str]) -> bool:
    if not value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin in origins
