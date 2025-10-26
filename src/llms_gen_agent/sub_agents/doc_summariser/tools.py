"""
This module provides a collection of tools for the doc_summariser agent.

Key functionalities include:
- `read_files`: Reads a list of files and stores their content in the tool context.
"""
from google.adk.tools import ToolContext

from llms_gen_agent.config import logger, setup_config


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


def process_batch_selection(tool_context: ToolContext) -> dict:
    """Manages the batch selection for the loop, increments iteration counter, and logs batch info."""
    logger.debug("Executing process_batch_selection")
    
    batches = tool_context.state.get("batches", [])
    loop_iteration = tool_context.state.get("loop_iteration", 0)
    
    if not batches:
        logger.debug("No more batches to process. Exiting loop.")
        tool_context.actions.escalate = True # Signal to exit the loop
        return {"status": "no_more_batches"}
    
    current_batch = batches.pop(0) # Get the next batch
    tool_context.state["batches"] = batches # Update batches in state
    tool_context.state["current_batch"] = current_batch # Set current batch
    
    loop_iteration += 1
    tool_context.state["loop_iteration"] = loop_iteration
    
    logger.debug(f"Processing batch {loop_iteration}. Files in batch: {len(current_batch)}. Remaining batches: {len(batches)}")
    
    return {"status": "batch_selected", "loop_iteration": loop_iteration, "files_in_batch": len(current_batch)}


def exit_loop(tool_context: ToolContext) -> None:
    """A special tool that signals the LoopAgent to terminate the loop."""
    tool_context.actions.escalate = True

def update_summaries(tool_context: ToolContext) -> dict:
    """Merges the batch_summaries into the all_summaries in the session state."""
    logger.debug("Executing update_summaries")
    
    batch_summaries_output = tool_context.state.get("batch_summaries", {})
    batch_summaries = batch_summaries_output.get("batch_summaries", {}) # Get the actual dict from the output_key
    
    if "all_summaries" not in tool_context.state:
        tool_context.state["all_summaries"] = {}
    
    tool_context.state["all_summaries"].update(batch_summaries)
    
    logger.debug(f"Merged {len(batch_summaries)} summaries from current batch. Total summaries collected: {len(tool_context.state['all_summaries'])}")
    
    return {"status": "success"}

def finalize_summaries(tool_context: ToolContext) -> dict:
    """Combines all individual file summaries and the project summary into the final doc_summaries format."""
    logger.debug("Executing finalize_summaries")
    all_summaries = tool_context.state.get("all_summaries", {})
    project_summary_raw = tool_context.state.get("project_summary_raw", {}).get("project_summary", "No project summary found.")

    final_doc_summaries = {
        "summaries": {
            **all_summaries,
            "project": project_summary_raw
        }
    }
    tool_context.state["doc_summaries"] = final_doc_summaries
    
    return {"status": "success"}
