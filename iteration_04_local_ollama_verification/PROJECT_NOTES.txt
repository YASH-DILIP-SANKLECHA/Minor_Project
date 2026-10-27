ITERATION 4: LOCAL OLLAMA VERIFICATION

- Overall project method: iterative and incremental development.
- Method used inside this increment: build -> test -> fix/rebuild this same increment -> retest -> accept.
- Why this method fits: after contradiction candidates exist, local public-fact verification has a bounded interface whose response handling can be corrected through tests.
- This project includes Iterations 1 to 3 plus local AI verification.
- Design: public contradiction candidate -> constrained local Qwen decision -> validated keep/remove outcome.
- Added: Ollama client, Qwen structured-decision handling, candidate deduplication, and verification response tests.
- Testing: verification response parsing, ambiguous-response handling, and candidate deduplication tests.
- Decision rule: established public facts are resolved by local Ollama using KEEP_FIRST or KEEP_SECOND.
- Cost: no paid API; the Ollama model runs locally.
- Integration: verified KEEP_FIRST or KEEP_SECOND decisions are passed to reconstruction.
- Deliverable: public factual conflicts can be automatically resolved after candidate detection.
- Acceptance condition: valid local verification decisions are applied and private claims are not guessed automatically.
- Iteration handling: if a response is ambiguous or parsing fails, correct the verification handling in this iteration and retest.
- Next iteration: add FastAPI state and manual-review handling.
