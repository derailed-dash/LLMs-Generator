"""Summarises the contents of a document"""
from google.adk import Agent
from google.genai.types import GenerateContentConfig

from ...config import get_config
from ...tools import adk_file_read_tool

config = get_config()

document_summariser_agent = Agent(
    model=config.model,
    name="document_summariser_agent",
    instruction="""Process the FIRST FIVE files in {directory_map}. 
    Each value is the path to a markdown file. 
    You must read each file using the `adk_file_read_tool`, passing in the file path as the 'input' argument.
    Summarise the contents of the provided markdown document in three sentences or fewer. 
    Leave a second delay between each summary generation, to avoid rate limits.
    Compile all the summaries in a dictionary with the format {file_path: summary}.
    """,
    tools=[
        adk_file_read_tool,
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.6,
        top_p=1,
        max_output_tokens=32000
    ),
    output_key="document_summaries"
)
