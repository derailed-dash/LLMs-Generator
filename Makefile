SHELL := /bin/bash

# Hide unwanted messages - to use, just add ${GREP_FILTER} to any command
GREP_FILTER = 2>&1 | grep -v -e '^$$' -e 'WSL' -e 'xdg-open'

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync --dev --extra jupyter

# Launch local dev playground
playground:
	@echo "================================================================================="
	@echo "| 🚀 Starting your agent playground...                                          |"
	@echo "|                                                                               |"
	@echo "| 🔍 Select your required agent and then interact                               |"
	@echo "================================================================================="
	uv run adk web --port 8501 src

cli:
	@echo "================================================================================="
	@echo "| 🚀 Starting your ADK CLI...                                                   |"
	@echo "================================================================================="
	uv run adk run src/llms_gen_agent

# Run unit and integration tests
test:
	@test -n "$(GOOGLE_CLOUD_PROJECT)" || (echo "Error: GOOGLE_CLOUD_PROJECT is not set. Setup environment before running tests" && exit 1)
	uv run pytest src/tests/unit
	-uv run pytest src/tests/integration # Don't fail the task if integration tests fail

# Run code quality checks (codespell, ruff, mypy)
lint:
	@echo "Running code quality checks..."
	uv sync --dev --extra jupyter --extra lint 
	uv run codespell -s
	uv run ruff check . --diff
	uv run mypy .

