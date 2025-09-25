"""
This module provides a shared logging utility for the application.

It offers a centralized `setup_logger` function that configures and returns a
standardized logger instance. This ensures consistent logging behavior,
formatting, and level across the entire application.

To use the logger in any module, import the `setup_logger` function and call it with a name, 
typically `__name__`, to get a logger instance specific to that module.

Example:
    ```
    from common_utils.logging_utils import setup_logger

    logger = setup_logger(__name__)
    ```

In this application we setup up the logger in `config.py`, and then expose that logger
to other modules. E.g.
    ```
    from llms_gen_agent.config import get_config, logger
    ```
"""

import logging
import os


def setup_logger(app_name: str) -> logging.Logger:
    # Suppress verbose logging from ADK and GenAI libraries - INFO logging is quite verbose
    logging.getLogger("google_adk").setLevel(logging.ERROR)
    logging.getLogger("google_genai").setLevel(logging.ERROR)
    
    # Suppress "Unclosed client session" warnings from aiohttp
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)

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
