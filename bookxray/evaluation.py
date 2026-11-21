"""Evaluate concept recall against a separately human-annotated inventory."""
import json
from pathlib import Path
from .audit import read_project
from .core import write_json

def evaluate(folder:Path,gold_path:Path)->dict:
    manifest,_,_,units = read_project(folder)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    if gold.get("source_sha256") != manifest["source_sha256"]:
        raise ValueError("Gold inventory does not match source checksum")
    concepts = gold.get("concepts")
    if not isinstance(concepts,list) or not concepts:
        raise ValueError("Gold inventory must contain at least one concept")
    sections = {s["id"] for s in manifest["sections"]}
    seen = set()
    findings = []
    for item in concepts:
        cid,sid = item.get("id"),item.get("section_id")
        if not isinstance(cid,str) or not cid or cid in seen or sid not in sections:
            raise ValueError("Invalid or duplicated gold concept")
        seen.add(cid)
        matches = item.get("matched_unit_ids",[])
        if not isinstance(matches,list):
            raise ValueError("Gold matches must be a list")
        possible = {u.get("id") for u in units if isinstance(u,dict) and u.get("section_id")==sid}
        if any(match not in possible for match in matches):
            raise ValueError("Gold match refers to nonexistent unit")
        findings.append({"id":cid,"section_id":sid,"covered":bool(matches),"matched_unit_ids":matches})
    count = sum(int(x["covered"]) for x in findings)
    result = {"gold_concepts":len(findings),"covered_concepts":count,
        "gold_concept_recall":count/len(findings),"precision":None,
        "annotator":gold.get("annotator","unspecified"),"per_concept":findings,
        "note":"Matches must be independently annotated. Precision requires separate false-positive labels."}
    write_json(folder/"gold_evaluation.json",result)
    return result
