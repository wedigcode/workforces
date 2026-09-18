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

    def test_evaluate_pr_verification_form_clean(self):
        """Test PR verification form reports clean pass for compliant code."""
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        py_file = self.test_dir / "math_utils.py"
        py_file.write_text(code, encoding="utf-8")
        diff = f"+++ b/math_utils.py\n@@ -0,0 +1,2 @@\n+{code.replace(chr(10), chr(10)+'+')}"

        form_md, passed, pushbacks, candidates = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["math_utils.py"], [], self.test_dir
        )
        self.assertTrue(passed)
        self.assertEqual(len(pushbacks), 0)
        self.assertIn("- [x] **is it dry:**", form_md)
        self.assertIn("- [x] **no new code exceeds 35 lines:**", form_md)
        self.assertIn("- [x] **should any new code be in its own method:**", form_md)
        self.assertIn("- [x] **is any of it too verbose or can it be simplified:**", form_md)
        self.assertIn("- [x] **code maintainability:**", form_md)

    def test_audit_function_length_violation_triggers_pushback(self):
        """Test functions exceeding 35 lines are flagged and trigger AI pushback."""
        long_func = "def process_big_data():\n" + "".join(f"    x_{i} = {i}\n" for i in range(40)) + "    return x_39\n"
        py_file = self.test_dir / "big_task.py"
        py_file.write_text(long_func, encoding="utf-8")
        diff = f"+++ b/big_task.py\n@@ -0,0 +1,42 @@\n+{long_func.replace(chr(10), chr(10)+'+')}"

        form_md, passed, pushbacks, candidates = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["big_task.py"], [], self.test_dir
        )
        self.assertFalse(passed)
        self.assertTrue(any("exceeds 35 lines" in p or "limit" in p for p in pushbacks))
        self.assertIn("- [ ] **no new code exceeds 35 lines:**", form_md)

    def test_audit_method_scoping_nested_control_flow(self):
        """Test deeply nested control flow blocks (indent >= 4) are flagged in production code."""
        nested_diff = (
            "+++ b/service.py\n"
            "@@ -10,10 +10,12 @@\n"
            "+    if True:\n"
            "+        for item in items:\n"
            "+            while active:\n"
            "+                if check():\n"
            "+                    do_work()\n"
        )
        passed, violations, _ = post_code_reviewer.audit_method_scoping(
            nested_diff, ["service.py"], self.test_dir
        )
        self.assertFalse(passed)
        self.assertTrue(any("Deeply nested" in v for v in violations))

    def test_is_test_file_detection(self):
        """Test is_test_file identifies test suites and specifications across ecosystems."""
        self.assertTrue(post_code_reviewer.is_test_file("tests/Service/Multisite/ReportDataParsers/MulticrimEnhancedPlusParserTest.php"))
        self.assertTrue(post_code_reviewer.is_test_file("test_service.py"))
        self.assertTrue(post_code_reviewer.is_test_file("tests/test_foo.py"))
        self.assertTrue(post_code_reviewer.is_test_file("components/Button.test.tsx"))
        self.assertTrue(post_code_reviewer.is_test_file("services/api.spec.ts"))
        self.assertTrue(post_code_reviewer.is_test_file("pkg/worker_test.go"))
        self.assertFalse(post_code_reviewer.is_test_file("src/Service/Multisite/ReportDataParsers/MulticrimEnhancedPlusParser.php"))
        self.assertFalse(post_code_reviewer.is_test_file("service.py"))
        self.assertFalse(post_code_reviewer.is_test_file("ui.ts"))

    def test_audit_method_scoping_ignores_test_files(self):
        """Test that deeply nested control flow in test files is excluded from pushback."""
        test_diff = (
            "+++ b/tests/Service/Multisite/ReportDataParsers/MulticrimEnhancedPlusParserTest.php\n"
            "@@ -415,10 +415,15 @@\n"
            "+                if ($id === 10) {\n"
            "+                    $this->assertEquals(10, $id);\n"
            "+                }\n"
        )
        passed, violations, _ = post_code_reviewer.audit_method_scoping(
            test_diff,
            ["tests/Service/Multisite/ReportDataParsers/MulticrimEnhancedPlusParserTest.php"],
            self.test_dir
        )
        self.assertTrue(passed)
        self.assertEqual(len(violations), 0)

    def test_is_test_file_avoids_contest_and_latest_false_positives(self):
        """Ensure production files ending in 'test.php' (e.g. contest.php, latest.php) are not flagged as tests."""
        self.assertFalse(post_code_reviewer.is_test_file("contest.php"))
        self.assertFalse(post_code_reviewer.is_test_file("latest.php"))
        self.assertFalse(post_code_reviewer.is_test_file("src/contest.php"))
        self.assertFalse(post_code_reviewer.is_test_file("src/latest.php"))
        self.assertFalse(post_code_reviewer.is_test_file("Contest.php"))
        self.assertTrue(post_code_reviewer.is_test_file("UserTest.php"))
        self.assertTrue(post_code_reviewer.is_test_file("user_test.php"))
        self.assertTrue(post_code_reviewer.is_test_file("user-test.php"))

    def test_audit_function_length_ignores_test_files(self):
        """Test that function length check skips functions in test files."""
        test_py = self.test_dir / "tests" / "test_long.py"
        test_py.parent.mkdir(parents=True, exist_ok=True)
        # Create a 40-line test function
        body = "\n".join(f"    x_{i} = {i}" for i in range(40))
        test_py.write_text(f"def test_massive():\n{body}\n", encoding="utf-8")

        diff = (
            "+++ b/tests/test_long.py\n"
            "@@ -1,45 +1,45 @@\n"
            "+def test_massive():\n"
        )
        passed, violations, _ = post_code_reviewer.audit_function_length(
            diff, ["tests/test_long.py"], self.test_dir, max_lines=35
        )
        self.assertTrue(passed)
        self.assertEqual(len(violations), 0)

    def test_audit_dry_principles_ignores_test_files(self):
        """Test that added functions in test files do not trigger DRY duplication violations."""
        diff = (
            "+++ b/tests/test_helper.py\n"
            "@@ -1,5 +1,5 @@\n"
            "+def parse_data(x):\n"
            "+    return x\n"
        )
        symbols = [{"name": "parse_data", "file": "service.py", "line": 10}]
        passed, violations, _ = post_code_reviewer.audit_dry_principles(
            diff, ["tests/test_helper.py"], symbols, self.test_dir
        )
        self.assertTrue(passed)
        self.assertEqual(len(violations), 0)

    def test_audit_class_helper_reuse_scoped_to_file(self):
        """Ensure manual parsing in a test file does not trigger helper warning on modified production file."""
        prod_file = self.test_dir / "service.php"
        prod_file.write_text(
            "<?php\nclass Service {\n    public function formatNumber($v) { return (float)$v; }\n}\n",
            encoding="utf-8"
        )
        diff = (
            "+++ b/service.php\n"
            "@@ -1,5 +1,6 @@\n"
            "+// clean comment in service\n"
            "+++ b/tests/ServiceTest.php\n"
            "@@ -10,5 +10,6 @@\n"
            "+$val = floatval('123.45');\n"
        )
        issues = post_code_reviewer.audit_class_helper_reuse(
            ["service.php", "tests/ServiceTest.php"], diff, self.test_dir
        )
        self.assertEqual(len(issues), 0)

    def test_audit_simplicity_redundant_boolean(self):
        """Test redundant boolean ternary (? true : false) is flagged."""
        diff = (
            "+++ b/ui.ts\n"
            "@@ -1,5 +1,5 @@\n"
            "+const isValid = check() ? true : false;\n"
        )
        passed, violations, _ = post_code_reviewer.audit_simplicity_and_verbosity(diff, ["ui.ts"])
        self.assertFalse(passed)
        self.assertTrue(any("Redundant boolean ternary" in v for v in violations))

    def test_security_bypass_caching_and_weekly_retry_lifecycle(self):
        """Test security bypass caching, 7-day non-blocking window, and cache updates."""
        import datetime
        now = datetime.datetime.now()
        manifest = self.test_dir / "package.json"
        manifest.write_text(json.dumps({"name": "test-pkg"}), encoding="utf-8")

        cache_path = self.test_dir / "workforces" / "memory" / "security-bypass.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Simulate active bypass entry within 7 days
        future_retry = (now + datetime.timedelta(days=5)).isoformat()
        initial_cache = {
            "bypasses": {
                "npm:vulnerability in semver": {
                    "ecosystem": "npm",
                    "summary": "vulnerability in semver",
                    "first_detected": now.isoformat(),
                    "last_tried": now.isoformat(),
                    "next_retry": future_retry,
                    "status": "bypassed"
                }
            }
        }
        cache_path.write_text(json.dumps(initial_cache), encoding="utf-8")

        loaded = post_code_reviewer.load_security_bypass_cache(self.test_dir)
        self.assertIn("npm:vulnerability in semver", loaded["bypasses"])

        # 2. Test saving and loading
        post_code_reviewer.save_security_bypass_cache(self.test_dir, loaded)
        reloaded = post_code_reviewer.load_security_bypass_cache(self.test_dir)
        self.assertEqual(reloaded["bypasses"]["npm:vulnerability in semver"]["next_retry"], future_retry)

    def test_security_bypass_remediation_attempt_success(self):
        """Test remediation attempt (npm audit fix) success clears bypass and resumes normal routine."""
        from unittest.mock import patch
        cache = {"bypasses": {"npm:vulnerability in tar": {"ecosystem": "npm", "summary": "vulnerability in tar", "status": "bypassed", "next_retry": "2020-01-01T00:00:00"}}}
        bypasses = cache["bypasses"]

        with patch.object(post_code_reviewer, "attempt_remediation", return_value=True):
            result = post_code_reviewer.handle_security_failure("npm", "vulnerability in tar", bypasses, self.test_dir, cache)

        self.assertIn("Security Remediation Succeeded", result)
        self.assertIn("Returned to normal routine", result)
        self.assertNotIn("npm:vulnerability in tar", bypasses)

    def test_security_bypass_remediation_attempt_failure_and_weekly_schedule(self):
        """Test remediation failure logs learnings to bypass cache and schedules 7-day retry."""
        from unittest.mock import patch
        cache = {"bypasses": {}}
        bypasses = cache["bypasses"]

        with patch.object(post_code_reviewer, "attempt_remediation", return_value=False):
            result = post_code_reviewer.handle_security_failure("npm", "unresolvable CVE-9999", bypasses, self.test_dir, cache)

        self.assertIn("Fix attempted but `unresolvable CVE-9999` unresolvable", result)
        self.assertIn("weekly retry", result)
        self.assertIn("npm:unresolvable CVE-9999", bypasses)
        entry = bypasses["npm:unresolvable CVE-9999"]
        self.assertEqual(entry["status"], "bypassed")
        self.assertIn("npm audit fix", entry.get("attempt", ""))
        self.assertIn("learnings", entry)

    def test_security_bypass_cache_corruption_resilience(self):
        """Test corrupted or invalid JSON in security-bypass.json recovers gracefully."""
        cache_path = self.test_dir / "workforces" / "memory" / "security-bypass.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Non-JSON content
        cache_path.write_text("corrupted non-json { syntax", encoding="utf-8")
        loaded = post_code_reviewer.load_security_bypass_cache(self.test_dir)
        self.assertEqual(loaded, {"bypasses": {}})

        # Non-dict JSON (e.g. array)
        cache_path.write_text("[\"invalid\", \"array\"]", encoding="utf-8")
        loaded_arr = post_code_reviewer.load_security_bypass_cache(self.test_dir)
        self.assertEqual(loaded_arr, {"bypasses": {}})

    def test_ai_pushback_with_no_justification(self):
        """Test rule violation without justification triggers AI pushback."""
        long_func = "def big_runner():\n" + "".join(f"    val_{i} = {i}\n" for i in range(40)) + "    return val_39\n"
        py_file = self.test_dir / "runner.py"
        py_file.write_text(long_func, encoding="utf-8")
        diff = f"+++ b/runner.py\n@@ -0,0 +1,42 @@\n+{long_func.replace(chr(10), chr(10)+'+')}"

        form_md, passed, pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["runner.py"], [], self.test_dir, justification=None
        )
        self.assertFalse(passed)
        self.assertTrue(any("Pushback" in p for p in pushbacks))
        self.assertTrue(any("No explanation provided" in p for p in pushbacks))
        self.assertIn("- [ ] **no new code exceeds 35 lines:**", form_md)

    def test_ai_pushback_with_bad_reason_rejected(self):
        """Test rule violation with trivial/evasive justification is rejected with pushback."""
        long_func = "def big_runner():\n" + "".join(f"    val_{i} = {i}\n" for i in range(40)) + "    return val_39\n"
        py_file = self.test_dir / "runner.py"
        py_file.write_text(long_func, encoding="utf-8")
        diff = f"+++ b/runner.py\n@@ -0,0 +1,42 @@\n+{long_func.replace(chr(10), chr(10)+'+')}"

        form_md, passed, pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["runner.py"], [], self.test_dir, justification="lazy"
        )
        self.assertFalse(passed)
        self.assertTrue(any("'lazy' is not an acceptable technical justification" in p for p in pushbacks))

    def test_ai_pushback_with_valid_technical_justification_accepted(self):
        """Test rule violation with legitimate technical rationale is accepted as justified."""
        long_func = "def big_runner():\n" + "".join(f"    val_{i} = {i}\n" for i in range(40)) + "    return val_39\n"
        py_file = self.test_dir / "runner.py"
        py_file.write_text(long_func, encoding="utf-8")
        diff = f"+++ b/runner.py\n@@ -0,0 +1,42 @@\n+{long_func.replace(chr(10), chr(10)+'+')}"

        form_md, passed, pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["runner.py"], [], self.test_dir,
            justification="Third-party AST visitor pattern requiring contiguous traversal structure"
        )
        self.assertTrue(passed)
        self.assertEqual(len(pushbacks), 0)
        self.assertIn("- [x] **no new code exceeds 35 lines:** [Justified:", form_md)

    def test_ai_pushback_in_diff_comment_justification(self):
        """Test justification provided directly in diff comments is extracted and accepted."""
        code_lines = [
            "# justification: Legacy protocol parser with strictly ordered packet decoding",
            "def parse_protocol():"
        ] + [f"    field_{i} = {i}" for i in range(38)] + ["    return field_37"]
        full_code = "\n".join(code_lines) + "\n"

        py_file = self.test_dir / "protocol.py"
        py_file.write_text(full_code, encoding="utf-8")
        diff = f"+++ b/protocol.py\n@@ -0,0 +1,42 @@\n+{full_code.replace(chr(10), chr(10)+'+')}"

        form_md, passed, pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["protocol.py"], [], self.test_dir
        )
        self.assertTrue(passed)
        self.assertEqual(len(pushbacks), 0)
        self.assertIn("- [x] **no new code exceeds 35 lines:** [Justified:", form_md)

    def test_security_bypass_active_unexpired_returns_info_notice(self):
        """Test active unexpired 7-day bypass returns info notice and does not block."""
        import datetime
        future_retry = (datetime.datetime.now() + datetime.timedelta(days=4)).isoformat()
        cache = {
            "bypasses": {
                "npm:vulnerability in axios": {
                    "ecosystem": "npm",
                    "summary": "vulnerability in axios",
                    "next_retry": future_retry,
                    "status": "bypassed"
                }
            }
        }
        res = post_code_reviewer.handle_security_failure(
            "npm", "vulnerability in axios", cache["bypasses"], self.test_dir, cache
        )
        self.assertIn("ℹ️ **Security Bypass Active (Weekly Re-check):**", res)
        self.assertIn("vulnerability in axios", res)
        self.assertIn(future_retry, res)

    def test_security_bypass_expired_retry_advances_schedule(self):
        """Test expired bypass re-try failure advances next_retry by +7 days and warns."""
        import datetime
        from unittest.mock import patch
        past_retry = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        cache = {
            "bypasses": {
                "npm:vulnerability in lodash": {
                    "ecosystem": "npm",
                    "summary": "vulnerability in lodash",
                    "next_retry": past_retry,
                    "status": "bypassed"
                }
            }
        }
        with patch.object(post_code_reviewer, "attempt_remediation", return_value=False):
            res = post_code_reviewer.handle_security_failure(
                "npm", "vulnerability in lodash", cache["bypasses"], self.test_dir, cache
            )
        entry = cache["bypasses"]["npm:vulnerability in lodash"]
        self.assertIn("⚠️ **Security Notice (Weekly Re-try):**", res)
        new_retry = datetime.datetime.fromisoformat(entry["next_retry"])
        self.assertGreater(new_retry, datetime.datetime.now() + datetime.timedelta(days=5))

    def test_direct_vs_transitive_vulnerability_distinction(self):
        """Test direct and transitive 3rd-party vulnerabilities emit non-blocking ⚠️ advisory notices with bypass tracking."""
        from unittest.mock import patch
        mock_audit = {
            "vulnerabilities": {
                "direct-vuln-pkg": {"isDirect": True, "severity": "high"},
                "transitive-vuln-pkg": {"isDirect": False, "severity": "moderate"}
            }
        }
        cache = {"bypasses": {}}
        bypasses = cache["bypasses"]
        with patch.object(post_code_reviewer, "attempt_remediation", return_value=False):
            issues = post_code_reviewer._process_npm_vulnerabilities(
                mock_audit["vulnerabilities"], bypasses, self.test_dir, cache
            )
        self.assertEqual(len(issues), 2)
        direct_issue = next(i for i in issues if "direct-vuln-pkg" in i)
        transitive_issue = next(i for i in issues if "transitive-vuln-pkg" in i)
        self.assertIn("⚠️ **3rd-Party Security Notice (npm):** Direct dependency `direct-vuln-pkg`", direct_issue)
        self.assertIn("⚠️ **3rd-Party Security Notice (npm):** Transitive dependency `transitive-vuln-pkg`", transitive_issue)
        self.assertIn("npm:vulnerability in transitive-vuln-pkg", bypasses)
        self.assertIn("npm:vulnerability in direct-vuln-pkg", bypasses)

    def test_security_audit_failure_not_swallowed(self):
        """Test npm audit exceptions or timeouts emit non-blocking ⚠️ 3rd-Party Security Audit Notice."""
        from unittest.mock import patch
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="npm audit", timeout=15)):
            issues = post_code_reviewer._run_node_audit(["package.json"], self.test_dir, {}, {"bypasses": {}})
        self.assertEqual(len(issues), 1)
        self.assertIn("⚠️ **3rd-Party Security Audit Notice (npm):**", issues[0])

    def test_audit_code_security_and_bug_patterns(self):
        """Test audit_code_security_and_bug_patterns catches hardcoded secrets and bug traps."""
        aws_sample_key = "AKIA" "IOSFODNN7EXAMPLE"
        diff = (
            "+++ b/auth.py\n"
            f"+def login(user, token='{aws_sample_key}'):\n"
            "+    pass\n"
            "+++ b/utils.py\n"
            "+def process_items(items=[]):\n"
            "+    pass\n"
        )
        sec_issues, bug_issues = post_code_reviewer.audit_code_security_and_bug_patterns(diff, ["auth.py", "utils.py"])
        self.assertTrue(any("Hardcoded Secret Blocked" in s for s in sec_issues))
        self.assertTrue(any("Mutable default argument" in b for b in bug_issues))

    def test_pre_existing_debt_in_untouched_files_is_non_blocking(self):
        """Test static analysis errors in untouched legacy files emit ⚠️ debt and do not block handoff."""
        from unittest.mock import patch
        mock_output = (
            "src/legacy/old_module.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
            "src/legacy/ancient.ts:88:2 - error TS2304: Cannot find name 'foo'.\n"
        )
        candidates = []
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            msg = post_code_reviewer._execute_single_check(
                self.test_dir,
                "typecheck",
                "tsc --noEmit",
                modified_files=["src/new_feature.ts"],
                candidates=candidates
            )
            self.assertIn("⚠️ **Pre-Existing Codebase Quality Debt (Typecheck):**", msg)
            self.assertNotIn("❌", msg)
            self.assertTrue(any("Code Quality Sprint" in c for c in candidates))

    def test_pre_existing_debt_uses_full_paths_not_basenames(self):
        """Test diagnostics in untouched files remain non-blocking even when basenames overlap."""
        from unittest.mock import patch
        mock_output = "src/legacy/foo.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            msg = post_code_reviewer._execute_single_check(
                self.test_dir,
                "typecheck",
                "tsc --noEmit",
                modified_files=["src/foo.ts"],
                candidates=[]
            )
            self.assertIn("⚠️ **Pre-Existing Codebase Quality Debt (Typecheck):**", msg)
            self.assertNotIn("❌", msg)

    def test_pre_existing_debt_without_diagnostic_paths_remains_blocking(self):
        """Test diagnostics without file paths are treated as blocking quality failures."""
        from unittest.mock import patch
        mock_output = "error TS18003: No inputs were found in config file 'tsconfig.json'.\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            msg = post_code_reviewer._execute_single_check(
                self.test_dir,
                "typecheck",
                "tsc --noEmit",
                modified_files=["src/new_feature.ts"],
                candidates=[]
            )
            self.assertIn("❌ **Quality Gate Failed (Typecheck):**", msg)
            self.assertNotIn("Pre-Existing Codebase Quality Debt", msg)

    def test_pre_existing_debt_with_ambiguous_short_path_remains_blocking(self):
        """Test short/ambiguous diagnostic paths are treated as blocking failures."""
        from unittest.mock import patch
        mock_output = "foo.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            msg = post_code_reviewer._execute_single_check(
                self.test_dir,
                "typecheck",
                "tsc --noEmit",
                modified_files=["src/foo.ts"],
                candidates=[]
            )
            self.assertIn("❌ **Quality Gate Failed (Typecheck):**", msg)
            self.assertNotIn("Pre-Existing Codebase Quality Debt", msg)

    def test_pre_existing_debt_does_not_match_by_suffix_path_overlap(self):
        """Test suffix-overlapping paths in different directories are not treated as modified."""
        from unittest.mock import patch
        mock_output = "packages/a/src/foo.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            msg = post_code_reviewer._execute_single_check(
                self.test_dir,
                "typecheck",
                "tsc --noEmit",
                modified_files=["src/foo.ts"],
                candidates=[]
            )
            self.assertIn("⚠️ **Pre-Existing Codebase Quality Debt (Typecheck):**", msg)
            self.assertNotIn("❌", msg)

    def test_touched_lines_addition_only_not_context(self):
        """Test _get_touched_lines only tracks added (+) lines, not context lines."""
        diff = (
            "+++ b/calc.py\n"
            "@@ -10,5 +10,6 @@\n"
            " def existing():\n"
            "     x = 1\n"
            "+    y = 2\n"
            "     z = 3\n"
            "     return x + z\n"
        )
        touched = post_code_reviewer._get_touched_lines(diff)
        self.assertEqual(touched.get("calc.py"), {12})

    def test_dry_violation_with_code_graph_symbol_and_justification(self):
        """Test functions matching existing code graph symbols populate violations and pushback."""
        symbols = [{"name": "duplicate_helper", "file": "src/utils.py", "line": 42}]
        diff = "+++ b/feature.py\n@@ -0,0 +1,3 @@\n+def duplicate_helper():\n+    return True\n"
        passed, viols, _ = post_code_reviewer.audit_dry_principles(diff, ["feature.py"], symbols, self.test_dir)
        self.assertFalse(passed)
        self.assertTrue(any("matches existing symbol in `src/utils.py`" in v for v in viols))

        _, form_passed, pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["feature.py"], symbols, self.test_dir, justification=None
        )
        self.assertFalse(form_passed)
        self.assertTrue(any("is it dry" in p for p in pushbacks))

        _, just_passed, just_pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["feature.py"], symbols, self.test_dir,
            justification="Different domain abstraction with specialized error semantics"
        )
        self.assertTrue(just_passed)
        self.assertEqual(len(just_pushbacks), 0)

    def test_detect_quality_commands_ignores_no_test_specified(self):
        """Test detect_quality_commands ignores npm default 'no test specified' script."""
        pkg_json = self.test_dir / "package.json"
        pkg_json.write_text(json.dumps({
            "name": "sample",
            "scripts": {"test": "echo \"Error: no test specified\" && exit 1"}
        }), encoding="utf-8")
        cmds = post_code_reviewer.detect_quality_commands(self.test_dir)
        self.assertNotIn("test", cmds)

    def test_detect_multi_stack_quality_commands(self):
        """Test multi-stack toolchain detection for Python, Go, Rust, and PHP."""
        (self.test_dir / "composer.json").write_text("{}", encoding="utf-8")
        vbin = self.test_dir / "vendor" / "bin"
        vbin.mkdir(parents=True, exist_ok=True)
        (vbin / "pest").write_text("#!/bin/sh\n", encoding="utf-8")
        (vbin / "phpstan").write_text("#!/bin/sh\n", encoding="utf-8")
        (vbin / "pint").write_text("#!/bin/sh\n", encoding="utf-8")

        (self.test_dir / "go.mod").write_text("module example.com/test\n", encoding="utf-8")
        (self.test_dir / "Cargo.toml").write_text("[package]\nname = \"test\"\n", encoding="utf-8")

        cmds = post_code_reviewer.detect_quality_commands(self.test_dir)
        self.assertIn(cmds.get("test"), ["./vendor/bin/pest", "cargo test", "go test ./..."])
        self.assertIn(cmds.get("typecheck"), ["./vendor/bin/phpstan analyse", "cargo check", "go vet ./..."])

    def test_untracked_files_diff_heuristics(self):
        """Test newly added untracked files are inspected in diff heuristics."""
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True)
        long_func = "def untracked_func():\n" + "".join(f"    x_{i} = {i}\n" for i in range(40)) + "    return x_39\n"
        (self.test_dir / "untracked.py").write_text(long_func, encoding="utf-8")

        diff = post_code_reviewer.get_git_diff(self.test_dir)
        self.assertIn("+++ b/untracked.py", diff)
        self.assertIn("+def untracked_func():", diff)

        _, passed, pushbacks, _ = post_code_reviewer.evaluate_pr_verification_form(
            diff, ["untracked.py"], [], self.test_dir
        )
        self.assertFalse(passed)
        self.assertTrue(any("exceeds 35 lines" in p for p in pushbacks))

    def test_heuristics_advisory_non_blocking_in_gate(self):
        """Test line length and checklist heuristics surface advisory feedback but do not block gate with strict=True."""
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        long_func = "def long_function():\n" + "".join(f"    v_{i} = {i}\n" for i in range(40)) + "    return v_39\n"
        (self.test_dir / "service.py").write_text(long_func, encoding="utf-8")

        report, passed = post_code_reviewer.run_code_review_gate(
            self.test_dir,
            target_dir_arg=str(self.test_dir),
            run_checks=False,
            strict=True
        )
        self.assertTrue(passed, "Advisory checklist heuristics should not block execution even when strict=True")
        self.assertIn("ADVISORY REVIEW FEEDBACK", report)
        self.assertIn("no new code exceeds 35 lines", report)
        self.assertNotIn("PRE-HANDOFF BLOCKER", report)

    def test_cli_strict_exit_zero_on_advisory_heuristics(self):
        """Test CLI command post_code_reviewer.py --strict exits with code 0 on advisory findings."""
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        long_func = "def long_function():\n" + "".join(f"    v_{i} = {i}\n" for i in range(40)) + "    return v_39\n"
        (self.test_dir / "service.py").write_text(long_func, encoding="utf-8")

        script_path = Path(__file__).parent.parent / "skills" / "post-code-review" / "scripts" / "post_code_reviewer.py"
        res = subprocess.run([sys.executable, str(script_path), "--root", str(self.test_dir), "--strict"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Expected 0 exit code, got {res.returncode}. Output: {res.stdout}\nStderr: {res.stderr}")

    def test_run_code_review_gate_uses_branch_diff_when_working_tree_is_clean(self):
        """Test committed feature-branch diffs are reviewed even with a clean working tree."""
        subprocess.run(["git", "init", "-b", "main"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def base():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.test_dir, capture_output=True)
        origin_main = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.test_dir, capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "update-ref", "refs/remotes/origin/main", origin_main], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.test_dir, capture_output=True)

        long_func = "def long_function():\n" + "".join(f"    v_{i} = {i}\n" for i in range(40)) + "    return v_39\n"
        (self.test_dir / "service.py").write_text(long_func, encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feature"], cwd=self.test_dir, capture_output=True)

        diff = post_code_reviewer.get_git_diff(self.test_dir)
        modified_files = post_code_reviewer.get_modified_files(self.test_dir)
        report, passed = post_code_reviewer.run_code_review_gate(
            self.test_dir,
            target_dir_arg=str(self.test_dir),
            run_checks=False,
            strict=True
        )

        self.assertIn("+++ b/service.py", diff)
        self.assertEqual(modified_files, ["service.py"])
        self.assertIn("**Modified Files Audited:** 1 file(s)", report)
        self.assertIn("ADVISORY REVIEW FEEDBACK", report)
        self.assertTrue(passed, "Advisory heuristics on committed branch diffs should stay non-blocking")

    def test_run_code_review_gate_accepts_fully_qualified_base_ref(self):
        """Test clean-branch fallback accepts env base refs like origin/main."""
        subprocess.run(["git", "init", "-b", "main"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def base():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.test_dir, capture_output=True)
        origin_main = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.test_dir, capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "update-ref", "refs/remotes/origin/main", origin_main], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def changed():\n    return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feature"], cwd=self.test_dir, capture_output=True)

        old_base_ref = os.environ.get("GITHUB_BASE_REF")
        os.environ["GITHUB_BASE_REF"] = "origin/main"
        try:
            self.assertEqual(post_code_reviewer.get_modified_files(self.test_dir), ["service.py"])
            self.assertIn("+++ b/service.py", post_code_reviewer.get_git_diff(self.test_dir))
        finally:
            if old_base_ref is None:
                os.environ.pop("GITHUB_BASE_REF", None)
            else:
                os.environ["GITHUB_BASE_REF"] = old_base_ref

    def test_run_code_review_gate_accepts_non_origin_remote_base_ref(self):
        """Test clean-branch fallback accepts fully qualified non-origin remote refs."""
        subprocess.run(["git", "init", "-b", "main"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def base():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.test_dir, capture_output=True)
        upstream_main = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.test_dir, capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "update-ref", "refs/remotes/upstream/main", upstream_main], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def changed():\n    return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feature"], cwd=self.test_dir, capture_output=True)

        old_base_ref = os.environ.get("GITHUB_BASE_REF")
        os.environ["GITHUB_BASE_REF"] = "refs/remotes/upstream/main"
        try:
            self.assertEqual(post_code_reviewer.get_modified_files(self.test_dir), ["service.py"])
            self.assertIn("+++ b/service.py", post_code_reviewer.get_git_diff(self.test_dir))
        finally:
            if old_base_ref is None:
                os.environ.pop("GITHUB_BASE_REF", None)
            else:
                os.environ["GITHUB_BASE_REF"] = old_base_ref

    def test_run_code_review_gate_prefers_closer_branch_point_over_stale_env_ref(self):
        """Test stale env base refs do not beat a closer local branch point."""
        subprocess.run(["git", "init", "-b", "main"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "root.py").write_text("def root():\n    return 0\n", encoding="utf-8")
        subprocess.run(["git", "add", "root.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "root"], cwd=self.test_dir, capture_output=True)
        (self.test_dir / "base.py").write_text("def base():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "base.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "main-base"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "branch", "legacy", "HEAD~1"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def changed():\n    return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feature"], cwd=self.test_dir, capture_output=True)

        old_base_ref = os.environ.get("GITHUB_BASE_REF")
        os.environ["GITHUB_BASE_REF"] = "legacy"
        try:
            self.assertEqual(post_code_reviewer.get_modified_files(self.test_dir), ["service.py"])
            diff = post_code_reviewer.get_git_diff(self.test_dir)
            self.assertIn("+++ b/service.py", diff)
            self.assertNotIn("+++ b/base.py", diff)
        finally:
            if old_base_ref is None:
                os.environ.pop("GITHUB_BASE_REF", None)
            else:
                os.environ["GITHUB_BASE_REF"] = old_base_ref

    def test_run_code_review_gate_falls_back_to_full_local_branch_lineage(self):
        """Test clean-branch fallback reviews all locally available commits, not just HEAD~1."""
        subprocess.run(["git", "init", "-b", "feature"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "first.py").write_text("def first():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "first.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "first"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "second.py").write_text("def second():\n    return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "second.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "second"], cwd=self.test_dir, capture_output=True)

        modified_files = post_code_reviewer.get_modified_files(self.test_dir)
        diff = post_code_reviewer.get_git_diff(self.test_dir)

        self.assertEqual(modified_files, ["first.py", "second.py"])
        self.assertIn("+++ b/first.py", diff)
        self.assertIn("+++ b/second.py", diff)

    def test_run_code_review_gate_uses_origin_head_for_nonstandard_default_branch(self):
        """Test clean-branch fallback can resolve base via origin/HEAD on nonstandard default branches."""
        subprocess.run(["git", "init", "-b", "stable"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def base():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.test_dir, capture_output=True)
        origin_stable = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.test_dir, capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "update-ref", "refs/remotes/origin/stable", origin_stable], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/stable"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.test_dir, capture_output=True)

        (self.test_dir / "service.py").write_text("def changed():\n    return 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "service.py"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feature"], cwd=self.test_dir, capture_output=True)

        self.assertEqual(post_code_reviewer.get_modified_files(self.test_dir), ["service.py"])
        self.assertIn("+++ b/service.py", post_code_reviewer.get_git_diff(self.test_dir))

    def test_validate_references_pack_json_resolves_against_repo_root(self):
        """Test validate-references.py resolves pack.json against repository root rather than teams/<team>/."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        teams_dir = self.test_dir / "teams" / "growth"
        teams_dir.mkdir(parents=True, exist_ok=True)
        rules_dir = self.test_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        skills_dir = self.test_dir / "skills" / "sample-skill"
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / "SKILL.md").write_text("# Sample Skill\n", encoding="utf-8")
        (rules_dir / "design-standards.md").write_text("# Design Standards\n", encoding="utf-8")

        (teams_dir / "pack.json").write_text(json.dumps({
            "name": "growth",
            "rules": ["design-standards.md"],
            "skills": ["sample-skill"],
            "agents": [],
            "workflows": []
        }), encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(val_script), str(self.test_dir)],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"validate-references should exit 0 with pack.json resolving against root: {res.stdout}")
        self.assertIn("Zero dangling file references found", res.stdout)
        self.assertFalse((teams_dir / "design-standards.md").exists(), "Should not create dummy stub in teams/growth/")

        # Guard against team-local fallback: A rule that exists ONLY in teams/growth/ must NOT satisfy pack.json
        (teams_dir / "team-only.md").write_text("# Team Only Rule\n", encoding="utf-8")
        (teams_dir / "pack.json").write_text(json.dumps({
            "name": "growth",
            "rules": ["design-standards.md", "team-only.md"],
            "skills": ["sample-skill"],
            "agents": [],
            "workflows": []
        }), encoding="utf-8")

        res_team_only = subprocess.run(
            [sys.executable, str(val_script), str(self.test_dir)],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(res_team_only.returncode, 0, "Team-local only file must not satisfy pack.json reference")
        self.assertIn("team-only.md", res_team_only.stdout)

        # Assert --fix creates the stub in root rules/, not teams/growth/
        res_fix = subprocess.run(
            [sys.executable, str(val_script), str(self.test_dir), "--fix"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res_fix.returncode, 0, f"--fix should resolve missing pack rule: {res_fix.stdout}")
        self.assertTrue((rules_dir / "team-only.md").exists(), "Auto-fix must create stub in root rules/")

    def test_validate_references_audits_skills_session_context_while_ignoring_session_notes(self):
        """Test validate-references.py audits skills/session-context while excluding workforces/session-context notes."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        sc_skill_dir = self.test_dir / "skills" / "session-context"
        sc_skill_dir.mkdir(parents=True, exist_ok=True)
        (sc_skill_dir / "SKILL.md").write_text("# Skill\n[Broken Link](nonexistent.md)\n", encoding="utf-8")

        wf_sc_dir = self.test_dir / "workforces" / "session-context"
        wf_sc_dir.mkdir(parents=True, exist_ok=True)
        (wf_sc_dir / "001_note.md").write_text("---\ntitle: note\n---\n# Note\n[Historical Broken Link](history.md)\n", encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(val_script), str(self.test_dir)],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("skills/session-context/SKILL.md", res.stdout)
        self.assertNotIn("001_note.md", res.stdout)

    def test_validate_references_only_excludes_exact_runtime_session_paths(self):
        """Test similarly named directories like session-context-backup are still audited."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        backup_dir = self.test_dir / "workforces" / "session-context-backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "note.md").write_text("# Backup\n[Broken](missing.md)\n", encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(val_script), str(self.test_dir)],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("workforces/session-context-backup/note.md", res.stdout)

    def test_validate_references_enforces_skill_md_for_pack_skills(self):
        """Test validate-references.py requires SKILL.md for skill candidates and creates SKILL.md on fix."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        teams_dir = self.test_dir / "teams" / "dev"
        teams_dir.mkdir(parents=True, exist_ok=True)
        (teams_dir / "pack.json").write_text(json.dumps({"skills": ["my-skill"]}), encoding="utf-8")
        (self.test_dir / "skills" / "my-skill").mkdir(parents=True, exist_ok=True)

        res = subprocess.run([sys.executable, str(val_script), str(self.test_dir)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("JSON skills: my-skill", res.stdout)

        res_fix = subprocess.run([sys.executable, str(val_script), str(self.test_dir), "--fix"], capture_output=True, text=True)
        self.assertEqual(res_fix.returncode, 0)
        self.assertTrue((self.test_dir / "skills" / "my-skill" / "SKILL.md").exists())

    def test_validate_references_supports_non_agents_editor_bases(self):
        """Test validate-references.py resolves pack.json against .claude and other editor bases."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        teams_dir = self.test_dir / ".claude" / "teams" / "dev"
        teams_dir.mkdir(parents=True, exist_ok=True)
        (teams_dir / "pack.json").write_text(json.dumps({"rules": ["clean-coder.md"], "skills": ["my-skill"]}), encoding="utf-8")
        (self.test_dir / ".claude" / "rules").mkdir(parents=True, exist_ok=True)
        (self.test_dir / ".claude" / "rules" / "clean-coder.md").write_text("# Rule\n", encoding="utf-8")
        (self.test_dir / ".claude" / "skills" / "my-skill").mkdir(parents=True, exist_ok=True)
        (self.test_dir / ".claude" / "skills" / "my-skill" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

        res = subprocess.run([sys.executable, str(val_script), str(self.test_dir)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Expected clean pass for .claude base: {res.stdout}")

    def test_validate_references_root_pack_does_not_use_editor_local_rule(self):
        """Test repo-root pack.json requires repo-root dependencies, not editor-local copies."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        teams_dir = self.test_dir / "teams" / "dev"
        teams_dir.mkdir(parents=True, exist_ok=True)
        (teams_dir / "pack.json").write_text(json.dumps({"rules": ["only-claude.md"]}), encoding="utf-8")
        claude_rules = self.test_dir / ".claude" / "rules"
        claude_rules.mkdir(parents=True, exist_ok=True)
        (claude_rules / "only-claude.md").write_text("# Claude Only\n", encoding="utf-8")

        res = subprocess.run([sys.executable, str(val_script), str(self.test_dir)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("JSON rules: only-claude.md", res.stdout)

        res_fix = subprocess.run([sys.executable, str(val_script), str(self.test_dir), "--fix"], capture_output=True, text=True)
        self.assertEqual(res_fix.returncode, 0)
        self.assertTrue((self.test_dir / "rules" / "only-claude.md").exists())
        self.assertEqual((claude_rules / "only-claude.md").read_text(encoding="utf-8"), "# Claude Only\n")

    def test_validate_references_fix_stays_within_installed_editor_base(self):
        """Test validate-references.py --fix creates missing pack.json dependencies in the same installed base."""
        val_script = REPO_ROOT / "skills" / "workforce-management" / "scripts" / "validate-references.py"
        claude_teams_dir = self.test_dir / ".claude" / "teams" / "dev"
        claude_teams_dir.mkdir(parents=True, exist_ok=True)
        (claude_teams_dir / "pack.json").write_text(json.dumps({
            "rules": ["missing-rule.md"],
            "skills": ["missing-skill"]
        }), encoding="utf-8")

        grok_teams_dir = self.test_dir / ".grok" / "teams" / "ops"
        grok_teams_dir.mkdir(parents=True, exist_ok=True)
        (grok_teams_dir / "pack.json").write_text(json.dumps({
            "workflows": ["missing-workflow"]
        }), encoding="utf-8")

        res_fix = subprocess.run([sys.executable, str(val_script), str(self.test_dir), "--fix"], capture_output=True, text=True)
        self.assertEqual(res_fix.returncode, 0, f"--fix should resolve installed-base pack refs: {res_fix.stdout}")
        self.assertTrue((self.test_dir / ".claude" / "rules" / "missing-rule.md").exists())
        self.assertTrue((self.test_dir / ".claude" / "skills" / "missing-skill" / "SKILL.md").exists())
        self.assertTrue((self.test_dir / ".grok" / "commands" / "missing-workflow.md").exists())
        self.assertFalse((self.test_dir / "rules" / "missing-rule.md").exists())
        self.assertFalse((self.test_dir / "skills" / "missing-skill").exists())
        self.assertFalse((self.test_dir / "workflows" / "missing-workflow.md").exists())


if __name__ == "__main__":
    unittest.main()
