import os

# from crewai_tools import FileReadTool
from google.adk.tools import ToolContext
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import ReadFileTool

# from google.adk.tools.crewai_tool import CrewaiTool
from .config import logger

read_file_tool = ReadFileTool()

# Wrap the custom tool with CrewaiTool for ADK
adk_file_read_tool = LangchainTool(
    name="FileRead",
    description="Reads the contents of a file",
    tool=read_file_tool
)

def _get_repo_details(repo_path: str) -> tuple[str, str]:
    """Extracts owner and repo name from the path."""
    path_parts = repo_path.strip(os.sep).split(os.sep)
    owner = path_parts[-2] if len(path_parts) > 1 else ""
    repo_name = path_parts[-1]
    return owner, repo_name


def discover_files(repo_path: str, tool_context: ToolContext) -> dict[str, list[str]]:
    """Discovers all relevant files in the repository and returns a directory map.

    Args:
        repo_path: The absolute path to the repository to scan.

    Returns:
        A dictionary mapping directories to lists of file paths.
    """
    logger.debug("Entering discover_files with repo_path: %s", repo_path)
    directory_map: dict[str, list[str]] = {}
    excluded_dirs = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
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

    tool_context.state["directory_map"] = directory_map
    for directory, files in directory_map.items():
        logger.debug(f"Directory: {directory}, Files: {files}")

    logger.debug("Exiting discover_files.")
    return directory_map

def generate_llms_txt(
    repo_path: str,
    directory_map: dict[str, list[str]],
    project_overview: str,
    doc_summaries: dict[str, str],
    section_summaries: dict[str, str],
) -> str:
    """
    Generates a llms.txt file for the repository in Markdown format.

    Args:
        repo_path: The absolute path to the repository to scan.
        directory_map: A dictionary mapping directories to lists of file paths.
        project_overview: A summary of the entire project.
        file_summaries: A dictionary mapping file paths to their summaries.
        section_summaries: A dictionary mapping section names to their summaries.
    """
    logger.debug("Entering generate_llms_txt for repo_path: %s", repo_path)
    logger.debug("Directory map contains %d entries.", len(directory_map))
    logger.debug("Project overview length: %d", len(project_overview))
    logger.debug("File summaries count: %d", len(doc_summaries))
    logger.debug("Section summaries count: %d", len(section_summaries))

    llms_txt_path = os.path.join(repo_path, "llms.txt")
    owner, repo_name = _get_repo_details(repo_path)
    base_url = f"https://github.com/{owner}/{repo_name}/blob/main/" if owner else ""

    with open(llms_txt_path, "w") as f:
        f.write(f"# {repo_name} Sitemap\n\n")
        f.write(f"{project_overview}\n\n")

        for directory, files in sorted(directory_map.items()):
            section_name = (
                os.path.relpath(directory, repo_path)
                .replace("/", " ")
                .strip()
                .title()
            )
            if section_name == ".":
                section_name = "Home"

            f.write(f"## {section_name}\n\n")
            f.write(f"{section_summaries.get(section_name, f'An overview of the {section_name} section.')}\n\n")

            for file_path in sorted(files):
                link_text = os.path.basename(file_path)
                relative_path = os.path.relpath(file_path, repo_path)
                summary = doc_summaries.get(file_path, "No summary available.")
                f.write(f"- [{link_text}]({base_url}{relative_path}): {summary}\n")
            f.write("\n")

    logger.debug("Exiting generate_llms_txt. llms.txt generated at %s", llms_txt_path)
    return f"llms.txt file generated successfully at {llms_txt_path}"

