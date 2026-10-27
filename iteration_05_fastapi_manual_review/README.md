ITERATION 5: FASTAPI AND MANUAL REVIEW

- Overall project method: iterative and incremental development.
- Method used inside this increment: build -> test -> fix/rebuild this same increment -> retest -> accept.
- Why this method fits: the manual-review API and state have clear interfaces after the Python pipeline is complete, while endpoint and state errors can be corrected through tests.
- This project includes Iterations 1 to 4 plus the local web backend.
- Design: refinement service -> FastAPI endpoints -> report, status, download, and manual-choice state.
- Added: FastAPI endpoints, live refinement status, reports, view/download endpoints, manual-review state, and final reconstruction after manual choices.
- Decision rule: public factual conflicts use local Ollama; explicitly personal/private conflicts are kept for user choice.
- Testing: private-scope and manual-verification API tests.
- Integration: refinement, report, download, and manual-choice state are exposed through FastAPI endpoints.
- Deliverable: the backend can support a full user workflow without a final frontend yet.
- Acceptance condition: API and manual-verification tests pass, including state updates after a user choice.
- Iteration handling: if an endpoint or review state fails, correct the FastAPI/manual workflow in this iteration and retest.
- Next iteration: integrate the full React/Vite frontend and validate the end-to-end system.
