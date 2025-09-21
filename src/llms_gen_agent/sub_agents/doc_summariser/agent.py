"""Summarises the contents of a document"""
import re

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai.types import GenerateContentConfig, HttpRetryOptions, Part

from llms_gen_agent.config import get_config, logger
from llms_gen_agent.schema_types import DocumentSummariesOutput
from llms_gen_agent.tools import adk_file_read_tool, after_file_read_callback

config = get_config()

retry_options=HttpRetryOptions(
            initial_delay=config.backoff_init_delay,
            attempts=config.backoff_attempts,
            exp_base=config.backoff_multiplier,
            max_delay=config.backoff_max_delay
)

def strip_json_markdown_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> LlmResponse | None:
    """
    Strips markdown code block delimiters (```json, ```) from the LLM's text response.
    This callback runs after the model generates content but before output_schema validation.
    """
    logger.debug("--- Callback: strip_json_markdown_callback running for agent: %s ---", callback_context.agent_name)

    if llm_response.content and llm_response.content.parts:
        # Assuming the response is text in the first part
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            logger.debug(f"--- Callback: Original LLM response text (first 100 chars): '{original_text[:100]}...'")

            # Regex to find and remove ```json and ```
            # re.DOTALL allows . to match newlines, \s* matches any whitespace (including newlines)
            # (.*?) is a non-greedy match for the content inside the code block
            cleaned_text = re.sub(r"```json\s*(.*?)\s*```", r"\\1", original_text, flags=re.DOTALL)
            cleaned_text = cleaned_text.strip() # Remove any leading/trailing whitespace

            if cleaned_text != original_text:
                logger.debug(f"--- Callback: Stripped markdown. Cleaned text (first 100 chars): '{cleaned_text[:100]}...'")
                # Create a new LlmResponse with the cleaned content
                # Use .model_copy(deep=True) to ensure you're not modifying the original immutable object directly
                new_content = llm_response.content.model_copy(deep=True)
                if new_content.parts and isinstance(new_content.parts[0], Part):
                    new_content.parts[0].text = cleaned_text
                    return LlmResponse(content=new_content)
                else:
                    logger.debug("--- Callback: Error: new_content.parts[0] is not a valid Part object after copy. ---")
                    return llm_response
            else:
                pass # Nothing to change

    return llm_response # Return the original response if no changes or not applicable

file_reader_agent_prompt="""You have a list of files: {files}."""
if config.max_files_to_process > 0:
    file_reader_agent_prompt += f"""You must only process the first {config.max_files_to_process} files."""
file_reader_agent_prompt += """For EACH file path (e.g. '/home/user/project/README.md') in the list, 
       you MUST read the file content using the `adk_file_read_tool`.
       Example: `adk_file_read_tool(file_path='/home/user/project/README.md')`

       Once you have read and stored the content these files, respond with a confirmation that all files have been read.
       Your confirmation message should be a simple text string, like "All files read and content stored."
       Do NOT include any other text or explanations in your final response for this turn.
"""

file_reader_agent = Agent(
    name="file_reader_agent",
    description="An agent that reads the content of multiple files and stores them in session state.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),
    instruction=file_reader_agent_prompt,
    tools=[
        adk_file_read_tool
    ],
    after_tool_callback=after_file_read_callback, # this stores the contents of each file read into session state
    # No output_schema or output_key here, as it's just collecting content in session state
)

content_summariser_prompt = """You are an expert summariser. 
You will summarise the contents of multiple files, and then you will summarise the overall project.
You will do this work in two phase.

# Phase 1: File Summarisation
- Your task is to summarize EACH individual file's content in three sentences or fewer.
- Do NOT start summaries with text like "This document is about" or "This document provides".
  Just immediately describe the content. E.g.
  Rather than this: "This document explains how to configure streaming behavior..."
  Say this: "Explains how to configure streaming behavior..."
- If you cannot generate a meaningful summary for a file, use 'No meaningful summary available.' as its summary.
- Aggregate ALL these individual summaries into a single JSON object.

# Phase 2: Project Summarisation
- After summarizing all the files, you MUST also provide an overall project summary, in no more than three paragraphs. 
- The project summary should be a high-level overview of the repository/folder, based on the content of the files.
- Focus on the content that is helpful for understanding the purpose of the project and the core components.
- The project summary MUST be stored in the same output JSON object with the key 'project'.

# Output Format
- The JSON object MUST have a single top-level key called 'summaries', which contains a dictionary.
- The dictionary contains all the summaries as key:value pairs.
- For the file summaries: the dictionary keys are the original file paths and values are their respective summaries.
- For the project summary: the key is `project`. THIS KEY MUST BE PRESENT. The value is the project summary. 
- Example: 
  {{"summaries": {{"/path/to/file1.md":"Summary of file 1.", 
                   "/path/to/file2.md":"Summary of file 2.",
                   "/path/to/file3.py":"Summary of python file."
                   "project":"Summary of the project."}} }}

IMPORTANT: Your final response MUST contain ONLY this JSON object. 
DO NOT include any other text,explanations, or markdown code block delimiters (```json).

Now I will provide you with the contents of multiple files. 
Note that each file has a unique path and associated content.

**FILE CONTENTS START:**
{files_content}
---
**FILE CONTENTS END:**

Now return the JSON object.
"""

content_summariser_agent = Agent(
    name="content_summarizer_agent",
    description="An agent that summarizes collected file contents and aggregates them.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),
    instruction=content_summariser_prompt,
    generate_content_config=GenerateContentConfig(
        temperature=0.6,
        top_p=1,
        max_output_tokens=32000
    ),
    output_schema=DocumentSummariesOutput, # This is the final output schema
    output_key="doc_summaries", # json with top level called 'summaries'
    after_model_callback=strip_json_markdown_callback # Apply callback here
)

document_summariser_agent = SequentialAgent(
    name="document_summariser_agent",
    description="A sequential agent that first reads file contents and then summarizes them.",
    sub_agents=[
        file_reader_agent,
        content_summariser_agent
    ]
)
