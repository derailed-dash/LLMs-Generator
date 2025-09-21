"""
This module provides the command-line interface (CLI) for the LLMS-Generator application.

The primary function of this module is to accept a repository path from the user and initiate the
llms.txt generation process by calling the `call_agent_async` function from the `runner` module.

Usage:
    `llms-gen --repo-path /path/to/your/repo [--output-path /path/to/llms.txt] [--log-level DEBUG]`
"""
import asyncio
import os

# Load .env before other imports
from dotenv import find_dotenv, load_dotenv

# recursively search upwards to find .env, and update vars if they exist
if not load_dotenv(find_dotenv(), override=True):
    raise ValueError("No .env file found. Exiting.")

import typer
from rich.console import Console

from client_fe.runner import APP_NAME, call_agent_async
from common_utils.logging_utils import setup_logger

app = typer.Typer()
console = Console()

@app.command()
def generate(
    repo_path: str = typer.Option(
        ...,
        "--repo-path",
        "-r",
        help="The absolute path to the repository/folder to generate the llms.txt file for.",
    ),
    output_path: str = typer.Option(
        None,
        "--output-path",
        "-o",
        help=("The absolute path to save the llms.txt file. If not specified, "
              "it will be saved in a `temp` directory in the current working directory.")
    ),
    log_level: str = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Set the log level for the application. This will override any LOG_LEVEL environment variable."
    )
):
    """
    Generate the llms.txt file for a given repository.
    """
    if log_level: # Override log level from cmd line
        os.environ["LOG_LEVEL"] = log_level.upper()

    # Now that env vars are set, we can create the logger
    logger = setup_logger(APP_NAME)

    logger.info(f"Generating llms.txt for repository at: {repo_path}")
    query = f"Generate the llms.txt file for the repository at {repo_path}"
    if output_path:
        query += f" and save it to {output_path}"

    asyncio.run(call_agent_async(query, logger))
    logger.info("llms.txt generation complete.")


if __name__ == "__main__":
    app()
