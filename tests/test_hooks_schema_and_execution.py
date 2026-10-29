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

from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_HOOKS_JSON = REPO_ROOT / "hooks.json"
PLUGINS_DIR = REPO_ROOT / "plugins"

PRE_TOOL_SCRIPT = REPO_ROOT / "skills" / "wf-code-graph" / "scripts" / "pre_tool_hook.py"
POST_TOOL_SCRIPT = REPO_ROOT / "skills" / "wf-post-code-review" / "scripts" / "post_tool_hook.py"


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

    def _create_consumer_tree(self, ws_root: Path) -> Tuple[Path, Path, Path]:
        """Create pure consumer workspace layout without root skills directory."""
        import shutil
        cg_scripts = ws_root / ".agents" / "skills" / "wf-code-graph" / "scripts"
        pcr_scripts = ws_root / ".agents" / "skills" / "wf-post-code-review" / "scripts"
        cg_scripts.mkdir(parents=True)
        pcr_scripts.mkdir(parents=True)
        for s in ["pre_tool_hook.py", "graph_indexer.py", "pre_impact_analyzer.py"]:
            shutil.copy2(REPO_ROOT / "skills" / "wf-code-graph" / "scripts" / s, cg_scripts / s)
        for s in ["post_tool_hook.py", "post_code_reviewer.py"]:
            shutil.copy2(REPO_ROOT / "skills" / "wf-post-code-review" / "scripts" / s, pcr_scripts / s)
        sample_py = ws_root / "calc.py"
        sample_py.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=ws_root, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=ws_root, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws_root, capture_output=True, check=True)
        return cg_scripts, pcr_scripts, sample_py

    def _verify_pre_hook_cmd(self, cmd: str, ws_root: Path, sample_py: Path) -> None:
        """Verify pre-tool hook execution in consumer directory."""
        payload = json.dumps({
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": str(sample_py)}},
            "workspacePaths": [str(ws_root)],
        })
        proc = subprocess.run(cmd, shell=True, input=payload, capture_output=True, text=True, timeout=30, cwd=ws_root)
        self.assertEqual(proc.returncode, 0, f"PreToolUse failed: {proc.stderr}")
        self.assertEqual(json.loads(proc.stdout.strip()), {"decision": "allow"})

    def _verify_post_hook_cmd(self, cmd: str, ws_root: Path, sample_py: Path) -> None:
        """Verify post-tool hook execution in consumer directory."""
        payload = json.dumps({
            "toolUse": {"name": "write_to_file", "args": {"TargetFile": str(sample_py)}},
            "workspacePaths": [str(ws_root)],
        })
        proc = subprocess.run(cmd, shell=True, input=payload, capture_output=True, text=True, timeout=30, cwd=ws_root)
        self.assertEqual(proc.returncode, 0, f"PostToolUse failed: {proc.stderr}")
        self.assertEqual(json.loads(proc.stdout.strip()), {})

    def _verify_external_cwd_hook(self, pcr_scripts: Path, ws_root: Path, sample_py: Path) -> None:
        """Verify post-tool hook execution when cwd is outside consumer root."""
        import tempfile
        payload = json.dumps({
            "toolUse": {"name": "write_to_file", "args": {"TargetFile": str(sample_py)}},
            "workspacePaths": [str(ws_root)],
        })
        with tempfile.TemporaryDirectory() as external_cwd:
            proc = subprocess.run(
                [sys.executable, str(pcr_scripts / "post_tool_hook.py")],
                input=payload,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=external_cwd,
            )
            self.assertEqual(proc.returncode, 0, f"post_tool_hook failed: {proc.stderr}")
            self.assertEqual(json.loads(proc.stdout.strip()), {})

    def test_hook_commands_in_pure_consumer_workspace_topology(self):
        """Verify hook execution in simulated consumer workspace with only .agents/."""
        import tempfile
        hooks_file = PLUGINS_DIR / "wf-programming-plugin" / "hooks.json"
        with open(hooks_file, "r", encoding="utf-8") as f:
            hooks_cfg = json.load(f)["wf-programming"]
        pre_cmd = hooks_cfg["PreToolUse"][0]["hooks"][0]["command"]
        post_cmd = hooks_cfg["PostToolUse"][0]["hooks"][0]["command"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            ws_root = Path(tmp_dir)
            _, pcr_scripts, sample_py = self._create_consumer_tree(ws_root)
            self.assertFalse((ws_root / "skills").exists())
            self._verify_pre_hook_cmd(pre_cmd, ws_root, sample_py)
            self._verify_post_hook_cmd(post_cmd, ws_root, sample_py)
            self._verify_external_cwd_hook(pcr_scripts, ws_root, sample_py)

    def test_claude_and_grok_tool_input_and_python_only_fallback(self):
        """Claude/Grok tool_input + cwd payloads index code-graph, and compiled hooks fall back to python when python3 is absent."""
        import shutil
        import tempfile

        sys.path.insert(0, str(REPO_ROOT / "skills" / "wf-management" / "scripts"))
        import compile_assets as ca

        profiles = ca.load_host_profiles(str(REPO_ROOT))
        with tempfile.TemporaryDirectory() as tmp_ws, tempfile.TemporaryDirectory() as tmp_bin, tempfile.TemporaryDirectory() as ext_cwd:
            ws_root = Path(tmp_ws) / "space in path"
            ws_root.mkdir(parents=True)
            cg_dir = ws_root / ".claude" / "skills" / "wf-code-graph" / "scripts"
            pcr_dir = ws_root / ".claude" / "skills" / "wf-post-code-review" / "scripts"
            iv_dir = ws_root / ".claude" / "skills" / "wf-management" / "scripts"
            for d in (cg_dir, pcr_dir, iv_dir):
                d.mkdir(parents=True)
            for s in ("pre_tool_hook.py", "graph_indexer.py", "pre_impact_analyzer.py"):
                shutil.copy2(REPO_ROOT / "skills" / "wf-code-graph" / "scripts" / s, cg_dir / s)
            for s in ("post_tool_hook.py", "post_code_reviewer.py"):
                shutil.copy2(REPO_ROOT / "skills" / "wf-post-code-review" / "scripts" / s, pcr_dir / s)
            shutil.copy2(REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate-references.py", iv_dir / "validate-references.py")

            calc_py = ws_root / "calc.py"
            caller_py = ws_root / "caller.py"
            calc_py.write_text("def compute_total(x: int) -> int:\n    return x * 2\n", encoding="utf-8")
            caller_py.write_text("from calc import compute_total\n\ndef run() -> int:\n    return compute_total(5)\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=ws_root, capture_output=True, check=True)

            claude_payload = json.dumps({
                "cwd": str(ws_root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(calc_py)},
            })
            res_pre = subprocess.run(
                [sys.executable, str(cg_dir / "pre_tool_hook.py")],
                input=claude_payload,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=ext_cwd,
            )
            self.assertEqual(res_pre.returncode, 0, res_pre.stderr)
            self.assertTrue((ws_root / "workforces" / "code-graph.json").is_file(), "Expected code-graph.json from Claude tool_input payload")
            self.assertIn("compute_total", res_pre.stderr)
            pre_stdout_obj = json.loads(res_pre.stdout.strip())
            self.assertNotIn("decision", pre_stdout_obj, "Claude PreToolUse must not emit deprecated top-level decision key")

            # Build a PATH directory with ONLY `python` (and basic POSIX sh utilities), NO `python3`
            os.symlink(sys.executable, Path(tmp_bin) / "python")
            env_no_py3 = dict(os.environ)
            env_no_py3["PATH"] = f"{tmp_bin}:/bin:/usr/bin"
            # Ensure /bin and /usr/bin don't shadow missing python3 if /usr/bin/python3 exists on macOS:
            if Path("/usr/bin/python3").exists():
                for util in ("sh", "env"):
                    for cand_dir in ("/bin", "/usr/bin"):
                        src_u = Path(cand_dir) / util
                        if src_u.exists() and not (Path(tmp_bin) / util).exists():
                            os.symlink(src_u, Path(tmp_bin) / util)
                env_no_py3["PATH"] = str(tmp_bin)

            prog_meta = json.loads((REPO_ROOT / "plugins" / "wf-programming-plugin" / "plugin.json").read_text(encoding="utf-8"))
            int_meta = json.loads((REPO_ROOT / "plugins" / "wf-integrity-plugin" / "plugin.json").read_text(encoding="utf-8"))
            claude_prog = ca.compile_plugin_hooks_for_host(prog_meta, profiles["claude"])
            claude_int = ca.compile_plugin_hooks_for_host(int_meta, profiles["claude"])

            pre_cmd = claude_prog["PreToolUse"][0]["hooks"][0]["command"]
            post_cmd = claude_prog["PostToolUse"][0]["hooks"][0]["command"]
            int_cmd = claude_int["PostToolUse"][0]["hooks"][0]["command"]

            sh_bin = str(Path(tmp_bin) / "sh") if (Path(tmp_bin) / "sh").exists() else "/bin/sh"
            for cmd, stdin_data in (
                (pre_cmd, claude_payload),
                (post_cmd, claude_payload),
                (int_cmd, claude_payload),
                (int_cmd, "{malformed-json-starting-with-brace"),
            ):
                proc = subprocess.run(
                    [sh_bin, "-c", cmd],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=ws_root,
                    env=env_no_py3,
                )
                self.assertEqual(proc.returncode, 0, f"Hook failed without python3 ({cmd}): {proc.stderr}")
                self.assertIsInstance(json.loads(proc.stdout.strip()), dict)


if __name__ == "__main__":
    unittest.main()

