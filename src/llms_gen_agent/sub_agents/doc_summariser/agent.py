"""
This module defines the `document_summariser_agent`, a sophisticated `SequentialAgent`
responsible for orchestrating the summarization of a collection of files within a repository.

The agent implements a batch-processing and looping mechanism to handle large numbers of files
efficiently, overcoming potential model context limitations.

The overall process orchestrated by `document_summariser_agent` is as follows:
1.  **Batch Creation:** Files discovered by a parent agent are split into manageable batches.
2.  **Iterative Batch Processing:** Each batch is processed in a loop, where:
    a.  Files within the current batch are read.
    b.  Individual summaries are generated for each file in the batch.
    c.  These batch summaries are aggregated into a master list of all summaries.
3.  **Project Summarization:** After all batches are processed, a high-level project summary
    is generated based on the aggregated file summaries and the project's README.md (if available).
4.  **Finalization:** All individual and project summaries are combined into a single,
    structured output format for consumption by other tools.
"""
import re

from google.adk.agents import Agent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai.types import GenerateContentConfig, HttpRetryOptions, Part

from llms_gen_agent.config import logger, setup_config
from llms_gen_agent.schema_types import BatchSummariesOutput, ProjectSummaryOutput

from .tools import create_file_batches, finalize_summaries, process_batch_selection, read_files, update_summaries

config = setup_config()

retry_options=HttpRetryOptions(
            initial_delay=config.backoff_init_delay,
            attempts=config.backoff_attempts,
            exp_base=config.backoff_multiplier,
            max_delay=config.backoff_max_delay
)

def clean_json_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> LlmResponse | None:
    """
    Strips markdown code block delimiters (```json, ```) from the LLM's text response.
    This callback runs after the model generates content but before output_schema validation.
    """
    logger.debug("--- Callback: clean_json_callback running for agent: %s ---", callback_context.agent_name)

    if llm_response.content and llm_response.content.parts:
        # Assuming the response is text in the first part
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            logger.debug(f"--- Callback: Original LLM response text (first 100 chars): '{original_text[:100]}...'")

            # Regex to find and remove ```<lang> and ```
            # re.DOTALL allows . to match newlines, \s* matches any whitespace (including newlines)
            # (.*?) is a non-greedy match for the content inside the code block
            match = re.search(r"```(?:\w*\s*)?(.*?)\s*```", original_text, flags=re.DOTALL)
            if match:
                cleaned_text = match.group(1).strip()
                logger.debug(f"--- Callback: Stripped markdown. Cleaned text (first 100 chars): '{cleaned_text[:100]}...'")
                # Create a new LlmResponse with the cleaned content
                # Use .model_copy(deep=True) to ensure you're not trying to modify the original immutable object directly
                new_content = llm_response.content.model_copy(deep=True)
                if new_content.parts and isinstance(new_content.parts[0], Part):
                    new_content.parts[0].text = cleaned_text
                    return LlmResponse(content=new_content)
                else:
                    logger.debug("--- Callback: Error: new_content.parts[0] is not a valid Part object after copy. ---")
                    return llm_response
            else:
                logger.debug("--- Callback: No markdown code block found. Returning original response. ---")
                return llm_response

    return llm_response # Return the original response if no changes or not applicable

# This agent reads the files from the 'current_batch' in session state.
file_reader_agent = Agent(
    name="file_reader_agent",
    description="An agent that reads the content of multiple files and stores them in session state.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),
    instruction="""You are a specialist in reading files. Your job is to run the `read_files`, 
    which will read a list of files in your session state, and store their contents.
    IMPORTANT: you should NOT pass any arguments to the `read_files` tool. 
    It will retrieve its data from session state. """,
    tools=[
        read_files
    ],
)

content_summariser_prompt = """You are an expert summariser.
Your task is to summarise EACH individual file's content in no more than four sentences.
The summary should reference any key concepts, classes, best practices, etc.
- Do NOT start summaries with text like "This document is about..." or "This page introduces..."
  Just immediately describe the content. E.g.
  - Rather than this: "This document explains how to configure streaming behavior..."
    Say this: "Explains how to configure streaming behavior..."
  - Rather than this: "This page introduces an agentic framework for..."
    Say this: "Introduces an agentic framework for..."
- If you cannot generate a meaningful summary, use 'No meaningful summary available.' as its summary.

The final output MUST be a JSON object with a single top-level key called 'batch_summaries', 
which contains a dictionary of file paths to summaries.
Example: {"batch_summaries": {"/path/to/file1.md":"Summary of file 1.", "/path/to/file2.md":"Summary of file 2."}}

IMPORTANT: Your final response MUST contain ONLY this JSON object.
DO NOT include any other text, explanations, or markdown code block delimiters.

FILE CONTENTS START:
{files_content}
---
FILE CONTENTS END:

Now return the JSON object.
"""

# This agent summarizes the content of files in the current batch.
content_summariser_agent = Agent(
    name="content_summarizer_agent",
    description="An agent that summarizes collected file contents and aggregates them.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),
    instruction=content_summariser_prompt,
    generate_content_config=GenerateContentConfig(
        temperature=0.5,
        top_p=1,
        max_output_tokens=64000
    ),
    output_schema=BatchSummariesOutput, # This is the final output schema
    output_key="batch_summaries", # json with top level called 'batch_summaries'
    after_model_callback=clean_json_callback # Apply callback here
)

# This agent is responsible for initially splitting all discovered files into batches.
batch_creation_agent = Agent(
    name="batch_creation_agent",
    description="Creates batches of files.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),    
    instruction=f"""You MUST call the `create_file_batches` tool with a `batch_size` of {config.batch_size}.
    This is your ONLY task.
    The `create_file_batches` tool will read the 'files' from the session state, create batches, 
    and store them in the 'batches' session state key.
    Do NOT respond with anything else. Just call the tool.""",
    tools=[create_file_batches]
)

# Agent to select the next batch or exit the loop
batch_selector_agent = Agent(
    name="batch_selector_agent",
    description="Selects the next batch of files to process or exits the loop.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),    
    instruction="""Call the `process_batch_selection` tool to manage batch selection and loop termination.""",
    tools=[process_batch_selection]
)

# Agent to aggregate summaries from each batch
update_summaries_agent = Agent(
    name="update_summaries_agent",
    description="Appends the latest batch summaries to the main summary list.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),    
    instruction="""You MUST call the `update_summaries` tool. This is your ONLY task.
    The `update_summaries` tool will merge the 'batch_summaries' from the session state into the 'all_summaries' dictionary 
    in the session state.
    Do NOT respond with anything else. Just call the tool.""",
    tools=[update_summaries]
)

# Agent to create the final project summary after the loop
project_summariser_agent = Agent(
    name="project_summariser_agent",
    description="Creates the final project summary from all file summaries.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),    
    instruction="""Read the content of the project's README.md file (if available in session state as 'readme_content').
    Then, review the 'all_summaries' from the session state.
    Generate a three-paragraph summary of the entire project based on these inputs.
    The output should be a JSON object with a single key 'project_summary' containing the generated summary.""",
    tools=[read_files], # To read the README
    output_schema=ProjectSummaryOutput,
    output_key="project_summary_raw",
    after_model_callback=clean_json_callback # Apply callback here
)

# This agent will process one batch sequentially
single_batch_processor = SequentialAgent(
    name="single_batch_processor",
    description="Reads and summarizes one batch of files.",
    sub_agents=[
        file_reader_agent, # Reads files from 'current_batch'
        content_summariser_agent, # Summarises files from 'current_batch'
        update_summaries_agent # Appends batch summaries to 'all_summaries'
    ]
)

# This LoopAgent iteratively processes each batch of files until all are summarized.
batch_processing_loop = LoopAgent(
    name="batch_processing_loop",
    description="Processes all file batches in a loop.",
    sub_agents=[
        batch_selector_agent, # Gets next batch or exits
        single_batch_processor
    ],
    max_iterations=200 # A safeguard against infinite loops
)

# This agent combines all collected summaries and the project summary into the final output.
final_summary_agent = Agent(
    name="final_summary_agent",
    description="Finalizes the document summaries by combining all individual and project summaries.",
    model=Gemini(
        model=config.model,
        retry_options=retry_options
    ),    
    instruction="""Call the `finalize_summaries` tool to combine all collected summaries and the project summary 
    into the final output format.""",
    tools=[finalize_summaries]
)

# This is the main document summariser agent, orchestrating the entire process.
document_summariser_agent = SequentialAgent(
    name="document_summariser_agent",
    description="Orchestrates the entire sequential file summarization process including batching and looping.",
    sub_agents=[
        batch_creation_agent, # Step 1: Create batches of files
        batch_processing_loop, # Step 2: Process each batch in a loop
        project_summariser_agent, # Step 3: Generate overall project summary
        final_summary_agent # Step 4: Finalize and combine all summaries
    ]
)
