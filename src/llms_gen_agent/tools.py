"""This module provides tools for the LLMS-Generator agent."""

import os
from typing import Any

from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import ReadFileTool

from .config import logger

read_file_tool = ReadFileTool()

# Wrap the custom tool with CrewaiTool for ADK
adk_file_read_tool = LangchainTool(
    name="FileRead",
    description="Reads the contents of a file",
    tool=read_file_tool, 
)

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
    logger.debug("Entering discover_files with repo_path: %s", repo_path)
    directory_map: dict[str, list[str]] = {}
    try:
        excluded_dirs = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache'}
        for root, subdirs, files in os.walk(repo_path):
            subdirs[:] = [d for d in subdirs if d not in excluded_dirs]
            for file in files:
                # For now, we'll stick with markdown files, but this can be expanded.
                if file.endswith(".md"):
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

def after_file_read_callback(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any) -> Any | None:
    tool_name = tool.name
    logger.debug("Entering after_file_read_callback for tool: %s", tool_name)
    logger.debug(f"Args: {args}")
    # logger.debug(f"Tool response: {tool_response}")

    if isinstance(tool_response, str):
        content = tool_response # The tool_response itself is the content
    elif isinstance(tool_response, dict) and "content" in tool_response:
        content = tool_response["content"]
    else:
        logger.warning("tool_response is a {type(tool_response)}. Expected str or dict.")

    tool_context.state[args["file_path"]] = content

    logger.debug("Exiting after_file_read_callback for tool: %s", tool_name)
    return tool_response    

# def generate_llms_txt(repo_path: str, doc_summaries_json: AggregatedSummariesOutput, tool_context: ToolContext) -> dict:
def generate_llms_txt(repo_path: str, doc_summaries: dict[str, str], tool_context: ToolContext) -> dict:
    """
    Generates a llms.txt file for the repository in Markdown format.

    Args:
        repo_path: The absolute path to the repository to scan.
        doc_summaries_json: An instance of AggregatedSummariesOutput containing the document summaries.        

    Other required data will be retrieved from session state.

    Returns:
        A dictionary with "status" (success/failure) and the path to the generated file.
    """
    logger.debug("Entering generate_llms_txt for repo_path: %s", repo_path)
    dirs = tool_context.state.get("dirs", [])
    files = tool_context.state.get("files", [])
    # doc_summaries = {item.file_path: item.summary for item in doc_summaries_json.summaries}

    logger.debug("We have %d directories.", len(dirs))
    logger.debug("We have %d files", len(files))
    logger.debug("We have %d sumamries", len(doc_summaries))
    # logger.debug("Section summaries count: %d", len(section_summaries))

    # Create variable llms_txt_path - It should be the current location where the user is, in a folder called temp.
    # Create the temp if it doesn't exit.
    temp_dir = os.path.join(os.getcwd(), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    llms_txt_path = os.path.join(temp_dir, "llms.txt") 

    owner, repo_name = _get_repo_details(repo_path)
    base_url = f"https://github.com/{owner}/{repo_name}/blob/main/" if owner else ""

    with open(llms_txt_path, "w") as f:
        f.write(f"# {repo_name} Sitemap\n\n")
        f.write("Placeholder for overview\n\n") # TODO: add real overview

        for directory in dirs:
            section_name = (
                os.path.relpath(directory, repo_path)
                .replace("/", " ")
                .strip()
                .title()
            )
            if section_name == ".":
                section_name = "Home"

            f.write(f"## {section_name}\n\n")
            # f.write(f"{section_summaries.get(section_name, f'An overview of the {section_name} section.')}\n\n")

            section_summaries = [(file_path, summary) for file_path, summary in doc_summaries.items() 
                                                       if file_path.startswith(directory)]

            for file_path, summary in sorted(section_summaries):
                link_text = os.path.basename(file_path)
                relative_path = os.path.relpath(file_path, repo_path)
                f.write(f"- [{link_text}]({base_url}{relative_path}): {summary}\n")
            f.write("\n")

    logger.debug("Exiting generate_llms_txt. llms.txt generated at %s", llms_txt_path)
    tool_context.state["llms_txt_path"] = llms_txt_path
    # Read the generated file content and store it in session state
    with open(llms_txt_path) as f:
        llms_content = f.read()
    tool_context.state["llms_content"] = llms_content
    return {"status": "success", "llms_txt_path": llms_txt_path}
