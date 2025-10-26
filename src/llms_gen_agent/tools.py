"""
This module provides a collection of tools for the LLMS-Generator agent.

These tools are designed to facilitate various operations within the LLMS-Generator workflow,
including file discovery, batch processing, and the final generation of the `llms.txt` sitemap file.

Key functionalities include:
- `create_file_batches`: Splits a list of file paths into smaller, manageable batches for processing.
- `discover_files`: Scans a repository to find relevant files (e.g., markdown and Python files),
  excluding common temporary or Git-related directories.
- `generate_llms_txt`: Constructs the `llms.txt` Markdown file, organizing
  discovered files into sections with their generated summaries and a project-level summary.
"""
import configparser
import os
import re
import math
from typing import List

import pathspec
from google.adk.tools import ToolContext

from .config import logger, setup_config


def _get_repo_details(repo_path: str) -> tuple[str, str]:
    """Extracts owner and repo name from the path."""
    path_parts = repo_path.strip(os.sep).split(os.sep)
    owner = path_parts[-2] if len(path_parts) > 1 else ""
    repo_name = path_parts[-1]
    return owner, repo_name

def _get_gitignore(repo_path: str) -> pathspec.PathSpec:
    """Reads the .gitignore file and returns a PathSpec object."""
    gitignore_path = os.path.join(repo_path, ".gitignore")
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path) as f:
            patterns = f.read().splitlines()
    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)


def create_file_batches(tool_context: ToolContext, batch_size: int = 10) -> List[List[str]]:
    """Splits a list of file paths into batches of a specified size.
    
    This tool retrieves the list of all discovered files from the session state,
    divides them into smaller batches, and stores these batches back into the
    session state for iterative processing by the LoopAgent.
    """
    file_paths = tool_context.state.get("files", [])
    logger.debug(f"create_file_batches: Received {len(file_paths)} files from session state.")
    logger.debug(f"Creating batches for {len(file_paths)} files with batch size {batch_size}")
    if not file_paths:
        logger.debug("No files to batch.")
        tool_context.state["batches"] = [] # Ensure batches is set even if empty
        return []
    num_batches = math.ceil(len(file_paths) / batch_size)
    batches = [file_paths[i * batch_size:(i + 1) * batch_size] for i in range(num_batches)]
    logger.debug(f"Created {len(batches)} batches.")
    tool_context.state["batches"] = batches # Store batches in session state
    return batches


def discover_files(repo_path: str, tool_context: ToolContext) -> dict:
    """Discovers all relevant files in the repository and stores their paths in the session state.

    This tool scans the specified repository, identifies files relevant for summarization
    (based on configured extensions), and excludes directories and files specified in
    `.env` and `.gitignore`. The discovered file paths are stored in `tool_context.state["files"]`.

    Args:
        repo_path: The absolute path to the repository to scan.

    Returns:
        A dictionary with "status" (success/failure) and "files" (a list of file paths).
    """
    logger.debug("Entering tool: discover_files with repo_path: %s", repo_path)
    config = setup_config()
    gitignore_spec = _get_gitignore(repo_path)

    directory_map: dict[str, list[str]] = {}
    try:
        for root, subdirs, files in os.walk(repo_path):
            # Exclude directories based on gitignore and config
            excluded_by_gitignore = set(gitignore_spec.match_files([os.path.join(root, d) for d in subdirs]))
            subdirs[:] = [d for d in subdirs if d not in config.excluded_dirs 
                                and os.path.join(root, d) not in excluded_by_gitignore]

            for file in files:
                file_path = os.path.join(root, file)
                if not gitignore_spec.match_file(file_path) and \
                   (any(file.endswith(ext) for ext in config.included_extensions) and \
                    not any(file.startswith(ext) for ext in config.excluded_files)):
                    directory = os.path.dirname(file_path)
                    if directory not in directory_map:
                        directory_map[directory] = []
                    directory_map[directory].append(file_path)

        all_dirs = list(directory_map.keys())
        tool_context.state["dirs"] = all_dirs # directories only
        logger.debug("Dirs\n:" + "\n".join([str(dir) for dir in all_dirs]))

        # Create a single list of all the files
        all_files = [file for files_list in directory_map.values() for file in files_list]
        tool_context.state["files"] = all_files
        logger.debug("Files\n:" + "\n".join([str(file) for file in all_files]))
        logger.debug("Exiting discover_files.")
        return {"status": "success", "files": all_files}
    except Exception as e:
        logger.error("Error in discover_files: %s", e)
        return {"status": "failure", "files": []}

def _get_remote_url_from_git_config(git_config_path: str) -> str | None:
    """Parses the git config to find the remote origin URL."""
    if not os.path.exists(git_config_path):
        return None

    config = configparser.ConfigParser()
    try:
        config.read(git_config_path)
        remote_url = config.get('remote "origin"', 'url')
        # Convert SSH URL to HTTPS URL
        if remote_url.startswith("git@"):
            remote_url = re.sub(r'^git@([^:]+):', r'https://\1/', remote_url)
        if remote_url.endswith(".git"):
            remote_url = remote_url[:-4]
        return remote_url
    except (configparser.NoSectionError, configparser.NoOptionError):
        return None

def _get_llms_txt_base_url(repo_path: str) -> str:
    """Determines the base URL (GitHub or empty for local) for links."""
    git_config_path = os.path.join(repo_path, ".git", "config")
    remote_url = _get_remote_url_from_git_config(git_config_path)

    if remote_url:
        return f"{remote_url}/blob/main/"
    else:
        return "" # Use relative paths if not a GitHub repo or .git not found


def _map_files_to_effective_sections(all_files: list[str], repo_path: str, max_depth: int) -> dict[str, str]:
    """Maps each file to its effective section directory based on a maximum depth.

    This function determines which directory a file should be associated with for the purpose of 
    generating sections in the llms.txt file. If a file's parent directory is deeper than `max_depth`, 
    the file is mapped to its closest ancestor directory that is within the `max_depth` limit.
    Files directly in the root are mapped to the root directory itself.

    Args:
        all_files: A list of absolute paths to all discovered files in the repository.
        repo_path: The absolute path to the root of the repository.
        max_depth: The maximum section depth allowed (e.g., 2 for two levels deep from the root, excluding the root itself).

    Returns:
        A dictionary where keys are absolute file paths and values are the absolute paths 
        of their effective section directories.
    """
    file_to_effective_section_dir = {}
    for file_path in all_files:
        relative_file_path = os.path.relpath(file_path, repo_path)
        relative_dir_path = os.path.dirname(relative_file_path)

        if relative_dir_path == "": # File is directly in the root
            effective_section_relative_path = "."
        else:
            path_parts = relative_dir_path.split(os.sep)
            effective_section_relative_parts = []
            for i, part in enumerate(path_parts):
                if i < max_depth:
                    effective_section_relative_parts.append(part)
                else:
                    break
            effective_section_relative_path = os.path.join(*effective_section_relative_parts)

        if effective_section_relative_path == ".":
            effective_section_absolute_path = repo_path
        else:
            effective_section_absolute_path = os.path.join(repo_path, effective_section_relative_path)
            
        file_to_effective_section_dir[file_path] = effective_section_absolute_path
    return file_to_effective_section_dir

def _write_llms_txt_section(f, directory: str, 
                            repo_path: str, 
                            files: list[str], 
                            file_to_effective_section_dir: dict[str, str], 
                            doc_summaries: dict[str, str], 
                            base_url: str):
    """Writes a single section (header and file list) to the llms.txt file."""
    
    section_name = (
        os.path.relpath(directory, repo_path)
        .replace("/", " ")
        .strip()
        .title()
    )
    if section_name == ".":
        section_name = "Home"

    f.write(f"## {section_name}\n\n")

    section_files_to_write = []
    for file_path in files:
        if file_to_effective_section_dir.get(file_path) == directory:
            summary = doc_summaries.get(file_path, "No summary")
            section_files_to_write.append((file_path, summary))

    logger.debug(f"Writing section: {section_name}")

    for file_path, summary in sorted(section_files_to_write):
        link_text = os.path.basename(file_path)
        relative_path = os.path.relpath(file_path, repo_path)
        f.write(f"- [{link_text}]({base_url}{relative_path}): {summary}\n")
    f.write("\n")

def generate_llms_txt(repo_path: str, tool_context: ToolContext, output_path: str = "") -> dict:
    """Generates a comprehensive llms.txt sitemap file for a given repository.

    This tool orchestrates the creation of an AI/LLM-friendly Markdown file (`llms.txt`)
    that provides a structured overview of the repository's contents. It retrieves
    the project summary and individual file summaries from the session state,
    organizes files into sections based on their directory structure, and
    generates Markdown links with their respective summaries.

    Args:
        repo_path: The absolute path to the root of the repository to scan.
        output_path: Optional. The absolute path to save the llms.txt file.
                     If not provided, it will be saved in a `temp` directory in the current working directory.

    Other required data (summaries, file lists) is retrieved from tool_context.state.

    Returns:
        A dictionary with:
        - "status": "success" if the file was generated successfully.
        - "llms_txt_path": The absolute path to the generated llms.txt file.
    """
    logger.debug("Entering generate_llms_txt for repo_path: %s", repo_path)
    dirs = tool_context.state.get("dirs", [])
    files = tool_context.state.get("files", [])
    doc_summaries_full = tool_context.state.get("doc_summaries", {})
    logger.debug(f"doc_summaries_full (raw from agent) type: {type(doc_summaries_full)}")
    
    doc_summaries = doc_summaries_full.get("summaries", {}) # remember, it has one top-level key called `summaries`
    project_summary = doc_summaries.pop("project", None)

    logger.debug("We have %d directories.", len(dirs))
    logger.debug("We have %d files", len(files))
    logger.debug("We have %d summaries (after popping project)", len(doc_summaries))
    logger.debug("Project summary: %s", project_summary[:100] if project_summary else "None")

    # If an output path has been specified...
    if output_path and output_path.strip():
        llms_txt_path = output_path
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    else: # Use default path - temp in the current working dir
        temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        llms_txt_path = os.path.join(temp_dir, "llms.txt")

    MAX_SECTION_DEPTH = 2 # Max two levels deep, not including the root
    repo_name = _get_repo_details(repo_path)[1]
    base_url = _get_llms_txt_base_url(repo_path)

    file_to_effective_section_dir = _map_files_to_effective_sections(files, repo_path, MAX_SECTION_DEPTH)
    
    # Collect all unique effective section directories
    effective_section_dirs = sorted(set(file_to_effective_section_dir.values()))

    with open(llms_txt_path, "w") as f:
        f.write(f"# {repo_name} Sitemap\n\n")
        f.write(f"{project_summary}\n\n" if project_summary else "No project summary found\n\n")

        for directory in effective_section_dirs:
            _write_llms_txt_section(f, directory, repo_path, files, file_to_effective_section_dir, doc_summaries, base_url)

    logger.debug("llms.txt generated at %s", llms_txt_path)
    tool_context.state["llms_txt_path"] = llms_txt_path
    return {"status": "success", "llms_txt_path": llms_txt_path}
