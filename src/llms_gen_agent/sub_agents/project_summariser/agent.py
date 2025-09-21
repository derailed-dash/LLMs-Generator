"""This module defines the project summariser agent."""

from google.adk import Agent
from google.genai.types import GenerateContentConfig

from llms_gen_agent.config import get_config
from llms_gen_agent.tools import adk_file_read_tool, after_file_read_callback

config = get_config()

project_summariser_agent = Agent(
    model=config.model,
    name="project_summariser_agent",
    instruction="""Summarise the contents of this project in three sentences or fewer. Only return the summary.
    To do this, you must use the `adk_file_read_tool` to read relevant project files (e.g., README.md) 
    by passing the file path as the 'input' argument.
    """,
    tools=[
        adk_file_read_tool,
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.6,
        top_p=1,
        max_output_tokens=8000
    ),
    output_key="project_summary"
)
