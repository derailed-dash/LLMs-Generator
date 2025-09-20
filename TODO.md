
# TODO

- [ ] Add logging during subagent calls - maybe with callbacks?
- [x] Eliminate 429/quote issues when calling Gemini, particularly from `document_summariser_agent`.
- [ ] Complete project summarisation step.
- [ ] Complete final `llms.txt` file creation.
- [ ] Remove temporary restriction on number of docs summarised.
- [ ] Implement parallel processing in `document_summariser_agent` to improve performance.
- [ ] Provide a client way to run the application without having to send a prompt, e.g. using CLI arguments.
- [ ] Increase test coverage by adding unit tests for the agents and other utility functions.
- [ ] Add integration tests to test the end-to-end functionality of the agent.
- [ ] Make repo public.
- [ ] Make the list of excluded directories in `discover_files` configurable.
