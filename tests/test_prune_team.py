#!/usr/bin/env python3
"""
Unit and Integration Tests for Reference-Counted Team Uninstaller (prune-team.py).
Tests:
- Programmatic dependency reference-counting across multiple installed teams (e.g. marketing + design).
- Shared skill preservation (brand-guidelines, image-workflow).
- Orphaned asset pruning (agents, skills, rules, workflows, plugins).
- Workspace layer & custom persona preservation in workforces/ (jordan-belfort.json).
- Registry updating in workrules.md and workstate.md.
- Dry run mode (--dry).
- Purge data mode (--purge-data).
"""

import os
import sys
import shutil
import tempfile
import unittest
import json

# Add scripts directory to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "workforce-management", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from resolve_manifest import resolve_manifest, get_installed_teams
from prune_team import prune_team, detect_base_dir

class TestPruneTeam(unittest.TestCase):
    def setUp(self):
        # Create a temporary workspace for isolated test execution
        self.test_dir = tempfile.mkdtemp(prefix="test_workforces_prune_")
        self.base_dir = os.path.join(self.test_dir, ".agents")
        self.workforces_dir = os.path.join(self.test_dir, "workforces")

        os.makedirs(os.path.join(self.base_dir, "agents"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "skills"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "rules"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "workflows"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "plugins"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "teams"), exist_ok=True)

        os.makedirs(os.path.join(self.workforces_dir, "teams"), exist_ok=True)
        os.makedirs(os.path.join(self.workforces_dir, "personas"), exist_ok=True)

        # Seed workrules.md with installed teams: [design, marketing]
        with open(os.path.join(self.workforces_dir, "workrules.md"), "w", encoding="utf-8") as f:
            f.write("# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - design\n  - marketing\n")

        # Seed workstate.md
        with open(os.path.join(self.workforces_dir, "workstate.md"), "w", encoding="utf-8") as f:
            f.write("# Work State\n\n## Active Teams\n| ID | Name |\n|---|---|\n| design | Design |\n| marketing | Marketing |\n")

        # Create files for design team
        # design uses: agents: [designer], rules: [design-standards.md], skills: [ui-ux-design, brand-guidelines, image-workflow, visual-design-fundamentals, design-anti-patterns], workflows: [wf-brand-context.md, wf-site-setup.md, wf-image-duplicate.md]
        with open(os.path.join(self.base_dir, "agents", "designer.md"), "w") as f:
            f.write("# Designer\n")
        with open(os.path.join(self.base_dir, "rules", "design-standards.md"), "w") as f:
            f.write("# Design Standards\n")
        for s in ["ui-ux-design", "brand-guidelines", "image-workflow", "visual-design-fundamentals", "design-anti-patterns"]:
            os.makedirs(os.path.join(self.base_dir, "skills", s), exist_ok=True)
            with open(os.path.join(self.base_dir, "skills", s, "SKILL.md"), "w") as f:
                f.write(f"# Skill {s}\n")
        with open(os.path.join(self.base_dir, "workflows", "wf-brand-context.md"), "w") as f:
            f.write("# Brand Context\n")
        with open(os.path.join(self.base_dir, "workflows", "wf-site-setup.md"), "w") as f:
            f.write("# Site Setup\n")

        # Create files for marketing team
        # marketing uses: agents: [marketer], rules: [design-standards.md], skills: [persona-management, brand-guidelines, image-workflow, ai-search-optimization, memory-management], workflows: [wf-brand-context.md]
        with open(os.path.join(self.base_dir, "agents", "marketer.md"), "w") as f:
            f.write("# Marketer\n")
        for s in ["persona-management", "ai-search-optimization"]:
            os.makedirs(os.path.join(self.base_dir, "skills", s), exist_ok=True)
            with open(os.path.join(self.base_dir, "skills", s, "SKILL.md"), "w") as f:
                f.write(f"# Skill {s}\n")

        # Create core assets
        with open(os.path.join(self.base_dir, "agents", "project-manager.md"), "w") as f:
            f.write("# Project Manager\n")
        with open(os.path.join(self.base_dir, "rules", "base.md"), "w") as f:
            f.write("# Base\n")
        for s in ["workforce-management", "memory-management", "issue-tracker", "session-context", "usage-tracker"]:
            os.makedirs(os.path.join(self.base_dir, "skills", s), exist_ok=True)
            with open(os.path.join(self.base_dir, "skills", s, "SKILL.md"), "w") as f:
                f.write(f"# Skill {s}\n")

        # Create user custom persona in workforces/personas/
        self.jordan_persona = os.path.join(self.workforces_dir, "personas", "jordan-belfort.json")
        with open(self.jordan_persona, "w", encoding="utf-8") as f:
            json.dump({
                "id": "jordan-belfort",
                "name": "Jordan Belfort / High-Energy Closer",
                "type": "author_voice",
                "tone": "Urgent, confident, assertive"
            }, f)

        # Create user custom workspace team folder
        self.marketing_ws_team = os.path.join(self.workforces_dir, "teams", "marketing")
        os.makedirs(self.marketing_ws_team, exist_ok=True)
        with open(os.path.join(self.marketing_ws_team, "team.json"), "w", encoding="utf-8") as f:
            json.dump({"id": "marketing", "custom_notes": "Q3 campaign settings"}, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_prune_shared_skill_preservation(self):
        """Test that uninstalling marketing preserves brand-guidelines and image-workflow because design is active."""
        # Pre-checks
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "brand-guidelines")))
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "image-workflow")))
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "persona-management")))
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "agents", "marketer.md")))

        # Run prune for marketing
        result = prune_team(
            team_name="marketing",
            target_dir=self.test_dir,
            toolkit_root=REPO_ROOT,
            purge_data=False,
            dry_run=False
        )
        self.assertTrue(result)

        # Assert shared skills are preserved
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "brand-guidelines")), "brand-guidelines must be preserved for design")
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "image-workflow")), "image-workflow must be preserved for design")
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "rules", "design-standards.md")), "design-standards.md must be preserved for design")

        # Assert unshared marketing-exclusive assets are pruned from .agents/
        self.assertFalse(os.path.exists(os.path.join(self.base_dir, "skills", "persona-management")), "persona-management should be pruned when no active team uses it")
        self.assertFalse(os.path.exists(os.path.join(self.base_dir, "skills", "ai-search-optimization")), "ai-search-optimization should be pruned")
        self.assertFalse(os.path.exists(os.path.join(self.base_dir, "agents", "marketer.md")), "marketer.md should be pruned from .agents/agents/")

        # Assert core assets remain intact
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "agents", "project-manager.md")))
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "memory-management")))

        # Assert workspace persona profile and workspace team folder stay behind
        self.assertTrue(os.path.exists(self.jordan_persona), "Workspace persona profile must stay behind")
        self.assertTrue(os.path.exists(self.marketing_ws_team), "Workspace team folder must stay behind unless purged")

        # Assert workrules.md was updated
        installed = get_installed_teams(self.test_dir, REPO_ROOT)
        self.assertEqual(installed, ["design"])

    def test_prune_dry_run_mode(self):
        """Test that dry run mode does not delete any files."""
        result = prune_team(
            team_name="marketing",
            target_dir=self.test_dir,
            toolkit_root=REPO_ROOT,
            purge_data=False,
            dry_run=True
        )
        self.assertTrue(result)

        # Assert files were NOT deleted
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "agents", "marketer.md")))
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, "skills", "persona-management")))
        
        # Installed teams in workrules.md should remain untouched
        installed = get_installed_teams(self.test_dir, REPO_ROOT)
        self.assertIn("marketing", installed)

    def test_prune_with_purge_data(self):
        """Test that --purge-data deletes workspace team data."""
        self.assertTrue(os.path.exists(self.marketing_ws_team))
        
        result = prune_team(
            team_name="marketing",
            target_dir=self.test_dir,
            toolkit_root=REPO_ROOT,
            purge_data=True,
            dry_run=False
        )
        self.assertTrue(result)

        # Workspace team folder should now be deleted
        self.assertFalse(os.path.exists(self.marketing_ws_team))

if __name__ == "__main__":
    unittest.main()
