#!/usr/bin/env python3
"""
Unit and Integration Tests for Workforce File Reference & Subtask Integrity Validator.
Tests:
- Reference integrity validation for markdown files and JSON manifests.
- Detection of dangling links and missing dependencies.
- Session context roadmap linter: flagging untracked roadmap items vs tracked issues.
"""

import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VALIDATE_SCRIPT_DIR = os.path.join(REPO_ROOT, "skills", "workforce-management", "scripts")
sys.path.insert(0, VALIDATE_SCRIPT_DIR)

import importlib
validate_mod = importlib.import_module("validate-references")


class TestValidateReferences(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_validate_refs_")
        self.session_dir = os.path.join(self.test_dir, "workforces", "session-context")
        self.inbox_dir = os.path.join(self.test_dir, "workforces", "issues", "inbox")
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(self.inbox_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clean_workspace(self):
        """Test clean workspace with 0 broken references."""
        # Create a valid markdown file referencing an existing file
        doc1 = os.path.join(self.test_dir, "doc1.md")
        doc2 = os.path.join(self.test_dir, "doc2.md")
        with open(doc2, "w", encoding="utf-8") as f:
            f.write("# Doc 2\n")
        with open(doc1, "w", encoding="utf-8") as f:
            f.write("# Doc 1\nLink to [Doc 2](file://" + doc2 + ")\n")

        broken = validate_mod.audit_references(self.test_dir)
        self.assertEqual(broken, 0)

    def test_broken_markdown_link(self):
        """Test detecting a dangling markdown link."""
        doc1 = os.path.join(self.test_dir, "broken.md")
        with open(doc1, "w", encoding="utf-8") as f:
            f.write("# Broken\nLink to [NonExistent](non_existent_file.md)\n")

        broken = validate_mod.audit_references(self.test_dir)
        self.assertEqual(broken, 1)

    def test_untracked_roadmap_in_session_context(self):
        """Test detecting untracked roadmap items in session context."""
        session_file = os.path.join(self.session_dir, "011_2026-08-22_roadmap_test.md")
        content = """---
session_id: "011"
tracked_issues: []
---

# Session 011: Strategic Roadmap

## 🧭 The 4-Phase Master Roadmap
- **Phase 1: Live SMS Gateway Sync** — Real-time SMS synchronization engine.
- **Phase 2: Multi-State Legal Engine** — Contract validator across state jurisdictions.
- **Phase 3: Broker Fleet Vault** — Multi-tenant team vault.
- **Phase 4: Stripe SaaS Billing** — Automated tiered billing subscriptions.
"""
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(content)

        session_notes, untracked = validate_mod.audit_session_context(self.test_dir)
        self.assertEqual(len(session_notes), 1)
        self.assertEqual(len(untracked), 4)
        items_text = " ".join([u["item"] for u in untracked])
        self.assertIn("Live SMS Gateway Sync", items_text)
        self.assertIn("Multi-State Legal Engine", items_text)

    def test_tracked_roadmap_in_session_context(self):
        """Test that roadmap items registered in tracked_issues pass validation."""
        session_file = os.path.join(self.session_dir, "011_2026-08-22_roadmap_test.md")
        content = """---
session_id: "011"
tracked_issues:
  - id: "phase-1"
    title: "Phase 1: Live SMS Gateway Sync"
  - id: "phase-2"
    title: "Phase 2: Multi-State Legal Engine"
  - id: "phase-3"
    title: "Phase 3: Broker Fleet Vault"
  - id: "phase-4"
    title: "Phase 4: Stripe SaaS Billing"
---

# Session 011: Strategic Roadmap

## 🧭 The 4-Phase Master Roadmap
- **Phase 1: Live SMS Gateway Sync** — Real-time SMS synchronization engine.
- **Phase 2: Multi-State Legal Engine** — Contract validator across state jurisdictions.
- **Phase 3: Broker Fleet Vault** — Multi-tenant team vault.
- **Phase 4: Stripe SaaS Billing** — Automated tiered billing subscriptions.
"""
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(content)

        session_notes, untracked = validate_mod.audit_session_context(self.test_dir)
        self.assertEqual(len(session_notes), 1)
        self.assertEqual(len(untracked), 0)


if __name__ == "__main__":
    unittest.main()
