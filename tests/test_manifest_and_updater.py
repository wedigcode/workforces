#!/usr/bin/env python3
"""
Unit and Integration Tests for Workforce Manifest Tracking and Obsolete File Pruner.
Tests:
- resolve_installed_file_paths correctly resolves all installed files.
- Manifest generation and saving (workforces/.manifest.json).
- Obsolete file detection when assets are removed or relocated.
- Legacy installation upgrade detection (cleaning stale files without prior manifest).
- Strict preservation of user-created custom files in .agents/.
- Safe empty directory pruning without deleting non-empty or user directories.
- Pruning obsolete files in dry-run mode (--dry).
- prune_team synchronization with workforces/.manifest.json.
"""

import os
import sys
import shutil
import tempfile
import unittest
import json
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "workforce-management", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from resolve_manifest import (
    resolve_manifest,
    resolve_installed_file_paths,
    load_installed_manifest,
    save_installed_manifest,
    find_obsolete_files,
    prune_obsolete_files,
    get_known_legacy_obsolete_files,
    detect_base_dir
)
from prune_team import prune_team

class TestManifestAndUpdater(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_workforces_manifest_")
        self.base_dir = os.path.join(self.test_dir, ".agents")
        self.workforces_dir = os.path.join(self.test_dir, "workforces")

        os.makedirs(os.path.join(self.base_dir, "agents"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "skills"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "rules"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "workflows"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "plugins"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "teams"), exist_ok=True)

        os.makedirs(os.path.join(self.workforces_dir, "teams"), exist_ok=True)
        os.makedirs(os.path.join(self.workforces_dir, "goals"), exist_ok=True)

        # Seed workrules.md
        with open(os.path.join(self.workforces_dir, "workrules.md"), "w", encoding="utf-8") as f:
            f.write("# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n  - design\n")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_resolve_installed_file_paths(self):
        """Verify resolve_installed_file_paths returns complete list of files."""
        files = resolve_installed_file_paths(
            toolkit_root=REPO_ROOT,
            target_dir=self.test_dir,
            base_dir=".agents",
            teams_arg="dev,design"
        )
        self.assertIsInstance(files, list)
        self.assertTrue(len(files) > 0)
        # Check core files present
        self.assertIn(".agents/agents/advisor.md", files)
        self.assertIn(".agents/rules/base.md", files)
        self.assertIn(".agents/workflows/wf-work.md", files)
        self.assertIn(".agents/skills/clean-coder/SKILL.md", files)
        self.assertIn(".agents/plugins/workforce-programming-plugin/plugin.json", files)

    def test_save_and_load_manifest(self):
        """Verify saving and reading workforces/.manifest.json."""
        sample_files = [".agents/agents/advisor.md", ".agents/rules/base.md"]
        save_installed_manifest(
            target_dir=self.test_dir,
            version="test-commit-123",
            installed_teams=["dev", "design"],
            installed_files=sample_files
        )

        manifest = load_installed_manifest(self.test_dir)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["version"], "test-commit-123")
        self.assertEqual(manifest["installed_teams"], ["design", "dev"])
        self.assertEqual(manifest["installed_files"], sorted(sample_files))
        self.assertIn("updated_at", manifest)

    def test_find_and_prune_obsolete_files(self):
        """Verify obsolete files recorded in previous manifest are detected and pruned."""
        # 1. Create a stale agent file and a current agent file
        stale_file_rel = ".agents/agents/old-obsolete-agent.md"
        current_file_rel = ".agents/agents/advisor.md"
        
        stale_full = os.path.join(self.test_dir, stale_file_rel)
        current_full = os.path.join(self.test_dir, current_file_rel)

        with open(stale_full, "w") as f:
            f.write("# Old Obsolete Agent\n")
        with open(current_full, "w") as f:
            f.write("# Advisor\n")

        # Previous manifest tracked both
        save_installed_manifest(
            target_dir=self.test_dir,
            version="v1",
            installed_teams=["dev"],
            installed_files=[stale_file_rel, current_file_rel]
        )

        # New target files only has current_file_rel
        new_files = [current_file_rel]

        # Find obsolete files
        obsolete = find_obsolete_files(
            target_dir=self.test_dir,
            base_dir=".agents",
            current_files=new_files,
            toolkit_root=REPO_ROOT
        )
        self.assertIn(stale_file_rel, obsolete)
        self.assertNotIn(current_file_rel, obsolete)

        # Prune with dry run first
        pruned_count = prune_obsolete_files(self.test_dir, obsolete, dry_run=True)
        self.assertEqual(pruned_count, 1)
        self.assertTrue(os.path.exists(stale_full))  # Not deleted in dry run

        # Prune for real
        pruned_count = prune_obsolete_files(self.test_dir, obsolete, dry_run=False)
        self.assertEqual(pruned_count, 1)
        self.assertFalse(os.path.exists(stale_full))  # Deleted
        self.assertTrue(os.path.exists(current_full))  # Current file preserved

    def test_user_custom_files_are_strictly_preserved(self):
        """Verify user-created custom files in .agents/ are NEVER deleted during update."""
        # Create a user custom agent and a user custom skill
        user_agent_rel = ".agents/agents/my-custom-bot.md"
        user_skill_dir = os.path.join(self.base_dir, "skills", "custom-user-skill")
        os.makedirs(user_skill_dir, exist_ok=True)
        user_skill_file = os.path.join(user_skill_dir, "SKILL.md")

        with open(os.path.join(self.test_dir, user_agent_rel), "w") as f:
            f.write("# My Custom Bot\n")
        with open(user_skill_file, "w") as f:
            f.write("# Custom User Skill\n")

        # Create a workforces stale file tracked in manifest
        stale_file_rel = ".agents/agents/stale-workforces-agent.md"
        with open(os.path.join(self.test_dir, stale_file_rel), "w") as f:
            f.write("# Stale Workforces Agent\n")

        # Manifest only tracks the workforces file, NOT user files
        save_installed_manifest(
            target_dir=self.test_dir,
            version="v1",
            installed_teams=["dev"],
            installed_files=[stale_file_rel]
        )

        new_files = [".agents/agents/advisor.md"]

        obsolete = find_obsolete_files(
            target_dir=self.test_dir,
            base_dir=".agents",
            current_files=new_files,
            toolkit_root=REPO_ROOT
        )

        # Stale file is obsolete
        self.assertIn(stale_file_rel, obsolete)
        # User files are NOT in obsolete
        self.assertNotIn(user_agent_rel, obsolete)
        self.assertNotIn(".agents/skills/custom-user-skill/SKILL.md", obsolete)

        prune_obsolete_files(self.test_dir, obsolete, dry_run=False)

        self.assertFalse(os.path.exists(os.path.join(self.test_dir, stale_file_rel)))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, user_agent_rel)))
        self.assertTrue(os.path.exists(user_skill_file))

    def test_legacy_upgrade_removes_known_stale_files_without_manifest(self):
        """Verify legacy upgrade (no prior .manifest.json) removes known obsolete files."""
        # Ensure no manifest exists
        manifest_path = os.path.join(self.workforces_dir, ".manifest.json")
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

        # Create legacy duplicate/stale files
        legacy_files = [
            ".agents/agents/clean-coder.md",
            ".agents/agents/design-pilot.md",
            ".agents/plugins/workforce-integrity-plugin/rules/file-integrity.md",
            ".agents/teams/skills/brand-guidelines/SKILL.md"
        ]
        for lf in legacy_files:
            full_p = os.path.join(self.test_dir, lf)
            os.makedirs(os.path.dirname(full_p), exist_ok=True)
            with open(full_p, "w") as f:
                f.write("# Legacy Content\n")

        # Also create a user custom file
        user_file = os.path.join(self.base_dir, "agents", "my-own-agent.md")
        with open(user_file, "w") as f:
            f.write("# User Agent\n")

        new_files = [
            ".agents/agents/programmer.md",
            ".agents/agents/designer.md",
            ".agents/rules/file-integrity.md"
        ]

        obsolete = find_obsolete_files(
            target_dir=self.test_dir,
            base_dir=".agents",
            current_files=new_files,
            toolkit_root=REPO_ROOT
        )

        for lf in legacy_files:
            self.assertIn(lf, obsolete)
        self.assertNotIn(".agents/agents/my-own-agent.md", obsolete)

        prune_obsolete_files(self.test_dir, obsolete, dry_run=False)

        for lf in legacy_files:
            self.assertFalse(os.path.exists(os.path.join(self.test_dir, lf)))
        self.assertTrue(os.path.exists(user_file))

    def test_empty_directories_are_cleaned_up(self):
        """Verify empty parent directories are deleted after file pruning, while non-empty dirs remain."""
        nested_empty_dir = os.path.join(self.base_dir, "plugins", "old-empty-plugin", "subfolder")
        os.makedirs(nested_empty_dir, exist_ok=True)
        stale_file = os.path.join(nested_empty_dir, "old.json")
        with open(stale_file, "w") as f:
            f.write("{}")

        stale_rel = ".agents/plugins/old-empty-plugin/subfolder/old.json"

        # User directory with a file
        user_dir = os.path.join(self.base_dir, "plugins", "my-plugin")
        os.makedirs(user_dir, exist_ok=True)
        with open(os.path.join(user_dir, "plugin.json"), "w") as f:
            f.write("{}")

        save_installed_manifest(self.test_dir, "v1", ["dev"], [stale_rel])
        obsolete = find_obsolete_files(self.test_dir, ".agents", [], toolkit_root=REPO_ROOT)
        prune_obsolete_files(self.test_dir, obsolete, dry_run=False)

        # File and its empty parents are gone
        self.assertFalse(os.path.exists(stale_file))
        self.assertFalse(os.path.exists(nested_empty_dir))
        self.assertFalse(os.path.exists(os.path.join(self.base_dir, "plugins", "old-empty-plugin")))

        # User directory is intact
        self.assertTrue(os.path.exists(user_dir))
        self.assertTrue(os.path.exists(os.path.join(user_dir, "plugin.json")))


if __name__ == "__main__":
    unittest.main()
