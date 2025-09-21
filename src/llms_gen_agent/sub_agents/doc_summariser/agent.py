"""Summarises the contents of a document"""
import re

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai.types import GenerateContentConfig, HttpRetryOptions, Part

from llms_gen_agent.config import get_config, logger
from llms_gen_agent.schema_types import DocumentSummariesOutput
from llms_gen_agent.tools import adk_file_read_tool, after_file_read_callback

config = get_config()

# --- Dynamic instruction provider for content_summarizer_agent ---
def content_summarizer_instruction_provider(context: ReadonlyContext) -> str:
    """ 
    We have already read each file and stored its contents in session.state["path-of-this-file"].
    It is easy to get our agent to expand {files} which is stored as a session state key.
    But it's not easy to get the agent to understand how to retrieve keys using the values of {files}.

    So to solve this problem, we'll create a dynamic prompt where we expand {files} to obtain
    all the paths. Each path is then sequentially used as the session key to retrieve the content.

    Then we can summarise the content for each file, in one LLM call.
    """
    # Get the list of file paths that were discovered
    files_to_summarize = context.state.get('files', [])

    # Build a string containing all file contents to be included in the prompt
    all_file_contents_for_prompt = {}
    for file_path in files_to_summarize:
        # Retrieve content from state using file_path as key (as stored by file_reader_agent)
        content = context.state.get(file_path)
        if content:
            all_file_contents_for_prompt[file_path] = content

    if not all_file_contents_for_prompt:
        # Fallback if no file contents are found (shouldn't happen if file_reader_agent works)
        return "No file contents found in session state to summarize. Please return an empty JSON object: {\"summaries\":{}}."

    # Construct the prompt including all file contents
    prompt_parts = [
        """You have access to the following file contents. 
        Your task is to summarize EACH file's content in three sentences or fewer.
        Aggregate ALL these individual summaries into a single JSON object.
        Return this aggregated JSON object.

        --- File Contents ---
        """
    ]

    for file_path, content in all_file_contents_for_prompt.items():
        prompt_parts.append(f"File: {file_path}\n")
        prompt_parts.append(f"Content:\n{content}\n---\n")

    prompt_parts.append("""\n
        **Output Format:**
        The JSON object MUST have a single key 'summaries' which contains a dictionary where 
        keys are the original file paths and values are their summaries.
        Example: {"summaries": {"/path/to/file1.md": "Summary of file 1.", "/path/to/file2.md":"Summary of file 2."}}

        IMPORTANT: Your final response MUST contain ONLY this JSON object. 
        DO NOT include any other text,explanations, or markdown code block delimiters (```json).
    """)

    logger.debug(f"Dynamic prompt: {prompt_parts}")
    return "\n".join(prompt_parts)

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
            print(f"--- Callback: Original LLM response text (first 100 chars): '{original_text[:100]}...'")

            # Regex to find and remove ```json and ```
            # re.DOTALL allows . to match newlines, \s* matches any whitespace (including newlines)
            # (.*?) is a non-greedy match for the content inside the code block
            cleaned_text = re.sub(r"```json\s*(.*?)\s*```", r"\\1", original_text, flags=re.DOTALL)
            cleaned_text = cleaned_text.strip() # Remove any leading/trailing whitespace

            if cleaned_text != original_text:
                print(f"--- Callback: Stripped markdown. Cleaned text (first 100 chars): '{cleaned_text[:100]}...'")
                # Create a new LlmResponse with the cleaned content
                # Use .copy(deep=True) to ensure you're not modifying the original immutable object directly
                new_content = llm_response.content.model_copy(deep=True)
                if new_content.parts and isinstance(new_content.parts[0], Part):
                    new_content.parts[0].text = cleaned_text
                    return LlmResponse(content=new_content)
                else:
                    print("--- Callback: Error: new_content.parts[0] is not a valid Part object after copy. ---")
                    return llm_response
            else:
                print("--- Callback: No markdown delimiters found or text unchanged. ---")

    print("--- Callback: Returning original LLM response. ---")
    return llm_response # Return the original response if no changes or not applicable

file_reader_agent = Agent(
    name="file_reader_agent",
    description="An agent that reads the content of multiple files and stores them in session state.",
    model=Gemini(
        model=config.model,
        retry_options=HttpRetryOptions(
            initial_delay=2,
            attempts=5,
            exp_base=2,
            max_delay=60
        )
    ),
    instruction="""You have a list of files: {files}.
       PROCESS ONLY THE FIRST FIVE FILES.
       
       For EACH file path (e.g., '/home/user/project/README.md') in the list, 
       you MUST read the file content using the `adk_file_read_tool`.
       Example: `adk_file_read_tool(file_path='/home/user/project/README.md')`

       Once you have read and stored the content these files, respond with a confirmation that all files have been read.
       Your confirmation message should be a simple text string, like "All files read and content stored."
       Do NOT include any other text or explanations in your final response for this turn.
    """,
    tools=[
        adk_file_read_tool
    ],
    after_tool_callback=after_file_read_callback, # this stores the contents of each file read into session state
    # No output_schema or output_key here, as it's just collecting content
)

content_summarizer_agent = Agent(
    name="content_summarizer_agent",
    description="An agent that summarizes collected file contents and aggregates them.",
    model=Gemini(
        model=config.model,
        retry_options=HttpRetryOptions(
            initial_delay=2,
            attempts=5,
            exp_base=2,
            max_delay=60
        )
    ),
    instruction=content_summarizer_instruction_provider, # <--- Use the dynamic instruction provider
    generate_content_config=GenerateContentConfig(
        temperature=0.6,
        top_p=1,
        max_output_tokens=32000
    ),
    output_schema=DocumentSummariesOutput, # This is the final output schema
    output_key="doc_summaries",
    after_model_callback=strip_json_markdown_callback # Apply callback here
)

document_summariser_agent = SequentialAgent(
    name="document_summariser_agent",
    description="A sequential agent that first reads file contents and then summarizes them.",
    sub_agents=[
        file_reader_agent,
        content_summarizer_agent
    ]
)
