"""HTTP Basic Auth helper for the AOBench leaderboard admin endpoints."""

import base64
import os


def check_basic_auth(authorization_header: str | None) -> bool:
    """Return True if the Authorization header is valid.

    Expects the header in the form ``Basic <base64(username:password)>``.
    The accepted password is read from the ``LEADERBOARD_ADMIN_PASSWORD``
    environment variable (default: ``"changeme"``).
    """
    if not authorization_header:
        return False
    if not authorization_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization_header[6:]).decode()
        username, password = decoded.split(":", 1)
        expected_pw = os.environ.get("LEADERBOARD_ADMIN_PASSWORD", "changeme")
        return username == "admin" and password == expected_pw
    except Exception:
        return False
