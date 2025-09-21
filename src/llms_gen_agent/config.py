"""This module provides configuration for the LLMS-Generator agent."""

import functools
import os
from dataclasses import dataclass

import google.auth

from common_utils.exceptions import ConfigError
from common_utils.logging_utils import setup_logger

agent_name = os.environ.setdefault("AGENT_NAME", "llms_gen_agent")
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

@functools.lru_cache(maxsize=1)
def get_config() -> Config:
    """Return a dictionary of the current config by reading from environment."""

    _, project_id = google.auth.default()
    if not project_id:
        raise ConfigError("GCP Project ID not set. Have you run scripts/setup-env.sh?")
    location = os.environ.setdefault(
        "GOOGLE_CLOUD_LOCATION", "global"
    )  # assume set as env var, but fail back to global
    model = os.environ.setdefault("MODEL", "gemini-2.5-flash")
    genai_use_vertexai = os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "true"
    max_files_to_process = int(os.environ.setdefault("MAX_FILES_TO_PROCESS", "0")) # 0 means no limit
    backoff_init_delay = int(os.environ.setdefault("BACKOFF_INIT_DELAY", "2"))
    backoff_attempts = int(os.environ.setdefault("BACKOFF_ATTEMPTS", "5"))
    backoff_max_delay = int(os.environ.setdefault("BACKOFF_MAX_DELAY", "60"))
    backoff_multiplier = int(os.environ.setdefault("BACKOFF_MULTIPLIER", "2"))

    logger.debug("agent_name set to %s", agent_name)
    logger.debug("project_id set to %s", project_id)
    logger.debug("location set to %s", location)
    logger.debug("model set to %s", model)
    logger.debug("max_files_to_process set to %s", max_files_to_process)
    logger.debug("genai_use_vertexai set to %s", genai_use_vertexai)
    logger.debug("backoff_attempts set to %s", backoff_attempts)

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

