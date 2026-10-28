import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cloud import try_dataset_samples as sampler
from cloud import verify_capabilities as base


def api(endpoint, params):
    if endpoint == "splits":
        return {"splits": [{"config": "default", "split": "train", "num_examples": 8}]}
    if endpoint == "rows":
        return {"rows": [{"row": {"amount": 12, "description": "invoice"}},
                         {"row": {"amount": 14, "description": "credit"}}]}
    raise ValueError(endpoint)


def node(slug):
    return {"category": "datasets", "name": slug,
            "url": "https://huggingface.co/datasets/" + slug}


class DatasetPilotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "site").mkdir()
        self.patches = [
            patch.object(sampler, "ROOT", root),
            patch.object(sampler, "PROOF", root / "site/evidence/hf-dataset-sample-ingestion-v1.json"),
            patch.object(base, "ROOT", root),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.root = root

    def test_actual_rows_consumption_creates_bounded_approval(self):
        state = {"nodes": [node("open/alpha"), node("open/beta")]}
        self.assertEqual(sampler.run(state, api), "validated")
        self.assertEqual(state["verifiedSkills"], 3)
        self.assertEqual(state["approvedResourceCount"], 2)
        self.assertEqual(len([s for s in state["skills"] if s["id"].startswith("dataset:")]), 2)
        self.assertEqual(len(base.valid_existing_skills(state["skills"])), 3)
        for v in state["approvedResources"]:
            self.assertEqual(v["approvedFor"], "read-only-dataset-sampling")
        proof = json.loads(sampler.PROOF.read_text())
        self.assertEqual(len(proof["reports"]), 2)
        self.assertEqual(proof["reports"][0]["columns"], ["amount", "description"])
        self.assertNotIn("invoice", sampler.PROOF.read_text())
        self.assertEqual(sampler.run(state, api), "no-new-evidence")
        state["nodes"].append(node("open/gamma"))
        self.assertEqual(sampler.run(state, api), "reinforced")
        self.assertEqual(state["verifiedSkills"], 4)
        self.assertEqual(state["approvedResourceCount"], 3)
        self.assertEqual(len(base.valid_existing_skills(state["skills"])), 4)

    def test_no_rows_means_no_approval(self):
        state = {"nodes": [node("open/alpha"), node("open/beta")]}
        def invalid(endpoint, params):
            if endpoint == "rows":
                return {"rows": []}
            return api(endpoint, params)
        self.assertEqual(sampler.run(state, invalid), "failed")
        self.assertEqual(state["approvedResourceCount"], 0)
        self.assertEqual(state["verifiedSkills"], 0)

    def test_no_url_injection_and_no_fetch_other_hosts(self):
        state = {"nodes": [{"category": "datasets", "name": "open/alpha",
                            "url": "https://evil.example/open/alpha"}, node("open/beta")]}
        self.assertEqual(sampler.run(state, api), "failed")
        self.assertEqual(state["approvedResourceCount"], 0)


if __name__ == "__main__":
    unittest.main()
