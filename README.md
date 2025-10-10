# LLMS-Generator

## Table of Contents

- [Repo Metadata](#repo-metadata)
- [Repo Overview](#repo-overview)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Installation](#installation)
- [How to Use](#how-to-use)
  - [Command](#command)
  - [Arguments](#arguments)
  - [Options](#options)

- [How to Use the Generated llms.txt](#how-to-use-the-generated-llmstxt)
- [Associated Articles](#associated-articles)
- [Useful Commands](#useful-commands)
  - [Testing](#testing)
  - [Running in a Local Container](#running-in-a-local-container)

## Repo Metadata

Author: Darren Lester

## Repo Overview

_LLMS-Generator_ is an agentic solution designed to create a `llms.txt` file for any given repo or folder.

The `llms.txt` file is an AI/LLM-friendly markdown file that enables an AI to understand the purpose of the a repo, as well as have a full understanding of the repo site map and the purpose of each file it finds. This is particularly useful when providing AIs (like Gemini) access to documentation repos.

An `llms.txt` file should have this structure:

- An `H1` with the name of the project or site
- An overview of the project / site purpose.
- Zero or more markdown sections delimited by `H2` headers, containing appropriate section summaries.
- Each section contains a list of of markdown hyperlinks, in the format: `[name](url): summary`.

See [here](https://github.com/AnswerDotAI/llms-txt) for a more detailed description of the `llms.txt` standard.

## How to Use the Generated llms.txt

An AI can easily read the `llms.txt` and follow the links it finds there. When you ask your agent a deep-dive question about a topic, the agent will be able to follow the appropriate links to give you grounded answers.

It is easy to provide an agent with the ability to consume an `llms.txt` file with an MCP server, like this one: [ADK-Docs-Ext](https://github.com/derailed-dash/adk-docs-ext).

## Related Links and Docs

- [Give Your AI Agents Deep Understanding With LLMS.txt](https://medium.com/google-cloud/give-your-ai-agents-deep-understanding-with-llms-txt-4f948590332b)
- [Give Your AI Agents Deep Understanding - Creating the LLMS.txt with a Multi-Agent ADK Solution - Coming Soon](tbd)
- [ADK Docs Extension for Gemini CLI](https://github.com/derailed-dash/adk-docs-ext)

## Solution Design

![Solution Design Diagram](docs/generate-llms-adk.drawio.png)

Check the design [here](docs/solution-design.md).

## Getting Started

To get started with LLMS-Generator, follow these steps:

### Prerequisites

*   **uv:** Ensure you have `uv` installed for Python package and environment management. If not, you can install it by following the instructions on the [uv website](https://astral.sh/uv/install/).
*   **Google Cloud SDK:** Install the Google Cloud SDK to interact with GCP services. Follow the official [Google Cloud SDK documentation](https://cloud.google.com/sdk/docs/install) for installation instructions.
*   **make:** Ensure `make` is installed on your system. It's typically available on most Unix-like systems.

### Environment Variables

This project uses a `.env` file to manage environment variables. Before running the application, you need to create a `.env` file in the root of the project.

You can copy the example below and customize it with your own values.

```bash
# .env

export GOOGLE_CLOUD_STAGING_PROJECT="your-staging-project-id"
export GOOGLE_CLOUD_PRD_PROJECT="your-prod-project-id"

# These Google Cloud variables are set by the scripts/setup-env.sh script
# GOOGLE_CLOUD_PROJECT=""
# GOOGLE_CLOUD_LOCATION="global"

export PYTHONPATH="src"

# Agent variables
export AGENT_NAME="llms_gen_agent" # The name of the agent
export MODEL="gemini-2.5-flash" # The model used by the agent
export GOOGLE_GENAI_USE_VERTEXAI="True" # True to use Vertex AI for auth; else use API key
export LOG_LEVEL="INFO"
export MAX_FILES_TO_PROCESS=10 # Set to 0 for no limit

# Exponential backoff parameters for the model API calls
export BACKOFF_INIT_DELAY=5
BACKOFF_ATTEMPTS=5
BACKOFF_MAX_DELAY=60
BACKOFF_MULTIPLIER=2 # exponential delay growth
```

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/derailed-dash/llms-generator.git
    cd llms-generator
    ```
2.  **Set up your environment:**
    Run the setup script to configure your Google Cloud project and authentication, and load environment variables from `.env`.
    ```bash
    source scripts/setup-env.sh
    ```
    This script will guide you through setting up the necessary environment variables and authenticating with Google Cloud.
3.  **Install dependencies:**
    Use `make install` to install all required Python dependencies using `uv`.
    ```bash
    make install
    ```

After completing these steps, your environment will be set up, and all dependencies will be installed, ready for development or running the agent.

## How to Use

Once the dependencies are installed and the environment is set up, you can use the `llms-gen` command-line tool to generate the `llms.txt` file.

### Command

The `llms-gen` command-line application is exposed via the `[project.scripts]` section in `pyproject.toml`. When the package is installed, this entry point allows you to run `llms-gen` directly from your terminal, which executes the `app` object defined in `src/client_fe/cli.py`.

```bash
llms-gen --repo-path /path/to/your/repo [OPTIONS]
```

E.g.

```bash
llms-gen --repo-path "/home/darren/localdev/gcp/adk-docs"
```

### Arguments

*   `--repo-path` / `-r`: (Required) The absolute path to the repository to generate the `llms.txt` file for.

### Options

*   `--output-path` / `-o`: The absolute path to save the `llms.txt` file. If not specified, it will be saved in a `temp` directory in the current working directory.
*   `--log-level` / `-l`: Set the log level for the application (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`). This will override any `LOG_LEVEL` environment variable.

## Useful Commands

| Command                       | Description                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| `source scripts/setup-env.sh` | Setup Google Cloud project and auth with Dev/Staging. Parameter options:<br> `[--noauth] [-t\|--target-env <DEV\|PROD>]` |
| `make install`                | Install all required dependencies using `uv` |
| `make playground`             | Launch UI for testing agent locally and remotely. This runs `uv run adk web src` |
| `make test`                   | Run unit and integration tests |
| `make lint`                   | Run code quality checks (codespell, ruff, mypy) |
| `make generate`               | Execute the Llms-Generator command line application |
| `uv run jupyter lab`          | Launch Jupyter notebook |

For full command options and usage, refer to the [Makefile](Makefile).

### Testing

- All tests are in the `src/tests` folder.
- We can run our tests with `make test`.
- Note that integration tests will fail if the development environment has not first been configured with the `setup-env.sh` script. This is because the test code will not have access to the required Google APIs.
- If we want to run tests verbosely, we can do this:

  ```bash
  uv run pytest -v -s src/tests/unit/test_name.py
  ```

#### Testing Locally

With ADK CLI:

```bash
uv run adk run src/llms_gen_agent
```

With GUI:

```bash
# Last param is the location of the agents
uv run adk web src

# Or we can use the Agent Starter Git make aliases
make install && make playground
```

### Running in a Local Container

```bash
# from project root directory

# Get a unique version to tag our image
export VERSION=$(git rev-parse --short HEAD)

# To build as a container image
docker build -t $SERVICE_NAME:$VERSION .

# To run as a local container
# We need to pass environment variables to the container
# and the Google Application Default Credentials (ADC)
docker run --rm -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT -e GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION \
  -e LOG_LEVEL=$LOG_LEVEL \
  -e APP_NAME=$APP_NAME \
  -e AGENT_NAME=$AGENT_NAME \
  -e GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI \
  -e MODEL=$MODEL \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/.config/gcloud/application_default_credentials.json" \
  --mount type=bind,source=${HOME}/.config/gcloud,target=/app/.config/gcloud \
   $SERVICE_NAME:$VERSION
```
