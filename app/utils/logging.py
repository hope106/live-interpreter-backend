from __future__ import annotations

import logging
import os
from typing import Optional, Union

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def _resolve_level(level: Union[int, str]) -> int:
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return level


def get_logger(name: str, level: Optional[Union[int, str]] = None) -> logging.Logger:
    """Return a logger configured to always emit console output at the given level."""
    logger = logging.getLogger(name)
    resolved_level = _resolve_level(level or _DEFAULT_LEVEL)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        handler.setLevel(resolved_level)
        logger.addHandler(handler)
    logger.setLevel(resolved_level)
    return logger
