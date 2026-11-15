#!/usr/bin/env python3
"""
Tests for PreToolUse worktree file protection against deleting, overwriting,
truncating, or discarding uncommitted, untracked, and Git-ignored files.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, rel_path: str):
    """Load a script module dynamically from its repository-relative path."""
    mod_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, str(mod_path))
    if not spec or not spec.loader:
        raise ImportError(f"Could not load {rel_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


deploy_safety_hook = _load_module("deploy_safety_hook", "skills/wf-post-code-review/scripts/deploy_safety_hook.py")


class TestUncommittedFileDeletionGuards(unittest.TestCase):
    """Verify deploy_safety_hook + worktree_file_guard protect local and dirty files."""

    def setUp(self):
        self._tmp_ctx = tempfile.TemporaryDirectory(prefix="wf_file_guard_")
        self.repo = Path(self._tmp_ctx.name)
        self.addCleanup(self._tmp_ctx.cleanup)
        self._outside_ctx = tempfile.TemporaryDirectory(prefix="wf_outside_")
        self.outside_dir = Path(self._outside_ctx.name)
        self.addCleanup(self._outside_ctx.cleanup)
        self.outside_file = self.outside_dir / "scratch.txt"
        self.outside_file.write_text("safe outside repo\n", encoding="utf-8")

        subprocess.run(["git", "init", "-b", "main"], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(self.repo), check=True, capture_output=True)

        (self.repo / ".gitignore").write_text(".env*\n*.key\n__pycache__/\n", encoding="utf-8")
        (self.repo / "clean_tracked.txt").write_text("committed clean\n", encoding="utf-8")
        (self.repo / "readme-deploy.md").write_text("# Deploy\n", encoding="utf-8")
        (self.repo / "subdir").mkdir(parents=True, exist_ok=True)
        (self.repo / "subdir" / "nested.md").write_text("# Nested\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(self.repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=str(self.repo), check=True, capture_output=True)

        (self.repo / "readme-deploy.md").write_text("# Deploy\nUNCOMMITTED LOCAL NOTES\n", encoding="utf-8")
        (self.repo / "subdir" / "nested.md").write_text("# Nested\nDIRTY\n", encoding="utf-8")
        (self.repo / "local-notes.md").write_text("untracked local notes\n", encoding="utf-8")
        (self.repo / ".env.local").write_text("SECRET=123\n", encoding="utf-8")
        (self.repo / "prod.key").write_text("PRIVATE KEY\n", encoding="utf-8")
        (self.repo / "__pycache__").mkdir(exist_ok=True)
        (self.repo / "__pycache__" / "mod.cpython-312.pyc").write_bytes(b"pyc")

    def test_blocks_deleting_or_discarding_uncommitted_untracked_and_ignored_files(self):
        blocked_commands = [
            "rm readme-deploy.md",
            "rm -f readme-deploy.md",
            "unlink readme-deploy.md",
            "git rm readme-deploy.md",
            "git rm -f readme-deploy.md",
            "echo wiped > readme-deploy.md",
            "mv clean_tracked.txt readme-deploy.md",
            'find . -name "readme-deploy.md" -delete',
            'python3 -c "import os; os.remove(\'readme-deploy.md\')"',
            "git checkout -- readme-deploy.md",
            "git checkout readme-deploy.md",
            "git restore readme-deploy.md",
            "cd subdir && rm nested.md",
            "rm local-notes.md",
            "rm .env.local",
            "rm *.key",
            "git clean -fd",
            "git clean -fdx",
            "git reset --hard",
            "git reset --merge",
            "git checkout -f",
            "git checkout .",
            "git restore .",
            "git switch -f",
            "git switch --discard-changes main",
            "git worktree remove --force .worktrees/x",
            "git stash drop",
            "git stash clear",
            "python3 skills/wf-doc-generator/scripts/scaffold_repo_okf.py --dehydrate-spec readme-deploy.md",
        ]
        for cmd in blocked_commands:
            with self.subTest(cmd=cmd):
                reason = deploy_safety_hook.inspect_command(cmd, cwd=str(self.repo))
                self.assertIsNotNone(reason, f"Expected consent gate block for: {cmd}")

    def test_allows_safe_git_clean_tracked_cache_and_outside_repo_ops(self):
        allowed_commands = [
            "git checkout -b feat/safe",
            "git switch -c feat/safe",
            "git checkout main",
            "git restore --staged readme-deploy.md",
            "git clean -n",
            "git rm --cached readme-deploy.md",
            'echo "append ok" >> readme-deploy.md',
            "rm clean_tracked.txt",
            "git rm clean_tracked.txt",
            "rm -rf __pycache__",
            f"rm {self.outside_file}",
        ]
        for cmd in allowed_commands:
            with self.subTest(cmd=cmd):
                reason = deploy_safety_hook.inspect_command(cmd, cwd=str(self.repo))
                self.assertIsNone(reason, f"Expected safe command to be allowed: {cmd} (blocked: {reason})")


if __name__ == "__main__":
    unittest.main()
