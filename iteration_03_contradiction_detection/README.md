ITERATION 3: CONTRADICTION DETECTION

- Overall project method: iterative and incremental development.
- Method used inside this increment: build -> test -> fix/rebuild this same increment -> retest -> accept.
- Why this method fits: the bounded requirement is to distinguish possible factual conflicts from duplicate content, while extraction and scoring can be refined through tests.
- This project includes Iterations 1 and 2 plus the new contradiction capability.
- Design: semantic candidates -> factual-value extraction and scoring -> contradiction candidates retained for verification.
- Added: factual-value extraction, utility and rarity signals, and contradiction candidates.
- Testing: information extraction, utility, scoring, and contradiction tests.
- Integration: contradiction candidates are evaluated after semantic duplicate analysis without removing unresolved facts.
- Deliverable: duplicate removal remains safe while possible factual conflicts are retained for verification.
- Acceptance condition: contradiction tests pass and candidates are retained rather than treated as duplicates.
- Iteration handling: if a rule misclassifies a pair, correct this contradiction logic and retest before acceptance.
- Next iteration: add local Ollama verification.
