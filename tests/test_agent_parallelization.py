#!/usr/bin/env python3
"""Tests for agent-parallelization skill and multi-agent Git orchestration."""

import os
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAgentParallelization(unittest.TestCase):
    def test_skill_file_exists_and_has_valid_frontmatter(self):
        skill_path = REPO_ROOT / "skills" / "agent-parallelization" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"Missing skill file: {skill_path}")
        content = skill_path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter")
        self.assertIn("name: agent-parallelization", content)
        self.assertIn("gh-stack", content)
        self.assertIn("Workspace: 'share'", content)
        self.assertIn("git rerere", content)

    def test_dev_pack_includes_skill(self):
        pack_path = REPO_ROOT / "teams" / "dev" / "pack.json"
        self.assertTrue(pack_path.exists(), f"Missing dev pack.json: {pack_path}")
        with open(pack_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        self.assertIn("agent-parallelization", pack.get("skills", []))

    def test_project_manager_declares_skill(self):
        pm_path = REPO_ROOT / "agents" / "project-manager.md"
        content = pm_path.read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", content)
        self.assertIn("Concurrency Topology Selection", content)
        self.assertIn("Parallel Worktree", content)

    def test_programmer_declares_skill(self):
        programmer_path = REPO_ROOT / "agents" / "programmer.md"
        content = programmer_path.read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", content)
        self.assertIn("gh-stack", content)
        self.assertIn("gh stack init", content)

    def test_rules_include_parallelization(self):
        base_rule = (REPO_ROOT / "rules" / "base.md").read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", base_rule)
        self.assertIn("Horizontal Fan-Out", base_rule)
        self.assertIn("Vertical Relay", base_rule)

        clean_coder_rule = (REPO_ROOT / "rules" / "clean-coder.md").read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", clean_coder_rule)
        self.assertIn("Worktree Isolation for Parallel Agents", clean_coder_rule)

    def test_worktrees_ignored_in_install_update_and_scanners(self):
        # 1. Check setup.sh
        setup_sh = (REPO_ROOT / "skills" / "workforce-management" / "scripts" / "setup.sh").read_text(encoding="utf-8")
        self.assertIn('add_gitignore_entry ".worktrees"', setup_sh)

        # 2. Check update.sh
        update_sh = (REPO_ROOT / "skills" / "workforce-management" / "scripts" / "update.sh").read_text(encoding="utf-8")
        self.assertIn('add_update_gitignore_entry ".worktrees"', update_sh)

        # 3. Check validate-references.py
        val_refs = (REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py").read_text(encoding="utf-8")
        self.assertIn('".worktrees"', val_refs)

        # 4. Check post_code_reviewer.py
        pcr = (REPO_ROOT / "skills" / "post-code-review" / "scripts" / "post_code_reviewer.py").read_text(encoding="utf-8")
        self.assertIn('".worktrees"', pcr)

        # 5. Check graph_indexer.py
        gi = (REPO_ROOT / "skills" / "code-graph" / "scripts" / "graph_indexer.py").read_text(encoding="utf-8")
        self.assertIn('".worktrees"', gi)


if __name__ == "__main__":
    unittest.main()
