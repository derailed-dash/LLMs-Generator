
# TODO

- [x] Eliminate 429/quote issues when calling Gemini, particularly from `document_summariser_agent`.
- [x] Add callback to ensure doc summariser agent creates output in the correct JSON format.
- [x] Add sequential agent such that all files are read first, and then all content is summarised second.
- [x] Add callback to capture the output of read files and store in session state.
- [ ] Complete project summarisation step.
- [ ] Fewer sections, controlled by folder depth.
- [ ] Complete final `llms.txt` file creation.
- [ ] Remove temporary restriction on number of docs summarised.
- [ ] Provide a client way to run the application without having to send a prompt, e.g. using CLI arguments.
- [ ] Make repo public.
- [ ] Write blog.
- [ ] Increase test coverage by adding unit tests for the agents and other utility functions.
- [ ] Add integration tests to test the end-to-end functionality of the agent.
- [ ] Make the list of excluded directories in `discover_files` configurable.
