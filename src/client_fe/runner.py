"""
This module is responsible for running the llms-gen agent.

It sets up the necessary session and runner from the `google-adk` library,
and then invokes the agent with the user's query. It also handles the 
streaming of events from the agent and displays the final response.
"""
from logging import Logger

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from rich.console import Console

from llms_gen_agent.agent import root_agent

APP_NAME = "generate_llms_client"
USER_ID = "cli_user"
SESSION_ID = "cli_session"

console = Console()

async def setup_session_and_runner(logger: Logger):
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    return runner


async def call_agent_async(query: str, logger: Logger) -> None:
    content = Content(role="user", parts=[Part(text=query)])
    runner = await setup_session_and_runner(logger)
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    final_response_content = "Final response not yet received."

    async for event in events:
        if function_calls := event.get_function_calls():
            tool_name = function_calls[0].name
            logger.info(f"_Using tool {tool_name}..._")
        elif event.actions and event.actions.transfer_to_agent:
            personality_name = event.actions.transfer_to_agent
            logger.info(f"_Delegating to agent: {personality_name}..._")
        elif event.is_final_response() and event.content and event.content.parts:
            final_response_content = event.content.parts[0].text

    logger.info("## Final Message")
    logger.info(final_response_content)
