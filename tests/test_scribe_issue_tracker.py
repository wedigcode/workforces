#!/usr/bin/env python3
"""
Unit and Integration Tests for Scribe & Issue Tracker Evolution & Lineage Protocol.
Tests:
- Issue creation with session_id and session_file lineage.
- Dynamic issue updates (--update) with evolution notes (deciding factors log).
- Similarity discovery (--find-similar).
- Bidirectional session synchronization (--sync-session).
- Frontmatter integrity and multi-issue session tracking.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_SCRIPT = os.path.join(REPO_ROOT, "skills", "issue-tracker", "scripts", "report-issue.py")

# Import report-issue module directly for unit testing internal functions
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "issue-tracker", "scripts"))
import importlib
report_issue_mod = importlib.import_module("report-issue")


class TestScribeIssueTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_scribe_issues_")
        self.inbox_dir = os.path.join(self.test_dir, "workforces", "issues", "inbox")
        self.triaged_dir = os.path.join(self.test_dir, "workforces", "issues", "triaged")
        self.session_dir = os.path.join(self.test_dir, "workforces", "session-context")

        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.triaged_dir, exist_ok=True)
        os.makedirs(self.session_dir, exist_ok=True)

        # Create a sample session context file
        self.session_file = os.path.join(self.session_dir, "022_2026-08-22_theme-strategy.md")
        self.session_content = """---
session_id: "022"
sequence: 22
created_at: 2026-08-22T07:11:00Z
updated_at: 2026-08-22T07:11:00Z
topic: Theme Strategy & Palette
tags: [design, theme, colors]
active_files:
  - src/styles/theme.css
parent_session_id: null
tracked_issues: []
---

# Session 022: Theme Strategy & Palette

## 🎯 Executive Summary & Product Brief
- Discussing theme strategy and brand color choices.

## 🧠 Decisions & Reasoning ("Why")
- Initial proposal for bold saturated accents.

## 📁 Key Files & Code Symbols
- [theme.css](file:///path/to/theme.css)

## 🔑 Keywords & Scanning Hooks
`theme`, `colors`, `design`
"""
        with open(self.session_file, "w", encoding="utf-8") as f:
            f.write(self.session_content)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_issue_with_session_lineage(self):
        """Test reporting a new issue linked to session context."""
        cmd = [
            sys.executable,
            REPORT_SCRIPT,
            "--title", "Adopt soft pastel color palette",
            "--type", "design",
            "--severity", "P2",
            "--reporter", "scribe",
            "--session-id", "022",
            "--session-file", self.session_file,
            "--file", "src/styles/theme.css",
            "--description", "Replace bright saturated colors with a soft pastel palette.",
            "--suggested-action", "Define pastel tokens in theme.css",
            "--evolution-note", "Initial request: switch to pastel tones for softer aesthetic.",
            "--out-dir", self.inbox_dir,
            "--sync-session",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Error: {result.stderr}")
        self.assertIn("✅ Issue reported:", result.stdout)
        self.assertIn("🔗 Synced to session context:", result.stdout)

        # Verify created file in inbox
        inbox_files = os.listdir(self.inbox_dir)
        self.assertEqual(len(inbox_files), 1)
        issue_path = os.path.join(self.inbox_dir, inbox_files[0])

        with open(issue_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = report_issue_mod.parse_frontmatter(content)
        self.assertEqual(meta.get("title"), "Adopt soft pastel color palette")
        self.assertEqual(meta.get("type"), "design")
        self.assertEqual(meta.get("severity"), "P2")
        self.assertEqual(meta.get("session_id"), "022")
        self.assertEqual(meta.get("session_file"), self.session_file)
        self.assertIn("🧠 Session Lineage & Deciding Factors", body)
        self.assertIn("Initial request: switch to pastel tones", body)

        # Verify session context was updated with tracked_issues
        with open(self.session_file, "r", encoding="utf-8") as f:
            session_data = f.read()

        s_meta, s_body = report_issue_mod.parse_frontmatter(session_data)
        self.assertTrue(len(s_meta.get("tracked_issues", [])) > 0)
        self.assertEqual(s_meta["tracked_issues"][0]["title"], "Adopt soft pastel color palette")
        self.assertIn("## 📋 Tracked Issues & Feature Ideas", s_body)
        self.assertIn("Adopt soft pastel color palette", s_body)

    def test_duplicate_prevention_and_find_similar(self):
        """Test finding similar issues and blocking duplicate creation."""
        # Create initial issue
        subprocess.run([
            sys.executable,
            REPORT_SCRIPT,
            "--title", "Fix database connection timeout",
            "--type", "bug",
            "--severity", "P1",
            "--description", "DB pool times out after 30 seconds of inactivity.",
            "--out-dir", self.inbox_dir,
        ], check=True)

        # Try creating identical or very similar issue
        result = subprocess.run([
            sys.executable,
            REPORT_SCRIPT,
            "--title", "Fix database connection timeout",
            "--type", "bug",
            "--severity", "P1",
            "--description", "Duplicate report",
            "--out-dir", self.inbox_dir,
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Similar issue(s) already exist", result.stdout)

        # Test --find-similar CLI mode
        similar_res = subprocess.run([
            sys.executable,
            REPORT_SCRIPT,
            "--find-similar", "database connection timeout",
            "--out-dir", self.inbox_dir,
            "--json",
        ], capture_output=True, text=True)
        self.assertEqual(similar_res.returncode, 0)
        matches = json.loads(similar_res.stdout)
        self.assertEqual(len(matches), 1)
        self.assertIn("database connection timeout", matches[0]["title"].lower())

    def test_update_issue_and_evolution_history(self):
        """Test updating an issue mid-session with evolved decisions."""
        # 1. Create initial issue
        subprocess.run([
            sys.executable,
            REPORT_SCRIPT,
            "--title", "Hero Section Visual Concept",
            "--type", "design",
            "--severity", "P2",
            "--session-id", "022",
            "--session-file", self.session_file,
            "--description", "Hero should feature a bold crimson red background.",
            "--out-dir", self.inbox_dir,
            "--sync-session",
        ], check=True)

        inbox_files = os.listdir(self.inbox_dir)
        issue_path = os.path.join(self.inbox_dir, inbox_files[0])

        # 2. Update issue 2 hours later with a requirement pivot
        update_cmd = [
            sys.executable,
            REPORT_SCRIPT,
            "--update", issue_path,
            "--description", "Hero should use a muted pastel sage tone with 60/40 visual rhythm.",
            "--evolution-note", "Requirement pivot: User decided red is too aggressive; switched to pastel sage.",
            "--sync-session",
        ]
        result = subprocess.run(update_cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Error: {result.stderr}")
        self.assertIn("✅ Issue updated:", result.stdout)
        self.assertIn("🔗 Synced to session context:", result.stdout)

        # 3. Verify issue markdown contains both initial formulation and updated evolution note
        with open(issue_path, "r", encoding="utf-8") as f:
            updated_content = f.read()

        meta, body = report_issue_mod.parse_frontmatter(updated_content)
        self.assertIn("muted pastel sage tone", body)
        self.assertIn("Requirement pivot: User decided red is too aggressive", body)
        self.assertIn("Initial formulation", body)

        # 4. Verify session context reflects the update
        with open(self.session_file, "r", encoding="utf-8") as f:
            session_data = f.read()

        s_meta, s_body = report_issue_mod.parse_frontmatter(session_data)
        self.assertEqual(len(s_meta["tracked_issues"]), 1)
        self.assertIn("Requirement pivot", s_body)

    def test_reject_issue_and_move_to_completed(self):
        """Test rejecting an idea, moving file to completed/, and updating session context with strikethrough audit trail."""
        # 1. Create initial issue in inbox
        subprocess.run([
            sys.executable,
            REPORT_SCRIPT,
            "--title", "Overly Complex Auth System",
            "--type", "idea",
            "--severity", "P2",
            "--session-id", "022",
            "--session-file", self.session_file,
            "--description", "Build custom biometric authentication engine from scratch.",
            "--out-dir", self.inbox_dir,
            "--sync-session",
        ], check=True)

        inbox_files = os.listdir(self.inbox_dir)
        self.assertEqual(len(inbox_files), 1)
        issue_path = os.path.join(self.inbox_dir, inbox_files[0])

        # 2. Reject the issue using --reject
        rejection_reason = "User explicitly rejected this idea: out of scope for MVP."
        reject_cmd = [
            sys.executable,
            REPORT_SCRIPT,
            "--update", issue_path,
            "--reject", rejection_reason,
            "--sync-session",
        ]
        result = subprocess.run(reject_cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Error: {result.stderr}")
        self.assertIn("✅ Issue updated:", result.stdout)
        self.assertIn("Moved issue from inbox/ to completed/", result.stdout)

        # 3. Verify file moved from inbox to completed
        completed_dir = os.path.join(self.test_dir, "workforces", "issues", "completed")
        self.assertEqual(len(os.listdir(self.inbox_dir)), 0)
        completed_files = os.listdir(completed_dir)
        self.assertEqual(len(completed_files), 1)

        completed_file_path = os.path.join(completed_dir, completed_files[0])
        with open(completed_file_path, "r", encoding="utf-8") as f:
            c_meta, c_body = report_issue_mod.parse_frontmatter(f.read())

        self.assertEqual(c_meta.get("triage_status"), "rejected")
        self.assertEqual(c_meta.get("status"), "completed")
        self.assertIn("❌ Rejected by user: User explicitly rejected this idea", c_body)
        self.assertIn("Decision:** Rejected (User explicitly rejected this idea", c_body)

        # 4. Verify session context contains strikethrough audit trail and rejected status
        with open(self.session_file, "r", encoding="utf-8") as f:
            s_meta, s_body = report_issue_mod.parse_frontmatter(f.read())

        self.assertEqual(s_meta["tracked_issues"][0]["status"], "rejected")
        self.assertIn("~~Overly Complex Auth System~~", s_body)
        self.assertIn("❌ **Rejected:** User explicitly rejected this idea", s_body)


if __name__ == "__main__":
    unittest.main()
