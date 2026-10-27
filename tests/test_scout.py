import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from cloud import scout


def response(url, auth=False):
    if "api.github.com" in url:
        # Différents dépôts à chaque page / requête pour tester la rotation
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(url).query)
        word = q.get("q", ["empty"])[0].replace(" ", "-")[:30]
        page = q.get("page", ["1"])[0]
        return {"items": [{"full_name": "open/" + word + "-" + page,
                           "html_url": "https://github.com/open/" + word + "-" + page}]}
    if "/models?" in url:
        return [{"id": "demo/model"}]
    if "/datasets?" in url:
        return [{"id": "demo/dataset"}]
    if "/spaces?" in url:
        return [{"id": "demo/space"}]
    raise ValueError(url)


class DiscoveryTests(unittest.TestCase):
    def test_rotating_queries_and_no_duplicate_discoveries(self):
        self.assertNotEqual(scout.plan(0), scout.plan(1))
        self.assertNotEqual(scout.plan(0), scout.plan(5))
        with patch.object(scout, "NOW", datetime(2026, 10, 27, tzinfo=timezone.utc)):
            state = {"nodes": [], "history": [], "verifiedSkills": 0}
            first = scout.collect(state, response)
            self.assertGreater(first["new"], 4)
            initial = state["resourceCount"]
            self.assertEqual(state["discovery"]["cursor"], 1)
            second = scout.collect(state, response)
            self.assertGreaterEqual(state["resourceCount"], initial)
            self.assertGreater(second["new"], 0)
            self.assertEqual(state["discovery"]["cursor"], 2)
            self.assertEqual(len({n["id"] for n in state["nodes"]}), len(state["nodes"]))
            self.assertEqual(sum(state["categoryCounts"].values()), state["resourceCount"])

    def test_poisoned_url_and_names_are_not_accepted(self):
        state = {"nodes": [], "verifiedSkills": 0}
        def malicious(url, auth=False):
            if "github.com" in url:
                return {"items": [{"full_name": "open/hidden",
                                   "html_url": "https://example.com/secret"}]}
            return [{"id": "invalid_without_separator"}]
        scout.collect(state, malicious)
        self.assertEqual(state["resourceCount"], 0)
        self.assertEqual(state["verifiedSkills"], 0)

    def test_capacity_safeguard_never_forges_skills(self):
        state = {"nodes": [], "verifiedSkills": 7}
        with patch.object(scout, "MAX_NODES", 2):
            scout.collect(state, response)
        self.assertEqual(state["resourceCount"], 2)
        self.assertEqual(state["verifiedSkills"], 7)


if __name__ == "__main__":
    unittest.main()
