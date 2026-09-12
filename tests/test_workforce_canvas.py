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
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANVAS_SCRIPT_DIR = REPO_ROOT / "skills" / "workforce-canvas" / "scripts"
if not CANVAS_SCRIPT_DIR.exists():
    CANVAS_SCRIPT_DIR = REPO_ROOT / ".agents" / "skills" / "workforce-canvas" / "scripts"
sys.path.insert(0, str(CANVAS_SCRIPT_DIR))

import server
import wait_for_message


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
        """Assert that workforce-canvas is part of CORE manifest regardless of installed teams."""
        resolver_dir = REPO_ROOT / "skills" / "workforce-management" / "scripts"
        sys.path.insert(0, str(resolver_dir))
        import resolve_manifest

        # Even with zero teams installed (pure core):
        manifest_none = resolve_manifest.resolve_manifest(str(REPO_ROOT), str(REPO_ROOT), teams_arg="none")
        self.assertIn("workforce-canvas", manifest_none["skills"])

        # With only marketing installed:
        manifest_mkt = resolve_manifest.resolve_manifest(str(REPO_ROOT), str(REPO_ROOT), teams_arg="marketing")
        self.assertIn("workforce-canvas", manifest_mkt["skills"])

        # With only dev installed:
        manifest_dev = resolve_manifest.resolve_manifest(str(REPO_ROOT), str(REPO_ROOT), teams_arg="dev")
        self.assertIn("workforce-canvas", manifest_dev["skills"])

    def test_standup_data_and_cockpit_helpers(self):
        """Verify get_standup_data, create_task_file, and resolve_inbox_item."""
        tasks = server.get_all_tasks(self.root_path)
        standup = server.get_standup_data(self.root_path, tasks, [], [])
        self.assertIsNotNone(standup["one_thing"])
        self.assertEqual(len(standup["needs_attention"]), 1)
        self.assertEqual(standup["needs_attention"][0]["id"], "task-mkt-01")

        # Test creating a new task
        new_task = server.create_task_file(self.root_path, {
            "title": "Automate Standup Cockpit View",
            "priority": "P0",
            "type": "feature",
            "description": "Render executive standup cockpit",
            "suggested_action": "Build UI"
        })
        self.assertEqual(new_task["priority"], "P0")
        self.assertTrue((self.root_path / new_task["file"]).exists())

        # Test resolving inbox item
        human_dir = self.root_path / "workforces" / "inbox" / "human_review"
        human_dir.mkdir(parents=True, exist_ok=True)
        inbox_file = human_dir / "inbox-test-approval.json"
        inbox_file.write_text(json.dumps({
            "id": "inbox-test-approval",
            "title": "Approval Item",
            "content": "Need approval on payment gateway",
            "requires_human": True
        }), encoding="utf-8")

        res = server.resolve_inbox_item(self.root_path, "inbox-test-approval", "approve", "P1", "feature")
        self.assertEqual(res["action"], "approved")
        self.assertFalse(inbox_file.exists())
        self.assertTrue((self.root_path / res["task"]["file"]).exists())

    def test_emit_event_creates_immutable_pending_file(self):
        """Verify emit_event creates pending/ and processed/ directories and writes immutable event files."""
        payload1 = {"comment": "Check JWT validation", "author": "@human", "target_id": "task-auth-01"}
        event1 = server.emit_event(self.root_path, "comment", payload1)

        events_dir = self.root_path / "workforces" / ".events"
        pending_dir = events_dir / "pending"
        processed_dir = events_dir / "processed"
        self.assertTrue(pending_dir.exists())
        self.assertTrue(processed_dir.exists())

        event1_file = pending_dir / f"{event1['id']}.json"
        self.assertTrue(event1_file.exists())
        self.assertIn("_0001_comment", event1["id"])

        data1 = json.loads(event1_file.read_text(encoding="utf-8"))
        self.assertEqual(data1["id"], event1["id"])
        self.assertEqual(data1["event_type"], "comment")
        self.assertEqual(data1["payload"]["comment"], "Check JWT validation")

        # Emit second event and verify sequence increment
        payload2 = {"title": "Add OAuth support", "type": "feature", "content": "Support Google OAuth"}
        event2 = server.emit_event(self.root_path, "inbox_submission", payload2)
        self.assertIn("_0002_inbox_submission", event2["id"])
        self.assertTrue((pending_dir / f"{event2['id']}.json").exists())

    def test_wait_for_message_immediate_catchup_offline_queue(self):
        """Verify immediate catch-up when events arrive while the watcher is offline (zero sleep, zero dropped messages)."""
        # 1. Queue events while watcher is offline
        ev1 = server.emit_event(self.root_path, "comment", {"comment": "First offline comment", "author": "@human"})
        ev2 = server.emit_event(self.root_path, "inbox_submission", {"title": "Offline Inbox Item", "type": "task"})
        ev3 = server.emit_event(self.root_path, "comment", {"comment": "Third offline comment", "author": "@designer"})

        pending_dir = self.root_path / "workforces" / ".events" / "pending"
        processed_dir = self.root_path / "workforces" / ".events" / "processed"
        cursor_file = self.root_path / "workforces" / ".events" / "cursor.json"

        self.assertEqual(len(list(pending_dir.glob("*.json"))), 3)

        # 2. Launch wait_for_message - must catch up immediately without sleeping
        t_start = time.time()
        processed = wait_for_message.wait_for_message(self.root_path, once=True)
        duration = time.time() - t_start

        # Zero-sleep catch-up should complete in well under 0.4s
        self.assertLess(duration, 0.4)
        self.assertEqual(len(processed), 3)
        self.assertEqual(processed[0]["id"], ev1["id"])
        self.assertEqual(processed[1]["id"], ev2["id"])
        self.assertEqual(processed[2]["id"], ev3["id"])

        # 3. Verify all pending events moved to processed/ and zero files remain in pending/
        self.assertEqual(len(list(pending_dir.glob("*.json"))), 0)
        self.assertEqual(len(list(processed_dir.glob("*.json"))), 3)

        # 4. Verify cursor.json is updated with last_processed_id and last_processed_timestamp
        self.assertTrue(cursor_file.exists())
        cursor_data = json.loads(cursor_file.read_text(encoding="utf-8"))
        self.assertEqual(cursor_data["last_processed_id"], ev3["id"])
        self.assertEqual(cursor_data["last_processed_timestamp"], ev3["timestamp"])
        self.assertEqual(cursor_data["total_processed"], 3)

        # 5. Subsequent run with no new events returns empty list immediately
        subsequent = wait_for_message.wait_for_message(self.root_path, once=True)
        self.assertEqual(subsequent, [])

    def test_wait_for_message_batch_processing_and_cursor(self):
        """Verify max-batch limits event processing and properly advances cursor across batches."""
        ev1 = server.emit_event(self.root_path, "comment", {"comment": "Batch 1", "author": "@human"})
        ev2 = server.emit_event(self.root_path, "comment", {"comment": "Batch 2", "author": "@human"})
        ev3 = server.emit_event(self.root_path, "comment", {"comment": "Batch 3", "author": "@human"})

        cursor_file = self.root_path / "workforces" / ".events" / "cursor.json"

        # First batch: max 2 events
        batch1 = wait_for_message.wait_for_message(self.root_path, once=True, max_batch=2)
        self.assertEqual(len(batch1), 2)
        self.assertEqual(batch1[0]["id"], ev1["id"])
        self.assertEqual(batch1[1]["id"], ev2["id"])

        cursor1 = json.loads(cursor_file.read_text(encoding="utf-8"))
        self.assertEqual(cursor1["last_processed_id"], ev2["id"])
        self.assertEqual(cursor1["total_processed"], 2)

        # Second batch: remaining 1 event
        batch2 = wait_for_message.wait_for_message(self.root_path, once=True, max_batch=2)
        self.assertEqual(len(batch2), 1)
        self.assertEqual(batch2[0]["id"], ev3["id"])

        cursor2 = json.loads(cursor_file.read_text(encoding="utf-8"))
        self.assertEqual(cursor2["last_processed_id"], ev3["id"])
        self.assertEqual(cursor2["total_processed"], 3)

    def test_wait_for_message_polling_detects_new_event(self):
        """Verify polling loop detects an event written after watcher starts."""
        results = []

        def worker():
            res = wait_for_message.wait_for_message(self.root_path, timeout=5.0, poll_interval=0.1)
            results.extend(res)

        t = threading.Thread(target=worker)
        t.start()

        time.sleep(0.2)
        server.emit_event(self.root_path, "comment", {"comment": "Dynamically arriving event", "author": "@human"})

        t.join(timeout=3.0)
        self.assertFalse(t.is_alive())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["payload"]["comment"], "Dynamically arriving event")

    def test_wait_for_message_stopped_session_exits(self):
        """Verify wait_for_message exits cleanly if canvas session is marked stopped."""
        session_file = self.root_path / "workforces" / ".canvas-session.json"
        session_file.write_text(json.dumps({"status": "stopped"}), encoding="utf-8")

        t_start = time.time()
        res = wait_for_message.wait_for_message(self.root_path, timeout=5.0, poll_interval=0.1)
        duration = time.time() - t_start

        self.assertEqual(res, [])
        self.assertLess(duration, 1.0)

    def test_wait_for_message_cli_execution(self):
        """Verify running wait_for_message.py via CLI executes properly and outputs formatted dispatch summary."""
        server.emit_event(self.root_path, "comment", {
            "comment": "CLI test verification",
            "author": "@programmer",
            "target_id": "task-auth-01",
            "file": "workforces/tasks/20260901-010000-build-auth-service.md",
            "pin": {"x": 10.0, "y": 20.0}
        })

        cli_script = CANVAS_SCRIPT_DIR / "wait_for_message.py"
        res = subprocess.run(
            [sys.executable, str(cli_script), "--root", str(self.root_path), "--once"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("WORKFORCE CANVAS EVENT DISPATCH", res.stdout)
        self.assertIn("CLI test verification", res.stdout)
        self.assertIn("@programmer", res.stdout)

    def test_wait_for_message_concurrent_workers_race_condition(self):
        """Verify multiple concurrent workers drain pending events with zero dropped events and zero deletions."""
        total_events = 12
        for i in range(total_events):
            server.emit_event(self.root_path, "comment", {"comment": f"Concurrent comment {i}", "author": "@tester"})

        pending_dir = self.root_path / "workforces" / ".events" / "pending"
        processed_dir = self.root_path / "workforces" / ".events" / "processed"
        self.assertEqual(len(list(pending_dir.glob("*.json"))), total_events)

        worker_results = [[], [], []]

        def worker(idx):
            res = wait_for_message.wait_for_message(self.root_path, once=True, max_batch=5)
            worker_results[idx].extend(res)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Collect all processed IDs across all workers
        processed_ids = []
        for r in worker_results:
            for ev in r:
                self.assertNotIn("error", ev, f"Worker encountered error event: {ev}")
                processed_ids.append(ev["id"])

        # No duplicate events claimed across workers
        self.assertEqual(len(processed_ids), len(set(processed_ids)))

        # Drain any remaining events in a final pass
        remaining = wait_for_message.wait_for_message(self.root_path, once=True, max_batch=20)
        for ev in remaining:
            self.assertNotIn("error", ev)
            processed_ids.append(ev["id"])

        self.assertEqual(len(processed_ids), total_events)
        self.assertEqual(len(list(pending_dir.glob("*.json"))), 0)
        self.assertEqual(len(list(processed_dir.glob("*.json"))), total_events)

    def test_wait_for_message_chronological_ordering_beyond_padding(self):
        """Verify sorting handles sequence numbers with differing digit lengths (e.g. 9999 vs 10000)."""
        pending_dir = self.root_path / "workforces" / ".events" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        now_ts = "20260912T120000Z"
        f1 = pending_dir / f"{now_ts}_9999_comment.json"
        f2 = pending_dir / f"{now_ts}_10000_comment.json"
        f3 = pending_dir / f"{now_ts}_10001_comment.json"

        f1.write_text(json.dumps({"id": f"{now_ts}_9999_comment", "timestamp": "2026-09-12T12:00:00Z", "payload": {"num": 1}}), encoding="utf-8")
        f2.write_text(json.dumps({"id": f"{now_ts}_10000_comment", "timestamp": "2026-09-12T12:00:00Z", "payload": {"num": 2}}), encoding="utf-8")
        f3.write_text(json.dumps({"id": f"{now_ts}_10001_comment", "timestamp": "2026-09-12T12:00:00Z", "payload": {"num": 3}}), encoding="utf-8")

        processed = wait_for_message.wait_for_message(self.root_path, once=True)
        self.assertEqual(len(processed), 3)
        self.assertEqual(processed[0]["id"], f"{now_ts}_9999_comment")
        self.assertEqual(processed[1]["id"], f"{now_ts}_10000_comment")
        self.assertEqual(processed[2]["id"], f"{now_ts}_10001_comment")

    def test_wait_for_message_get_cursor_helper(self):
        """Verify get_cursor returns valid defaults when missing and parsed state when present."""
        empty_dir = Path(tempfile.mkdtemp(prefix="test_cursor_"))
        cursor_default = wait_for_message.get_cursor(empty_dir)
        self.assertIsNone(cursor_default["last_processed_id"])
        self.assertEqual(cursor_default["total_processed"], 0)

        ev = server.emit_event(empty_dir, "comment", {"comment": "Cursor test", "author": "@tester"})
        wait_for_message.wait_for_message(empty_dir, once=True)

        cursor_active = wait_for_message.get_cursor(empty_dir)
        self.assertEqual(cursor_active["last_processed_id"], ev["id"])
        self.assertEqual(cursor_active["total_processed"], 1)
        shutil.rmtree(empty_dir, ignore_errors=True)




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

    def test_heartbeat_endpoints(self):
        # GET /api/heartbeat
        url_get = f"http://127.0.0.1:{self.port}/api/heartbeat"
        req_get = urllib.request.Request(url_get)
        with urllib.request.urlopen(req_get, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "alive")
            self.assertIn("idle_timeout", data)
            self.assertIn("time_remaining", data)
            self.assertIn("server_pid", data)

        # POST /api/heartbeat
        url_post = f"http://127.0.0.1:{self.port}/api/heartbeat"
        req_post = urllib.request.Request(url_post, data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_post, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "alive")

    def test_shutdown_endpoint(self):
        class TestTCPServer(server.socketserver.TCPServer):
            allow_reuse_address = True

        test_httpd = TestTCPServer(("127.0.0.1", 0), server.WorkforceCanvasHandler)
        test_port = test_httpd.server_address[1]
        server.WorkforceCanvasHandler.httpd_instance = test_httpd
        server.WorkforceCanvasHandler.is_shutting_down = False
        t = threading.Thread(target=test_httpd.serve_forever)
        t.daemon = True
        t.start()
        time.sleep(0.1)

        shut_url = f"http://127.0.0.1:{test_port}/api/shutdown"
        shut_req = urllib.request.Request(shut_url, data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(shut_req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])

        t.join(timeout=2)
        test_httpd.server_close()
        self.assertFalse(t.is_alive())

    def test_idle_watchdog_auto_shutdown(self):
        class TestTCPServer(server.socketserver.TCPServer):
            allow_reuse_address = True

        test_httpd = TestTCPServer(("127.0.0.1", 0), server.WorkforceCanvasHandler)
        server.WorkforceCanvasHandler.httpd_instance = test_httpd
        server.WorkforceCanvasHandler.idle_timeout = 1  # 1 second timeout
        server.WorkforceCanvasHandler.last_activity_time = time.time() - 2  # Already expired
        server.WorkforceCanvasHandler.is_shutting_down = False

        t = threading.Thread(target=test_httpd.serve_forever)
        t.daemon = True
        t.start()
        time.sleep(0.05)

        # Trigger watchdog logic
        elapsed = time.time() - server.WorkforceCanvasHandler.last_activity_time
        if elapsed >= server.WorkforceCanvasHandler.idle_timeout:
            server.WorkforceCanvasHandler.trigger_shutdown(delay=0.05)

        t.join(timeout=2)
        test_httpd.server_close()
        self.assertFalse(t.is_alive())


    def test_inbox_submit_and_listing(self):
        # 1. Submit item via POST /api/inbox/submit
        url = f"http://127.0.0.1:{self.port}/api/inbox/submit"
        payload = json.dumps({
            "title": "Chrome Extension Research Capture",
            "content": "Found high-value competitor telemetry on SaaS pricing.",
            "type": "research",
            "source_url": "https://example.com/pricing",
            "selection": "Enterprise plan: $99/mo with unlimited seats",
            "auto_dispatch": False,
            "tags": ["pricing", "competitor"]
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertIn("id", data)
            self.assertIn("file", data)

        # 2. List items via GET /api/inbox
        list_url = f"http://127.0.0.1:{self.port}/api/inbox"
        list_req = urllib.request.Request(list_url)
        with urllib.request.urlopen(list_req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            inbox_data = json.loads(resp.read().decode("utf-8"))
            self.assertGreaterEqual(inbox_data["count"], 1)
            titles = [item["title"] for item in inbox_data["items"]]
            self.assertIn("Chrome Extension Research Capture", titles)

    def test_comments_and_visual_pins(self):
        url = f"http://127.0.0.1:{self.port}/api/comments"
        payload = json.dumps({
            "target_type": "task",
            "target_id": "sample-task",
            "file": "workforces/tasks/20260901-task.md",
            "comment": "Ensure button contrast complies with WCAG AA.",
            "author": "@designer",
            "pin": {"x": 42.5, "y": 78.0},
            "stitch_url": "https://stitch.withgoogle.com/projects/mock-123"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["comment"]["author"], "@designer")
            self.assertEqual(data["comment"]["pin"]["x"], 42.5)

        # Verify comment retrieval via GET /api/comments
        get_url = f"http://127.0.0.1:{self.port}/api/comments?target_id=sample-task"
        with urllib.request.urlopen(urllib.request.Request(get_url), timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            comments_data = json.loads(resp.read().decode("utf-8"))
            self.assertGreaterEqual(len(comments_data["comments"]), 1)

        # Verify task file was updated with evolution note
        task_content = (self.tasks_dir / "20260901-task.md").read_text(encoding="utf-8")
        self.assertIn("@designer", task_content)
        self.assertIn("WCAG AA", task_content)

        # 3. Post comment with target_id ONLY (no file path)
        payload2 = json.dumps({
            "target_id": "sample-task",
            "comment": "Added secondary feedback without explicit file path.",
            "author": "@programmer",
            "pin": {"x": 10.0, "y": 20.0}
        }).encode("utf-8")
        req2 = urllib.request.Request(url, data=payload2, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2, timeout=3) as resp2:
            self.assertEqual(resp2.status, 200)
            data2 = json.loads(resp2.read().decode("utf-8"))
            self.assertTrue(data2["success"])

        # Verify task was updated and comment is queryable via filename or target_id
        task_content2 = (self.tasks_dir / "20260901-task.md").read_text(encoding="utf-8")
        self.assertIn("secondary feedback", task_content2)

        get_url_by_filename = f"http://127.0.0.1:{self.port}/api/comments?target_id=20260901-task.md"
        with urllib.request.urlopen(urllib.request.Request(get_url_by_filename), timeout=3) as resp_fn:
            self.assertEqual(resp_fn.status, 200)
            fn_data = json.loads(resp_fn.read().decode("utf-8"))
            self.assertGreaterEqual(len(fn_data["comments"]), 1)

    def test_turn_summary_and_document_endpoints(self):
        # Create a mock turn-summary.txt
        tmp_dir = self.root_path / "workforces" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        summary_file = tmp_dir / "turn-summary.txt"
        summary_file.write_text("Turn summary: 10 tools executed, 0 errors.", encoding="utf-8")

        # GET /api/turn-summary
        url = f"http://127.0.0.1:{self.port}/api/turn-summary"
        with urllib.request.urlopen(urllib.request.Request(url), timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["exists"])
            self.assertIn("10 tools executed", data["content"])

        # GET /api/document?path=workforces/tasks/20260901-task.md
        doc_url = f"http://127.0.0.1:{self.port}/api/document?path=workforces/tasks/20260901-task.md"
        with urllib.request.urlopen(urllib.request.Request(doc_url), timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            doc_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(doc_data["name"], "20260901-task.md")
            self.assertEqual(doc_data["type"], "markdown")
            self.assertIn("Sample Canvas Task", doc_data["content"])

    def test_inbox_heartbeat_watcher_routing(self):
        watcher = server.InboxHeartbeatWatcher(self.root_path, interval=0.1)
        pending_dir = self.root_path / "workforces" / "inbox" / "pending"
        processed_dir = self.root_path / "workforces" / "inbox" / "processed"
        human_dir = self.root_path / "workforces" / "inbox" / "human_review"
        ideas_dir = self.root_path / "workforces" / "ideas"
        pending_dir.mkdir(parents=True, exist_ok=True)

        # 1. Item requiring human review (.json)
        human_item = {
            "id": "inbox-human-01",
            "title": "Subjective Design Polish",
            "content": "Need human eyes on color palette.",
            "type": "design",
            "auto_dispatch": False,
            "requires_human": True
        }
        (pending_dir / "human-01.json").write_text(json.dumps(human_item), encoding="utf-8")

        # 2. Item auto-dispatchable (.json)
        dispatch_item = {
            "id": "inbox-auto-01",
            "title": "Run Unit Test Suite",
            "content": "Execute pytest across all unit tests.",
            "type": "dev",
            "auto_dispatch": True
        }
        (pending_dir / "auto-01.json").write_text(json.dumps(dispatch_item), encoding="utf-8")

        # 3. Item auto-dispatchable Markdown (.md)
        md_item_content = """---
id: "inbox-md-01"
title: "Benchmark Competitor Latency"
type: "research"
priority: "P1"
auto_dispatch: true
---
Analyze roundtrip latency for web socket canvas syncing.
"""
        (pending_dir / "benchmark-latency.md").write_text(md_item_content, encoding="utf-8")

        # 4. Item routed to ideas folder
        idea_item = {
            "id": "inbox-idea-01",
            "title": "AR Canvas Spatial Mode",
            "content": "Explore WebXR 3D node canvas projection.",
            "type": "idea",
            "auto_dispatch": False
        }
        (pending_dir / "idea-spatial.json").write_text(json.dumps(idea_item), encoding="utf-8")

        # Run single scan
        watcher._scan_and_route(pending_dir, processed_dir, human_dir, self.tasks_dir)

        # Assert human item routed to human_dir
        self.assertTrue((human_dir / "human-01.json").exists())
        self.assertFalse((pending_dir / "human-01.json").exists())

        # Assert auto item created a task in tasks_dir and moved to processed_dir
        self.assertTrue((processed_dir / "auto-01.json").exists())
        self.assertFalse((pending_dir / "auto-01.json").exists())
        created_tasks = list(self.tasks_dir.glob("*run-unit-test-suite*.md"))
        self.assertEqual(len(created_tasks), 1)
        self.assertIn("Execute pytest", created_tasks[0].read_text(encoding="utf-8"))

        # Assert md item created a task in tasks_dir and moved to processed_dir
        self.assertTrue((processed_dir / "benchmark-latency.json").exists())
        self.assertFalse((pending_dir / "benchmark-latency.md").exists())
        created_md_tasks = list(self.tasks_dir.glob("*benchmark-competitor-latency*.md"))
        self.assertEqual(len(created_md_tasks), 1)
        self.assertIn("Analyze roundtrip latency", created_md_tasks[0].read_text(encoding="utf-8"))

        # Assert idea was routed to workforces/ideas/
        self.assertTrue(ideas_dir.exists())
        created_ideas = list(ideas_dir.glob("*ar-canvas-spatial-mode*.md"))
        self.assertEqual(len(created_ideas), 1)
        self.assertIn("WebXR", created_ideas[0].read_text(encoding="utf-8"))

    def test_session_state_file_lifecycle(self):
        server.write_session_state(self.root_path, "running", 8765, 12345, {"test_mode": True})
        session_file = self.root_path / "workforces" / ".canvas-session.json"
        self.assertTrue(session_file.exists())
        state = json.loads(session_file.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["port"], 8765)
        self.assertEqual(state["pid"], 12345)
        self.assertTrue(state["test_mode"])

        server.write_session_state(self.root_path, "stopped", 8765, 12345)
        state_stopped = json.loads(session_file.read_text(encoding="utf-8"))
        self.assertEqual(state_stopped["status"], "stopped")

    def test_copilot_sidebar_visibility_and_web_elements(self):
        """Verify web assets contain the intelligent copilot sidebar toggle and close elements."""
        web_dir = REPO_ROOT / "skills" / "workforce-canvas" / "web"
        index_html = (web_dir / "index.html").read_text(encoding="utf-8")
        canvas_js = (web_dir / "canvas.js").read_text(encoding="utf-8")
        canvas_css = (web_dir / "canvas.css").read_text(encoding="utf-8")

        # HTML elements check
        self.assertIn('id="studio-copilot-feed"', index_html)
        self.assertIn('id="btn-close-copilot-panel"', index_html)
        self.assertIn('id="btn-toggle-task-inspector"', index_html)

        # CSS rule check
        self.assertIn('#studio-copilot-feed.hidden', canvas_css)
        self.assertIn('display: none !important;', canvas_css)

        # JS contract checks
        self.assertIn('btn-close-copilot-panel', canvas_js)
        self.assertIn('btn-toggle-task-inspector', canvas_js)
        self.assertIn("studioState.activeScenario === 'cockpit'", canvas_js)
        self.assertIn("studioState.activeScenario === 'tasks'", canvas_js)
        self.assertIn("copilotFeed.classList.add('hidden')", canvas_js)

    def test_kanban_pipeline_ordering_and_archive_support(self):
        """Verify Kanban pipeline is ordered (todo, in_progress, blocked, done) and archive is supported."""
        web_dir = REPO_ROOT / "skills" / "workforce-canvas" / "web"
        index_html = (web_dir / "index.html").read_text(encoding="utf-8")
        canvas_js = (web_dir / "canvas.js").read_text(encoding="utf-8")

        # Verify pipeline ordering in HTML
        todo_pos = index_html.find('id="kanban-col-todo"')
        in_prog_pos = index_html.find('id="kanban-col-in-progress"')
        blocked_pos = index_html.find('id="kanban-col-blocked"')
        done_pos = index_html.find('id="kanban-col-done"')

        self.assertTrue(todo_pos != -1 and in_prog_pos != -1 and blocked_pos != -1 and done_pos != -1)
        self.assertTrue(todo_pos < in_prog_pos < blocked_pos < done_pos, "Pipeline columns must be ordered: Up Next (todo), In Progress, Blocked / Stalled, Completed (done)")

        # Verify hide completed button and archive buttons in HTML
        self.assertIn('id="btn-toggle-completed-filter"', index_html)
        self.assertIn('id="btn-kanban-archive-all-done"', index_html)

        # Verify JS contracts
        self.assertIn("['todo', 'in_progress', 'blocked', 'done']", canvas_js)
        self.assertIn('refreshActiveWorkspaceView', canvas_js)
        self.assertIn('btn-archive-task', canvas_js)
        self.assertIn('btn-toggle-completed-filter', canvas_js)

        # Test backend task archive support
        sample_task = self.tasks_dir / "20260901-task.md"
        updated = server.update_task_file(self.root_path, str(sample_task.relative_to(self.root_path)), {"archived": True})
        self.assertTrue(sample_task.read_text(encoding="utf-8").find("archived: true") != -1)

        tasks = server.get_all_tasks(self.root_path)
        t1 = next(t for t in tasks if t["id"] == "sample-task")
        self.assertTrue(t1["archived"])

    def test_task_auto_assignment_and_dispatch_queue(self):
        """Verify moving a task to in_progress auto-assigns the agent and records to dispatch queue."""
        # Create unassigned dev task
        unassigned_task = self.tasks_dir / "20260905-unassigned-feature.md"
        unassigned_task.write_text("""---
id: "task-unassigned-01"
title: "Implement API Rate Limiter"
type: "dev"
priority: "P1"
status: "todo"
reporter: "@human"
---
Rate limiter token bucket algorithm.
""", encoding="utf-8")

        # Update to in_progress without providing assignee
        updated = server.update_task_file(self.root_path, "20260905-unassigned-feature.md", {"status": "in_progress"})
        self.assertEqual(updated.get("status"), "in_progress")
        self.assertEqual(updated.get("delegated_to"), "@programmer")
        self.assertEqual(updated.get("assignee"), "@programmer")

        # Check dispatch queue file was created
        queue_file = self.tasks_dir / ".dispatch_queue.json"
        self.assertTrue(queue_file.exists())
        queue_items = json.loads(queue_file.read_text(encoding="utf-8"))
        self.assertTrue(len(queue_items) > 0)
        q_entry = next((i for i in queue_items if i.get("task_id") == "task-unassigned-01"), None)
        self.assertIsNotNone(q_entry)
        self.assertEqual(q_entry.get("agent"), "@programmer")
        self.assertEqual(q_entry.get("status"), "pending_execution")

        # Create design task and verify @designer mapping
        design_task = self.tasks_dir / "20260905-brand-refresh.md"
        design_task.write_text("""---
id: "task-design-01"
title: "Create Brand Mockups"
type: "design"
priority: "P2"
status: "todo"
---
Brand tokens and mockups.
""", encoding="utf-8")
        updated_design = server.update_task_file(self.root_path, "20260905-brand-refresh.md", {"status": "in_progress"})
        self.assertEqual(updated_design.get("delegated_to"), "@designer")

        # Verify watcher sweeps queue without error
        watcher = server.InboxHeartbeatWatcher(self.root_path)
        watcher._sweep_dispatch_queue(self.tasks_dir)
        queue_items_after = json.loads(queue_file.read_text(encoding="utf-8"))
        notified_entry = next((i for i in queue_items_after if i.get("task_id") == "task-unassigned-01"), None)
        self.assertTrue(notified_entry.get("notified"))

    def test_human_comment_inquiry_queues_dispatch(self):
        """Verify adding an inquiry comment from @human queues an actionable entry in .dispatch_queue.json."""
        task_file = self.tasks_dir / "20260906-audit-task.md"
        task_file.write_text("""---
id: "task-audit-01"
title: "Audit DB Query Latency"
type: "perf"
priority: "P1"
status: "todo"
---
Profile queries.
""", encoding="utf-8")

        comment_payload = {
            "target_type": "task",
            "target_id": "task-audit-01",
            "file": "workforces/tasks/20260906-audit-task.md",
            "comment": "can you check if this is done already",
            "author": "@human"
        }
        res = server.save_comment(self.root_path, comment_payload)
        self.assertEqual(res.get("dispatched_agent"), "@researcher")

        # Verify queue contains the comment inquiry
        queue_file = self.tasks_dir / ".dispatch_queue.json"
        self.assertTrue(queue_file.exists())
        queue_items = json.loads(queue_file.read_text(encoding="utf-8"))
        entry = next((i for i in queue_items if i.get("task_id") == "task-audit-01"), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("agent"), "@researcher")
        self.assertIn("Human comment inquiry", entry.get("action", ""))

    def test_http_event_emission_for_comments_and_inbox(self):
        """Verify POST /api/comments and POST /api/inbox/submit emit events into workforces/.events/pending/."""
        # Drain any existing events from previous tests
        events_dir = self.root_path / "workforces" / ".events"
        pending_dir = events_dir / "pending"
        if pending_dir.exists():
            for f in pending_dir.glob("*.json"):
                f.unlink()

        # 1. POST /api/comments
        comment_url = f"http://127.0.0.1:{self.port}/api/comments"
        comment_payload = json.dumps({
            "target_type": "task",
            "target_id": "sample-task",
            "file": "workforces/tasks/20260901-task.md",
            "comment": "Event emission test comment on task.",
            "author": "@auditor",
            "pin": {"x": 33.3, "y": 66.6},
            "stitch_url": "https://stitch.example.com/item/1"
        }).encode("utf-8")

        req1 = urllib.request.Request(comment_url, data=comment_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req1, timeout=3) as resp:
            self.assertEqual(resp.status, 200)

        # 2. POST /api/inbox/submit
        inbox_url = f"http://127.0.0.1:{self.port}/api/inbox/submit"
        inbox_payload = json.dumps({
            "title": "Event Emission Inbox Item",
            "content": "Verify event queue pipeline capture.",
            "type": "feature",
            "source_url": "https://example.com/feature-request",
            "selection": "Code snippet",
            "auto_dispatch": False,
            "tags": ["event", "pipeline"]
        }).encode("utf-8")

        req2 = urllib.request.Request(inbox_url, data=inbox_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2, timeout=3) as resp:
            self.assertEqual(resp.status, 200)

        # 3. Verify events appeared in pending/
        self.assertTrue(pending_dir.exists())
        pending_files = list(pending_dir.glob("*.json"))
        self.assertEqual(len(pending_files), 2)

        # Find comment event
        comment_event_file = next((f for f in pending_files if "_comment.json" in f.name), None)
        self.assertIsNotNone(comment_event_file)
        c_data = json.loads(comment_event_file.read_text(encoding="utf-8"))
        self.assertEqual(c_data["event_type"], "comment")
        self.assertEqual(c_data["payload"]["comment"], "Event emission test comment on task.")
        self.assertEqual(c_data["payload"]["author"], "@auditor")
        self.assertEqual(c_data["payload"]["pin"]["x"], 33.3)

        # Find inbox submission event
        inbox_event_file = next((f for f in pending_files if "_inbox_submission.json" in f.name), None)
        self.assertIsNotNone(inbox_event_file)
        i_data = json.loads(inbox_event_file.read_text(encoding="utf-8"))
        self.assertEqual(i_data["event_type"], "inbox_submission")
        self.assertEqual(i_data["payload"]["title"], "Event Emission Inbox Item")
        self.assertEqual(i_data["payload"]["type"], "feature")
        self.assertEqual(i_data["payload"]["source_url"], "https://example.com/feature-request")

        # 4. Drain pending events using wait_for_message and verify cursor
        processed = wait_for_message.wait_for_message(self.root_path, once=True)
        self.assertEqual(len(processed), 2)
        self.assertEqual(len(list(pending_dir.glob("*.json"))), 0)

        cursor_file = events_dir / "cursor.json"
        self.assertTrue(cursor_file.exists())
        cursor_data = json.loads(cursor_file.read_text(encoding="utf-8"))
        self.assertIn("last_processed_id", cursor_data)
        self.assertIn("last_processed_timestamp", cursor_data)
        self.assertGreaterEqual(cursor_data["total_processed"], 2)


if __name__ == "__main__":
    unittest.main()

