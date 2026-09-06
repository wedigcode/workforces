#!/usr/bin/env python3
"""
Test Suite: Lifecycle Hooks Schema & Script Execution
Validates JSON syntax, schema compliance of root hooks.json and plugins/*/hooks.json,
and executes pre_tool_hook.py and post_tool_hook.py with mock payloads on stdin.
"""

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_HOOKS_JSON = REPO_ROOT / "hooks.json"
PLUGINS_DIR = REPO_ROOT / "plugins"

PRE_TOOL_SCRIPT = REPO_ROOT / "skills" / "code-graph" / "scripts" / "pre_tool_hook.py"
POST_TOOL_SCRIPT = REPO_ROOT / "skills" / "post-code-review" / "scripts" / "post_tool_hook.py"


class TestHooksSchema(unittest.TestCase):
    """Verifies syntax and structure of hooks.json definitions."""

    def setUp(self):
        self.hook_files = list(PLUGINS_DIR.glob("**/hooks*.json"))
        if ROOT_HOOKS_JSON.is_file():
            self.hook_files.append(ROOT_HOOKS_JSON)
        self.assertGreater(len(self.hook_files), 0, "No hooks.json files found under plugins/")

    def _validate_hook_file(self, hook_path: Path):
        """Helper to assert schema of an individual hooks.json file."""
        with open(hook_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as err:
                self.fail(f"Invalid JSON in {hook_path}: {err}")

        self.assertIsInstance(
            data,
            dict,
            f"Top-level structure in {hook_path} must be an object keyed by hook name",
        )
        self.assertGreater(
            len(data),
            0,
            f"Hook file {hook_path} cannot be empty",
        )

        for hook_name, hook_def in data.items():
            self.assertIsInstance(
                hook_def,
                dict,
                f"Hook definition '{hook_name}' in {hook_path} must be an object",
            )
            has_valid_event = any(k in hook_def for k in ("PreToolUse", "PostToolUse"))
            self.assertTrue(
                has_valid_event,
                f"Hook '{hook_name}' in {hook_path} must contain 'PreToolUse' and/or 'PostToolUse'",
            )

            for phase in ("PreToolUse", "PostToolUse"):
                if phase in hook_def:
                    phase_rules = hook_def[phase]
                    self.assertIsInstance(
                        phase_rules,
                        list,
                        f"Phase '{phase}' in '{hook_name}' must be a list of rule objects",
                    )
                    for rule in phase_rules:
                        self.assertIn(
                            "matcher",
                            rule,
                            f"Missing 'matcher' in rule under '{hook_name}.{phase}' in {hook_path}",
                        )
                        matcher = rule["matcher"]
                        self.assertIsInstance(matcher, str)

                        # Matcher must be either wildcard '*' or compile as valid regex
                        if matcher != "*":
                            try:
                                re.compile(matcher)
                            except re.error as err:
                                self.fail(
                                    f"Invalid regex matcher '{matcher}' in {hook_path}: {err}"
                                )

                        self.assertIn(
                            "hooks",
                            rule,
                            f"Missing 'hooks' list in rule under '{hook_name}.{phase}' in {hook_path}",
                        )
                        hooks_list = rule["hooks"]
                        self.assertIsInstance(hooks_list, list)
                        self.assertGreater(len(hooks_list), 0)

                        for hook_action in hooks_list:
                            self.assertIsInstance(hook_action, dict)
                            self.assertEqual(
                                hook_action.get("type"),
                                "command",
                                f"Hook action must have type 'command' in {hook_path}",
                            )
                            cmd = hook_action.get("command")
                            self.assertIsInstance(cmd, str)
                            self.assertTrue(
                                cmd.strip(),
                                f"Empty command in hook action in {hook_path}",
                            )
                            if "timeout" in hook_action:
                                self.assertIsInstance(
                                    hook_action["timeout"],
                                    (int, float),
                                    f"Timeout must be numeric in {hook_path}",
                                )

    def test_root_hooks_json_schema(self):
        """Assert root hooks.json has valid JSON syntax and conforms to Antigravity hook schema if present."""
        if ROOT_HOOKS_JSON.is_file():
            self._validate_hook_file(ROOT_HOOKS_JSON)

    def test_all_plugin_hooks_json_schema(self):
        """Assert all hooks.json in plugins/ have valid JSON syntax and conform to hook schema."""
        plugin_hook_files = list(PLUGINS_DIR.glob("**/hooks*.json"))
        self.assertGreater(
            len(plugin_hook_files),
            0,
            "No hook files found under plugins/",
        )
        for ph in plugin_hook_files:
            with self.subTest(file=ph.relative_to(REPO_ROOT)):
                self._validate_hook_file(ph)


class TestHookScriptsExecution(unittest.TestCase):
    """Verifies execution of pre_tool_hook.py and post_tool_hook.py via stdin/stdout."""

    def test_pre_tool_hook_execution_valid_input(self):
        """Verify pre_tool_hook.py processes valid toolCall JSON, emits {"decision": "allow"} and exits 0."""
        self.assertTrue(PRE_TOOL_SCRIPT.is_file(), f"Missing {PRE_TOOL_SCRIPT}")

        payload = json.dumps({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "tests/test_dummy.py",
                    "CodeContent": "# dummy test code",
                },
            },
            "workspacePaths": [str(REPO_ROOT)],
        })

        proc = subprocess.run(
            [sys.executable, str(PRE_TOOL_SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            proc.returncode,
            0,
            f"pre_tool_hook.py failed with returncode {proc.returncode}. Stderr: {proc.stderr}",
        )
        out = proc.stdout.strip()
        try:
            parsed_out = json.loads(out)
        except json.JSONDecodeError:
            self.fail(f"pre_tool_hook.py did not emit valid JSON on stdout: '{out}'")

        self.assertEqual(
            parsed_out,
            {"decision": "allow"},
            f"Expected {{'decision': 'allow'}}, got: {parsed_out}",
        )

    def test_pre_tool_hook_execution_empty_and_malformed_input(self):
        """Verify pre_tool_hook.py handles empty or malformed stdin gracefully without failing."""
        for invalid_input in ("", "   \n  ", "not-a-valid-json-string {"):
            with self.subTest(input_sample=invalid_input):
                proc = subprocess.run(
                    [sys.executable, str(PRE_TOOL_SCRIPT)],
                    input=invalid_input,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=REPO_ROOT,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"pre_tool_hook.py crashed on invalid stdin: {proc.stderr}",
                )
                out = proc.stdout.strip()
                parsed_out = json.loads(out)
                self.assertEqual(parsed_out, {"decision": "allow"})

    def test_post_tool_hook_execution_valid_input(self):
        """Verify post_tool_hook.py processes valid toolUse JSON, emits {} and exits 0."""
        self.assertTrue(POST_TOOL_SCRIPT.is_file(), f"Missing {POST_TOOL_SCRIPT}")

        payload = json.dumps({
            "toolUse": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "tests/test_dummy.py",
                },
            },
            "workspacePaths": [str(REPO_ROOT)],
        })

        proc = subprocess.run(
            [sys.executable, str(POST_TOOL_SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            proc.returncode,
            0,
            f"post_tool_hook.py failed with returncode {proc.returncode}. Stderr: {proc.stderr}",
        )
        out = proc.stdout.strip()
        try:
            parsed_out = json.loads(out)
        except json.JSONDecodeError:
            self.fail(f"post_tool_hook.py did not emit valid JSON on stdout: '{out}'")

        self.assertEqual(
            parsed_out,
            {},
            f"Expected empty JSON object {{}}, got: {parsed_out}",
        )

    def test_post_tool_hook_execution_empty_and_malformed_input(self):
        """Verify post_tool_hook.py handles empty or malformed stdin gracefully without failing."""
        for invalid_input in ("", "   \n  ", "not-a-valid-json-string {"):
            with self.subTest(input_sample=invalid_input):
                proc = subprocess.run(
                    [sys.executable, str(POST_TOOL_SCRIPT)],
                    input=invalid_input,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=REPO_ROOT,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"post_tool_hook.py crashed on invalid stdin: {proc.stderr}",
                )
                out = proc.stdout.strip()
                parsed_out = json.loads(out)
                self.assertEqual(parsed_out, {})


if __name__ == "__main__":
    unittest.main()
