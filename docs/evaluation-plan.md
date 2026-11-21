# Evaluation plan / 真实测试计划

## Tests implemented

Python tests cover Markdown sections, empty-agent audit failure, exact evidence pass, fabricated quote rejection, source tamper rejection, EPUB spine ordering and CLI exit codes. GitHub Actions executes the no-network standard-library test suite.

## Pending real-world tests (NOT completed)

1. Chinese and English EPUB with TOC, footnotes and images: compare reading order and hierarchy to human annotations.
2. Scanned Chinese PDF: measure OCR failure and require explicit review, not invented text.
3. Technical textbook with code, equations and tables: human inspection for lost symbols and text order.
4. Long-form literature: inspect causal character and plot relations across chapters; no spoilers by default.
5. Research/social science book with disputed claims: evaluate premise/evidence separation and external attribution.
6. Deliberately corrupted or missing chapters, false source offsets, wrong-page references: audit sensitivity and false positives.
7. Independent gold concept inventory: calculate precision/recall by chapter, not from output volume.
8. Two-agent blind review: evaluate factual groundedness and instructional effectiveness without sharing generator self-scores.

## Reporting

Only show measured quantities: section hits, evidence offsets and actionable problems. Concept recall is null until an independently labeled sample exists. No fabricated benchmark scores. Distinguish parser quality, semantic fidelity and pedagogical helpfulness. Add time, environment, model version, books permitted for benchmarking and reproducible commands for every future test.
