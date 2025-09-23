# Solution Design: LLMS-Generator

## 1. Goals

The primary goal of the LLMS-Generator is to create a `llms.txt` file for any given code repository. This file is designed to be easily parsable by Large Language Models (LLMs), providing them with a structured and summarized understanding of the repository's content and layout. This enables more accurate and context-aware interactions with the codebase by AI agents.

The `llms.txt` file will adhere to a specific format, including:
- A main header (`H1`) with the project's name.
- A high-level overview of the project's purpose.
- Sections (`H2`) representing repository directories.
- A list of markdown links to files within each section, with a concise summary for each file.

## 2. Summary of Functional Requirements

- The application must be initiated via a Command Line Interface (CLI).
- The user must provide the absolute path to the target repository.
- The user can optionally specify an output path for the generated `llms.txt` file.
- The application must intelligently discover relevant files (e.g., `.md`, `.py`) while ignoring irrelevant directories and files (e.g., `.git`, `__pycache__`, `.venv`).
- The application must generate a concise summary for each discovered file.
- The application must generate a high-level summary of the entire project.
- The application must construct the `llms.txt` file in the specified format, including the project and file summaries.
- The application must handle both local repositories (using relative file paths) and GitHub repositories (using full GitHub URLs).
- The system must be resilient to API errors (e.g., rate limiting) by implementing a retry mechanism.
- The application's behavior should be configurable through environment variables (e.g., log level, maximum number of files to process).

## 3. Summary of Non-Functional Requirements

- **Usability:** The CLI should be intuitive and easy to use for developers.
- **Reliability:** The application should be robust, with graceful error handling for issues like invalid paths or API failures.
- **Performance:** While summarization is time-intensive, the application should be reasonably performant. A configurable file limit (`MAX_FILES_TO_PROCESS`) is included to manage performance on very large repositories.
- **Extensibility:** The agent-based architecture should allow for easy addition of new features and modification of existing logic.
- **Maintainability:** The codebase is modular, with a clear separation of concerns (CLI, agent logic, tools), to facilitate easy maintenance.
- **Testability:** The project includes a suite of unit tests, and the `Makefile` provides a simple command for running them.

## 4. Solution Design

The LLMS-Generator is implemented as an agentic application using the `google-adk` framework. The architecture is composed of a CLI, an orchestrator agent, and several sub-agents and tools.

- **User Interface (UI):** A CLI built with `Typer` serves as the primary entry point for the user. It is defined in `src/client_fe/cli.py`.

- **Orchestrator Agent:** The `generate_llms_coordinator` in `src/llms_gen_agent/agent.py` is the main agent that orchestrates the entire workflow.

- **Workflow:**
  1. The user runs the `llms-gen` command from the CLI, providing the repository path.
  2. The CLI invokes the `runner.py` script, which sets up the ADK `Runner` and `Session` and starts the `generate_llms_coordinator` agent.
  3. The `generate_llms_coordinator` agent executes the following sequence:
     a. It calls the `discover_files` tool to get a list of all relevant file paths in the repository.
     b. It delegates the summarization task to the `document_summariser_agent`.
     c. The `document_summariser_agent` (a `SequentialAgent`) first uses the `file_reader_agent` to read the content of each file. A callback (`after_file_read_callback`) stores this content in the session state.
     d. Next, the `content_summariser_agent` processes the file contents from the session state, generating a summary for each file and an overall project summary. A callback (`strip_json_markdown_callback`) is used to clean the LLM's JSON output.
     e. The `generate_llms_coordinator` receives the summaries from the sub-agent.
     f. Finally, it calls the `generate_llms_txt` tool to write the final `llms.txt` file.

- **Sub-Agents:** The `document_summariser_agent` is a `SequentialAgent` that composes the `file_reader_agent` and `content_summariser_agent`, demonstrating a modular, multi-agent approach.

- **Tools:** The system relies on a set of tools to interact with the file system and process data:
  - `discover_files`: Scans the repository to find files.
  - `adk_file_read_tool`: Reads the content of a file.
  - `generate_llms_txt`: Writes the final `llms.txt` file.

- **Configuration:** Application configuration is managed through a `.env` file and environment variables, loaded by `src/llms_gen_agent/config.py`.

## 5. Key Design Decisions

- **Agent-Based Architecture (`google-adk`):**
  - **Rationale:** This provides a modular and extensible framework. By breaking down the logic into independent agents and tools, the system is easier to develop, test, and maintain. It also allows for the orchestration of complex workflows by the LLM.

- **`SequentialAgent` for Summarisation:**
  - **Rationale:** The summarization process is naturally a two-step sequence: read all files, then summarize them. Using a `SequentialAgent` ensures this order of operations, leading to a more reliable and predictable workflow.

- **Command Line Interface (`Typer`):**
  - **Rationale:** A CLI is a standard and efficient interface for a developer-focused tool. `Typer` simplifies the creation of a clean and professional CLI, complete with automatic help generation and argument parsing.

- **Configuration via `.env` and Environment Variables:**
  - **Rationale:** This is a standard practice for managing application settings. It allows for easy configuration for different environments (development, testing, production) without modifying the source code.

- **Callbacks for Post-Processing:**
  - **Rationale:** Callbacks (`after_file_read_callback`, `strip_json_markdown_callback`) provide a powerful mechanism for injecting custom logic into the agent's execution lifecycle. This is used to store data in the session state and to clean up LLM output before validation, keeping the core agent logic clean and focused.

- **Schema Validation with `pydantic`:**
  - **Rationale:** Using `pydantic` models like `DocumentSummariesOutput` to define the expected output schema for the summarization agent makes the system more robust. It ensures that the data passed between agents is in the correct format, reducing the likelihood of runtime errors.

- **Exponential Backoff for API Calls:**
  - **Rationale:** The implementation of `HttpRetryOptions` with exponential backoff is a critical design choice for ensuring reliability. It makes the agent resilient to transient network issues and API rate-limiting errors, which is particularly important for a process that makes numerous API calls.
