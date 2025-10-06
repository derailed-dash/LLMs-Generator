"""Unit tests for the `retry_utils` module.

This module contains tests for the `async_retry_with_exponential_backoff`
decorator, ensuring that it correctly handles function calls that succeed
immediately, fail consistently, and succeed after a few transient errors.
"""

from unittest.mock import AsyncMock

import pytest
from google.api_core.exceptions import ResourceExhausted

from common_utils.retry_utils import async_retry_with_exponential_backoff


@pytest.mark.asyncio
async def test_async_retry_success_first_time():
    """Tests that the decorator calls the decorated function only once if it succeeds on the first attempt."""
    # Arrange: Create a mock async function that returns a success value immediately.
    mock_async_func = AsyncMock(return_value="success")

    # Act: Decorate the mock function and call it.
    decorated_func = async_retry_with_exponential_backoff(mock_async_func)
    result = await decorated_func()

    # Assert: Verify that the result is correct and the function was called only once.
    assert result == "success"
    mock_async_func.assert_called_once()


@pytest.mark.asyncio
async def test_async_retry_raises_resource_exhausted():
    """Tests that the decorator retries on ResourceExhausted and eventually raises the exception after all attempts fail."""
    # Arrange: Create a mock async function that consistently raises a ResourceExhausted error.
    mock_async_func = AsyncMock(side_effect=ResourceExhausted("Too many requests"))

    # Act: Decorate the mock function.
    decorated_func = async_retry_with_exponential_backoff(mock_async_func)

    # Assert: The decorated function should raise the exception after exhausting all retry attempts.
    with pytest.raises(ResourceExhausted):
        await decorated_func()

    # Assert: Verify that the function was called the expected number of times (initial call + 4 retries = 5).
    assert mock_async_func.call_count == 5


@pytest.mark.asyncio
async def test_async_retry_succeeds_after_failures():
    """Tests that the decorator successfully returns a value after a few transient ResourceExhausted errors."""
    # Arrange: Create a mock async function that fails twice with ResourceExhausted and then succeeds.
    mock_async_func = AsyncMock(
        side_effect=[
            ResourceExhausted("Too many requests"),
            ResourceExhausted("Too many requests"),
            "success",
        ]
    )

    # Act: Decorate the mock function and call it.
    decorated_func = async_retry_with_exponential_backoff(mock_async_func)
    result = await decorated_func()

    # Assert: Verify that the final result is the success value.
    assert result == "success"
    # Assert: Verify that the function was called three times (2 failures + 1 success).
    assert mock_async_func.call_count == 3
