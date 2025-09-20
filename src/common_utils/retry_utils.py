"""Provide a retry decorator for handling transient errors."""

import logging
from functools import wraps

from google.api_core.exceptions import ResourceExhausted
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

def async_retry_with_exponential_backoff(f):
    """
    A decorator for async functions to retry with exponential backoff on ResourceExhausted errors.
    """
    @wraps(f)
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(ResourceExhausted),
        reraise=True,
    )
    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except ResourceExhausted as e:
            logger.warning(f"ResourceExhausted error encountered, retrying...: {e}")
            raise
    return wrapper
