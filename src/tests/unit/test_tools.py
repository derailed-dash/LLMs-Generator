"""Unit tests for the tools used by the LLMS-Generator agent.

This module contains tests for the functions in `llms_gen_agent.tools`.
It uses mocking to isolate the functions from the file system and other
external dependencies.
"""

import os
from unittest.mock import MagicMock, mock_open, patch

from llms_gen_agent.tools import (
    _get_repo_details,
    discover_files,
    generate_llms_txt,
)


def test_get_repo_details():
    """Tests the _get_repo_details function for a standard repo path."""
    # Act: Call the function with a standard path
    owner, repo_name = _get_repo_details("/path/to/owner/repo_name")
    # Assert: Check if the owner and repo name are extracted correctly
    assert owner == "owner"
    assert repo_name == "repo_name"


def test_get_repo_details_with_trailing_slash():
    """Tests the _get_repo_details function to ensure it handles trailing slashes."""
    # Act: Call the function with a path that includes a trailing slash
    owner, repo_name = _get_repo_details("/path/to/owner/repo_name/")
    # Assert: Check if the owner and repo name are extracted correctly
    assert owner == "owner"
    assert repo_name == "repo_name"


@patch("os.walk")
def test_discover_files(mock_walk):
    """Tests the discover_files function to ensure it correctly maps a directory structure.

    This test mocks `os.walk` to simulate a file system structure and verifies
    that the function correctly identifies markdown files while ignoring non-relevant
    files and directories like `.git`.
    """
    # Arrange: Set up the mock for os.walk to return a predefined directory structure.
    # This simulates a repository with a root README, a 'docs' folder, and a '.git' folder.
    repo_path = "/fake/repo"
    mock_walk.return_value = [
        ("/fake/repo", ["docs", ".git"], ["README.md"]),
        ("/fake/repo/docs", [], ["guide.md", "other.txt"]),
    ]
    # Arrange: Mock the tool_context object which is used to pass state between tools.
    tool_context = MagicMock()
    tool_context.state = {}

    # Act: Call the function to discover files in the mocked repository path.
    result = discover_files(repo_path, tool_context)

    # Assert: Verify the function returned the correct map of directories to markdown files.
    # It should include README.md and docs/guide.md, but exclude other.txt and the .git directory.
    expected_files = ["/fake/repo/README.md", "/fake/repo/docs/guide.md"]
    assert result == {"status": "success", "files": expected_files}
    # Assert: Verify that the resulting map was stored in the tool_context state.
    assert tool_context.state["files"] == expected_files
    assert tool_context.state["dirs"] == ["/fake/repo", "/fake/repo/docs"]
    # Assert: Ensure os.walk was called exactly once with the specified repo path.
    mock_walk.assert_called_once_with(repo_path)


@patch("builtins.open", new_callable=mock_open, read_data='[remote "origin"]\nurl = https://github.com/owner/repo_name.git')
@patch("os.getcwd", return_value="/fake/cwd")
@patch("os.makedirs")
@patch("os.path.exists", return_value=True) # Simulate .git/config file exists
def test_generate_llms_txt_github_repo(mock_exists, mock_makedirs, mock_getcwd, mock_file):
    """Tests the generate_llms_txt function for a GitHub-like repository.

    It verifies that the `llms.txt` file is written with GitHub URLs.
    """
    # Arrange: Set up all the necessary input data for the function.
    repo_path = "/fake/owner/repo_name"
    doc_summaries = {
        "project": "Placeholder for overview",
        "/fake/owner/repo_name/README.md": "The main README.",
        "/fake/owner/repo_name/docs/guide.md": "A helpful guide.",
        "/fake/owner/repo_name/docs/api/index.md": "API documentation index.",
        "/fake/owner/repo_name/docs/api/v1/intro.md": "Introduction to API v1.",
    }

    tool_context = MagicMock()
    tool_context.state = {
        "dirs": [
            "/fake/owner/repo_name",
            "/fake/owner/repo_name/docs",
            "/fake/owner/repo_name/docs/api",
            "/fake/owner/repo_name/docs/api/v1",
        ],
        "files": [
            "/fake/owner/repo_name/README.md",
            "/fake/owner/repo_name/docs/guide.md",
            "/fake/owner/repo_name/docs/new_file.md", # New file without summary
            "/fake/owner/repo_name/docs/api/index.md",
            "/fake/owner/repo_name/docs/api/v1/intro.md",
        ],
        "doc_summaries": {"summaries": doc_summaries},
    }
    # Act: Call the function to generate the llms.txt content.
    result = generate_llms_txt(
        repo_path,
        tool_context,
    )

    # Assert: Check that the llms.txt file was opened in write mode.
    expected_llms_txt_path = "/fake/cwd/temp/llms.txt"
    mock_file.assert_any_call(expected_llms_txt_path, "w")
    mock_getcwd.assert_called_once()
    mock_makedirs.assert_called_once_with("/fake/cwd/temp", exist_ok=True)
    mock_exists.assert_called_once_with(os.path.join(repo_path, ".git", "config"))

    # Assert: Get the handle for the mocked file to check what was written.
    handle = mock_file()

    # Assert: Capture all calls to write and join them to form the complete written content.
    written_content = "".join([call.args[0] for call in handle.write.call_args_list])

    # Assert: Define the expected content based on the generate_llms_txt logic.
    expected_content = (
        "# repo_name Sitemap\n\n"
        "Placeholder for overview\n\n"
        "## Home\n\n"
        "- [README.md](https://github.com/owner/repo_name/blob/main/README.md): The main README.\n"
        "\n"  # Newline after the file list for Home section
        "## Docs\n\n"
        "- [guide.md](https://github.com/owner/repo_name/blob/main/docs/guide.md): A helpful guide.\n"
        "- [new_file.md](https://github.com/owner/repo_name/blob/main/docs/new_file.md): No summary\n"
        "\n"  # Newline after the file list for Docs section
        "## Docs Api\n\n"
        "- [index.md](https://github.com/owner/repo_name/blob/main/docs/api/index.md): API documentation index.\n"
        "- [intro.md](https://github.com/owner/repo_name/blob/main/docs/api/v1/intro.md): Introduction to API v1.\n"
        "\n"
    )

    # Assert: Verify that the captured content matches the expected content.
    assert written_content == expected_content

    # Assert: Check that the function returns the expected success message.
    assert result == {"status": "success", "llms_txt_path": expected_llms_txt_path}


@patch("builtins.open", new_callable=mock_open)
@patch("os.getcwd", return_value="/fake/cwd")
@patch("os.makedirs")
@patch("os.path.exists", return_value=False) # Simulate .git directory does not exist
def test_generate_llms_txt_local_repo(mock_exists, mock_makedirs, mock_getcwd, mock_file):
    """Tests the generate_llms_txt function for a local repository.

    It verifies that the `llms.txt` file is written with relative paths.
    """
    # Arrange: Set up all the necessary input data for the function.
    repo_path = "/fake/local_repo"
    doc_summaries = {
        "project": "Placeholder for overview",
        "/fake/local_repo/README.md": "The main README.",
        "/fake/local_repo/docs/guide.md": "A helpful guide.",
        "/fake/local_repo/docs/api/index.md": "API documentation index.",
        "/fake/local_repo/docs/api/v1/intro.md": "Introduction to API v1.",
    }

    tool_context = MagicMock()
    tool_context.state = {
        "dirs": [
            "/fake/local_repo",
            "/fake/local_repo/docs",
            "/fake/local_repo/docs/api",
            "/fake/local_repo/docs/api/v1",
        ],
        "files": [
            "/fake/local_repo/README.md",
            "/fake/local_repo/docs/guide.md",
            "/fake/local_repo/docs/new_file.md", # New file without summary
            "/fake/local_repo/docs/api/index.md",
            "/fake/local_repo/docs/api/v1/intro.md",
        ],
        "doc_summaries": {"summaries": doc_summaries},
    }
    # Act: Call the function to generate the llms.txt content.
    result = generate_llms_txt(
        repo_path,
        tool_context,
    )

    # Assert: Check that the llms.txt file was opened in write mode.
    expected_llms_txt_path = "/fake/cwd/temp/llms.txt"
    mock_file.assert_called_once_with(expected_llms_txt_path, "w")
    mock_getcwd.assert_called_once()
    mock_makedirs.assert_called_once_with("/fake/cwd/temp", exist_ok=True)
    mock_exists.assert_called_once_with(os.path.join(repo_path, ".git", "config"))

    # Assert: Get the handle for the mocked file to check what was written.
    handle = mock_file()

    # Assert: Capture all calls to write and join them to form the complete written content.
    written_content = "".join([call.args[0] for call in handle.write.call_args_list])

    # Assert: Define the expected content based on the generate_llms_txt logic.
    expected_content = (
        "# local_repo Sitemap\n\n"
        "Placeholder for overview\n\n"
        "## Home\n\n"
        "- [README.md](README.md): The main README.\n"
        "\n"  # Newline after the file list for Home section
        "## Docs\n\n"
        "- [guide.md](docs/guide.md): A helpful guide.\n"
        "- [new_file.md](docs/new_file.md): No summary\n"
        "\n"  # Newline after the file list for Docs section
        "## Docs Api\n\n"
        "- [index.md](docs/api/index.md): API documentation index.\n"
        "- [intro.md](docs/api/v1/intro.md): Introduction to API v1.\n"
        "\n"
    )

    # Assert: Verify that the captured content matches the expected content.
    assert written_content == expected_content

    # Assert: Check that the function returns the expected success message.
    assert result == {"status": "success", "llms_txt_path": expected_llms_txt_path}
