"""This module provides configuration for the LLMS-Generator agent."""

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
DEFAULT_EXCLUDED_DIRS = ".git,.github,overrides,.venv,node_modules,__pycache__,.pytest_cache"
DEFAULT_EXCLUDED_FILES = "__init__"
DEFAULT_INCLUDED_EXTENSIONS = ".md,.py"

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

    excluded_dirs: set[str]
    excluded_files: set[str]
    included_extensions: set[str]
    
    valid: bool = True # Set this to False to force config reload from env vars
    
    def invalidate(self):
        """ Invalidate current config. This forces the config to be refreshed from the environment when
        get_config() is next called. """
        logger.debug("Invalidating current config.")
        self.valid = False

    def __str__(self):
        return (
            f"Agent Name: {self.agent_name}\n"
            f"Project ID: {self.project_id}\n"
            f"Location: {self.location}\n"
            f"Model: {self.model}\n"
            f"GenAI Use VertexAI: {self.genai_use_vertexai}\n"
            f"Max Files To Process: {self.max_files_to_process}\n"
            f"Backoff Init Delay: {self.backoff_init_delay}\n"
            f"Backoff Attempts: {self.backoff_attempts}\n"
            f"Backoff Max Delay: {self.backoff_max_delay}\n"
            f"Backoff Multiplier: {self.backoff_multiplier}\n"
            f"Excluded Dirs: {self.excluded_dirs}\n"
            f"Excluded Files: {self.excluded_files}\n"
            f"Included Extensions: {self.included_extensions}\n"
        )

def _get_env_var(key: str, default_value: str, type_converter: Callable=str):
    """Helper to get environment variables with a default and type conversion."""
    return type_converter(os.environ.setdefault(key, default_value))

current_config = None

def setup_config() -> Config:
    """Gets the application configuration by reading from the environment.
    The expensive Google Auth call to determine the project ID is only performed once.
    If the current_config is invalid, the config will be refreshed from the environment.
    Otherwise, the cached config is returned.

    Returns:
        Config: An object containing the current application configuration.

    Raises:
        ConfigError: If the GCP Project ID cannot be determined on the first call.
    """
    global current_config
    
    # Load env vars
    location = _get_env_var("GOOGLE_CLOUD_LOCATION", DEFAULT_GCP_LOCATION)
    model = _get_env_var("MODEL", DEFAULT_MODEL)
    genai_use_vertexai = _get_env_var("GOOGLE_GENAI_USE_VERTEXAI", DEFAULT_GENAI_USE_VERTEXAI, lambda x: x.lower() == "true")
    max_files_to_process = _get_env_var("MAX_FILES_TO_PROCESS", DEFAULT_MAX_FILES_TO_PROCESS, int)
    backoff_init_delay = _get_env_var("BACKOFF_INIT_DELAY", DEFAULT_BACKOFF_INIT_DELAY, int)
    backoff_attempts = _get_env_var("BACKOFF_ATTEMPTS", DEFAULT_BACKOFF_ATTEMPTS, int)
    backoff_max_delay = _get_env_var("BACKOFF_MAX_DELAY", DEFAULT_BACKOFF_MAX_DELAY, int)
    backoff_multiplier = _get_env_var("BACKOFF_MULTIPLIER", DEFAULT_BACKOFF_MULTIPLIER, int)
    excluded_dirs = set(_get_env_var("EXCLUDED_DIRS", DEFAULT_EXCLUDED_DIRS).split(','))
    excluded_files = set(_get_env_var("EXCLUDED_FILES", DEFAULT_EXCLUDED_FILES).split(','))
    included_extensions = set(_get_env_var("INCLUDED_EXTENSIONS", DEFAULT_INCLUDED_EXTENSIONS).split(','))
    
    if current_config: # If we've already loaded the config before
        if current_config.valid: # return it as is
            return current_config
        else: # Current config invalid - we need to update it
            current_config.location=location
            current_config.model=model
            current_config.genai_use_vertexai=genai_use_vertexai
            current_config.max_files_to_process=max_files_to_process
            current_config.backoff_init_delay=backoff_init_delay
            current_config.backoff_attempts=backoff_attempts
            current_config.backoff_max_delay=backoff_max_delay
            current_config.backoff_multiplier=backoff_multiplier
            current_config.excluded_dirs=excluded_dirs
            current_config.excluded_files=excluded_files
            current_config.included_extensions=included_extensions
            
            logger.info(f"Updated config:\n{current_config}")
            return current_config            

    # If we're here, then we've never created a config before
    _, project_id = google.auth.default()
    if not project_id:
        raise ConfigError("GCP Project ID not set. Have you run scripts/setup-env.sh?")

    current_config = Config(
        agent_name=agent_name,
        project_id=project_id,
        location=location,
        model=model,
        genai_use_vertexai=genai_use_vertexai,
        max_files_to_process=max_files_to_process,
        backoff_init_delay=backoff_init_delay,
        backoff_attempts=backoff_attempts,
        backoff_max_delay=backoff_max_delay,
        backoff_multiplier=backoff_multiplier,
        excluded_dirs=excluded_dirs,
        excluded_files=excluded_files,
        included_extensions=included_extensions
    )
    
    logger.info(f"Loaded config:\n{current_config}")
    return current_config

