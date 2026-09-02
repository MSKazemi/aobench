"""HTTP Basic Auth helper for the AOBench leaderboard admin endpoints."""

import base64
import hmac
import os

from aobench.utils.logging import get_logger

logger = get_logger(__name__)

_ADMIN_USERNAME = "admin"
_PASSWORD_ENV = "LEADERBOARD_ADMIN_PASSWORD"


def check_basic_auth(authorization_header: str | None) -> bool:
    """Return True if the Authorization header carries valid admin credentials.

    Expects ``Basic <base64(username:password)>``. The accepted password is read
    from ``LEADERBOARD_ADMIN_PASSWORD``.

    **There is no default password.** When the variable is unset or empty every
    request is rejected, and the admin endpoints are unreachable. This helper
    guards ``POST /admin/rebuild``, which rewrites every CLEAR score, so a
    built-in fallback credential would mean any deployment that forgot to
    configure one shipped with a publicly known password.

    Comparisons are constant-time: a plain ``==`` leaks how much of the secret
    matched through its timing.
    """
    expected_pw = os.environ.get(_PASSWORD_ENV, "")
    if not expected_pw:
        logger.warning(
            "%s is not set — leaderboard admin endpoints are disabled. "
            "Set it to enable them.",
            _PASSWORD_ENV,
        )
        return False

    if not authorization_header or not authorization_header.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(authorization_header[6:], validate=True).decode()
        username, password = decoded.split(":", 1)
    except Exception:
        # Malformed header — deny, and do not distinguish the failure mode.
        return False

    user_ok = hmac.compare_digest(username, _ADMIN_USERNAME)
    pw_ok = hmac.compare_digest(password, expected_pw)
    return user_ok and pw_ok
