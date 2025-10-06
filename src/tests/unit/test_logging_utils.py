"""Unit tests for the `logging_utils` module.

This module contains tests for the `setup_logger` function, ensuring that it
correctly configures the logger based on environment variables and sets the
appropriate handlers and propagation flags.
"""

import logging
import os
from unittest.mock import patch

from common_utils.logging_utils import setup_logger


def test_setup_logger_default_level():
    """Tests that the logger is set up with the default INFO level when no environment variable is set."""
    # Arrange: Clear environment variables to ensure the default is used.
    with patch.dict(os.environ, {}, clear=True):
        # Act: Set up the logger.
        logger = setup_logger("test_app")
        # Assert: Verify that the logger's level is INFO.
        assert logger.level == logging.INFO


def test_setup_logger_with_env_var():
    """Tests that the logger level is correctly set from the LOG_LEVEL environment variable."""
    # Arrange: Set the LOG_LEVEL environment variable to DEBUG.
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
        # Act: Set up the logger.
        logger = setup_logger("test_app_debug")
        # Assert: Verify that the logger's level is DEBUG.
        assert logger.level == logging.DEBUG

def test_setup_logger_propagates_false():
    """Tests that the logger's propagate attribute is set to False to prevent duplicate logging."""
    # Act: Set up the logger.
    logger = setup_logger("test_app_propagate")
    # Assert: Verify that the propagate attribute is False.
    assert not logger.propagate

def test_setup_logger_has_handler():
    """Tests that the logger has a stream handler after setup."""
    # Act: Set up the logger.
    logger = setup_logger("test_app_handler")
    # Assert: Verify that the logger has at least one handler.
    assert logger.hasHandlers()
