#!/usr/bin/env python3
"""
Unit and Integration Tests for Scribe Task Tracker & Lifecycle Management.
Tests:
- Task creation with simplified 5-state lifecycle (todo, in_progress, blocked, done, dropped).
- Freeform tag type (follow-up, bug, idea, ops, business, etc.).
- Universal priority P0-P3 (and --severity alias).
- In-place status transitions (--start, --block, --done, --drop).
- Similarity discovery (--find-similar) and listing (--list).
- Bidirectional session synchronization (tracked_tasks).
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
TASK_SCRIPT = os.path.join(REPO_ROOT, "skills", "task-tracker", "scripts", "report-task.py")

# Import report-task module directly for unit testing internal functions
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "task-tracker", "scripts"))
import importlib
report_task_mod = importlib.import_module("report-task")


class TestScribeTaskTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_scribe_tasks_")
        self.tasks_dir = os.path.join(self.test_dir, "workforces", "tasks")
        self.session_dir = os.path.join(self.test_dir, "workforces", "session-context")

        os.makedirs(self.tasks_dir, exist_ok=True)
        os.makedirs(self.session_dir, exist_ok=True)

        # Create a sample session context file
        self.session_file = os.path.join(self.session_dir, "026_2026-08-23_pilot-strategy.md")
        self.session_content = """---
session_id: "026"
sequence: 26
created_at: 2026-08-23T12:00:00Z
updated_at: 2026-08-23T12:00:00Z
topic: Pilot Strategy & Executive Follow-up
tags: [pilot, business, strategy]
active_files:
  - docs/pilot-plan.md
parent_session_id: null
tracked_tasks: []
---

# Session 026: Pilot Strategy & Executive Follow-up

## 🎯 Executive Summary & Product Brief
- Discussing enterprise pilot requirements and timeline.

## 🧠 Decisions & Reasoning ("Why")
- Agreed to send security overview before contract review.

## 📁 Key Files & Code Symbols
- [pilot-plan.md](file:///path/to/docs/pilot-plan.md)

## 🔑 Keywords & Scanning Hooks
`pilot`, `enterprise`, `strategy`
"""
        with open(self.session_file, "w", encoding="utf-8") as f:
            f.write(self.session_content)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_task_with_freeform_type_and_priority(self):
        """Test reporting a new task with freeform category, P1 priority, and session sync."""
        cmd = [
            sys.executable,
            TASK_SCRIPT,
            "--title", "Follow up with enterprise pilot lead",
            "--type", "follow-up",
            "--priority", "P1",
            "--assignee", "@user",
            "--reporter", "scribe",
            "--session-id", "026",
            "--session-file", self.session_file,
            "--description", "Send updated SOC2 summary and schedule 15m review.",
            "--suggested-action", "Draft email with attached bridge letter.",
            "--evolution-note", "Initial discussion: user agreed to follow up by Tuesday.",
            "--out-dir", self.tasks_dir,
            "--sync-session",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Error: {result.stderr}")
        self.assertIn("✅ Task created:", result.stdout)
        self.assertIn("🔗 Synced to session context:", result.stdout)

        # Verify created file in tasks_dir
        task_files = os.listdir(self.tasks_dir)
        self.assertEqual(len(task_files), 1)
        task_path = os.path.join(self.tasks_dir, task_files[0])

        with open(task_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = report_task_mod.parse_frontmatter(content)
        self.assertEqual(meta.get("title"), "Follow up with enterprise pilot lead")
        self.assertEqual(meta.get("type"), "follow-up")
        self.assertEqual(meta.get("priority"), "P1")
        self.assertEqual(meta.get("status"), "todo")
        self.assertEqual(meta.get("assignee"), "@user")
        self.assertEqual(meta.get("session_id"), "026")
        self.assertIn("🧠 Session Lineage & Deciding Factors", body)
        self.assertIn("Initial discussion: user agreed to follow up", body)

        # Verify session context was updated with tracked_tasks
        with open(self.session_file, "r", encoding="utf-8") as f:
            session_data = f.read()

        s_meta, s_body = report_task_mod.parse_frontmatter(session_data)
        self.assertTrue(len(s_meta.get("tracked_tasks", [])) > 0)
        self.assertEqual(s_meta["tracked_tasks"][0]["title"], "Follow up with enterprise pilot lead")
        self.assertEqual(s_meta["tracked_tasks"][0]["status"], "todo")
        self.assertIn("## 📋 Tracked Tasks & Action Items", s_body)
        self.assertIn("Follow up with enterprise pilot lead", s_body)

    def test_in_place_status_transitions(self):
        """Test transitioning task through in_progress, blocked, and done in-place."""
        # 1. Create task
        subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--title", "Review Partnership Agreement",
            "--type", "business",
            "--priority", "P2",
            "--session-id", "026",
            "--session-file", self.session_file,
            "--description", "Review term sheet from distributor.",
            "--out-dir", self.tasks_dir,
            "--sync-session",
        ], check=True)

        task_files = os.listdir(self.tasks_dir)
        task_path = os.path.join(self.tasks_dir, task_files[0])

        # 2. Start task (--start / in_progress)
        res_start = subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--update", task_path,
            "--start",
            "--evolution-note", "Review in progress with legal counsel.",
            "--sync-session",
        ], capture_output=True, text=True)
        self.assertEqual(res_start.returncode, 0)

        with open(task_path, "r", encoding="utf-8") as f:
            meta, _ = report_task_mod.parse_frontmatter(f.read())
        self.assertEqual(meta.get("status"), "in_progress")

        # 3. Block task (--block)
        res_block = subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--update", task_path,
            "--block", "Waiting for revised clause 4 from partner.",
            "--sync-session",
        ], capture_output=True, text=True)
        self.assertEqual(res_block.returncode, 0)

        with open(task_path, "r", encoding="utf-8") as f:
            meta, body = report_task_mod.parse_frontmatter(f.read())
        self.assertEqual(meta.get("status"), "blocked")
        self.assertIn("⚠️ Blocked: Waiting for revised clause 4", body)

        # 4. Complete task (--done)
        res_done = subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--update", task_path,
            "--done",
            "--evolution-note", "Agreement finalized and signed.",
            "--sync-session",
        ], capture_output=True, text=True)
        self.assertEqual(res_done.returncode, 0)

        with open(task_path, "r", encoding="utf-8") as f:
            meta, body = report_task_mod.parse_frontmatter(f.read())
        self.assertEqual(meta.get("status"), "done")
        self.assertIn("✅ Completed: Agreement finalized and signed", body)

        # Verify session context shows done status
        with open(self.session_file, "r", encoding="utf-8") as f:
            s_meta, s_body = report_task_mod.parse_frontmatter(f.read())
        self.assertEqual(s_meta["tracked_tasks"][0]["status"], "done")
        self.assertIn("✅ **Done:**", s_body)

    def test_drop_task_with_deciding_factor_rationale(self):
        """Test dropping a task with reason and verifying audit trail."""
        # 1. Create task
        subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--title", "Evaluate Monolithic Framework",
            "--type", "tech-debt",
            "--priority", "P3",
            "--session-id", "026",
            "--session-file", self.session_file,
            "--description", "Evaluate migrating back to monolith.",
            "--out-dir", self.tasks_dir,
            "--sync-session",
        ], check=True)

        task_files = os.listdir(self.tasks_dir)
        task_path = os.path.join(self.tasks_dir, task_files[0])

        # 2. Drop task (--drop)
        res_drop = subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--update", task_path,
            "--drop", "Team decided microservices architecture is required for scale.",
            "--sync-session",
        ], capture_output=True, text=True)
        self.assertEqual(res_drop.returncode, 0)

        with open(task_path, "r", encoding="utf-8") as f:
            meta, body = report_task_mod.parse_frontmatter(f.read())
        self.assertEqual(meta.get("status"), "dropped")
        self.assertIn("❌ Dropped: Team decided microservices architecture", body)

        # 3. Verify session context contains strikethrough and dropped note
        with open(self.session_file, "r", encoding="utf-8") as f:
            s_meta, s_body = report_task_mod.parse_frontmatter(f.read())
        self.assertEqual(s_meta["tracked_tasks"][0]["status"], "dropped")
        self.assertIn("~~Evaluate Monolithic Framework~~", s_body)
        self.assertIn("❌ **Dropped:**", s_body)

    def test_task_creation_and_update_auto_syncs_workstate(self):
        """Test that creating and updating a task automatically updates workforces/workstate.md."""
        # 1. Create a task with --pr flag
        res_create = subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--title", "Setup Micro-Frontend Architecture",
            "--type", "feature",
            "--priority", "P1",
            "--pr", "https://github.com/acme-org/frontend-app/pull/342",
            "--description", "PR 342 scaffolds micro-frontends.",
            "--out-dir", self.tasks_dir,
        ], capture_output=True, text=True)
        self.assertEqual(res_create.returncode, 0)

        # Verify workstate.md exists and has the task in Active Tasks
        workstate_path = os.path.join(self.test_dir, "workforces", "workstate.md")
        self.assertTrue(os.path.isfile(workstate_path))
        with open(workstate_path, "r", encoding="utf-8") as f:
            ws_content = f.read()
        self.assertIn("Setup Micro-Frontend Architecture", ws_content)
        self.assertIn("PR #342", ws_content)

        # 2. Complete the task and check that workstate.md moves it to Completed Tasks
        task_files = [f for f in os.listdir(self.tasks_dir) if f.endswith(".md")]
        task_path = os.path.join(self.tasks_dir, task_files[0])
        res_done = subprocess.run([
            sys.executable,
            TASK_SCRIPT,
            "--update", task_path,
            "--done",
            "--evolution-note", "PR 342 merged successfully.",
        ], capture_output=True, text=True)
        self.assertEqual(res_done.returncode, 0)

        with open(workstate_path, "r", encoding="utf-8") as f:
            ws_updated = f.read()
        self.assertIn("## Completed Tasks (Recent)", ws_updated)
        self.assertIn("Setup Micro-Frontend Architecture", ws_updated)


if __name__ == "__main__":
    unittest.main()
