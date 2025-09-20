"""
This module defines the main agent for the LLMS-Generator application.
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import GenerateContentConfig

from .config import get_config
from .sub_agents.doc_summariser import document_summariser_agent
from .sub_agents.project_summariser import project_summariser_agent
from .tools import discover_files, generate_llms_txt

config = get_config()

generate_llms_coordinator = Agent(
    name="generate_llms_coordinator",
    description="An agent that generates a llms.txt file for a given repository.",
    model=config.model,
    tools=[
        discover_files, # automatically wrapped as FunctionTool
        generate_llms_txt, # automatically wrapped as FunctionTool
        AgentTool(agent=document_summariser_agent),
        AgentTool(agent=project_summariser_agent),
    ],
    instruction="""You are an expert in analyzing code repositories and generating `llms.txt` files.
Your goal is to create a comprehensive and accurate `llms.txt` file that will help other LLMs
understand the repository. When the user asks you to generate the file, you should ask for the
absolute path to the repository.

Here's the detailed process you should follow:
1.  **Discover Files**: Use the `discover_files` tool with the provided `repo_path` to get a
    `directory_map` of all relevant files.
    In your response to the user, print this map.
2.  **Summarize Files**: Use `document_summariser_agent` to process the files in the `directory_map`.
    The `document_summariser_agent` will return the summaries as `document_summaries`
    which is a dictionary of {file_path: summary}.
3.  Respond with the final set of `document_summaries`.
    In your final response to the user, print these summaries as a table.

""",
    generate_content_config=GenerateContentConfig(
        temperature=0.6,
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
#     the `directory_map`, the `project_overview`, the collected `file_summaries`, and the
#     `section_summaries`.