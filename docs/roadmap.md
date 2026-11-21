# Roadmap / 路线图

## v0.1: baseline (implemented code; CI result must be checked)

Local file ingestion, EPUB spine parsing, optional PDF adapters, manifests, exact source packets, manual Agent-compatible units, deterministic evidence/section audit, export gate, schema, bilingual README and unit tests.

## v0.2: analysis automation (implemented foundation)

OpenAI-compatible model adapter with explicit consent, JSON unit extraction, bounded retries, and per-packet checkpoint/resume implemented. Better hierarchical TOC and parser quality flags remain pending.

## v0.3: evaluation (initial implementation)

Independent reviewer-model pass with targeted repair, blocked export on review failure, and human-annotated gold concept-recall evaluator implemented. Real gold datasets, robust semantic benchmarks, and dashboard remain pending.

## v0.4: retrieval / teaching

LangExtract adapter, graph interface (consider LightRAG), knowledge dependencies, learning diagnostics, adaptive teaching and book-to-book comparisons.

## Before stable release

Full parser compatibility tests; real books with lawful access; dependency license audit; strict privacy review; security assessment; reproducible performance benchmark. Do not claim any roadmap task completed before it is implemented and tested.
