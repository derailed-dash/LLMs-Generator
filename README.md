# LLMS-Generator

## Repo Metadata

Author: Darren Lester

## Table of Contents

- [Repo Overview](#repo-overview)
- [Getting Started](#getting-started)
- [How to Use the Generated llms.txt](#how-to-use-the-generated-llmstxt)
- [Associated Articles](#associated-articles)
- [Useful Commands](#useful-commands)
  - [Testing](#testing)
  - [Running in a Local Container](#running-in-a-local-container)

## Getting Started

To get started with LLMS-Generator, follow these steps:

### Prerequisites

*   **uv:** Ensure you have `uv` installed for Python package and environment management. If not, you can install it by following the instructions on the [uv website](https://astral.sh/uv/install/).
*   **Google Cloud SDK:** Install the Google Cloud SDK to interact with GCP services. Follow the official [Google Cloud SDK documentation](https://cloud.google.com/sdk/docs/install) for installation instructions.
*   **make:** Ensure `make` is installed on your system. It's typically available on most Unix-like systems.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AnswerDotAI/llms-generator.git
    cd llms-generator
    ```
2.  **Set up your environment:**
    Run the setup script to configure your Google Cloud project and authentication.
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

## Repo Overview

_LLMS-Generator_ is an agentic solution designed to create a `llms.txt` file for any given repo or folder.

The `llms.txt` file is an AI/LLM-friendly markdown file that enables an AI to understand the purpose of the a repo, as well as have a full understanding of the repo site map and the purpose of each file it finds. This is particularly useful when providing AIs (like Gemini) access to documentation repos.

The `llms.txt` file will have this structure:

- An H1 with the name of the project or site
- An overview of the project / site purpose.
- Zero or more markdown sections delimited by H2 headers, containing appropriate section summaries.
- Each section contains a list of of markdown hyperlinks, in the format: `[name](url): summary`.

See [here](https://github.com/AnswerDotAI/llms-txt) for a more detailed description of the `llms.txt` standard.

## How to Use the Generated llms.txt

An AI can easily read the `llms.txt` and follow the links it finds there. When you ask your agent a deep-dive question about a topic, the agent will be able to follow the appropriate links to give you grounded answers.

## Associated Articles

Coming soon

## Useful Commands

| Command                       | Description                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| `source scripts/setup-env.sh` | Setup Google Cloud project and auth with Dev/Staging. Parameter options:<br> `[--noauth] [-t\|--target-env <DEV\|PROD>]` |
| `make install`                | Install all required dependencies using `uv` |
| `make playground`             | Launch UI for testing agent locally and remotely. This runs `uv run adk web src` |
| `make test`                   | Run unit and integration tests |
| `make lint`                   | Run code quality checks (codespell, ruff, mypy) |
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

With CLI:

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
