"""
This module defines the main agent for the LLMS-Generator application.
"""
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import GenerateContentConfig, HttpRetryOptions

from .config import get_config
from .sub_agents.doc_summariser import document_summariser_agent
from .tools import discover_files, generate_llms_txt

config = get_config()

# Agent is an alias for LlmAgent
# It is non-deterministic and decides what tools to use, 
# or what other agents to delegate to
generate_llms_coordinator = Agent(
    name="generate_llms_coordinator",
    description="An agent that generates a llms.txt file for a given repository. Coordinates overall process.",
    model=Gemini(
        model=config.model,
        retry_options=HttpRetryOptions(
            initial_delay=config.backoff_init_delay,
            attempts=config.backoff_attempts,
            exp_base=config.backoff_multiplier,
            max_delay=config.backoff_max_delay
        )
    ),        
    instruction="""You are an expert in analyzing code repositories and generating `llms.txt` files.
Your goal is to create a comprehensive and accurate `llms.txt` file that will help other LLMs
understand the repository. When the user asks you to generate the file, you should ask for the
absolute path to the repository/folder, and optionally an output path.

Here's the detailed process you should follow:
1.  **Discover Files**: Use the `discover_files` tool with the provided `repo_path` to get a list of all
    relevant files paths, in the return value `files`.
2.  **Check Files List**: Check you received a success response and a list of files.
    If not, you should provide an appropriate response to the user and STOP HERE.
3.  **Summarize Files**: Delegate to the `document_summariser_agent` Agent Tool.
    **CRITICAL: This tool MUST be called with NO arguments.**
    The `document_summariser_agent` will read the list of files from the session state 
    (which was populated by the `discover_files` tool). 
    The `document_summariser_agent` will then return the full set of summaries as JSON 
    with a single key `summaries` that contains a dictionary of all the path:summary pairs.
    **Example of correct call:** `document_summariser_agent()`
4.  **Check Summary Response**: you should have received a JSON response containing the summaries.
    This contains all the files originally discovered, with each mapped to a summary.
    If so, continue. If not, you should provide an appropriate response to the user and STOP HERE.
5.  **Generate `llms.txt**: Call the `generate_llms_txt` tool.
    Provide `repo_path` as an argument. If the user provided an output path, 
    provide it as the `output_path` argument.
    The tool will determine other required values from session state.
6.  **Response**
    Finally, respond to the user confirming whether the `llms.txt` creation was successful.
    State the path where the file has been created, which is stored in session state key `llms_txt_path`.
""",
    tools=[
        discover_files, # automatically wrapped as FunctionTool
        generate_llms_txt, # automatically wrapped as FunctionTool
        AgentTool(agent=document_summariser_agent)
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.1,
        top_p=1,
        max_output_tokens=60000
    )
)

root_agent = generate_llms_coordinator

