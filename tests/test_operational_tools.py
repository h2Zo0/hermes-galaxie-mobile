import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cloud import operational_tools as toolkit
from cloud import verify_capabilities as verifier


class OperationalToolkitTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        (root/"site").mkdir()
        for obj,attr,value in [(toolkit,"ROOT",root),(verifier,"ROOT",root)]:
            p=patch.object(obj,attr,value)
            p.start()
            self.addCleanup(p.stop)
        self.root=root

    def test_registry_holds_100_distinct_executable_functions(self):
        self.assertEqual(len(toolkit.CAPABILITIES),100)
        self.assertEqual(len(toolkit.SAMPLES),100)
        self.assertEqual(len({id(fn) for _,fn in toolkit.CAPABILITIES.values()}),100)
        self.assertEqual({d for d,_ in toolkit.CAPABILITIES.values()},
                         {"text","data","finance","stats","dates","web","operations","validation"})
        for name in toolkit.CAPABILITIES:
            with self.subTest(name=name):
                self.assertGreaterEqual(len(toolkit.SAMPLES[name]),2)
                self.assertEqual(len(toolkit.evaluate(name)),2)

    def test_only_tested_tools_are_signed_and_counted(self):
        state={"nodes":[],"skills":[],"history":[{"verified":0}]}
        outcome=toolkit.run(state)
        self.assertEqual(outcome["defined"],100)
        self.assertFalse(outcome["failures"],outcome["failures"])
        self.assertEqual(outcome["new"],100)
        self.assertEqual(state["verifiedSkills"],100)
        self.assertEqual(state["operationalToolkit"]["verifiedTools"],100)
        self.assertEqual(state["history"][-1]["verified"],100)
        self.assertEqual(len(verifier.valid_existing_skills(state["skills"])),100)
        self.assertEqual(len({x["id"] for x in state["skills"]}),100)
        self.assertEqual(toolkit.run(state)["new"],0)

    def test_a_bad_implementation_cannot_get_a_validated_badge(self):
        state={"nodes":[],"skills":[]}
        orig=toolkit.CAPABILITIES["margin_euros"]
        with patch.dict(toolkit.CAPABILITIES,{"margin_euros":("finance",lambda p:999)}):
            outcome=toolkit.run(state)
        self.assertEqual(outcome["new"],99)
        self.assertEqual(state["verifiedSkills"],99)
        self.assertEqual(outcome["failures"][0]["name"],"margin_euros")
        self.assertFalse((self.root/"site/evidence/toolkit-margin-euros-v1.json").exists())
        self.assertEqual(toolkit.run(state)["valid"],100)

    def test_runtime_rejects_unregistered_operations(self):
        with self.assertRaises(KeyError):
            toolkit.execute("__import__",{})
        with self.assertRaises(TypeError):
            toolkit.execute("mean",[1,2,3])


if __name__=="__main__":
    unittest.main()
