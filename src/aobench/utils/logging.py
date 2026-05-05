"""Structured logging utilities for AOBench.

Usage in any module::

    from aobench.utils.logging import get_logger
    logger = get_logger(__name__)
    logger.debug("tool called: %s", tool_name)

Call ``configure_logging()`` once at CLI entry points to set up handlers.
When not called (e.g. in library/test usage) the root ``aobench`` logger is
a no-op by default (NullHandler), which is the recommended pattern for libraries.
"""

from __future__ import annotations

import logging
import sys

_ROOT = "aobench"

# Library default: silence unless the caller configures logging
logging.getLogger(_ROOT).addHandler(logging.NullHandler())


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``aobench`` hierarchy.

    Pass ``__name__`` from the calling module so log records carry the full
    module path (e.g. ``aobench.runners.runner``).
    """
    if not name.startswith(_ROOT):
        name = f"{_ROOT}.{name}"
    return logging.getLogger(name)


def configure_logging(level: str | int = "WARNING") -> None:
    """Configure the ``aobench`` root logger with a stderr StreamHandler.

    Intended to be called once from CLI entry points.  Safe to call multiple
    times — installs at most one StreamHandler.

    Args:
        level: Log level name (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, etc.)
               or an integer constant from the ``logging`` module.
    """
    root = logging.getLogger(_ROOT)

    # Remove the NullHandler that was added above, if still present
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.NullHandler)]

    # Avoid duplicate handlers when called more than once
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
