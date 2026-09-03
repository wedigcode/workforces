#!/usr/bin/env python3
"""
Unit and Integration Tests for Workforce Command Canvas Server and Data Aggregator.
Tests:
- YAML frontmatter parsing and task extraction across teams.
- Code blast radius caller/callee tracing from code-graph.json.
- Task status updates, priority modification, and evolution note appending.
- Dependency connection linking between tasks.
- HTTP API endpoints (/api/state, /api/impact, /api/task/update, /api/task/connect).
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANVAS_SCRIPT_DIR = REPO_ROOT / ".agents" / "skills" / "workforce-canvas" / "scripts"
if not CANVAS_SCRIPT_DIR.exists():
    CANVAS_SCRIPT_DIR = REPO_ROOT / "skills" / "workforce-canvas" / "scripts"
sys.path.insert(0, str(CANVAS_SCRIPT_DIR))

import server


class TestWorkforceCanvas(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_canvas_")
        self.root_path = Path(self.test_dir)
        self.workforces_dir = self.root_path / "workforces"
        self.tasks_dir = self.workforces_dir / "tasks"
        self.hypotheses_dir = self.workforces_dir / "hypotheses"
        self.goals_dir = self.workforces_dir / "goals"

        os.makedirs(self.tasks_dir, exist_ok=True)
        os.makedirs(self.hypotheses_dir, exist_ok=True)
        os.makedirs(self.goals_dir, exist_ok=True)

        # Create sample task 1 (dev)
        self.task1_file = self.tasks_dir / "20260901-010000-build-auth-service.md"
        self.task1_file.write_text("""---
id: "task-auth-01"
title: "Build Auth Service"
type: "dev"
priority: "P1"
status: "in_progress"
reporter: "@programmer"
blocked_by: []
---
Implementation of JWT token verification.
""", encoding="utf-8")

        # Create sample task 2 (marketing, blocked by task 1)
        self.task2_file = self.tasks_dir / "20260901-020000-launch-signup-campaign.md"
        self.task2_file.write_text("""---
id: "task-mkt-01"
title: "Launch Signup Campaign"
type: "marketing"
priority: "P2"
status: "blocked"
reporter: "@marketer"
blocked_by: ["task-auth-01"]
---
Ad campaigns on Google and Twitter.
""", encoding="utf-8")

        # Create sample code-graph.json
        self.code_graph_file = self.workforces_dir / "code-graph.json"
        self.code_graph_file.write_text(json.dumps({
            "symbol_count": 3,
            "symbols": [
                {
                    "name": "login_handler",
                    "kind": "function",
                    "file": "src/auth.py",
                    "line": 42,
                    "calls": ["verify_token", "db_lookup", "isinstance", "len"]
                },
                {
                    "name": "verify_token",
                    "kind": "function",
                    "file": "src/tokens.py",
                    "line": 15,
                    "calls": ["hash_secret"]
                },
                {
                    "name": "db_lookup",
                    "kind": "function",
                    "file": "src/database.py",
                    "line": 88,
                    "calls": []
                },
                {
                    "name": "api_gateway",
                    "kind": "function",
                    "file": "src/gateway.py",
                    "line": 100,
                    "calls": ["login_handler"]
                }
            ]
        }, indent=2), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_task_extraction_and_team_categorization(self):
        tasks = server.get_all_tasks(self.root_path)
        self.assertEqual(len(tasks), 2)

        task_map = {t["id"]: t for t in tasks}
        self.assertIn("task-auth-01", task_map)
        self.assertIn("task-mkt-01", task_map)

        # Verify team mapping
        self.assertEqual(task_map["task-auth-01"]["team"], "dev")
        self.assertEqual(task_map["task-mkt-01"]["team"], "marketing")
        self.assertEqual(task_map["task-mkt-01"]["blocked_by"], ["task-auth-01"])

    def test_code_blast_radius_tracing(self):
        # Target: login_handler
        blast = server.get_code_blast_radius(self.root_path, symbol_name="login_handler")
        self.assertTrue(blast["found"])
        self.assertEqual(blast["target"]["name"], "login_handler")

        # Upstream callees (what login_handler calls - only internal methods)
        callee_names = [c["name"] for c in blast["upstream_callees"]]
        self.assertIn("verify_token", callee_names)
        self.assertIn("db_lookup", callee_names)
        # Assert external/stdlib noise is filtered out
        self.assertNotIn("isinstance", callee_names)
        self.assertNotIn("len", callee_names)

        # Downstream callers (blast radius: who calls login_handler)
        caller_names = [c["name"] for c in blast["downstream_callers"]]
        self.assertIn("api_gateway", caller_names)
        self.assertIn("src/gateway.py", blast["affected_files"])

    def test_task_file_update_and_evolution_note(self):
        updates = {
            "status": "done",
            "priority": "P0",
            "evolution_note": "Token rotation security issue resolved."
        }
        res = server.update_task_file(
            self.root_path,
            "workforces/tasks/20260901-010000-build-auth-service.md",
            updates
        )
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["priority"], "P0")
        self.assertIn("Token rotation security issue resolved", res["_body"])

        # Verify file content persisted to disk
        content = self.task1_file.read_text(encoding="utf-8")
        self.assertIn('status: "done"', content)
        self.assertIn('priority: "P0"', content)
        self.assertIn("Evolution Note", content)

    def test_task_connection_dependency(self):
        # Programmatically connect task 2 to a new blocker
        all_tasks = server.get_all_tasks(self.root_path)
        task2 = next(t for t in all_tasks if t["id"] == "task-mkt-01")
        blocked_by = task2.get("blocked_by", [])
        blocked_by.append("task-external-dep")

        server.update_task_file(self.root_path, task2["file"], {"blocked_by": blocked_by})

        # Reload and check
        updated_tasks = server.get_all_tasks(self.root_path)
        updated_task2 = next(t for t in updated_tasks if t["id"] == "task-mkt-01")
        self.assertIn("task-external-dep", updated_task2["blocked_by"])

    def test_task_relationship_and_commit_linking(self):
        """Test linking git commits, symbols, and docs to tasks."""
        tasks = [
            {
                "id": "task-test-01",
                "title": "Interactive Workforce Canvas Engine",
                "body": "Implemented canvas in [docs/canvas.md](docs/canvas.md) using sync_workstate_from_tasks."
            }
        ]
        available_symbols = [
            {"name": "sync_workstate_from_tasks", "file": "personal_sync.py", "line": 40},
            {"name": "setUp", "file": "tests/test_foo.py", "line": 10}  # Should be filtered out
        ]
        commits = [
            {"hash": "6e8f477", "author": "Aaron", "date": "2026-09-03", "message": "feat(canvas): add interactive workforce canvas engine"}
        ]

        server.link_task_relationships(tasks, available_symbols, commits)

        task = tasks[0]
        self.assertEqual(len(task["linked_commits"]), 1)
        self.assertEqual(task["linked_commits"][0]["hash"], "6e8f477")
        self.assertEqual(len(task["linked_docs"]), 1)
        self.assertEqual(task["linked_docs"][0]["url"], "docs/canvas.md")
        sym_names = [s["name"] for s in task["linked_symbols"]]
        self.assertIn("sync_workstate_from_tasks", sym_names)
        self.assertNotIn("setUp", sym_names)

    def test_universal_core_installation_across_all_team_configurations(self):
        """Assert that workforce-canvas and wf-canvas are part of CORE manifest regardless of installed teams."""
        resolver_dir = REPO_ROOT / "skills" / "workforce-management" / "scripts"
        sys.path.insert(0, str(resolver_dir))
        import resolve_manifest

        # Even with zero teams installed (pure core):
        manifest_none = resolve_manifest.resolve_manifest(str(REPO_ROOT), str(REPO_ROOT), teams_arg="none")
        self.assertIn("workforce-canvas", manifest_none["skills"])
        self.assertIn("wf-canvas.md", manifest_none["workflows"])

        # With only marketing installed:
        manifest_mkt = resolve_manifest.resolve_manifest(str(REPO_ROOT), str(REPO_ROOT), teams_arg="marketing")
        self.assertIn("workforce-canvas", manifest_mkt["skills"])
        self.assertIn("wf-canvas.md", manifest_mkt["workflows"])

        # With only dev installed:
        manifest_dev = resolve_manifest.resolve_manifest(str(REPO_ROOT), str(REPO_ROOT), teams_arg="dev")
        self.assertIn("workforce-canvas", manifest_dev["skills"])
        self.assertIn("wf-canvas.md", manifest_dev["workflows"])


class TestWorkforceCanvasHTTPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="test_canvas_http_")
        cls.root_path = Path(cls.test_dir)
        cls.tasks_dir = cls.root_path / "workforces" / "tasks"
        os.makedirs(cls.tasks_dir, exist_ok=True)

        task_file = cls.tasks_dir / "20260901-task.md"
        task_file.write_text("""---
id: "sample-task"
title: "Sample Canvas Task"
type: "dev"
status: "todo"
priority: "P2"
---
Test description.
""", encoding="utf-8")

        server.WorkforceCanvasHandler.root_dir = cls.root_path

        class ReusableTCPServer(server.socketserver.TCPServer):
            allow_reuse_address = True

        cls.httpd = ReusableTCPServer(("127.0.0.1", 0), server.WorkforceCanvasHandler)
        cls.port = cls.httpd.server_address[1]
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_get_state_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/state"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("tasks", data)
            self.assertIn("stats", data)
            self.assertEqual(data["stats"]["total_tasks"], 1)

    def test_update_task_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/task/update"
        payload = json.dumps({
            "file": "workforces/tasks/20260901-task.md",
            "updates": {"status": "in_progress"}
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["task"]["status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
