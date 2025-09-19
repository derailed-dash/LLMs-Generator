# Project: LLMS-Generator

---
***IMPORTANT: Run this check at the start of EVERY session!***

Google Cloud configuration is achieved through a combination of `.env` and the `scripts/setup-env.sh` script. 

Before providing your FIRST response in any conversation, you MUST perform the following steps:
1.  Run `printenv GOOGLE_CLOUD_PROJECT` to check the environment variable.
2.  Based only on the output of that command, state whether the variable is set.
3.  If it is not set, advise me to run `scripts/setup-env.sh` before resuming the conversation.

The presence of this environment variable indicates that the script has been run. The absence of this variable indicates that the script has NOT been run.

Note that failures with Google Cloud are likely if this script has not been run. For example, tests will fail. If tests are failing, we should check if the script has been run.
---

## Project Overview

_LLMS-Generator_ is an agentic solution designed to create a `llms.txt` file for any given repo or folder.

The `llms.txt` file is an AI/LLM-friendly markdown file that enables an AI to understand the purpose of the a repo, as well as have a full understanding of the repo site map and the purpose of each file it finds. This is particularly useful when providing AIs (like Gemini) access to documentation repos.

The `llms.txt` file will have this structure:

- An H1 with the name of the project or site
- An overview of the project / site purpose.
- Zero or more markdown sections delimited by H2 headers, containing appropriate section summaries.
- Each section contains a list of of markdown hyperlinks, in the format: `[name](url): summary`.

See [here](https://github.com/AnswerDotAI/llms-txt) for a more detailed description of the `llms.txt` standard.

## Building and Running

### Dependencies

- **uv:** Python package manager
- **Google Cloud SDK:** For interacting with GCP services
- **make:** For running common development tasks

Project dependencies are managed in `pyproject.toml` and can be installed using `uv`. The `make` commands streamline many `uv` and `adk` commands.

## Development Guide

- **Configuration:** Project dependencies and metadata are defined in `pyproject.toml`.
- **Dependencies:** Project dependencies are managed in `pyproject.toml`. The `[project]` section defines the main dependencies, and the `[dependency-groups]` section defines development and optional dependencies.
- **Source code:** Lives in the `src/` directory. This includes agents, frontends, notebooks and tests.
- **Notebooks:** The `notebooks/` directory contains Jupyter notebooks for prototyping, testing, and evaluating the agent.
- **Testing:** The project includes unit and integration tests in `src/tests/`. Tests are written using `pytest` and `pytest-asyncio`. They can be run with `make test`
- **Linting:** The project uses `ruff` for linting and formatting, `mypy` for static type checking, and `codespell` for checking for common misspellings. The configuration for these tools can be found in `pyproject.toml`. We can run linting with `make lint`.
- **AI-Assisted Development:** The `GEMINI.md` file provides context for AI tools like Gemini CLI to assist with development.

## Project Plan

- The `TODO.md` captures the overall plan for this project.
