"""Strict offset checks plus transparent unmeasured-quality flags."""
from __future__ import annotations

import json
from pathlib import Path

from .core import digest, write_json


def read_project(folder: Path) -> tuple[dict, str, list, list]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    text = (folder / "source.txt").read_text(encoding="utf-8")
    packets = [json.loads(line) for line in (folder / "work_packets.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    units = json.loads((folder / "units.json").read_text(encoding="utf-8"))
    return manifest, text, packets, units


def page_at(manifest: dict, start: int, end: int) -> int | None:
    for page in manifest.get("page_spans", []):
        if page["start"] <= start < end <= page["end"]:
            return page["page"]
    return None


def validate(folder: Path) -> dict:
    manifest, text, packets, units = read_project(folder)
    problems = []
    def flag(severity: str, code: str, detail: str) -> None:
        problems.append({"severity": severity, "code": code, "detail": detail})

    if digest(text) != manifest.get("source_sha256"):
        flag("error", "SOURCE_CHANGED", "Original normalized source checksum differs.")
    if "".join(p.get("text", "") for p in packets) != text:
        flag("error", "PACKET_COVERAGE", "Packets do not exactly reconstruct the source.")
    for packet in packets:
        a, b = packet.get("start"), packet.get("end")
        if not isinstance(a, int) or not isinstance(b, int) or a < 0 or b <= a or text[a:b] != packet.get("text"):
            flag("error", "PACKET_OFFSETS", f"Bad packet: {packet.get('id')}")

    if not isinstance(units, list):
        flag("error", "UNITS_FORMAT", "units.json must contain an array.")
        units = []
    if not units:
        flag("error", "NO_UNITS", "No agent-authored units; preparation alone is not a book analysis.")
    by_id = {s["id"]: s for s in manifest["sections"]}
    section_hits: set[str] = set()
    seen_ids: set[str] = set()
    total_evidence, verified_evidence = 0, 0

    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            flag("error", "UNIT_FORMAT", f"Unit at index {index} is not an object.")
            continue
        uid, sid = unit.get("id"), unit.get("section_id")
        section = by_id.get(sid)
        if not isinstance(uid, str) or not uid.strip() or uid in seen_ids:
            flag("error", "UNIT_ID", f"Missing or duplicate unit ID at index {index}.")
        else:
            seen_ids.add(uid)
        if not section:
            flag("error", "SECTION_ID", f"Unit {uid} has invalid section {sid}.")
        if not isinstance(unit.get("title"), str) or not unit["title"].strip():
            flag("error", "UNIT_TITLE", f"Missing title: {uid}.")
        explanation = unit.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            flag("error", "UNIT_EXPLANATION", f"Missing explanation: {uid}.")
        elif len(explanation.strip()) < 60:
            flag("warning", "SHALLOW_EXPLANATION", f"Review explanation depth for {uid}.")
        if unit.get("source_type") not in {"book", "inference", "external"}:
            flag("error", "SOURCE_TYPE", f"Invalid source attribution for {uid}.")
        refs = unit.get("evidence")
        if not isinstance(refs, list) or not refs:
            flag("error", "MISSING_EVIDENCE", f"Unit {uid} lacks supporting references.")
            continue
        grounded = False
        for ref in refs:
            total_evidence += 1
            if not isinstance(ref, dict):
                flag("error", "EVIDENCE_FORMAT", f"Malformed evidence in {uid}.")
                continue
            a, b, quote = ref.get("start"), ref.get("end"), ref.get("quote")
            if (type(a) is not int or type(b) is not int or not isinstance(quote, str)
                    or not (0 <= a < b <= len(text)) or text[a:b] != quote):
                flag("error", "EVIDENCE_MISMATCH", f"Unverifiable quote/offsets for {uid}.")
                continue
            if section is None or not (section["start"] <= a < b <= section["end"]):
                flag("error", "EVIDENCE_OUTSIDE_SECTION", f"Reference from {uid} points outside its section.")
                continue
            derived_page = page_at(manifest, a, b)
            if ref.get("page") is not None and ref["page"] != derived_page:
                flag("error", "UNVERIFIED_PAGE", f"Page claim for {uid} is unsupported.")
                continue
            verified_evidence += 1
            grounded = True
        if grounded and section:
            section_hits.add(sid)
    nonempty = [s for s in manifest["sections"] if s["non_whitespace_chars"]]
    for section in nonempty:
        if section["id"] not in section_hits:
            flag("error", "SECTION_UNCOVERED", f"{section['id']}: {section['title']} has no cited unit.")
    errors = [p for p in problems if p["severity"] == "error"]
    return {
        "status": "pass" if not errors else "fail",
        "source_sha256": manifest["source_sha256"],
        "sections_identified": len(nonempty),
        "sections_with_cited_units": len(section_hits),
        "section_coverage_ratio": len(section_hits) / len(nonempty) if nonempty else 0,
        "knowledge_coverage_ratio": None,
        "knowledge_coverage_note": "Requires a human-annotated gold inventory; NEVER inferred from section coverage.",
        "units_submitted": len(units), "evidence_total": total_evidence,
        "evidence_offsets_verified": verified_evidence,
        "issues": problems, "ingestion_warnings": manifest.get("warnings", []),
        "limitations": [
            "Exact quote offsets do not establish conceptual or factual fidelity.",
            "A cited unit per section does not prove all key concepts were captured.",
            "Scan OCR, diagrams, mathematical derivations, and pedagogy still require review.",
        ],
    }


def write_report(folder: Path, report: dict) -> None:
    write_json(folder / "audit.json", report)
    lines = [
        "# BookXray deterministic audit", "",
        f"Status: {report['status'].upper()}",
        f"Sections: {report['sections_with_cited_units']}/{report['sections_identified']}",
        f"Verified reference offsets: {report['evidence_offsets_verified']}/{report['evidence_total']}",
        "Gold-standard concept recall: NOT MEASURED.", "",
        "## Problems and warnings",
    ]
    lines.extend(f"- [{p['severity']}] {p['code']}: {p['detail']}" for p in report["issues"])
    if not report["issues"]:
        lines.append("- No deterministic audit problems detected.")
    lines += ["", "## Ingestion warnings"]
    lines.extend("- " + w for w in report["ingestion_warnings"])
    if not report["ingestion_warnings"]:
        lines.append("- None.")
    lines += ["", "## Unverified quality", *("- " + x for x in report["limitations"]), ""]
    (folder / "audit.md").write_text("\n".join(lines), encoding="utf-8")


def export(folder: Path) -> Path:
    report = validate(folder)
    write_report(folder, report)
    if report["status"] != "pass":
        raise RuntimeError("Audit failed; analysis export blocked. See audit.md")
    manifest, _text, _packets, units = read_project(folder)
    groups: dict[str, list[dict]] = {}
    for unit in units:
        groups.setdefault(unit["section_id"], []).append(unit)
    lines = [
        f"# BookXray: {manifest['source_name']}", "",
        "> AI-authored explanation. Citation offsets have been checked, but interpretation",
        "> accuracy and completeness have NOT been independently established.", "",
    ]
    for section in manifest["sections"]:
        lines += [f"## {section['id']} — {section['title']}", ""]
        for unit in groups.get(section["id"], []):
            lines += [f"### {unit['title']}", "", unit["explanation"], ""]
            refs = []
            for evidence in unit["evidence"]:
                page = page_at(manifest, evidence["start"], evidence["end"])
                location = f"offsets {evidence['start']}–{evidence['end']}"
                if page is not None:
                    location += f", PDF page {page}"
                refs.append(location)
            lines += [f"Source: {'; '.join(refs)} | Attribution: {unit['source_type']}", ""]
    lines += ["---", "Automatic evidence audit: PASS. Human concept-recall and fidelity evaluation: PENDING.", ""]
    target = folder / "analysis.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
