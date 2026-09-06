#!/usr/bin/env python3
"""
Test Suite: End-to-End Setup and Update Distribution
Verifies subprocess execution of setup.sh and update.sh in temporary workspaces,
verifying hooks distribution, skill installation, manifest recording, and
pruning of obsolete workflow files.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "workforce-management" / "scripts"
SETUP_SCRIPT = SCRIPTS_DIR / "setup.sh"
UPDATE_SCRIPT = SCRIPTS_DIR / "update.sh"


class TestSetupAndUpdateE2E(unittest.TestCase):
    """Integration test suite for workforce setup.sh and update.sh scripts."""

    def setUp(self):
        self.assertTrue(SETUP_SCRIPT.is_file(), f"setup.sh not found at {SETUP_SCRIPT}")
        self.assertTrue(UPDATE_SCRIPT.is_file(), f"update.sh not found at {UPDATE_SCRIPT}")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_setup_project_antigravity_e2e(self):
        """Verify setup.sh initializes a clean project with skills, hooks, and manifest tracking."""
        res = subprocess.run(
            [
                "bash",
                str(SETUP_SCRIPT),
                str(self.target_path),
                "--type",
                "project",
                "--editor",
                "antigravity",
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            res.returncode,
            0,
            f"setup.sh exited with code {res.returncode}.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )

        # Assert modular plugin hooks exist and are valid JSON
        hooks_path = self.target_path / ".agents" / "plugins" / "workforce-programming-plugin" / "hooks.json"
        self.assertTrue(
            hooks_path.is_file(),
            f"Expected workforce-programming-plugin/hooks.json to exist at {hooks_path}",
        )
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks_data = json.load(f)
        self.assertIsInstance(hooks_data, dict)
        self.assertIn("workforce-programming", hooks_data)

        # Assert .agents/skills/wf-sync/SKILL.md exists
        wf_sync_skill = self.target_path / ".agents" / "skills" / "wf-sync" / "SKILL.md"
        self.assertTrue(
            wf_sync_skill.is_file(),
            f"Expected wf-sync skill at {wf_sync_skill}",
        )
        self.assertGreater(wf_sync_skill.stat().st_size, 0)

        # Assert workforces/.manifest.json contains hooks.json
        manifest_path = self.target_path / "workforces" / ".manifest.json"
        self.assertTrue(
            manifest_path.is_file(),
            f"Expected manifest at {manifest_path}",
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        installed_files = manifest_data.get("installed_files", [])
        has_hooks = any("hooks.json" in f for f in installed_files)
        self.assertTrue(
            has_hooks,
            f"Expected hooks.json to be recorded in installed_files: {installed_files}",
        )

        # Assert workforces/.version exists
        version_path = self.target_path / "workforces" / ".version"
        self.assertTrue(version_path.is_file(), f"Expected .version at {version_path}")

    def test_update_prunes_obsolete_workflows(self):
        """Verify update.sh removes stale workflow files previously recorded in manifest."""
        # 1. Run initial setup
        res_setup = subprocess.run(
            [
                "bash",
                str(SETUP_SCRIPT),
                str(self.target_path),
                "--type",
                "project",
                "--editor",
                "antigravity",
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_setup.returncode, 0, "Initial setup failed")

        # 2. Simulate an obsolete workflow file in the target workspace
        wf_dir = self.target_path / ".agents" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        obsolete_wf = wf_dir / "wf-obsolete.md"
        obsolete_wf.write_text("# Obsolete Workflow\nDeprecated.\n", encoding="utf-8")
        self.assertTrue(obsolete_wf.is_file())

        # Record the obsolete workflow in workforces/.manifest.json
        manifest_path = self.target_path / "workforces" / ".manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["installed_files"].append(".agents/workflows/wf-obsolete.md")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 3. Run update.sh --non-interactive --force
        res_update = subprocess.run(
            [
                "bash",
                str(UPDATE_SCRIPT),
                str(self.target_path),
                "--non-interactive",
                "--force",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(
            res_update.returncode,
            0,
            f"update.sh failed with returncode {res_update.returncode}.\nSTDOUT: {res_update.stdout}\nSTDERR: {res_update.stderr}",
        )

        # 4. Assert the obsolete workflow was pruned
        self.assertFalse(
            obsolete_wf.exists(),
            f"Expected {obsolete_wf} to be pruned by update.sh, but it still exists",
        )

        # 5. Assert current skills and hooks remain intact
        wf_sync_skill = self.target_path / ".agents" / "skills" / "wf-sync" / "SKILL.md"
        self.assertTrue(wf_sync_skill.is_file())
        hooks_file = self.target_path / ".agents" / "plugins" / "workforce-programming-plugin" / "hooks.json"
        self.assertTrue(hooks_file.is_file())


if __name__ == "__main__":
    unittest.main()
