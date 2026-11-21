import json
import tempfile
import unittest
from pathlib import Path
from bookxray.core import prepare
from bookxray.agent import anchored_units,run
from bookxray.evaluation import evaluate
from bookxray.audit import export

class FakeModel:
    def __init__(self,outputs):
        self.outputs=list(outputs)
        self.calls=0
    def complete(self,system,prompt):
        self.calls+=1
        return self.outputs.pop(0)

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        source=root/"book.md"
        source.write_text("# Concepts\nA pointer stores a memory address. A pointer can be null.",encoding="utf-8")
        self.folder=root/"output"
        self.manifest=prepare(source,self.folder)
        self.packet=json.loads((self.folder/"work_packets.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.unit={"title":"Pointer semantics","explanation":"A pointer stores an address and may be null. A careful explanation must distinguish the pointer value from the value referenced and address edge cases.",
            "source_type":"book","quote":"A pointer stores a memory address."}

    def test_validated_generation_and_resume(self):
        gen=FakeModel([{"units":[self.unit]}])
        reviewer=FakeModel([{"pass":True,"issues":[]}])
        report=run(self.folder,gen,reviewer,generator_id="gen",reviewer_id="review")
        self.assertEqual(report["status"],"pass")
        self.assertEqual(report["semantic_review"]["review_passed"],1)
        self.assertTrue(export(self.folder).exists())
        again=run(self.folder,gen,reviewer,generator_id="gen",reviewer_id="review")
        self.assertEqual(again["status"],"pass")
        self.assertEqual(gen.calls,1)

    def test_reviewer_repair(self):
        gen=FakeModel([{"units":[self.unit]},{"units":[self.unit]}])
        reviewer=FakeModel([{"pass":False,"issues":["Explain null pointers"]},{"pass":True,"issues":[]}])
        report=run(self.folder,gen,reviewer,generator_id="g",reviewer_id="r")
        self.assertEqual(report["status"],"pass")
        self.assertEqual(gen.calls,2)

    def test_review_failure_blocks_export(self):
        gen=FakeModel([{"units":[self.unit]}])
        reviewer=FakeModel([{"pass":False,"issues":["Missing key idea"]}])
        report=run(self.folder,gen,reviewer,generator_id="g",reviewer_id="r",max_repairs=0)
        self.assertEqual(report["status"],"fail")
        with self.assertRaises(RuntimeError):
            export(self.folder)

    def test_quote_fabrication_rejected(self):
        bad=dict(self.unit,quote="This text does not exist.")
        with self.assertRaises(ValueError):
            anchored_units(self.packet,{"units":[bad]})

    def test_independence_guard(self):
        with self.assertRaises(ValueError):
            run(self.folder,FakeModel([]),FakeModel([]),generator_id="same",reviewer_id="same")

    def test_gold_recall(self):
        gen=FakeModel([{"units":[self.unit]}])
        reviewer=FakeModel([{"pass":True,"issues":[]}])
        run(self.folder,gen,reviewer,generator_id="g",reviewer_id="r")
        gold=self.folder/"gold.json"
        gold.write_text(json.dumps({"source_sha256":self.manifest["source_sha256"],"annotator":"human",
            "concepts":[{"id":"C1","section_id":"S001","matched_unit_ids":["S001-P001-K001"]},
                        {"id":"C2","section_id":"S001","matched_unit_ids":[]}]}),encoding="utf-8")
        result=evaluate(self.folder,gold)
        self.assertEqual(result["gold_concept_recall"],0.5)
        self.assertIsNone(result["precision"])
