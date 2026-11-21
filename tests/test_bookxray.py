"""Small deterministic tests; no API key or network is needed."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from bookxray.audit import export, validate
from bookxray.cli import main
from bookxray.core import prepare


class BookXrayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def sample(self):
        source = self.root / "sample.md"
        source.write_text("# Foundations\nA variable stores a value.\n\n## Pointers\nA pointer refers to an address.", encoding="utf-8")
        project = self.root / "out"
        manifest = prepare(source, project, max_chars=200)
        return project, manifest

    def fill_units(self, project, manifest):
        source = (project / "source.txt").read_text(encoding="utf-8")
        units = []
        for section in manifest["sections"]:
            start = source.index("A variable", section["start"]) if section["id"] == "S001" else source.index("A pointer", section["start"])
            quote = "A variable stores a value." if section["id"] == "S001" else "A pointer refers to an address."
            units.append({
                "id": "K-" + section["id"], "section_id": section["id"],
                "title": "Grounded concept", "source_type": "book",
                "explanation": "The selected sentence introduces the essential concept; this explanatory note is authored for the test fixture only, and is not asserted as a complete lesson.",
                "evidence": [{"start": start, "end": start + len(quote), "quote": quote}],
            })
        (project / "units.json").write_text(json.dumps(units), encoding="utf-8")

    def test_prepare_and_audit(self):
        project, manifest = self.sample()
        self.assertEqual(len(manifest["sections"]), 2)
        self.assertEqual(validate(project)["status"], "fail")
        self.fill_units(project, manifest)
        report = validate(project)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["evidence_offsets_verified"], 2)
        self.assertIsNone(report["knowledge_coverage_ratio"])
        self.assertTrue(export(project).exists())

    def test_tampering_rejected(self):
        project, manifest = self.sample()
        self.fill_units(project, manifest)
        units = json.loads((project / "units.json").read_text(encoding="utf-8"))
        units[0]["evidence"][0]["quote"] = "a fabricated citation"
        (project / "units.json").write_text(json.dumps(units), encoding="utf-8")
        result = validate(project)
        self.assertEqual(result["status"], "fail")
        self.assertIn("EVIDENCE_MISMATCH", [p["code"] for p in result["issues"]])
        with self.assertRaises(RuntimeError):
            export(project)

    def test_source_integrity(self):
        project, manifest = self.sample()
        self.fill_units(project, manifest)
        (project / "source.txt").write_text("modified", encoding="utf-8")
        self.assertEqual(validate(project)["status"], "fail")

    def test_epub_spine_order(self):
        source = self.root / "tiny.epub"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
            archive.writestr("OPS/book.opf", '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>')
            archive.writestr("OPS/a.xhtml", "<html><body><h1>Later</h1><p>Second item</p></body></html>")
            archive.writestr("OPS/b.xhtml", "<html><body><h1>First</h1><p>First item</p></body></html>")
        project = self.root / "epub"
        prepare(source, project)
        text = (project / "source.txt").read_text(encoding="utf-8")
        self.assertLess(text.index("First item"), text.index("Second item"))

    def test_no_heading_marks_uncertainty(self):
        source = self.root / "plain.txt"
        source.write_text("Unstructured prose without headings.", encoding="utf-8")
        result = prepare(source, self.root / "plain")
        self.assertEqual(len(result["sections"]), 1)
        self.assertTrue(any("synthetic" in w.lower() for w in result["warnings"]))

    def test_cli_prepare(self):
        source = self.root / "cli.md"
        source.write_text("# Chapter\nThis is source text.", encoding="utf-8")
        self.assertEqual(main(["prepare", str(source), "--output", str(self.root / "cli")]), 0)
        self.assertEqual(main(["audit", str(self.root / "cli")]), 2)


if __name__ == "__main__":
    unittest.main()
