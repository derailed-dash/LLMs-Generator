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

- **Sub-Agents:** The `document_summariser_agent` is a `SequentialAgent` that orchestrates a complex workflow involving batching, looping, and aggregation. It composes several sub-agents:
  - `batch_creation_agent`: Creates batches of files.
  - `batch_processing_loop`: A `LoopAgent` that iteratively processes each batch.
  - `project_summariser_agent`: Generates the overall project summary.
  - `final_summary_agent`: Combines all summaries into the final output format.

- **Tools:** The system relies on a set of tools to interact with the file system and process data:
  - `discover_files`: Scans the repository to find files.
  - `create_file_batches`: Splits the discovered files into manageable batches.
  - `read_files`: Reads the content of files for summarization.
  - `update_summaries`: Merges batch summaries into a master list.
  - `finalize_summaries`: Combines all summaries and the project summary into the final output.
  - `generate_llms_txt`: Writes the final `llms.txt` file.

**Note:** The `generate-llms-adk.drawio.png` diagram needs to be updated to reflect the new architecture.

- **Configuration:** Application configuration is managed through a `.env` file and environment variables, loaded by `src/llms_gen_agent/config.py`.

## 5. Key Design Decisions

- **Use Generative AI:** since we need to summarise artifacts (including documentation and code) in a folder or repo, a generative AI solution is ideal.

- **Use Gemini-2.5-Flash:** Gemini is a leading multi-modal foundation model, well-suited to the task of document summarisation. Flash is used because it is both faster and cheaper than Pro, and we do not need the more sophisticated reasoning capabilities of the Pro model.

- **Agent-Based Architecture (`google-adk`):**
  - **Rationale:** This provides a modular and extensible framework. By breaking down the logic into independent agents and tools, the system is easier to develop, test, and maintain. It also allows for the orchestration of complex workflows by the LLM.

- **Sequential Agent for Summarisation (with Batching and Looping):**
  - **Rationale:** The summarization process for potentially large codebases is now handled by a sophisticated `SequentialAgent` (`document_summariser_agent`) that orchestrates a multi-step workflow. This workflow involves:
    1.  **Batching:** Files are split into smaller, manageable batches to prevent exceeding LLM context windows.
    2.  **Iterative Processing:** A `LoopAgent` processes each batch sequentially, ensuring all files are summarized.
    3.  **Aggregation:** Summaries from individual batches are collected and merged into a comprehensive list.
    This approach ensures a reliable, predictable, and scalable summarization process, even for extensive repositories.

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
     a. It calls the `discover_files` tool to get a list of all relevant file paths in the repository. The discovered files are stored in the session state.
     b. It delegates the summarization task to the `document_summariser_agent`.
     c. The `document_summariser_agent` (a `SequentialAgent`) orchestrates the following steps:
        i.  The `batch_creation_agent` calls the `create_file_batches` tool to split the discovered files into batches and stores them in the session state.
        ii. The `batch_processing_loop` (a `LoopAgent`) then iteratively processes each batch:
            - The `batch_selector_agent` retrieves the next batch from the session state. If no more batches, it signals to exit the loop.
            - The `single_batch_processor` (a `SequentialAgent`) then processes the current batch:
                - The `file_reader_agent` reads the content of the files in the current batch. The content is stored in the session state.
                - The `content_summariser_agent` processes the file contents from the session state, generating a summary for each file in the batch.
                - The `update_summaries_agent` merges these batch summaries into a master `all_summaries` list in the session state.
        iii. After the loop completes, the `project_summariser_agent` reads the `all_summaries` and the project's `README.md` (if available) from the session state, and generates a high-level project summary.
        iv. The `final_summary_agent` combines the `all_summaries` and the generated project summary into the final `doc_summaries` format in the session state.
     d. The `generate_llms_coordinator` receives the final `doc_summaries` from the `document_summariser_agent`.
     e. Finally, it calls the `generate_llms_txt` tool to write the final `llms.txt` file using the collected summaries.
