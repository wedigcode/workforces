#!/usr/bin/env python3
"""Tests for agent-parallelization skill and multi-agent Git orchestration."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAgentParallelization(unittest.TestCase):
    def test_skill_file_exists_and_has_valid_frontmatter(self):
        skill_path = REPO_ROOT / "skills" / "wf-agent-parallelization" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"Missing skill file: {skill_path}")
        content = skill_path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter")
        self.assertIn("name: wf-agent-parallelization", content)
        self.assertIn("gh-stack", content)
        self.assertIn("Workspace: 'share'", content)
        self.assertIn("git rerere", content)

    def test_dev_pack_includes_skill(self):
        pack_path = REPO_ROOT / "teams" / "dev" / "pack.json"
        self.assertTrue(pack_path.exists(), f"Missing dev pack.json: {pack_path}")
        with open(pack_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        self.assertIn("wf-agent-parallelization", pack.get("skills", []))

    def test_project_manager_declares_skill(self):
        pm_path = REPO_ROOT / "agents" / "wf-project-manager.md"
        content = pm_path.read_text(encoding="utf-8")
        self.assertIn("wf-agent-parallelization", content)
        self.assertIn("Concurrency Topology Selection", content)
        self.assertIn("Parallel Worktree", content)

    def test_programmer_declares_skill(self):
        programmer_path = REPO_ROOT / "agents" / "wf-programmer.md"
        content = programmer_path.read_text(encoding="utf-8")
        self.assertIn("wf-agent-parallelization", content)
        self.assertIn("stacked PRs", content)
        # The gh-stack commands live once, in the skill the agent points to.
        skill = (REPO_ROOT / "skills" / "wf-agent-parallelization" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("gh stack init", skill)

    def test_rules_include_parallelization(self):
        base_rule = (REPO_ROOT / "rules" / "wf-base.md").read_text(encoding="utf-8")
        self.assertIn("wf-agent-parallelization", base_rule)
        self.assertIn("Horizontal Fan-Out", base_rule)
        self.assertIn("Vertical Relay", base_rule)

        clean_coder_rule = (REPO_ROOT / "rules" / "wf-clean-coder.md").read_text(encoding="utf-8")
        self.assertIn("wf-agent-parallelization", clean_coder_rule)
        self.assertIn("Worktree Isolation for Parallel Agents", clean_coder_rule)

    def test_worktrees_ignored_in_install_update_and_scanners(self):
        # 1. Check setup.sh
        setup_sh = (REPO_ROOT / "skills" / "wf-management" / "scripts" / "setup.sh").read_text(encoding="utf-8")
        self.assertIn('add_gitignore_entry ".worktrees"', setup_sh)
        self.assertIn('add_gitignore_entry "workforces/tasks/.claim.lock"', setup_sh)

        # 2. Check update.sh
        update_sh = (REPO_ROOT / "skills" / "wf-management" / "scripts" / "update.sh").read_text(encoding="utf-8")
        self.assertIn('add_update_gitignore_entry ".worktrees"', update_sh)
        self.assertIn('add_update_gitignore_entry "workforces/tasks/.claim.lock"', update_sh)

        # 3. Check validate-references.py
        val_refs = (REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate-references.py").read_text(encoding="utf-8")
        self.assertIn('".worktrees"', val_refs)

        # 4. Check post_code_reviewer.py
        pcr = (REPO_ROOT / "skills" / "wf-post-code-review" / "scripts" / "post_code_reviewer.py").read_text(encoding="utf-8")
        self.assertIn('".worktrees"', pcr)

        # 5. Check graph_indexer.py
        gi = (REPO_ROOT / "skills" / "wf-code-graph" / "scripts" / "graph_indexer.py").read_text(encoding="utf-8")
        self.assertIn('".worktrees"', gi)

    def test_claim_lock_gitignored_on_setup_and_update(self):
        setup_sh = REPO_ROOT / "skills" / "wf-management" / "scripts" / "setup.sh"
        update_sh = REPO_ROOT / "skills" / "wf-management" / "scripts" / "update.sh"
        entry = "workforces/tasks/.claim.lock"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            subprocess.run(["git", "init"], cwd=str(ws), check=True, capture_output=True)
            res = subprocess.run(
                ["bash", str(setup_sh), str(ws), "--type", "project", "--hosts", "claude", "--teams", "dev", "--non-interactive"],
                cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            gitignore = ws / ".gitignore"
            self.assertIn(entry, gitignore.read_text(encoding="utf-8").splitlines())
            self.assertEqual(subprocess.run(["git", "check-ignore", "-q", entry], cwd=str(ws)).returncode, 0)
            self.assertEqual(subprocess.run(["git", "check-ignore", "-q", "workforces/tasks/TASK-001.md"], cwd=str(ws)).returncode, 1)

            # Simulate pre-existing install missing the lock entry; verify --dry and idempotent update.sh
            stripped = "\n".join(line for line in gitignore.read_text(encoding="utf-8").splitlines() if line != entry) + "\n"
            gitignore.write_text(stripped, encoding="utf-8")
            dry = subprocess.run(["bash", str(update_sh), str(ws), "--dry", "--non-interactive"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn(entry, dry.stdout)
            self.assertNotIn(entry, gitignore.read_text(encoding="utf-8").splitlines())

            for _ in range(2):
                upd = subprocess.run(["bash", str(update_sh), str(ws), "--non-interactive"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
                self.assertEqual(upd.returncode, 0, upd.stdout + upd.stderr)
            lines = gitignore.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines.count(entry), 1)
            self.assertEqual(subprocess.run(["git", "check-ignore", "-q", entry], cwd=str(ws)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
