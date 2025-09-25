# Solution Design: LLMS-Generator

## 1. Goals

The goal of the LLMS-Generator is to create a llms.txt file for any given code repository or folder. Th llms.txt file is designed to be easily parsable by Large Language Models (LLMs), providing them with a structured and summarised understanding of the repo's content and layout. This enables more accurate and context-aware interactions with the codebase by AI agents; e.g. with Gemini CLI.

The `llms.txt` file will adhere to a specific format, including:
- A main header (`H1`) with the project's name.
- A high-level overview of the project's purpose.
- Sections (`H2`) representing repository directories.
- A list of markdown links to files within each section, with a concise summary for each file.

## 2. Functional Requirements

- The application must be initiated via a Command Line Interface (CLI).
- The user must provide the absolute path to the target repository.
- The user can optionally specify an output path for the generated `llms.txt` file.
- The application must intelligently discover relevant files (e.g., `.md`, `.py`) while ignoring irrelevant directories and files (e.g., `.git`, `__pycache__`, `.venv`).
- The application must generate a concise summary for each discovered file.
- The application must generate a high-level summary of the entire project.
- The application must construct the `llms.txt` file in the specified format, including the project and file summaries.
- The application must handle both local repositories (using relative file paths) and GitHub repositories (using full GitHub URLs).
- The application's behavior should be configurable through environment variables (e.g., log level, maximum number of files to process).

## 3. Architecturally Significant Requirements (NFRs)

- **Concurrency:** This is a developer-centric application. Initially it will run locally, and there is no need for concurrent use. This could be added later.
- **Reliability:** The application should be robust, with graceful error handling for issues like invalid paths or API failures. The system must be resilient to API rate limiting by implementing a retry mechanism.
- **High availability and DR:** As an infrequently and locally run developer-centric application, there is no requirement for HA or DR.
- **Performance:** While summarisation is time-intensive, the application should be reasonably performant. A configurable file limit should be included to manage performance on very large repositories.
- **Extensibility:** The agent-based architecture should allow for easy addition of new features and modification of existing logic.
- **Maintainability:** The codebase is modular, with a clear separation of concerns (CLI, agent logic, tools), to facilitate easy maintenance.
- **Testability:** The project should include a suite of unit tests.

## 4. Solution Design

The LLMS-Generator is implemented as an agentic application using the `google-adk` framework. The architecture is composed of a CLI, an orchestrator agent, and several sub-agents and tools.

The solution design below shows component interactions, and the arrow labels show the sequence of interactions:

![Solution Design Diagram](generate-llms-adk.drawio.png)

- **Sub-Agents:** The `document_summariser_agent` is a `SequentialAgent` that composes the `file_reader_agent` and `content_summariser_agent`, demonstrating a modular, multi-agent approach.

- **Tools:** The system relies on a set of tools to interact with the file system and process data:
  - `discover_files`: Scans the repository to find files.
  - `adk_file_read_tool`: Reads the content of a file.
  - `generate_llms_txt`: Writes the final `llms.txt` file.

- **Configuration:** Application configuration is managed through a `.env` file and environment variables, loaded by `src/llms_gen_agent/config.py`.

## 5. Key Design Decisions

- **Use Generative AI:** since we need to summarise artifacts (including documentation and code) in a folder or repo, a generative AI solution is ideal.

- **Use Gemini-2.5-Flash:** Gemini is a leading multi-modal foundation model, well-suited to the task of document summarisation. Flash is used because it is both faster and cheaper than Pro, and we do not need the more sophisticated reasoning capabilities of the Pro model.

- **Agent-Based Architecture (`google-adk`):**
  - **Rationale:** This provides a modular and extensible framework. By breaking down the logic into independent agents and tools, the system is easier to develop, test, and maintain. It also allows for the orchestration of complex workflows by the LLM.

- **Sequential Agent for Summarisation:**
  - **Rationale:** The summarisation process is naturally a two-step sequence: read all files, then summarize them. Using a `SequentialAgent` ensures this order of operations, leading to a more reliable and predictable workflow.

- **Command Line Interface with `Typer`:**
  - **Rationale:** A CLI is a standard and efficient interface for a developer-focused tool. The `Typer` package simplifies the creation of a clean and professional CLI, complete with automatic help generation and argument parsing.

- **Schema Validation with `pydantic`:**
  - **Rationale:** UWe can define the expected output schema for the summarisation agent, to make the system more robust. This ensures that the data passed between agents is in the correct format, reducing the likelihood of runtime errors.

- **Exponential Backoff for API Calls:**
  - **Rationale:** The application may make frequent calls to the model in a short amount of time. This will lead to [429 errors](https://cloud.google.com/blog/products/ai-machine-learning/learn-how-to-handle-429-resource-exhaustion-errors-in-your-llms). We can mitigate with exponential backoff.

- **No persistence required:** it is expected that the entire flow can be accomplished without any need for external working storage or databases. If the workflow exceeds what is possible within model context, we can implement external persistence later. E.g. we could implement a simple Firestore database to store content we have gathered, and to build up the summaries, before returning them to the agent.

## 6. Workflow
  1. The user runs the `llms-gen` command from the CLI, providing the repository path.
  2. The CLI invokes the `runner.py` script, which sets up the ADK `Runner` and `Session` and starts the `generate_llms_coordinator` agent.
  3. The `generate_llms_coordinator` agent executes the following sequence:
     a. It calls the `discover_files` tool to get a list of all relevant file paths in the repository.
     b. It delegates the summarization task to the `document_summariser_agent`.
     c. The `document_summariser_agent` (a `SequentialAgent`) first uses the `file_reader_agent` to read the content of all the files. The content is stored in the session state.
     d. Next, the `content_summariser_agent` processes the file contents from the session state, generating a summary for each file and an overall project summary. A callback (`clean_json_callback`) is used to clean the LLM's JSON output.
     e. The `generate_llms_coordinator` receives the summaries from the sub-agent.
     f. Finally, it calls the `generate_llms_txt` tool to write the final `llms.txt` file.
