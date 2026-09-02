"""
Tests for Personal Sync & Follow-Up Radar Aggregator (`personal_sync.py` and `/sync --me`).
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PERSONAL_SYNC_SCRIPT = os.path.join(ROOT_DIR, "skills", "task-tracker", "scripts", "personal_sync.py")

# Add scripts directory to sys.path for direct import testing
sys.path.insert(0, os.path.join(ROOT_DIR, "skills", "task-tracker", "scripts"))
import personal_sync  # type: ignore


class TestPersonalSync(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workforces_dir = os.path.join(self.test_dir, "workforces")
        self.tasks_dir = os.path.join(self.workforces_dir, "tasks")
        self.session_dir = os.path.join(self.workforces_dir, "session-context")
        self.hypotheses_dir = os.path.join(self.workforces_dir, "hypotheses", "running")

        os.makedirs(self.tasks_dir, exist_ok=True)
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(self.hypotheses_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_frontmatter(self):
        """Test parsing YAML frontmatter from markdown content."""
        sample = """---
title: "Test Task"
status: "in_progress"
priority: "P0"
assignee: "@user"
tags: ["frontend", "oauth"]
active: true
---

# Test Task Body
This is the description.
"""
        meta, body = personal_sync.parse_frontmatter(sample)
        self.assertEqual(meta.get("title"), "Test Task")
        self.assertEqual(meta.get("status"), "in_progress")
        self.assertEqual(meta.get("priority"), "P0")
        self.assertEqual(meta.get("assignee"), "@user")
        self.assertEqual(meta.get("tags"), ["frontend", "oauth"])
        self.assertTrue(meta.get("active"))
        self.assertIn("This is the description.", body)

    def test_tasks_summary_aggregation(self):
        """Test parsing and grouping tasks from workforces/tasks/."""
        # 1. In-progress task
        task1 = """---
title: "OAuth Callback Flow"
type: "task"
priority: "P0"
status: "in_progress"
assignee: "@user"
suggested_action: "Complete test cases"
---
# OAuth Callback Flow
"""
        with open(os.path.join(self.tasks_dir, "20260827-01-oauth-callback.md"), "w", encoding="utf-8") as f:
            f.write(task1)

        # 2. Blocked task
        task2 = """---
title: "Staging CloudFormation Deployment"
type: "ops"
priority: "P1"
status: "blocked"
assignee: "@user"
suggested_action: "Waiting on IAM credentials"
---
# Staging CloudFormation Deployment
"""
        with open(os.path.join(self.tasks_dir, "20260827-02-staging-deploy.md"), "w", encoding="utf-8") as f:
            f.write(task2)

        # 3. High priority todo task
        task3 = """---
title: "API Rate Limiting Middleware"
type: "security"
priority: "P1"
status: "todo"
assignee: "@user"
---
# API Rate Limiting Middleware
"""
        with open(os.path.join(self.tasks_dir, "20260827-03-rate-limiting.md"), "w", encoding="utf-8") as f:
            f.write(task3)

        # 4. Low priority todo task (P3)
        task4 = """---
title: "Update Logo Favicon"
type: "design"
priority: "P3"
status: "todo"
---
# Update Logo Favicon
"""
        with open(os.path.join(self.tasks_dir, "20260827-04-favicon.md"), "w", encoding="utf-8") as f:
            f.write(task4)

        summary = personal_sync.get_tasks_summary(self.test_dir)
        self.assertEqual(len(summary["in_progress"]), 1)
        self.assertEqual(summary["in_progress"][0]["title"], "OAuth Callback Flow")
        self.assertEqual(len(summary["blocked"]), 1)
        self.assertEqual(summary["blocked"][0]["title"], "Staging CloudFormation Deployment")
        self.assertEqual(len(summary["high_priority_todo"]), 1)
        self.assertEqual(summary["high_priority_todo"][0]["title"], "API Rate Limiting Middleware")
        self.assertEqual(summary["total_active"], 3)

    def test_workstate_and_session_context_parsing(self):
        """Test reading workstate sprint items and latest session context."""
        workstate_content = """# Work State

## Active Tasks
| # | Task | Status | Owner |
|---|------|--------|-------|
| 1 | Auth Microservice | In Progress | @programmer |
| 2 | Billing Portal | Blocked | @programmer |

## Unforeseen Risks & Discovered Gaps
- AWS SDK v3 migration required before deploying staging
"""
        with open(os.path.join(self.workforces_dir, "workstate.md"), "w", encoding="utf-8") as f:
            f.write(workstate_content)

        session_content = """---
session_id: "027"
topic: "Generalized Task Model"
updated_at: "2026-08-27T06:00:00"
active_files: ["src/auth.py"]
---

# Session 027

## 🧠 Decisions & Reasoning ("Why")
- In-Place Status Transitions: Simplified state machine to prevent broken markdown links.
- Universal Priority Scale: Standardized on P0-P3.
"""
        with open(os.path.join(self.session_dir, "027_2026-08-27_generalized_task_model.md"), "w", encoding="utf-8") as f:
            f.write(session_content)

        ws = personal_sync.get_workstate_summary(self.test_dir)
        self.assertEqual(len(ws["active_sprint_tasks"]), 2)
        self.assertEqual(len(ws["roadblocks"]), 1)
        self.assertIn("AWS SDK v3 migration", ws["roadblocks"][0])

        sc = personal_sync.get_session_context_summary(self.test_dir)
        self.assertEqual(sc["session_id"], "027")
        self.assertEqual(sc["topic"], "Generalized Task Model")
        self.assertEqual(len(sc["recent_decisions"]), 2)

    def test_hypotheses_scanning(self):
        """Test scanning running hypotheses."""
        hyp_content = """---
title: "Outbound Problem-First Email Test"
owner: "sales"
status: "running"
---
# Outbound Test
"""
        with open(os.path.join(self.hypotheses_dir, "HYP-01.md"), "w", encoding="utf-8") as f:
            f.write(hyp_content)

        hypotheses = personal_sync.get_running_hypotheses(self.test_dir)
        self.assertEqual(len(hypotheses), 1)
        self.assertEqual(hypotheses[0]["title"], "Outbound Problem-First Email Test")
        self.assertEqual(hypotheses[0]["owner"], "sales")

    def test_full_personal_sync_generation_and_cli(self):
        """Test end-to-end data aggregation and markdown formatting via CLI."""
        # Create minimal task and session note
        with open(os.path.join(self.tasks_dir, "task-1.md"), "w", encoding="utf-8") as f:
            f.write("""---
title: "Build Personal Sync Engine"
type: "feature"
priority: "P0"
status: "in_progress"
suggested_action: "Ship tests and update workflows"
---
""")

        with open(os.path.join(self.session_dir, "028_2026-08-27_sync_me.md"), "w", encoding="utf-8") as f:
            f.write("""---
session_id: "028"
topic: "Personal Sync Workflow"
---
# Session 028
## 🧠 Decisions & Reasoning ("Why")
- Autonomous Multi-Source Discovery: Enables AI to inspect all active tools.
""")

        # 1. Run Python API directly
        data = personal_sync.generate_personal_sync_data(self.test_dir, check_github=False)
        self.assertEqual(len(data["tasks"]["in_progress"]), 1)
        self.assertEqual(data["session_context"]["topic"], "Personal Sync Workflow")

        md = personal_sync.format_markdown_report(data)
        self.assertIn("Personal Sync & Follow-Up Radar (`/sync --me`)", md)
        self.assertIn("Build Personal Sync Engine", md)
        self.assertIn("Personal Sync Workflow", md)

        # 2. Run via CLI subprocess (JSON)
        res_json = subprocess.run(
            ["python3", PERSONAL_SYNC_SCRIPT, "--root", self.test_dir, "--format", "json", "--no-github"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_json.returncode, 0, f"Error: {res_json.stderr}")
        parsed_json = json.loads(res_json.stdout)
        self.assertIn("tasks", parsed_json)
        self.assertEqual(len(parsed_json["tasks"]["in_progress"]), 1)

        # 3. Run via CLI subprocess (Markdown)
        res_md = subprocess.run(
            ["python3", PERSONAL_SYNC_SCRIPT, "--root", self.test_dir, "--format", "markdown", "--no-github"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_md.returncode, 0, f"Error: {res_md.stderr}")
        self.assertIn("Personal Sync & Follow-Up Radar", res_md.stdout)

    def test_get_tracked_repos(self):
        """Test extracting tracked repositories across workrules, workstate, and projects."""
        # Write workrules with list
        workrules = """# Work Rules
## GitHub Settings
- tracked_repos:
  - acme-org/backend-service
  - acme-org/frontend-app
  - https://github.com/acme-org/landing-page.git
"""
        with open(os.path.join(self.workforces_dir, "workrules.md"), "w", encoding="utf-8") as f:
            f.write(workrules)

        repos = personal_sync.get_tracked_repos(self.test_dir)
        self.assertIn("acme-org/backend-service", repos)
        self.assertIn("acme-org/frontend-app", repos)
        self.assertIn("acme-org/landing-page", repos)

    def test_sync_workstate_from_tasks(self):
        """Test dynamically projecting workstate.md from workforces/tasks/."""
        # 1. Create in-progress task with PR
        task1 = """---
title: "OAuth Redo Flow"
type: "feature"
priority: "P0"
status: "in_progress"
assignee: "@programmer"
github_pr: "https://github.com/acme-org/backend-service/pull/1495"
suggested_action: "Merge staging branch"
---
# OAuth Redo Flow
"""
        with open(os.path.join(self.tasks_dir, "task-1495.md"), "w", encoding="utf-8") as f:
            f.write(task1)

        # 2. Create done task
        task2 = """---
title: "Fix Token Expiry Bug"
type: "bug"
priority: "P1"
status: "done"
assignee: "@programmer"
updated_at: "2026-09-01T12:00:00"
---
# Fix Token Expiry Bug
"""
        with open(os.path.join(self.tasks_dir, "task-done.md"), "w", encoding="utf-8") as f:
            f.write(task2)

        # Run workstate sync
        success = personal_sync.sync_workstate_from_tasks(self.test_dir)
        self.assertTrue(success)

        workstate_path = os.path.join(self.workforces_dir, "workstate.md")
        self.assertTrue(os.path.isfile(workstate_path))
        with open(workstate_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("## Active Tasks", content)
        self.assertIn("OAuth Redo Flow", content)
        self.assertIn("PR #1495", content)
        self.assertIn("## Completed Tasks (Recent)", content)
        self.assertIn("Fix Token Expiry Bug", content)

    def test_reconcile_github_tasks(self):
        """Test auto-reconciliation of tasks when linked GitHub PR is merged."""
        # Create a task linked to PR #1495
        task_content = """---
title: "Migrate Auth Endpoints"
type: "task"
priority: "P0"
status: "in_progress"
github_pr: "1495"
---
# Migrate Auth Endpoints

## Description
Waiting on PR 1495 merge.

## 🧠 Session Lineage & Deciding Factors
- **2026-09-02 08:00:** Created task.
"""
        task_file = os.path.join(self.tasks_dir, "task-auth.md")
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(task_content)

        # Mock subprocess.run for gh pr view
        original_run = subprocess.run
        def mock_run(cmd, *args, **kwargs):
            if len(cmd) >= 3 and cmd[0] == "gh" and cmd[1] == "pr" and cmd[2] == "view":
                # Return merged PR payload
                mock_res = unittest.mock.MagicMock()
                mock_res.returncode = 0
                mock_res.stdout = json.dumps({
                    "state": "MERGED",
                    "title": "PR #1495 Auth Migration",
                    "url": "https://github.com/acme-org/backend-service/pull/1495",
                    "mergedAt": "2026-09-02T09:00:00Z"
                })
                return mock_res
            return original_run(cmd, *args, **kwargs)

        try:
            with unittest.mock.patch("subprocess.run", side_effect=mock_run):
                with unittest.mock.patch("shutil.which", return_value="/usr/local/bin/gh"):
                    reconciled = personal_sync.reconcile_github_tasks(self.test_dir, tracked_repos=["acme-org/backend-service"])
                    self.assertEqual(len(reconciled), 1)
                    self.assertEqual(reconciled[0]["status"], "done")
                    self.assertIn("merged on GitHub", reconciled[0]["reason"])

            # Verify task file was updated in-place to 'done'
            with open(task_file, "r", encoding="utf-8") as f:
                updated_content = f.read()
            meta, body = personal_sync.parse_frontmatter(updated_content)
            self.assertEqual(meta.get("status"), "done")
            self.assertIn("Auto-synced: PR #1495 was merged", body)
        finally:
            pass


if __name__ == "__main__":
    unittest.main()
