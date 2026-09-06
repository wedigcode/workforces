#!/usr/bin/env python3
"""Tests for git-workflow rule, workspace parallelization topologies, and PR discipline."""

import os
import json
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "workforce-management" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from resolve_manifest import resolve_manifest, CORE_RULES


class TestGitWorkflowRule(unittest.TestCase):
    def test_git_workflow_rule_files_exist(self):
        source_rule = REPO_ROOT / "rules" / "git-workflow.md"
        agent_rule = REPO_ROOT / ".agents" / "rules" / "git-workflow.md"

        self.assertTrue(source_rule.exists(), f"Missing rule file: {source_rule}")
        self.assertTrue(agent_rule.exists(), f"Missing mirrored agent rule file: {agent_rule}")

    def test_git_workflow_contains_core_mandates(self):
        rule_content = (REPO_ROOT / "rules" / "git-workflow.md").read_text(encoding="utf-8")

        # 1. Zero Blockers & PR-first review
        self.assertIn("Zero Blockers Mandate", rule_content)
        self.assertIn("GitHub PR-First Code Review", rule_content)
        self.assertIn("Do NOT ask the user for permission to create standard commits", rule_content)

        # 2. Execution Topologies shown up-front
        self.assertIn("Topology 1: Parallel Isolated Worktrees", rule_content)
        self.assertIn("Topology 2: Vertical Relay", rule_content)
        self.assertIn("Topology 3: Direct Single-Branch", rule_content)
        self.assertIn("Workspace: 'share'", rule_content)
        self.assertIn("gh stack", rule_content)
        self.assertIn(".worktrees/", rule_content)

        # 3. Stack-agnostic quality gates
        self.assertIn("Universal Stack-Agnostic Quality Gates", rule_content)
        self.assertIn("npm test", rule_content)
        self.assertIn("pytest", rule_content)
        self.assertIn("go test", rule_content)
        self.assertIn("cargo test", rule_content)
        self.assertIn("phpunit", rule_content)

        # 4. Deterministic commit milestones
        self.assertIn("The 5 Deterministic Commit Milestones", rule_content)
        self.assertIn("Task Completion Gate", rule_content)
        self.assertIn("Structural Scaffolding", rule_content)
        self.assertIn("Session / Turn Handoff", rule_content)

        # 5. Conventional Commits
        self.assertIn("Conventional Commit Protocol", rule_content)
        self.assertIn("feat(", rule_content)
        self.assertIn("fix(", rule_content)
        self.assertIn("Task: workforces/tasks/", rule_content)

        # 6. High-Quality PR discipline
        self.assertIn("gh pr create", rule_content)
        self.assertIn("Quality Gate Verification Proof", rule_content)
        self.assertIn("Reviewer Inspection Guide", rule_content)
        self.assertIn("Architectural & Component Changes", rule_content)

    def test_resolve_manifest_includes_git_workflow_as_core_rule(self):
        self.assertIn("git-workflow.md", CORE_RULES)
        manifest = resolve_manifest(toolkit_root=str(REPO_ROOT), target_dir=str(REPO_ROOT), teams_arg="none")
        self.assertIn("git-workflow.md", manifest["rules"])

    def test_dev_pack_declares_git_workflow_rule(self):
        pack_path = REPO_ROOT / "teams" / "dev" / "pack.json"
        with open(pack_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("git-workflow.md", data.get("rules", []))

    def test_base_and_clean_coder_rules_cross_reference_git_workflow(self):
        base_rule = (REPO_ROOT / "rules" / "base.md").read_text(encoding="utf-8")
        clean_coder = (REPO_ROOT / "rules" / "clean-coder.md").read_text(encoding="utf-8")

        self.assertIn("git-workflow", base_rule)
        self.assertIn("git-workflow", clean_coder)


if __name__ == "__main__":
    unittest.main()
