import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cloud import verify_capabilities as verifier


def node(slug):
    return {"category": "github", "name": slug, "url": "https://github.com/" + slug}


def mock_fetch(path):
    slug = "/".join(path.split("/")[1:3])
    if slug == "fake/broken":
        raise ValueError("Erreur réseau simulée")
    if path.endswith("/languages"):
        return {"Python": 90, "JavaScript": 10}
    return {
        "full_name": slug, "html_url": "https://github.com/" + slug,
        "archived": False, "disabled": False, "private": False,
        "default_branch": "main", "stargazers_count": 2, "pushed_at": "2026-10-26T00:00:00Z",
    }


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "site").mkdir()
        self.p1 = patch.object(verifier, "ROOT", self.root)
        self.p2 = patch.object(verifier, "EVIDENCE", self.root / "site/evidence/github-repository-audit.json")
        self.p1.start()
        self.p2.start()
        self.addCleanup(self.p1.stop)
        self.addCleanup(self.p2.stop)

    def test_real_audit_produces_verified_proof_and_works_twice(self):
        state = {"nodes": [node("sample/alpha"), node("sample/beta")], "history": [{"verified": 0}]}
        self.assertEqual(verifier.run(state, mock_fetch), "validated")
        self.assertEqual(state["verifiedSkills"], 1)
        self.assertEqual(state["history"][-1]["verified"], 1)
        proof = json.loads(verifier.EVIDENCE.read_text())
        self.assertTrue(proof["checksPassed"])
        self.assertEqual(len(proof["reports"]), 2)
        self.assertEqual(proof["reports"][0]["primaryLanguageSharePercent"], 90)
        self.assertEqual(verifier.run(state, lambda path: self.fail("Pas de répétition inutile")), "no-new-evidence")
        self.assertEqual(state["verifiedSkills"], 1)

    def test_new_deposits_strengthen_same_skill_without_new_fake_skill(self):
        state = {"nodes": [node("sample/alpha"), node("sample/beta")]}
        self.assertEqual(verifier.run(state, mock_fetch), "validated")
        state["nodes"].extend((node("sample/gamma"), node("sample/delta")))
        self.assertEqual(verifier.run(state, mock_fetch), "reinforced")
        self.assertEqual(state["verifiedSkills"], 1)
        self.assertEqual(state["skills"][0]["practiceCount"], 4)
        proof = json.loads(verifier.EVIDENCE.read_text())
        self.assertEqual(len(proof["reports"]), 4)
        self.assertEqual(len(set(r["repository"] for r in proof["reports"])), 4)

    def test_one_success_does_not_count(self):
        state = {"nodes": [node("sample/alpha")]}
        self.assertEqual(verifier.run(state, mock_fetch), "failed")
        self.assertEqual(state["verifiedSkills"], 0)
        self.assertFalse(verifier.EVIDENCE.exists())

    def test_broken_candidate_is_skipped_with_evidence_of_failure(self):
        state = {"nodes": [node("fake/broken"), node("sample/alpha"), node("sample/beta")]}
        self.assertEqual(verifier.run(state, mock_fetch), "validated")
        self.assertEqual(state["capabilityTrials"][0]["failures"][0]["reason"], "ValueError")

    def test_invalid_language_data_and_identity_are_rejected(self):
        metadata = mock_fetch("repos/sample/alpha")
        for bad in ({}, {"Python": -4}, {"Python": "5"}):
            with self.assertRaises(ValueError):
                verifier.analyze_repository("sample/alpha", metadata, bad)
        with self.assertRaises(ValueError):
            verifier.analyze_repository("another/alpha", metadata, {"Python": 5})

    def test_fake_state_cannot_manufacture_validation(self):
        state = {"nodes": [], "verifiedSkills": 999, "skills": [{
            "id": verifier.SKILL_ID, "status": "validated",
            "proofPath": "evidence/github-repository-audit.json"
        }]}
        self.assertEqual(verifier.run(state, mock_fetch), "failed")
        self.assertEqual(state["verifiedSkills"], 0)

    def test_untrusted_resource_links_are_ignored(self):
        state = {"nodes": [
            {"category": "github", "name": "sample/alpha",
             "url": "https://evil.example/sample/alpha"}, node("sample/beta")
        ]}
        self.assertEqual(verifier.run(state, mock_fetch), "failed")
        self.assertEqual(state["verifiedSkills"], 0)


if __name__ == "__main__":
    unittest.main()
