"""Unit tests for the `doc_summariser` agent and its callbacks.

This module contains tests for the `clean_json_callback` function used by the
`doc_summariser` agent. The tests ensure that the callback correctly handles
various LLM response formats, cleaning up markdown formatting where necessary.
"""

from unittest.mock import MagicMock

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part

from llms_gen_agent.sub_agents.doc_summariser.agent import clean_json_callback


def test_clean_json_callback_with_markdown():
    """Tests that the callback correctly removes markdown from a JSON response."""
    # Arrange: Create a mock callback context and an LLM response containing
    # a JSON string wrapped in markdown code block delimiters.
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    llm_response = LlmResponse(
        content=Content(
            parts=[
                Part(
                    text='```json\n{"key": "value"}\n```'
                )
            ]
        )
    )

    # Act: Invoke the callback with the mock context and response.
    new_response = clean_json_callback(callback_context, llm_response)

    # Assert: Verify that the markdown delimiters have been stripped, leaving only the JSON string.
    assert new_response is not None
    assert new_response.content is not None
    assert new_response.content.parts[0].text == '{"key": "value"}'


def test_clean_json_callback_no_markdown():
    """Tests that the callback returns the original response if no markdown is present."""
    # Arrange: Create a mock LLM response with a plain JSON string.
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    llm_response = LlmResponse(
        content=Content(
            parts=[
                Part(
                    text='{"key": "value"}'
                )
            ]
        )
    )

    # Act: Invoke the callback.
    new_response = clean_json_callback(callback_context, llm_response)

    # Assert: The response should be unchanged since no markdown was present.
    assert new_response is not None
    assert new_response.content is not None
    assert new_response.content.parts[0].text == '{"key": "value"}'

def test_clean_json_callback_no_content():
    """Tests that the callback handles responses with no content."""
    # Arrange: Create an LLM response with no content.
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    llm_response = LlmResponse(content=None)

    # Act: Invoke the callback.
    new_response = clean_json_callback(callback_context, llm_response)

    # Assert: The response should be returned as is, with no content.
    assert new_response is not None
    assert new_response.content is None


def test_clean_json_callback_no_text_part():
    """Tests that the callback handles responses that have content but no text part."""
    # Arrange: Create an LLM response with content that has no text part.
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    llm_response = LlmResponse(
        content=Content(
            parts=[]
        )
    )

    # Act: Invoke the callback.
    new_response = clean_json_callback(callback_context, llm_response)

    # Assert: The response should be returned as is.
    assert new_response is not None
    assert new_response.content is not None
    assert not new_response.content.parts
