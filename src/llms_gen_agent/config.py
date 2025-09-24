"""This module provides configuration for the LLMS-Generator agent."""

import functools
import os
from collections.abc import Callable
from dataclasses import dataclass

import google.auth

from common_utils.exceptions import ConfigError
from common_utils.logging_utils import setup_logger

# --- Constants for default environment variables ---
DEFAULT_AGENT_NAME = "llms_gen_agent"
DEFAULT_GCP_LOCATION = "global"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_GENAI_USE_VERTEXAI = "True"
DEFAULT_MAX_FILES_TO_PROCESS = "0"
DEFAULT_BACKOFF_INIT_DELAY = "2"
DEFAULT_BACKOFF_ATTEMPTS = "5"
DEFAULT_BACKOFF_MAX_DELAY = "60"
DEFAULT_BACKOFF_MULTIPLIER = "2"

agent_name = os.environ.setdefault("AGENT_NAME", DEFAULT_AGENT_NAME)
logger = setup_logger(agent_name)


@dataclass
class Config:
    """Holds application configuration."""

    agent_name: str
    project_id: str
    location: str
    model: str
    genai_use_vertexai: bool
    
    max_files_to_process: int # 0 means no limit
    
    backoff_init_delay: int
    backoff_attempts: int
    backoff_max_delay: int
    backoff_multiplier: int

def _get_env_var(key: str, default_value: str, type_converter: Callable=str):
    """Helper to get environment variables with a default and type conversion."""
    return type_converter(os.environ.setdefault(key, default_value))

@functools.lru_cache(maxsize=1)
def get_config() -> Config:
    """Return a dictionary of the current config by reading from environment."""

    _, project_id = google.auth.default()
    if not project_id:
        raise ConfigError("GCP Project ID not set. Have you run scripts/setup-env.sh?")

    # GCP Configuration
    location = _get_env_var("GOOGLE_CLOUD_LOCATION", DEFAULT_GCP_LOCATION)
    model = _get_env_var("MODEL", DEFAULT_MODEL)
    genai_use_vertexai = _get_env_var("GOOGLE_GENAI_USE_VERTEXAI", DEFAULT_GENAI_USE_VERTEXAI, lambda x: x.lower() == "true")
    
    # Agent Specific Configuration
    max_files_to_process = _get_env_var("MAX_FILES_TO_PROCESS", DEFAULT_MAX_FILES_TO_PROCESS, int)
    
    # Backoff Configuration
    backoff_init_delay = _get_env_var("BACKOFF_INIT_DELAY", DEFAULT_BACKOFF_INIT_DELAY, int)
    backoff_attempts = _get_env_var("BACKOFF_ATTEMPTS", DEFAULT_BACKOFF_ATTEMPTS, int)
    backoff_max_delay = _get_env_var("BACKOFF_MAX_DELAY", DEFAULT_BACKOFF_MAX_DELAY, int)
    backoff_multiplier = _get_env_var("BACKOFF_MULTIPLIER", DEFAULT_BACKOFF_MULTIPLIER, int)

    logger.debug("Agent name set to %s", agent_name)
    logger.debug("Project ID set to %s", project_id)
    logger.debug("Location set to %s", location)
    logger.debug("Model set to %s", model)
    logger.debug("Max files to process set to %s", max_files_to_process)
    logger.debug("GenAI use Vertex AI set to %s", genai_use_vertexai)
    logger.debug("Backoff initial delay set to %s", backoff_init_delay)
    logger.debug("Backoff attempts set to %s", backoff_attempts)
    logger.debug("Backoff max delay set to %s", backoff_max_delay)
    logger.debug("Backoff multiplier set to %s", backoff_multiplier)

    return Config(
        agent_name=agent_name,
        project_id=project_id,
        location=location,
        model=model,
        genai_use_vertexai=genai_use_vertexai,
        max_files_to_process=max_files_to_process,
        backoff_init_delay=backoff_init_delay,
        backoff_attempts=backoff_attempts,
        backoff_max_delay=backoff_max_delay,
        backoff_multiplier=backoff_multiplier
    )

