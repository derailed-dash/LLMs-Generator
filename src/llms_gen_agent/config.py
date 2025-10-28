"""
This module provides a centralized configuration management system for the LLMS-Generator agent.

It defines a `Config` dataclass that holds all configuration parameters, and a `setup_config` 
function that loads these parameters from environment variables. This approach allows for easy 
configuration of the agent's behavior without modifying the source code.

Key Features:
- **Centralized Configuration:** All configuration parameters are managed in one place.
- **Environment-Based:** Configuration is loaded from environment variables, which can be
  conveniently managed using a `.env` file.
- **Default Values:** Sensible default values are provided for all parameters.
- **Type Safety:** The `Config` dataclass ensures that configuration parameters are of the
  correct type.
- **Caching:** The configuration is loaded only once and then cached for performance. The
  expensive `google.auth.default()` call to determine the GCP Project ID is also cached.
- **Dynamic Reloading:** The configuration can be dynamically reloaded by invalidating the
  cache, which is useful in long-running applications or testing scenarios.

How to Use:
To access the configuration in any part of the application, simply import and call the 
`setup_config` function:

    from llms_gen_agent.config import setup_config

    config = setup_config()
    print(f"Using model: {config.model}")

The `setup_config` function will return a `Config` object with all the current configuration
parameters.
"""

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
DEFAULT_BATCH_SIZE = "10"

agent_name = os.environ.get("AGENT_NAME", DEFAULT_AGENT_NAME)
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
    batch_size: int
    
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
            f"Batch Size: {self.batch_size}\n"
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
    return type_converter(os.environ.get(key, default_value))

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

    if current_config and current_config.valid:
        return current_config

    config_data = {
        "location": _get_env_var("GOOGLE_CLOUD_LOCATION", DEFAULT_GCP_LOCATION),
        "model": _get_env_var("MODEL", DEFAULT_MODEL),
        "genai_use_vertexai": _get_env_var(
            "GOOGLE_GENAI_USE_VERTEXAI", 
            DEFAULT_GENAI_USE_VERTEXAI, 
            lambda x: x.lower() == "true" # check if lowercase value is true, and return bool
        ),
        "max_files_to_process": _get_env_var("MAX_FILES_TO_PROCESS", DEFAULT_MAX_FILES_TO_PROCESS, int),
        "batch_size": _get_env_var("BATCH_SIZE", DEFAULT_BATCH_SIZE, int),
        "backoff_init_delay": _get_env_var("BACKOFF_INIT_DELAY", DEFAULT_BACKOFF_INIT_DELAY, int),
        "backoff_attempts": _get_env_var("BACKOFF_ATTEMPTS", DEFAULT_BACKOFF_ATTEMPTS, int),
        "backoff_max_delay": _get_env_var("BACKOFF_MAX_DELAY", DEFAULT_BACKOFF_MAX_DELAY, int),
        "backoff_multiplier": _get_env_var("BACKOFF_MULTIPLIER", DEFAULT_BACKOFF_MULTIPLIER, int),
        "excluded_dirs": set(_get_env_var("EXCLUDED_DIRS", DEFAULT_EXCLUDED_DIRS).split(',')),
        "excluded_files": set(_get_env_var("EXCLUDED_FILES", DEFAULT_EXCLUDED_FILES).split(',')),
        "included_extensions": set(_get_env_var("INCLUDED_EXTENSIONS", DEFAULT_INCLUDED_EXTENSIONS).split(','))
    }

    if current_config:  # Invalid config, so update it
        for key, value in config_data.items():
            setattr(current_config, key, value)
        current_config.valid = True
        logger.info(f"Updated config:\n{current_config}")
        return current_config
    else:  # First time setup, create a new config
        _, project_id = google.auth.default()
        if not project_id:
            raise ConfigError("GCP Project ID not set. Have you run scripts/setup-env.sh?")

        current_config = Config(
            agent_name=agent_name,
            project_id=project_id,
            **config_data
        )
        logger.info(f"Loaded config:\n{current_config}")
        return current_config

