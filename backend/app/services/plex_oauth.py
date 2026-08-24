from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

_PIN_TTL = timedelta(minutes=15)

_lock = threading.Lock()
_pending: dict[str, tuple[MyPlexPinLogin, datetime]] = {}


def _evict_expired() -> None:
    now = datetime.now(timezone.utc)
    expired = [
        pid for pid, (_, created_at) in _pending.items() if now - created_at > _PIN_TTL
    ]
    for pid in expired:
        del _pending[pid]


def create_pin() -> dict[str, Any]:
    # plexapi declares py.typed but leaves these methods unannotated, so mypy
    # strict can't type-check the calls (see PlexService for the same issue).
    pinlogin = MyPlexPinLogin(oauth=True)  # type: ignore[no-untyped-call]
    oauth_url = pinlogin.oauthUrl()  # type: ignore[no-untyped-call]
    pin_id = str(pinlogin._id)

    with _lock:
        _evict_expired()
        _pending[pin_id] = (pinlogin, datetime.now(timezone.utc))

    return {"id": pin_id, "oauth_url": oauth_url}


def check_pin(pin_id: str) -> dict[str, Any]:
    with _lock:
        entry = _pending.get(pin_id)
        if entry is None:
            raise KeyError(pin_id)
        pinlogin, _ = entry

    if not pinlogin.checkLogin():  # type: ignore[no-untyped-call]
        return {"authenticated": False}

    with _lock:
        _pending.pop(pin_id, None)

    return {"authenticated": True, "token": pinlogin.token}


def list_servers(token: str) -> list[dict[str, Any]]:
    account = MyPlexAccount(token=token)  # type: ignore[no-untyped-call]
    servers = []
    for resource in account.resources():  # type: ignore[no-untyped-call]
        if "server" not in (resource.provides or ""):
            continue
        connections = [
            {"uri": conn.uri, "local": conn.local} for conn in resource.connections
        ]
        if connections:
            servers.append({"name": resource.name, "connections": connections})
    return servers
