"""
Tests for Strategy Sync, Factual Telemetry Grounding, Tool Enablement, and Design Preferences Memory.
"""

import os
import shutil
import tempfile
import unittest
import subprocess
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStrategySyncAndDesignMemory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workforces_dir = os.path.join(self.test_dir, "workforces")
        os.makedirs(os.path.join(self.workforces_dir, "issues", "inbox"), exist_ok=True)
        os.makedirs(os.path.join(self.workforces_dir, "hypotheses", "running"), exist_ok=True)
        os.makedirs(os.path.join(self.workforces_dir, "session-context"), exist_ok=True)
        os.makedirs(os.path.join(self.workforces_dir, "memory"), exist_ok=True)

        # Copy templates
        skills_dir = os.path.join(self.test_dir, "skills")
        shutil.copytree(os.path.join(ROOT_DIR, "skills"), skills_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_report_issue_with_tools_and_delegation(self):
        """Test reporting an issue with recommended tools, delegation target, and github labels."""
        script_path = os.path.join(self.test_dir, "skills", "issue-tracker", "scripts", "report-issue.py")
        cmd = [
            "python3",
            script_path,
            "--title", "Auth Token Cache Optimization",
            "--type", "refactor",
            "--severity", "P2",
            "--reporter", "programmer",
            "--tools", "jules,github-copilot",
            "--delegated-to", "jules",
            "--github-labels", "tool:jules,status:async-pending",
            "--out-dir", os.path.join(self.workforces_dir, "issues", "inbox"),
            "--description", "Offload token caching refactor to async worker",
            "--suggested-action", "Run jules session and review patch",
        ]
        res = subprocess.run(cmd, cwd=self.test_dir, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")

        inbox_dir = os.path.join(self.workforces_dir, "issues", "inbox")
        files = os.listdir(inbox_dir)
        self.assertEqual(len(files), 1)

        with open(os.path.join(inbox_dir, files[0]), "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("recommended_tools:", content)
        self.assertIn("jules", content)
        self.assertIn("github-copilot", content)
        self.assertIn('delegated_to: "jules"', content)
        self.assertIn("tool:jules", content)
        self.assertIn("**Recommended Tools:** `jules, github-copilot`", content)
        self.assertIn("**Delegated To:** `jules`", content)

    def test_hypothesis_with_tools_and_delegation(self):
        """Test creating a hypothesis with recommended tools, delegation, and labels."""
        script_path = os.path.join(self.test_dir, "skills", "hypothesis-tracker", "scripts", "hypothesis.py")
        cmd = [
            "python3",
            script_path,
            "--create",
            "--title", "Solo Agent Mobile Checkout Demand",
            "--owner", "sales",
            "--statement", "Solo agents will convert at 15% if presented with 1-touch mobile checkout",
            "--tools", "google-vids,google-slides",
            "--delegated-to", "marketer",
            "--github-labels", "tool:vids,type:hypothesis",
            "--root", self.test_dir,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")

        running_dir = os.path.join(self.workforces_dir, "hypotheses", "running")
        files = os.listdir(running_dir)
        self.assertEqual(len(files), 1)

        with open(os.path.join(running_dir, files[0]), "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("recommended_tools:", content)
        self.assertIn("google-vids", content)
        self.assertIn('delegated_to: "marketer"', content)
        self.assertIn("**Recommended Tools:** `google-vids, google-slides`", content)

    def test_design_preferences_memory_file(self):
        """Verify design preferences memory file exists and contains negative constraints."""
        pref_path = os.path.join(ROOT_DIR, "workforces", "memory", "design-preferences.md")
        self.assertTrue(os.path.exists(pref_path), "design-preferences.md does not exist")

        with open(pref_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Negative Design Constraints", content)
        self.assertIn("Yellow on Light/White", content)
        self.assertIn("No Emojis as UI Icons", content)
        self.assertIn("Refero Styles", content)

    def test_validate_references_script(self):
        """Test validate-references script on root directory without false-positive template errors."""
        validator_path = os.path.join(ROOT_DIR, "skills", "workforce-management", "scripts", "validate-references.py")
        res = subprocess.run(["python3", validator_path, ROOT_DIR], capture_output=True, text=True)
        # Should not crash and return 0
        self.assertEqual(res.returncode, 0, f"Validator error: {res.stderr}\nOutput: {res.stdout}")


if __name__ == "__main__":
    unittest.main()
