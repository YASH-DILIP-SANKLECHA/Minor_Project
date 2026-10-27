ITERATION 2: SEMANTIC DUPLICATE REFINEMENT

- Overall project method: iterative and incremental development.
- Method used inside this increment: build -> test -> fix/rebuild this same increment -> retest -> accept.
- Why this method fits: the duplicate-detection requirement is bounded after Iteration 1 produced stable information units, while thresholds and decisions can be corrected through tests.
- This project includes all Iteration 1 files plus the new refinement capability.
- Design: information units -> local embeddings -> similarity candidates -> duplicate decision -> optimized reconstruction.
- Added: local all-MiniLM-L6-v2 embeddings, cosine similarity, redundancy candidates, duplicate decisions, optimization, and reconstruction.
- Testing: embeddings, redundancy, decisions, optimizer, and reconstruction tests.
- Integration: semantic comparison is connected to the Iteration 1 information-unit pipeline.
- Deliverable: similar or duplicate statements can be identified and safely reduced to one representative.
- Acceptance condition: duplicate tests pass and semantically similar content is reduced without silently deleting possible factual conflicts.
- Iteration handling: if duplicate decisions are unsafe, correct the similarity/decision logic in this iteration and retest.
- Next iteration: add deterministic contradiction detection.
