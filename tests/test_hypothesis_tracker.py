#!/usr/bin/env python3
"""
Unit tests for the Hypothesis & Experiment Tracker skill (hypothesis.py).
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

# Add scripts directory to path
SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "hypothesis-tracker", "scripts"))
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

import hypothesis


class TestHypothesisTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workforces_dir = os.path.join(self.test_dir, "workforces")
        os.makedirs(os.path.join(self.workforces_dir, "session-context"), exist_ok=True)

        # Create dummy session context note
        self.session_file = os.path.join(self.workforces_dir, "session-context", "024_2026-08-23_test-session.md")
        with open(self.session_file, "w", encoding="utf-8") as f:
            f.write("""---
session_id: "024"
sequence: 24
created_at: "2026-08-23T05:00:00"
updated_at: "2026-08-23T05:00:00"
topic: "Test Session"
tracked_hypotheses: []
---

# Session 024: Test Session

## 🎯 Executive Summary & Product Brief
- Testing hypothesis engine.

## 🧠 Decisions & Reasoning ("Why")
- Test decision.
""")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_pacing_calculation(self):
        # On track (60% progress at week 2 of 4)
        prog, status, badge = hypothesis.calculate_metric_pacing(0, 100, 60, 2, 4)
        self.assertAlmostEqual(prog, 60.0)
        self.assertEqual(status, "on_track")
        self.assertIn("On Track", badge)

        # At risk (30% progress at week 2 of 4)
        prog, status, badge = hypothesis.calculate_metric_pacing(0, 100, 30, 2, 4)
        self.assertAlmostEqual(prog, 30.0)
        self.assertEqual(status, "at_risk")
        self.assertIn("At Risk", badge)

        # Off track (10% progress at week 2 of 4)
        prog, status, badge = hypothesis.calculate_metric_pacing(0, 100, 10, 2, 4)
        self.assertAlmostEqual(prog, 10.0)
        self.assertEqual(status, "off_track")
        self.assertIn("Off Track", badge)

        # Kill recommended (time up, target missed)
        prog, status, badge = hypothesis.calculate_metric_pacing(0, 100, 20, 4, 4)
        self.assertEqual(status, "kill_recommended")
        self.assertIn("Target Missed", badge)

    def test_create_and_read_hypothesis(self):
        class DummyArgs:
            id = "HYP-20260823-99"
            title = "Test Cold Email Cadence"
            status = "running"
            owner = "sales"
            supporting_teams = ["marketing"]
            goal_id = "Q1-KR1"
            goal_title = "Acquire 10 customers"
            statement = "We believe sending 50 emails will yield 5 replies in 2 weeks."
            timeframe_weeks = 2
            current_week = 1
            kill_threshold = "Reply rate < 2%"
            pivot_plan = "Switch to LinkedIn"
            metrics = json.dumps([
                {"name": "Sends", "type": "leading", "baseline": 0, "target": 50, "current": 10, "unit": "count"},
                {"name": "Reply Rate", "type": "leading", "baseline": 0, "target": 10, "current": 2, "unit": "%"}
            ])
            session_id = "024"
            session_file = self.session_file
            sync_session = True

        file_path = hypothesis.create_hypothesis(DummyArgs(), self.test_dir)
        self.assertTrue(os.path.exists(file_path))

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = hypothesis.parse_frontmatter(content)
        self.assertEqual(meta.get("id"), "HYP-20260823-99")
        self.assertEqual(meta.get("owner"), "sales")
        self.assertEqual(meta.get("status"), "running")
        self.assertEqual(len(meta.get("metrics", [])), 2)
        self.assertIn("Scientific Hypothesis Statement", body)

        # Check session context was synced
        with open(self.session_file, "r", encoding="utf-8") as sf:
            s_meta, s_body = hypothesis.parse_frontmatter(sf.read())
        self.assertEqual(len(s_meta.get("tracked_hypotheses", [])), 1)
        self.assertEqual(s_meta["tracked_hypotheses"][0]["id"], "HYP-20260823-99")

    def test_update_metrics_and_kill(self):
        # First create
        class CreateArgs:
            id = "HYP-20260823-01"
            title = "Video Outbound"
            status = "running"
            owner = "sales"
            supporting_teams = []
            goal_id = "Q1-KR1"
            goal_title = "Revenue"
            statement = "Video outbound test."
            timeframe_weeks = 3
            current_week = 1
            kill_threshold = "Replies < 3%"
            pivot_plan = "Revert to text"
            metrics = json.dumps([
                {"name": "Sends", "type": "leading", "baseline": 0, "target": 100, "current": 0, "unit": "count"},
                {"name": "Replies", "type": "leading", "baseline": 0, "target": 10, "current": 0, "unit": "count"}
            ])
            session_id = "024"
            session_file = self.session_file
            sync_session = False

        created_path = hypothesis.create_hypothesis(CreateArgs(), self.test_dir)

        # Update telemetry
        class UpdateArgs:
            update = "HYP-20260823-01"
            file = None
            current_week = 2
            metrics_data = "Sends=60,Replies=1"
            insight = "Low reply rate observed."
            rationale = None
            status = None
            kill = None
            pivot = None
            validate = None
            session_file = self.session_file
            sync_session = False

        updated_path = hypothesis.update_hypothesis(UpdateArgs(), self.test_dir)
        self.assertIsNotNone(updated_path)

        with open(updated_path, "r", encoding="utf-8") as f:
            content = f.read()
        meta, body = hypothesis.parse_frontmatter(content)
        self.assertEqual(meta["metrics"][0]["current"], 60)
        self.assertEqual(meta["metrics"][1]["current"], 1)
        self.assertIn("Low reply rate observed", body)

        # Kill experiment
        class KillArgs:
            update = "HYP-20260823-01"
            file = None
            current_week = 3
            metrics_data = None
            insight = None
            rationale = "Kill threshold reached: replies too low."
            status = "invalidated"
            kill = "HYP-20260823-01"
            pivot = None
            validate = None
            session_file = self.session_file
            sync_session = True

        killed_path = hypothesis.update_hypothesis(KillArgs(), self.test_dir)
        self.assertIsNotNone(killed_path)
        self.assertIn("invalidated", killed_path)
        self.assertTrue(os.path.exists(killed_path))

        with open(killed_path, "r", encoding="utf-8") as f:
            content = f.read()
        meta, body = hypothesis.parse_frontmatter(content)
        self.assertEqual(meta["status"], "invalidated")
        self.assertIn("Kill threshold reached", body)

    def test_sync_review_generation(self):
        class CreateArgs:
            id = "HYP-20260823-02"
            title = "SEO Programmatic Cluster"
            status = "running"
            owner = "growth"
            supporting_teams = []
            goal_id = "Q1-KR2"
            goal_title = "Organic Traffic"
            statement = "Programmatic cluster test."
            timeframe_weeks = 4
            current_week = 2
            kill_threshold = "Traffic < 100/wk"
            pivot_plan = "Shift keywords"
            metrics = json.dumps([
                {"name": "Pages", "type": "leading", "baseline": 0, "target": 50, "current": 30, "unit": "count"}
            ])
            session_id = "024"
            session_file = ""
            sync_session = False

        hypothesis.create_hypothesis(CreateArgs(), self.test_dir)

        review_md = hypothesis.generate_sync_review(self.test_dir)
        self.assertIn("HYP-20260823-02", review_md)
        self.assertIn("@growth", review_md)
        self.assertIn("Q1-KR2", review_md)


if __name__ == "__main__":
    unittest.main()
