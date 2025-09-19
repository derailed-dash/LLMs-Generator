"""Shared logging utility."""

import logging
import os


def setup_logger(app_name: str) -> logging.Logger:
    """Sets up and a logger for the application."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    app_logger = logging.getLogger(app_name)
    log_level_num = getattr(logging, log_level, logging.INFO)
    app_logger.setLevel(log_level_num)

    # Add a handler only if one doesn't exist to prevent duplicate logs
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d:%(name)s - %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)

    app_logger.propagate = False  # Prevent propagation to the root logger
    app_logger.info("Logger initialised for %s.", app_name)
    app_logger.debug("DEBUG level logging enabled.")

    return app_logger
