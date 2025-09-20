"""
This module defines the main agent for the LLMS-Generator application.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import GenerateContentConfig, HttpRetryOptions

from .config import get_config
from .sub_agents.doc_summariser import document_summariser_agent
from .sub_agents.project_summariser import project_summariser_agent
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
            initial_delay=1,
            attempts=3
        )
    ),        
    instruction="""You are an expert in analyzing code repositories and generating `llms.txt` files.
Your goal is to create a comprehensive and accurate `llms.txt` file that will help other LLMs
understand the repository. When the user asks you to generate the file, you should ask for the
absolute path to the repository/folder.

Here's the detailed process you should follow:
1.  **Discover Files**: Use the `discover_files` tool with the provided `repo_path` to get a list of all
    relevant files paths, in the return value `files`.
2.  **Check Files List**: Check you received a success response and a list of files.
    If not, you should provide an appropriate response to the user and STOP HERE.
3.  **Summarize Files**: Delegate to the `document_summariser_agent` Agent Tool.
    This tool does NOT require any arguments. The `document_summariser_agent` will 
    read the list of files from the session state under the key 'files' (which was populated by the
    `discover_files` tool). The `document_summariser_agent` will then return the full set of summaries as
    `doc_summaries` as a dictionary of format {{file_path: summary}}.
4.  **Check Summary Response**: you should have received a dictionary called `doc_summaries` containing all 
    the files originally discovered, with each mapped to a summary.
    If so, continue. If not, you should provide an appropriate response to the user and STOP HERE.
5.  Respond with the final set of `doc_summaries`.
    In your final response to the user, print these summaries as a table.
""",
    tools=[
        discover_files, # automatically wrapped as FunctionTool
        generate_llms_txt, # automatically wrapped as FunctionTool
        AgentTool(agent=document_summariser_agent),
        AgentTool(agent=project_summariser_agent),
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=1,
        max_output_tokens=32768
    )
)

root_agent = generate_llms_coordinator

# 4.  **Generate Section Summaries**: For each directory (section) in the `directory_map`, generate
#     a concise summary. You can use a generic placeholder or generate a summary based on the
#     directory name. Collect these into a dictionary where keys are section names and values are
#     their summaries.
# 5.  **Generate llms.txt**: Finally, call the `generate_llms_txt` tool, providing the `repo_path`,
#     the `directory_map`, the `project_overview`, the collected `doc_summaries`, and the
#     `section_summaries`.
