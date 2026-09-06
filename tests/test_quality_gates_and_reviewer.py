#!/usr/bin/env python3
"""
Test Suite: Quality Engineering Gates & Post-Code Reviewer
Tests automated quality gate auto-detection, quality triad execution,
dependency security audit alerts, and project setup quality templates.
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
REVIEWER_SCRIPT = REPO_ROOT / "skills" / "post-code-review" / "scripts" / "post_code_reviewer.py"
TEMPLATES_DIR = REPO_ROOT / "skills" / "site-setup" / "templates" / "quality-toolchain"

sys.path.insert(0, str(REVIEWER_SCRIPT.parent))
import post_code_reviewer


class TestQualityGatesAndReviewer(unittest.TestCase):
    """Verifies quality gate runners, command detection, and security audits."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_quality_gates_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_quality_templates_exist_and_valid(self):
        """Ensure all 4 quality engineering starter templates exist and are valid."""
        expected_files = [
            "dependency-cruiser.js",
            "dependabot.yml",
            "quality-ci.yml",
            "stryker.config.json"
        ]
        for fname in expected_files:
            tpl_path = TEMPLATES_DIR / fname
            self.assertTrue(tpl_path.is_file(), f"Template missing: {tpl_path}")
            content = tpl_path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 20, f"Template {fname} is too small or empty")

        # Validate JSON format for stryker.config.json
        stryker_json = json.loads((TEMPLATES_DIR / "stryker.config.json").read_text(encoding="utf-8"))
        self.assertIn("mutate", stryker_json)
        self.assertIn("thresholds", stryker_json)

    def test_detect_node_quality_commands(self):
        """Test detection of npm scripts in package.json."""
        pkg_json = self.test_dir / "package.json"
        pkg_json.write_text(json.dumps({
            "name": "sample-app",
            "scripts": {
                "typecheck": "tsc --noEmit",
                "lint": "biome check .",
                "test": "vitest run"
            }
        }), encoding="utf-8")

        cmds = post_code_reviewer.detect_quality_commands(self.test_dir)
        self.assertEqual(cmds.get("typecheck"), "npm run typecheck")
        self.assertEqual(cmds.get("lint"), "npm run lint")
        self.assertEqual(cmds.get("test"), "npm test")

    def test_detect_node_fallback_commands(self):
        """Test fallback detection when package.json lacks explicit scripts but config files exist."""
        (self.test_dir / "package.json").write_text(json.dumps({"name": "bare"}), encoding="utf-8")
        (self.test_dir / "tsconfig.json").write_text("{}", encoding="utf-8")
        (self.test_dir / "biome.json").write_text("{}", encoding="utf-8")

        cmds = post_code_reviewer.detect_quality_commands(self.test_dir)
        if shutil.which("npx"):
            self.assertIn("tsc", cmds.get("typecheck", ""))
            self.assertIn("biome", cmds.get("lint", ""))

    def test_run_quality_gate_checks_success(self):
        """Test running successful quality checks."""
        cmds = {
            "typecheck": f"{sys.executable} -c 'import sys; sys.exit(0)'",
            "lint": f"{sys.executable} -c 'import sys; sys.exit(0)'",
            "test": f"{sys.executable} -c 'import sys; sys.exit(0)'"
        }
        issues, passed = post_code_reviewer.run_quality_gate_checks(self.test_dir, cmds)
        self.assertTrue(passed)
        self.assertEqual(len(issues), 0)

    def test_run_quality_gate_checks_failure(self):
        """Test running failing quality checks flags errors and blocks handoff."""
        cmds = {
            "typecheck": f"{sys.executable} -c 'import sys; sys.stderr.write(\"Type error: TS2322\\n\"); sys.exit(1)'",
            "lint": f"{sys.executable} -c 'import sys; sys.exit(0)'",
            "test": f"{sys.executable} -c 'import sys; sys.stderr.write(\"AssertionError: expected 1 to equal 2\\n\"); sys.exit(1)'"
        }
        issues, passed = post_code_reviewer.run_quality_gate_checks(self.test_dir, cmds)
        self.assertFalse(passed)
        self.assertEqual(len(issues), 2)
        self.assertTrue(any("Typecheck" in iss for iss in issues))
        self.assertTrue(any("Test" in iss for iss in issues))

    def test_audit_dependency_security_no_changes(self):
        """Test security audit returns clean when no dependency manifests modified."""
        issues = post_code_reviewer.audit_dependency_security(["src/app.ts", "README.md"], self.test_dir)
        self.assertEqual(len(issues), 0)

    def test_audit_dependency_security_modified_manifest(self):
        """Test security audit is invoked when dependency manifests are modified."""
        # Creates a mock package.json
        (self.test_dir / "package.json").write_text(json.dumps({"name": "test"}), encoding="utf-8")
        # Should not crash and handle result gracefully
        issues = post_code_reviewer.audit_dependency_security(["package.json"], self.test_dir)
        self.assertIsInstance(issues, list)

    def test_run_code_review_gate_pre_handoff_blocker(self):
        """Test run_code_review_gate reports PRE-HANDOFF BLOCKER when checks fail."""
        (self.test_dir / "package.json").write_text(json.dumps({
            "name": "sample",
            "scripts": {
                "test": f"{sys.executable} -c 'sys.exit(1)'"
            }
        }), encoding="utf-8")

        # Initialize git repo in test_dir
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        report, passed = post_code_reviewer.run_code_review_gate(
            self.test_dir,
            target_dir_arg=str(self.test_dir),
            run_checks=True
        )
        self.assertFalse(passed)
        self.assertIn("PRE-HANDOFF BLOCKER", report)
        self.assertIn("Quality Gate Failed (Test)", report)


if __name__ == "__main__":
    unittest.main()
