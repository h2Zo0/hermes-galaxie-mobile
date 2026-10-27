import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cloud import qualify_resources as q
from cloud import verify_capabilities as previous


def candidate(cat, slug):
    prefix = {"models": "", "datasets": "datasets/", "spaces": "spaces/"}[cat]
    return {"category": cat, "name": slug,
            "url": "https://huggingface.co/" + prefix + slug}


def fixture(cat, slug):
    if cat == "models":
        return {"id": slug, "pipeline_tag": "text-generation",
                "cardData": {"license": "apache-2.0"},
                "siblings": [{"rfilename": "config.json"}], "gated": False}
    if cat == "datasets":
        return {"id": slug, "tags": ["license:cc-by-4.0"],
                "siblings": [{"rfilename": "data/train.parquet"},
                             {"rfilename": "README.md"}], "gated": False}
    if cat == "spaces":
        return {"id": slug, "cardData": {"sdk": "gradio"},
                "runtime": {"stage": "RUNNING"}}
    raise AssertionError(cat)


class QualifierTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "site").mkdir()
        for module in (q, previous):
            patcher = patch.object(module, "ROOT", root)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.root = root

    def fetch(self, cat, slug):
        return fixture(cat, slug)

    def test_three_distinct_capabilities_with_independent_proofs(self):
        state = {"nodes": [candidate(cat, "demo/" + suffix)
                           for cat in q.MISSIONS for suffix in ("one", "two")],
                 "history": [{"verified": 0}]}
        result = q.run_all(state, self.fetch)
        self.assertEqual(result, {cat: "validated" for cat in q.MISSIONS})
        self.assertEqual(state["verifiedSkills"], 3)
        self.assertEqual(state["history"][-1]["verified"], 3)
        self.assertEqual(len({s["id"] for s in state["skills"]}), 3)
        for skill in state["skills"]:
            path = self.root / "site" / skill["proofPath"]
            proof = json.loads(path.read_text())
            self.assertEqual(len({item["id"] for item in proof["reports"]}), 2)
            self.assertTrue(proof["checksPassed"])
            self.assertEqual(proof["skillId"], skill["id"])
        self.assertTrue(all(value == "no-new-evidence"
                            for value in q.run_all(state, self.fetch).values()))
        self.assertEqual(state["verifiedSkills"], 3)
        state["nodes"].extend(candidate(cat, "demo/" + suffix)
                              for cat in q.MISSIONS for suffix in ("three", "four"))
        self.assertTrue(all(value == "reinforced"
                            for value in q.run_all(state, self.fetch).values()))
        self.assertEqual(state["verifiedSkills"], 3)
        self.assertTrue(all(skill["practiceCount"] == 4 for skill in state["skills"]))
        self.assertTrue(all(len(json.loads((self.root / "site" / skill["proofPath"]).read_text())["reports"]) == 4
                            for skill in state["skills"]))

    def test_api_identity_mismatch_cannot_validate(self):
        state = {"nodes": [candidate("models", "demo/one"),
                           candidate("models", "demo/two")]}
        def wrong_identity(cat, slug):
            record = fixture(cat, slug)
            record["id"] = "other/source"
            return record
        self.assertEqual(q.mission(state, "models", wrong_identity), "failed")
        self.assertEqual(state["verifiedSkills"], 0)

    def test_missing_license_rejects_model_and_dataset(self):
        for cat in ("models", "datasets"):
            record = fixture(cat, "demo/test")
            record.pop("cardData", None)
            record["tags"] = []
            with self.subTest(cat=cat), self.assertRaises(ValueError):
                q.assess(cat, "demo/test", record)

    def test_dataset_needs_actual_file_inventory(self):
        record = fixture("datasets", "demo/test")
        record["siblings"] = [{"rfilename": "README.md"}]
        with self.assertRaises(ValueError):
            q.assess("datasets", "demo/test", record)

    def test_space_needs_observed_runtime(self):
        record = fixture("spaces", "demo/test")
        record["runtime"] = {}
        with self.assertRaises(ValueError):
            q.assess("spaces", "demo/test", record)

    def test_round_robin_escapes_permanent_early_failures(self):
        state = {"nodes": [candidate("models", "demo/bad"+str(i)) for i in range(23)]
                 + [candidate("models", "demo/good23"), candidate("models", "demo/good24")],
                 "discovery": {"cursor": 1}}
        def fetch(cat, slug):
            if slug.startswith("demo/bad"):
                raise ValueError("fichier incomplet")
            return fixture(cat, slug)
        self.assertEqual(q.mission(state, "models", fetch), "validated")
        self.assertEqual(state["verifiedSkills"], 1)
        self.assertEqual(state["skills"][0]["resourcesTested"][-1],
                         "https://huggingface.co/demo/good24")

    def test_url_mismatch_ignored(self):
        state = {"nodes": [{"category": "models", "name": "demo/one",
                            "url": "https://attacker.example/demo/one"},
                           candidate("models", "demo/two")]}
        self.assertEqual(q.mission(state, "models", self.fetch), "failed")
        self.assertEqual(state["verifiedSkills"], 0)

    def test_bad_resources_skipped_without_fake_progress(self):
        state = {"nodes": [candidate("spaces", name) for name in
                           ("demo/bad", "demo/one", "demo/two")]}
        def fetch(cat, slug):
            if slug == "demo/bad":
                raise TimeoutError("test")
            return fixture(cat, slug)
        self.assertEqual(q.mission(state, "spaces", fetch), "validated")
        self.assertEqual(state["capabilityTrials"][-1]["failures"][0]["reason"], "TimeoutError")


if __name__ == "__main__":
    unittest.main()
