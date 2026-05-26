"""Tests for graph and lint scanner over the fixture repo."""
from __future__ import annotations

import datetime as dt
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"

sys.path.insert(0, str(HERE.parent))  # .claude/skills/graph/
sys.path.insert(0, str(HERE.parent.parent / "lint"))  # .claude/skills/lint/

from graph import build, confidence, refresh_candidates  # noqa: E402


class GraphShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = build(FIXTURE)

    def test_node_count(self):
        # alice, bob, acme (index), product, old-product, proj (index), note, orphan
        self.assertEqual(len(self.g.nodes), 8)

    def test_folder_keyed_indices(self):
        self.assertIn("acme", self.g.nodes)
        self.assertTrue(self.g.nodes["acme"].is_index)
        self.assertIn("proj", self.g.nodes)
        self.assertTrue(self.g.nodes["proj"].is_index)

    def test_alice_has_inbound(self):
        inbound = self.g.nodes["alice"].inbound
        # product.md, acme/index.md, note.md all link to alice
        self.assertIn("product", inbound)
        self.assertIn("acme", inbound)
        self.assertIn("note", inbound)

    def test_folder_link_resolves(self):
        # product.md has [[acme]] which should resolve to the folder index
        self.assertIn("acme", self.g.nodes["product"].outbound)

    def test_supersedes_edge(self):
        # product.md frontmatter supersedes: old-product
        self.assertIn("old-product", self.g.nodes["product"].supersedes)
        self.assertIn("product", self.g.nodes["old-product"].superseded_by)

    def test_broken_link(self):
        targets = {target for _src, target in self.g.broken_links}
        self.assertIn("nonexistent-target", targets)

    def test_orphan_has_no_inbound(self):
        self.assertEqual(len(self.g.nodes["orphan"].inbound), 0)


class ConfidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = build(FIXTURE)
        cls.today = dt.date(2026, 4, 19)

    def test_alice_is_high(self):
        # 3 sources, last_updated 4 days ago (within 30), no contradictions
        self.assertEqual(confidence(self.g.nodes["alice"], self.today), "high")

    def test_bob_is_low_from_contradiction(self):
        # contradiction marker forces low
        self.assertEqual(confidence(self.g.nodes["bob"], self.today), "low")

    def test_index_is_na(self):
        self.assertEqual(confidence(self.g.nodes["acme"], self.today), "n/a")

    def test_product_is_medium(self):
        # 1 source, 9 days ago → medium
        self.assertEqual(confidence(self.g.nodes["product"], self.today), "medium")


class RefreshCandidateTests(unittest.TestCase):
    def test_old_product_not_flagged_as_refresh(self):
        # old-product has only 1 inbound (from product), below REFRESH_MIN_INBOUND=2
        g = build(FIXTURE)
        today = dt.date(2026, 4, 19)
        flagged = {n.stem for n, _age in refresh_candidates(g, today)}
        self.assertNotIn("old-product", flagged)

    def test_alice_not_flagged_recent(self):
        g = build(FIXTURE)
        today = dt.date(2026, 4, 19)
        flagged = {n.stem for n, _age in refresh_candidates(g, today)}
        # alice has 3 inbound but is recent
        self.assertNotIn("alice", flagged)


class LintScannerTests(unittest.TestCase):
    def test_scan_finds_orphan_and_broken(self):
        from scanner import scan
        today = dt.date(2026, 4, 19)
        report = scan(FIXTURE, today)
        orphan_paths = {str(rel) for rel, _suggs in report["orphans"]}
        self.assertIn("projects/proj/orphan.md", orphan_paths)
        broken_targets = {t[1] for t in report["broken"]}
        self.assertIn("nonexistent-target", broken_targets)


if __name__ == "__main__":
    unittest.main()
