"""Unit tests for the Config class in llms_gen_agent.config."""

import os
import sys
from unittest.mock import patch

import pytest

from common_utils.exceptions import ConfigError


@pytest.fixture(autouse=True)
def mock_env_and_auth():
    """Fixture to clear environment variables and mock google.auth.default for each test."""
    # Clear sys.modules to force re-import of config.py
    if "llms_gen_agent.config" in sys.modules:
        del sys.modules["llms_gen_agent.config"]

    with patch.dict(os.environ, {}, clear=True):
        with patch("google.auth.default", return_value=(None, None)) as mock_auth_default:
            yield mock_auth_default


def test_get_config_defaults(mock_env_and_auth):
    """Tests that get_config returns default values when no environment variables are set."""
    mock_env_and_auth.return_value = (None, "test-project-id")
    from llms_gen_agent.config import setup_config
    config = setup_config()

    assert config.agent_name == "llms_gen_agent"
    assert config.project_id == "test-project-id"
    assert config.location == "global"
    assert config.model == "gemini-2.5-flash"
    assert config.genai_use_vertexai is True


def test_get_config_env_vars(mock_env_and_auth):
    """Tests that get_config correctly reads values from environment variables."""
    env_vars = {
        "AGENT_NAME": "my-test-agent",
        "GOOGLE_CLOUD_PROJECT": "my-gcp-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "MODEL": "gemini-pro",
        "GOOGLE_GENAI_USE_VERTEXAI": "False",
    }
    with patch.dict(os.environ, env_vars):
        mock_env_and_auth.return_value = (None, "my-gcp-project")
        from llms_gen_agent.config import setup_config
        config = setup_config()

    assert config.agent_name == "my-test-agent"
    assert config.project_id == "my-gcp-project"
    assert config.location == "us-central1"
    assert config.model == "gemini-pro"
    assert config.genai_use_vertexai is False


def test_get_config_no_project_id(mock_env_and_auth):
    """Tests that get_config raises ConfigError if project ID is not set."""
    mock_env_and_auth.return_value = (None, None)
    from llms_gen_agent.config import setup_config
    with pytest.raises(ConfigError, match="GCP Project ID not set"):
        setup_config()
