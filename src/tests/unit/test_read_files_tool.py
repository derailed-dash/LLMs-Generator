"""
Unit tests for the tools in the `doc_summariser` sub-agent.

This module contains tests for the `read_files` function in the
`llms_gen_agent.sub_agents.doc_summariser.tools` module. It uses mocking to
isolate the function from the file system and configuration dependencies.
"""

from unittest.mock import MagicMock, mock_open, patch

from llms_gen_agent.sub_agents.doc_summariser.tools import read_files


def test_read_files_success():
    """Tests that read_files successfully reads a list of files."""
    # Arrange: Set up a mock ToolContext with a list of files to be read.
    tool_context = MagicMock()
    tool_context.state = {"files": ["/fake/file1.txt", "/fake/file2.txt"]}
    # Arrange: Mock the 'open' function to simulate reading file content.
    m = mock_open(read_data="file content")
    with patch("builtins.open", m):
        # Act: Call the function under test.
        result = read_files(tool_context)

    # Assert: Verify that the function returns a success status.
    assert result == {"status": "success"}
    # Assert: Check that the file content was correctly stored in the tool context.
    assert tool_context.state["files_content"] == {
        "/fake/file1.txt": "file content",
        "/fake/file2.txt": "file content",
    }
    # Assert: Ensure that 'open' was called for each file.
    assert m.call_count == 2


def test_read_files_file_not_found():
    """Tests that read_files gracefully handles a FileNotFoundError."""
    # Arrange: Set up a mock ToolContext with a non-existent file.
    tool_context = MagicMock()
    tool_context.state = {"files": ["/fake/non_existent_file.txt"]}
    # Arrange: Mock the 'open' function to raise a FileNotFoundError.
    with patch("builtins.open", mock_open()) as m:
        m.side_effect = FileNotFoundError
        # Act: Call the function under test.
        result = read_files(tool_context)

    # Assert: Verify that the function returns a 'warnings' status.
    assert result == {"status": "warnings"}
    # Assert: Check that an appropriate error message was stored in the tool context.
    assert "Error: Could not read file" in tool_context.state["files_content"]["/fake/non_existent_file.txt"]


def test_read_files_permission_error():
    """Tests that read_files gracefully handles a PermissionError."""
    # Arrange: Set up a mock ToolContext with a file that has permission issues.
    tool_context = MagicMock()
    tool_context.state = {"files": ["/fake/permission_denied.txt"]}
    # Arrange: Mock the 'open' function to raise a PermissionError.
    with patch("builtins.open", mock_open()) as m:
        m.side_effect = PermissionError
        # Act: Call the function under test.
        result = read_files(tool_context)

    # Assert: Verify that the function returns a 'warnings' status.
    assert result == {"status": "warnings"}
    # Assert: Check that an appropriate error message was stored in the tool context.
    assert "Error: Could not read file" in tool_context.state["files_content"]["/fake/permission_denied.txt"]


def test_read_files_unicode_decode_error():
    """Tests that read_files gracefully handles a UnicodeDecodeError."""
    # Arrange: Set up a mock ToolContext with a file that has encoding issues.
    tool_context = MagicMock()
    tool_context.state = {"files": ["/fake/bad_encoding.txt"]}
    # Arrange: Mock the 'open' function to raise a UnicodeDecodeError.
    with patch("builtins.open", mock_open()) as m:
        m.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "reason")
        # Act: Call the function under test.
        result = read_files(tool_context)

    # Assert: Verify that the function returns a 'warnings' status.
    assert result == {"status": "warnings"}
    # Assert: Check that an appropriate error message was stored in the tool context.
    assert "Error: Could not read file" in tool_context.state["files_content"]["/fake/bad_encoding.txt"]

