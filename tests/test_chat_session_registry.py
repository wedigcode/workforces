#!/usr/bin/env python3
"""
Unit tests for Chat Session Registry, Multi-Session Routing, and Targeted Event Dispatch.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

CANVAS_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "workforce-canvas" / "scripts"
sys.path.insert(0, str(CANVAS_SCRIPTS))

from session_registry import (
    detect_current_chat_session,
    get_chat_sessions,
    register_chat_session,
    heartbeat_chat_session,
    unregister_chat_session,
    emit_session_directive,
)
from wait_for_message import (
    process_pending_events,
    format_event_summary,
)
from server import (
    create_task_file,
    update_task_file,
    get_all_tasks,
    emit_event,
)

class TestChatSessionRegistry(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="wf_test_session_")
        self.root_path = Path(self.test_dir)
        (self.root_path / "workforces" / "tasks").mkdir(parents=True, exist_ok=True)
        (self.root_path / "workforces" / ".events" / "pending").mkdir(parents=True, exist_ok=True)
        (self.root_path / "workforces" / ".events" / "processed").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detect_current_chat_session_env(self):
        old_val = os.environ.get("ANTIGRAVITY_CONVERSATION_ID")
        try:
            os.environ["ANTIGRAVITY_CONVERSATION_ID"] = "session-alpha-12345"
            detected = detect_current_chat_session()
            self.assertEqual(detected, "session-alpha-12345")
        finally:
            if old_val is not None:
                os.environ["ANTIGRAVITY_CONVERSATION_ID"] = old_val
            else:
                os.environ.pop("ANTIGRAVITY_CONVERSATION_ID", None)

    def test_register_and_heartbeat_and_prune(self):
        entry_a = register_chat_session(
            root_dir=self.root_path,
            session_id="chat-session-aaa",
            alias="Chat Alpha",
            role="watcher",
            port=8765,
            status="active"
        )
        self.assertEqual(entry_a["session_id"], "chat-session-aaa")
        self.assertEqual(entry_a["alias"], "Chat Alpha")
        self.assertTrue(entry_a["has_watcher"])

        entry_b = register_chat_session(
            root_dir=self.root_path,
            session_id="chat-session-bbb",
            alias="Chat Beta",
            role="webserver",
            port=8766,
            status="active"
        )
        self.assertEqual(entry_b["session_id"], "chat-session-bbb")
        self.assertTrue(entry_b["has_server"])

        sessions = get_chat_sessions(self.root_path)
        self.assertIn("chat-session-aaa", sessions)
        self.assertIn("chat-session-bbb", sessions)

        self.assertTrue(heartbeat_chat_session(self.root_path, "chat-session-aaa", current_task="task-1"))
        sessions_after_hb = get_chat_sessions(self.root_path)
        self.assertEqual(sessions_after_hb["chat-session-aaa"]["current_task"], "task-1")

        self.assertTrue(unregister_chat_session(self.root_path, "chat-session-bbb", status="stopped"))
        sessions_after_unreg = get_chat_sessions(self.root_path)
        self.assertEqual(sessions_after_unreg["chat-session-bbb"]["status"], "stopped")

    def test_targeted_event_isolation(self):
        ev1 = emit_session_directive(
            root_dir=self.root_path,
            target_session_id="chat-session-1",
            message="Focus on implementing feature X",
            sender="@human"
        )
        self.assertEqual(ev1["target_chat_session_id"], "chat-session-1")

        ev2 = emit_session_directive(
            root_dir=self.root_path,
            target_session_id="chat-session-2",
            message="Review PR #45",
            sender="@human"
        )
        self.assertEqual(ev2["target_chat_session_id"], "chat-session-2")

        processed_by_session1 = process_pending_events(
            root_dir=self.root_path,
            chat_session_id="chat-session-1"
        )
        self.assertEqual(len(processed_by_session1), 1)
        self.assertEqual(processed_by_session1[0]["target_chat_session_id"], "chat-session-1")

        pending_dir = self.root_path / "workforces" / ".events" / "pending"
        remaining_pending = list(pending_dir.glob("*.json"))
        self.assertEqual(len(remaining_pending), 1)

        processed_by_session2 = process_pending_events(
            root_dir=self.root_path,
            chat_session_id="chat-session-2"
        )
        self.assertEqual(len(processed_by_session2), 1)
        self.assertEqual(processed_by_session2[0]["target_chat_session_id"], "chat-session-2")

        self.assertEqual(len(list(pending_dir.glob("*.json"))), 0)

    def test_task_creation_and_assignment_with_chat_session(self):
        task_data = {
            "title": "Build Multi-Session Dashboard Sync",
            "priority": "P0",
            "type": "dev",
            "team": "dev",
            "description": "Ensure distinct sessions can be selected.",
            "chat_session_id": "chat-session-gamma"
        }
        created = create_task_file(self.root_path, task_data)
        self.assertEqual(created["chat_session_id"], "chat-session-gamma")

        all_tasks = get_all_tasks(self.root_path)
        self.assertEqual(len(all_tasks), 1)
        self.assertEqual(all_tasks[0]["chat_session_id"], "chat-session-gamma")

        updated = update_task_file(self.root_path, all_tasks[0]["file"], {"chat_session_id": "chat-session-delta"})
        self.assertEqual(updated["chat_session_id"], "chat-session-delta")

if __name__ == "__main__":
    unittest.main()
