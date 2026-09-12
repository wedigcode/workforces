#!/usr/bin/env python3
"""
Unit Tests for /wf-update and /wf-dashboard Commands
Verifies skill definitions, manifest inclusion, setup/update scripts,
and command documentation consistency.
"""

import os
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
DOT_AGENTS_SKILLS = REPO_ROOT / ".agents" / "skills"
SCRIPTS_DIR = SKILLS_DIR / "workforce-management" / "scripts"


class TestWfUpdateAndDashboardCommands(unittest.TestCase):
    """Verifies /wf-update and /wf-dashboard skills and toolkit wiring."""

    def test_wf_update_skill_files_exist(self):
        """Verify wf-update skill exists in both skills/ and .agents/skills/."""
        skill_file = SKILLS_DIR / "wf-update" / "SKILL.md"
        dot_agents_file = DOT_AGENTS_SKILLS / "wf-update" / "SKILL.md"

        self.assertTrue(skill_file.is_file(), f"Missing {skill_file}")
        self.assertTrue(dot_agents_file.is_file(), f"Missing {dot_agents_file}")

        content = skill_file.read_text(encoding="utf-8")
        self.assertIn("name: wf-update", content)
        self.assertIn("/wf-update", content)
        self.assertIn("update.sh", content)
        self.assertIn("workforce-management", content)

    def test_wf_dashboard_skill_files_exist(self):
        """Verify wf-dashboard skill exists in both skills/ and .agents/skills/."""
        skill_file = SKILLS_DIR / "wf-dashboard" / "SKILL.md"
        dot_agents_file = DOT_AGENTS_SKILLS / "wf-dashboard" / "SKILL.md"

        self.assertTrue(skill_file.is_file(), f"Missing {skill_file}")
        self.assertTrue(dot_agents_file.is_file(), f"Missing {dot_agents_file}")

        content = skill_file.read_text(encoding="utf-8")
        self.assertIn("name: wf-dashboard", content)
        self.assertIn("/wf-dashboard", content)
        self.assertIn("server.py", content)
        self.assertIn("Inbox", content)

    def test_resolve_manifest_includes_new_skills_in_core(self):
        """Verify resolve_manifest.py includes wf-update and wf-dashboard in CORE_SKILLS."""
        resolve_manifest_file = SCRIPTS_DIR / "resolve_manifest.py"
        content = resolve_manifest_file.read_text(encoding="utf-8")

        core_match = re.search(r"CORE_SKILLS\s*=\s*\{([^}]+)\}", content, re.DOTALL)
        self.assertIsNotNone(core_match, "CORE_SKILLS not found in resolve_manifest.py")
        core_skills = {item.strip().strip("'\"") for item in core_match.group(1).replace("\n", "").split(",") if item.strip()}

        self.assertIn("wf-update", core_skills, "CORE_SKILLS must contain 'wf-update'")
        self.assertIn("wf-dashboard", core_skills, "CORE_SKILLS must contain 'wf-dashboard'")

    def test_setup_and_update_scripts_include_new_skills(self):
        """Verify setup.sh and update.sh include wf-update and wf-dashboard in ALLOWED_SKILLS."""
        setup_sh = SCRIPTS_DIR / "setup.sh"
        update_sh = SCRIPTS_DIR / "update.sh"

        setup_content = setup_sh.read_text(encoding="utf-8")
        update_content = update_sh.read_text(encoding="utf-8")

        self.assertIn("wf-update", setup_content, "setup.sh ALLOWED_SKILLS missing 'wf-update'")
        self.assertIn("wf-dashboard", setup_content, "setup.sh ALLOWED_SKILLS missing 'wf-dashboard'")

        self.assertIn("wf-update", update_content, "update.sh ALLOWED_SKILLS missing 'wf-update'")
        self.assertIn("wf-dashboard", update_content, "update.sh ALLOWED_SKILLS missing 'wf-dashboard'")


if __name__ == "__main__":
    unittest.main()
