# Open-source integration decisions

The first release deliberately limits dependency surface. External projects are not vendored.

| Project | Role | Decision |
| --- | --- | --- |
| Docling (MIT) | Complex PDF-to-Markdown parsing | Optional runtime adapter, currently implemented |
| PyMuPDF (AGPL/commercial licensing applies) | Page-aware PDF text extraction | Optional runtime adapter; REVIEW distribution and deployment obligations |
| LangExtract (Apache-2.0) | Span-aware structured extraction | Planned adapter, not integrated |
| MarkItDown (MIT) | Additional source formats | Planned adapter, not integrated |
| LightRAG (MIT) | Knowledge graph and hybrid retrieval | Deferred to V2 |
| DeepEval (Apache-2.0) | LLM evaluation | Planned evaluation, not installed |
| Ragas (Apache-2.0) | Groundedness evaluation | Planned evaluation, not installed |
| MinerU (project-specific license) | OCR/layout for scanned books | Research-only until terms reviewed |
| BookWorm AI | Hierarchical long-book pipeline inspiration | Design reference only |

Project license remains Apache-2.0. Optional PyMuPDF has **AGPL/commercial licensing**, so it must not be packaged as though it were Apache-2.0. Its integration is an optional third-party dependency; operators must assess their own distribution/network obligations. Where this is not acceptable, select Docling or another appropriately licensed parser. Verify third-party licenses again before a binary release. This file does not constitute legal advice.
