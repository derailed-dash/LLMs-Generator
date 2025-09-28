"""
This module provides a collection of tools for the LLMS-Generator agent.

The tools are designed to facilitate the discovery of files within a given repository, 
read their contents, and generate a structured `llms.txt` sitemap file based on the findings.

Key functionalities include:
- `discover_files`: Scans a repository to find relevant files (e.g. markdown and python files),
  excluding common temporary or git-related directories.
- `read_files`: Reads a list of files and stores their content in the tool context.
- `generate_llms_txt`: Constructs the `llms.txt` Markdown file, organizing
  discovered files into sections with summaries.
"""
import configparser
import os

from google.adk.tools import ToolContext

from .config import logger, setup_config


def _get_repo_details(repo_path: str) -> tuple[str, str]:
    """Extracts owner and repo name from the path."""
    path_parts = repo_path.strip(os.sep).split(os.sep)
    owner = path_parts[-2] if len(path_parts) > 1 else ""
    repo_name = path_parts[-1]
    return owner, repo_name


def discover_files(repo_path: str, tool_context: ToolContext) -> dict:
    """Discovers all relevant files in the repository and returns a list of file paths.

    Args:
        repo_path: The absolute path to the repository to scan.

    Returns:
        A dictionary with "status" (success/failure) and "files" (a list of file paths).
    """
    logger.debug("Entering tool: discover_files with repo_path: %s", repo_path)

    excluded_dirs = {'.git', '.github', 'overrides', '.venv', 'node_modules', '__pycache__', '.pytest_cache'}
    excluded_files = {'__init__'}
    included_extensions = {'.md', '.py'}

    directory_map: dict[str, list[str]] = {}
    try:
        for root, subdirs, files in os.walk(repo_path):
            
            # Modify subdirs in place so that os.walk() sees changes directly
            subdirs[:] = [d for d in subdirs if d not in excluded_dirs]
            for file in files:
                if (any(file.endswith(ext) for ext in included_extensions) 
                        and not any(file.startswith(ext) for ext in excluded_files)):
                    file_path = os.path.join(root, file)
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

def read_files(tool_context: ToolContext) -> dict:
    """Reads the content of files and stores it in the tool context.

    This function retrieves a list of file paths from the `files` key in the
    `tool_context.state`. It then iterates through this list, reads the
    content of each file, and stores it in a dictionary under the

    `files_content` key in the `tool_context.state`. The file path serves as
    the key for its content.

    It avoids re-reading files by checking if the file path already exists
    in the `files_content` dictionary.

    Returns:
        A dictionary with a "status" key indicating the outcome ("success").
    """
    logger.debug("Executing read_files")
    config = setup_config() # dynamically load config
    
    file_paths = tool_context.state.get("files", [])
    logger.debug(f"Got {len(file_paths)} files")

    # Implement max files constraint
    if config.max_files_to_process > 0:
        logger.info(f"Limiting to {config.max_files_to_process} files")
        file_paths = file_paths[:config.max_files_to_process]

    # Initialise our session state key    
    tool_context.state["files_content"] = {}
    
    response = {"status": "success"}
    for file_path in file_paths:
        if file_path not in tool_context.state["files_content"]:
            try:
                logger.debug(f"Reading file: {file_path}")
                with open(file_path) as f:
                    content = f.read()
                    logger.debug(f"Read content: {content[:80]}...")
                    tool_context.state["files_content"][file_path] = content
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                logger.warning("Could not read file %s: %s", file_path, e)
                # Store an error message so the summarizer knows it failed
                tool_context.state["files_content"][file_path] = f"Error: Could not read file. Reason: {e}"
                response = {"status": "warnings"}
            except Exception as e:
                logger.error("An unexpected error occurred while reading %s: %s", file_path, e)
                tool_context.state["files_content"][file_path] = f"Error: An unexpected error occurred. Reason: {e}"
                response = {"status": "warnings"}
    
    return response

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
    except (configparser.NoSectionError, configparser.NoOptionError, FileNotFoundError):
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

    This function orchestrates the creation of an AI/LLM-friendly Markdown file (`llms.txt`) 
    that provides a structured overview of the repository's contents. It includes a project summary, 
    and organizes files into sections based on their directory structure, with a configurable maximum section depth.

    For each file, it generates a Markdown link with its summary. If a summary is not available, 
    "No summary" is used as a placeholder. Links are generated as GitHub URLs if the repository is 
    detected as a Git repository, otherwise, relative local paths are used.

    Args:
        repo_path: The absolute path to the root of the repository to scan.
        output_path: Optional. The absolute path to save the llms.txt file. 
                     If not provided, it will be saved in a `temp` directory in the current working directory.

    Other required data is retrieved from tool_context.

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
