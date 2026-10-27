ITERATION 1: PYTHON DATA FOUNDATION

- Overall project method: iterative and incremental development.
- Method used inside this increment: build -> test -> fix/rebuild this same increment -> retest -> accept.
- Why this method fits: parsing and sentence segmentation have stable, clearly defined requirements but defects can be corrected before acceptance.
- Requirement: accept a TXT dataset and preserve its statements as structured records.
- Design: document model -> parser -> sentence segmenter -> information units.
- Implementation: Python models, document parser, sentence segmenter, and pipeline service.
- Testing: parser and segmenter tests.
- Integration: parser and segmenter are assembled into the Python information-unit pipeline.
- Deliverable: a stable Python input pipeline; no similarity, contradiction, Ollama, manual review, backend API, or frontend yet.
- Acceptance condition: parser and segmenter tests pass and structured sentence records are stable.
- Iteration handling: if those tests fail, correct this Python foundation and retest before moving forward.
- Next iteration: add semantic duplicate detection.
