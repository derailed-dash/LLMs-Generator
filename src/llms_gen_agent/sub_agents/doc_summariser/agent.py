"""Summarises the contents of a document"""
from google.adk import Agent
from google.adk.models.google_llm import Gemini
from google.genai.types import GenerateContentConfig, HttpRetryOptions
from pydantic import BaseModel, Field

from ...config import get_config
from ...tools import adk_file_read_tool

config = get_config()

class SummaryOutput(BaseModel):
    file_path: str = Field(description="The path to the document.")
    summary: str = Field(description="A summary of of the document.")

class AggregatedSummariesOutput(BaseModel):
    # This model will contain a list of SummaryOutput objects
    summaries: list[SummaryOutput] = Field(description="A list of aggregated document summaries.")

document_summariser_agent = Agent(
    name="document_summariser_agent",
    description="An agent that summarises documents. Given a list of document paths, you read and summarise each document.",
    model=Gemini(
        model=config.model,
        retry_options=HttpRetryOptions(
            initial_delay=1,
            attempts=5
        )
    ), 
    instruction="""You have been provided with a list of file paths: {files}.
       Your task is to process the first 10 files from this list.
       For EACH file path in the list, you must perform the following steps:
       1. Read the file content: Call the `adk_file_read_tool`. The argument to this tool must be the single
          file path you are currently processing. For example, if the file path is '/path/to/file.md', you would
          call `adk_file_read_tool(input='/path/to/file.md')`.
       2. Summarize the content: After reading the file, summarize its content in three sentences or fewer.
          After processing all 10 files, aggregate all the summaries.
          Return the aggregated summaries as a JSON object with the format: 
          {"summaries": [{"file_path": "summary"}, {"file_path":"summary"}, ...]} """,
    tools=[
        adk_file_read_tool,
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.6,
        top_p=1,
        max_output_tokens=32000
    ),
    output_schema=AggregatedSummariesOutput,
    output_key="doc_summaries"
)
