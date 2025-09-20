"""Unit tests for the tools used by the LLMS-Generator agent.

This module contains tests for the functions in `llms_gen_agent.tools`.
It uses mocking to isolate the functions from the file system and other
external dependencies.
"""

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
    directory_map = discover_files(repo_path, tool_context)

    # Assert: Verify the function returned the correct map of directories to markdown files.
    # It should include README.md and docs/guide.md, but exclude other.txt and the .git directory.
    assert directory_map == {
        "/fake/repo": ["/fake/repo/README.md"],
        "/fake/repo/docs": ["/fake/repo/docs/guide.md"],
    }
    # Assert: Verify that the resulting map was stored in the tool_context state.
    assert tool_context.state["directory_map"] == directory_map
    # Assert: Ensure os.walk was called exactly once with the specified repo path.
    mock_walk.assert_called_once_with(repo_path)


@patch("builtins.open", new_callable=mock_open)
def test_generate_llms_txt(mock_file):
    """Tests the generate_llms_txt function to ensure it writes the correct content.

    This test mocks the built-in `open` function to intercept the file-writing
    operation. It then verifies that the `llms.txt` file is written with the
    expected H1, overview, H2 sections, and formatted markdown links.
    """
    # Arrange: Set up all the necessary input data for the function.
    repo_path = "/fake/repo"
    directory_map = {
        "/fake/repo": ["/fake/repo/README.md"],
        "/fake/repo/docs": ["/fake/repo/docs/guide.md"],
    }
    project_overview = "This is a fake project."
    doc_summaries = {
        "/fake/repo/README.md": "The main README.",
        "/fake/repo/docs/guide.md": "A helpful guide.",
    }
    section_summaries = {
        "Home": "The root of the project.",
        "Docs": "All the documentation.",
    }

    # Act: Call the function to generate the llms.txt content.
    result = generate_llms_txt(
        repo_path,
        directory_map,
        project_overview,
        doc_summaries,
        section_summaries,
    )

    # Assert: Check that the llms.txt file was opened in write mode.
    mock_file.assert_called_once_with("/fake/repo/llms.txt", "w")

    # Assert: Get the handle for the mocked file to check what was written.
    handle = mock_file()

    # Assert: Verify that all expected content parts were written to the file.
    # These checks ensure the structure (H1, overview, H2s, lists) is correct.
    # The write.assert_any_call() method checks if the write method on the handle object 
    # was ever called with the exact string provided as an argument.
    handle.write.assert_any_call("# repo Sitemap\n\n")
    handle.write.assert_any_call("This is a fake project.\n\n")
    handle.write.assert_any_call("## Docs\n\n")
    handle.write.assert_any_call("All the documentation.\n\n")
    handle.write.assert_any_call(
        "- [guide.md](https://github.com/fake/repo/blob/main/docs/guide.md): A helpful guide.\n"
    )
    handle.write.assert_any_call("\n")
    handle.write.assert_any_call("## Home\n\n")
    handle.write.assert_any_call("The root of the project.\n\n")
    handle.write.assert_any_call(
        "- [README.md](https://github.com/fake/repo/blob/main/README.md): The main README.\n"
    )

    # Assert: Check that the function returns the expected success message.
    assert result == "llms.txt file generated successfully at /fake/repo/llms.txt"
