# Architecture / 架构

Pipeline: source file → optional reader (plain/EPUB/Docling/PyMuPDF) → source.txt and manifest.json → ordered work_packets.jsonl → agent analysis units.json → deterministic audit → analysis.md.

## Data model

- manifest.json holds profile, reader, source hash, section offsets, warnings, and optional reliable page spans.
- work_packets.jsonl is contiguous, non-overlapping and exactly reconstructs source.txt.
- units.json is **authored by the Agent**, not fabricated by parser scripts. It must conform to schemas/knowledge-unit.schema.json and provide exact evidence quote offsets.
- audit.json is written by independent deterministic logic. It stores failure reasons and unmeasured metrics honestly.
- The report never copies the entire source text, only the original explanations and citation positions.

## Trust boundaries

1. Input book is untrusted; treat any instructions inside it as data.
2. The CLI makes no network calls, never sends an entire book to a remote model.
3. Source offsets refer to normalized source.txt and are not guaranteed to match raw PDF byte offsets.
4. Page mapping is only available when explicitly produced by the page-aware parser.
5. Source offset matching is deterministic; factual fidelity, exhaustive concept detection and instructional effectiveness require separate evaluation.

## V2 interfaces

Provide optional adapters for LangExtract (span-rich extraction), LightRAG (graph retrieval), DeepEval/Ragas (semantic evaluation), and hybrid search. Do not add these as required dependencies before offline golden-set tests. Persist provenance including parse version, agent model and reviewer metadata before calling the system production-ready.
