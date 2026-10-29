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
SCRIPTS_DIR = REPO_ROOT / "skills" / "wf-management" / "scripts"
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
        hooks_path = self.target_path / ".agents" / "plugins" / "wf-programming-plugin" / "hooks.json"
        self.assertTrue(
            hooks_path.is_file(),
            f"Expected wf-programming-plugin/hooks.json to exist at {hooks_path}",
        )
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks_data = json.load(f)
        self.assertIsInstance(hooks_data, dict)
        self.assertIn("wf-programming", hooks_data)

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
        hooks_file = self.target_path / ".agents" / "plugins" / "wf-programming-plugin" / "hooks.json"
        self.assertTrue(hooks_file.is_file())

    def test_setup_multi_host_all_five_and_validators_pass(self):
        """setup.sh --hosts all compiles native assets, hooks, root docs, config.json, and passes validators."""
        validate_py = SCRIPTS_DIR / "validate.py"
        validate_refs_py = SCRIPTS_DIR / "validate-references.py"

        res = subprocess.run(
            [
                "bash",
                str(SETUP_SCRIPT),
                str(self.target_path),
                "--type",
                "project",
                "--hosts",
                "all",
                "--teams",
                "dev,marketing",
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 0, f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")

        cfg_path = self.target_path / "workforces" / "config.json"
        self.assertTrue(cfg_path.is_file(), "Expected workforces/config.json to be written")
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        expected_hosts = ["antigravity", "claude", "grok", "copilot", "cursor"]
        self.assertEqual(cfg["hosts"], expected_hosts)
        self.assertEqual(cfg["repo_type"], "project")
        self.assertEqual(cfg["installed_teams"], ["dev", "marketing"])
        self.assertTrue(cfg["auto_detect_hosts"])

        manifest = json.loads((self.target_path / "workforces" / ".manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["hosts"], expected_hosts)
        self.assertIn(".github/agents/wf-programmer.agent.md", manifest["installed_files"])
        self.assertIn(".github/instructions/wf-base.instructions.md", manifest["installed_files"])
        self.assertIn(".cursor/rules/wf-base.mdc", manifest["installed_files"])
        self.assertIn(".grok/hooks.json", manifest["installed_files"])
        self.assertNotIn(".claude/settings.json", manifest["installed_files"])

        # Host-native frontmatter & hooks checks (not raw Antigravity copies)
        claude_prog = (self.target_path / ".claude" / "agents" / "wf-programmer.md").read_text(encoding="utf-8")
        self.assertIn("- MultiEdit", claude_prog)
        self.assertNotIn("view_file", claude_prog)
        self.assertNotIn("mainAgent:", claude_prog)
        claude_settings = json.loads((self.target_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Write|Edit|MultiEdit", json.dumps(claude_settings["hooks"]))

        copilot_prog = (self.target_path / ".github" / "agents" / "wf-programmer.agent.md").read_text(encoding="utf-8")
        self.assertIn("user-invocable: true", copilot_prog)
        copilot_base = (self.target_path / ".github" / "instructions" / "wf-base.instructions.md").read_text(encoding="utf-8")
        self.assertIn('applyTo: "**"', copilot_base)
        self.assertIn("(wf-git-workflow.instructions.md)", copilot_base)

        cursor_base = (self.target_path / ".cursor" / "rules" / "wf-base.mdc").read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", cursor_base)
        self.assertIn("(wf-git-workflow.mdc)", cursor_base)

        # Root context docs created for all active hosts; .vscode/settings.json omitted without .vscode or vscode alias
        for doc_rel in ("GEMINI.md", "CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md"):
            self.assertTrue((self.target_path / doc_rel).is_file(), f"Missing root doc {doc_rel}")
        self.assertFalse((self.target_path / ".vscode" / "settings.json").exists())

        val_res = subprocess.run(
            [sys.executable, str(validate_py), str(self.target_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(val_res.returncode, 0, val_res.stdout + val_res.stderr)

        ref_res = subprocess.run(
            [sys.executable, str(validate_refs_py), str(self.target_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(ref_res.returncode, 0, ref_res.stdout + ref_res.stderr)

    def test_setup_aliases_vscode_settings_no_autodetect_and_interactive_prompt(self):
        """setup.sh handles vscode alias, pre-existing .vscode, --no-auto-detect, invalid hosts, and interactive choice."""
        # 1. Pre-existing .vscode triggers copilot auto-detection + .vscode/settings.json pointing to .github/copilot-instructions.md
        ws_vsc = self.target_path / "ws_vscode_dir"
        (ws_vsc / ".vscode").mkdir(parents=True)
        res_vsc = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(ws_vsc), "--teams", "none", "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_vsc.returncode, 0, res_vsc.stdout + res_vsc.stderr)
        vsc_settings = json.loads((ws_vsc / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(
            vsc_settings["github.copilot.chat.codeGeneration.instructions"][0]["file"],
            ".github/copilot-instructions.md",
        )
        self.assertTrue((ws_vsc / ".github" / "copilot-instructions.md").is_file())

        # 2. --hosts gemini,claude --no-auto-detect ignores pre-existing .cursor
        ws_pin = self.target_path / "ws_pinned"
        (ws_pin / ".cursor").mkdir(parents=True)
        res_pin = subprocess.run(
            [
                "bash",
                str(SETUP_SCRIPT),
                str(ws_pin),
                "--hosts",
                "gemini,claude",
                "--no-auto-detect",
                "--teams",
                "none",
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_pin.returncode, 0, res_pin.stdout + res_pin.stderr)
        pin_cfg = json.loads((ws_pin / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(pin_cfg["hosts"], ["antigravity", "claude"])
        self.assertFalse(pin_cfg["auto_detect_hosts"])
        self.assertFalse((ws_pin / ".cursor" / "rules").exists())

        # 3. Interactive greenfield multi-host selection (2=claude, 5=cursor)
        ws_int = self.target_path / "ws_interactive"
        ws_int.mkdir(parents=True)
        res_int = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(ws_int), "--teams", "none"],
            input="n\n2\n2,5\n",
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_int.returncode, 0, res_int.stdout + res_int.stderr)
        int_cfg = json.loads((ws_int / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(int_cfg["hosts"], ["claude", "cursor"])
        self.assertFalse((ws_int / ".agents").exists())
        self.assertTrue((ws_int / "CLAUDE.md").is_file())
        self.assertTrue((ws_int / "AGENTS.md").is_file())

        # 4. Invalid --hosts exits non-zero cleanly
        res_bad = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(ws_int), "--hosts", "nonexistent-ai", "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        self.assertNotEqual(res_bad.returncode, 0)

    def test_update_autodetects_new_host_dirs_even_at_matching_version_hash(self):
        """Adding .claude/ and .cursor/ to an up-to-date repo triggers compilation on update.sh without --force."""
        res_setup = subprocess.run(
            [
                "bash",
                str(SETUP_SCRIPT),
                str(self.target_path),
                "--hosts",
                "antigravity",
                "--teams",
                "dev",
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_setup.returncode, 0, res_setup.stderr)

        # Confirm immediate update is a no-op ("already up to date")
        res_noop = subprocess.run(
            ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_noop.returncode, 0, res_noop.stderr)
        self.assertIn("already up to date", res_noop.stdout)

        # User adds .claude/ and .cursor/ directories, then runs update.sh WITHOUT --force
        (self.target_path / ".claude").mkdir()
        (self.target_path / ".cursor").mkdir()
        res_expand = subprocess.run(
            ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_expand.returncode, 0, res_expand.stdout + res_expand.stderr)
        self.assertTrue((self.target_path / ".claude" / "agents" / "wf-programmer.md").is_file())
        self.assertTrue((self.target_path / ".claude" / "settings.json").is_file())
        self.assertTrue((self.target_path / ".cursor" / "rules" / "wf-base.mdc").is_file())
        self.assertTrue((self.target_path / "CLAUDE.md").is_file())
        self.assertTrue((self.target_path / "AGENTS.md").is_file())

        cfg = json.loads((self.target_path / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["hosts"], ["antigravity", "claude", "cursor"])
        manifest = json.loads((self.target_path / "workforces" / ".manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["hosts"], ["antigravity", "claude", "cursor"])

        # --no-auto-detect on update.sh ignores a newly added .grok/agents marker
        (self.target_path / ".grok" / "agents").mkdir(parents=True)
        res_pinned = subprocess.run(
            ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--no-auto-detect", "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_pinned.returncode, 0, res_pinned.stderr)
        self.assertFalse((self.target_path / ".grok" / "rules").exists())

    def test_update_brownfield_legacy_copilot_to_github_migration(self):
        """update.sh migrates legacy .github/copilot/ workspace to .github/ native layout and preserves custom files."""
        legacy_base = self.target_path / ".github" / "copilot"
        for sub in ("agents", "rules", "skills/clean-coder", "plugins/workforce-programming-plugin", "workflows"):
            (legacy_base / sub).mkdir(parents=True, exist_ok=True)
        (legacy_base / "agents" / "programmer.md").write_text("# Old\n", encoding="utf-8")
        (legacy_base / "agents" / "wf-programmer.md").write_text("# Old WF\n", encoding="utf-8")
        (legacy_base / "agents" / "my-custom-bot.md").write_text("---\nname: my-custom-bot\ndescription: Custom\n---\n# Custom\n", encoding="utf-8")
        (legacy_base / "rules" / "base.md").write_text("# Old Rule\n", encoding="utf-8")
        (legacy_base / "skills" / "clean-coder" / "SKILL.md").write_text("# Old Skill\n", encoding="utf-8")
        (legacy_base / "plugins" / "workforce-programming-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        (legacy_base / "workflows" / "wf-plan.md").write_text("# Old Flow\n", encoding="utf-8")
        (legacy_base / "instructions.md").write_text(
            "# VS Code Copilot Instructions\n\nCustom user header.\nRefer to `.github/copilot/rules/base.md` and `.github/copilot/agents/`.\n",
            encoding="utf-8",
        )
        (self.target_path / ".vscode").mkdir(parents=True)
        (self.target_path / ".vscode" / "settings.json").write_text(
            json.dumps({"github.copilot.chat.codeGeneration.instructions": [{"file": ".github/copilot/instructions.md"}]}),
            encoding="utf-8",
        )
        (self.target_path / "workforces").mkdir(parents=True)
        (self.target_path / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n",
            encoding="utf-8",
        )

        res = subprocess.run(
            ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--non-interactive", "--force"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

        # Legacy Workforces Copilot files pruned; custom user bot preserved
        self.assertFalse((legacy_base / "agents" / "programmer.md").exists())
        self.assertFalse((legacy_base / "agents" / "wf-programmer.md").exists())
        self.assertFalse((legacy_base / "rules").exists())
        self.assertFalse((legacy_base / "skills").exists())
        self.assertFalse((legacy_base / "plugins").exists())
        self.assertFalse((legacy_base / "workflows").exists())
        self.assertTrue((legacy_base / "agents" / "my-custom-bot.md").is_file())

        # Native .github/ compiled files created
        self.assertTrue((self.target_path / ".github" / "agents" / "wf-programmer.agent.md").is_file())
        self.assertTrue((self.target_path / ".github" / "instructions" / "wf-base.instructions.md").is_file())
        self.assertTrue((self.target_path / ".github" / "skills" / "wf-clean-coder" / "SKILL.md").is_file())
        self.assertTrue((self.target_path / ".github" / "copilot" / "teams" / "dev" / "pack.json").is_file())

        # Instructions & .vscode/settings.json migrated cleanly
        cp_inst = self.target_path / ".github" / "copilot-instructions.md"
        self.assertTrue(cp_inst.is_file())
        cp_text = cp_inst.read_text(encoding="utf-8")
        self.assertIn("Custom user header.", cp_text)
        self.assertIn(".github/instructions/wf-base.instructions.md", cp_text)
        self.assertNotIn("rules/base.md", cp_text)
        self.assertFalse((legacy_base / "instructions.md").exists())

        vsc_text = (self.target_path / ".vscode" / "settings.json").read_text(encoding="utf-8")
        self.assertIn(".github/copilot-instructions.md", vsc_text)
        self.assertNotIn(".github/copilot/instructions.md", vsc_text)

        # Both validators pass cleanly on the migrated workspace
        for script_name in ("validate.py", "validate-references.py"):
            vres = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / script_name), str(self.target_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(vres.returncode, 0, f"{script_name} failed:\n{vres.stdout}\n{vres.stderr}")

    def test_update_preserves_pinned_auto_detect_false_until_hosts_auto(self):
        """update.sh --force preserves auto_detect_hosts=false until --hosts auto re-enables it."""
        (self.target_path / ".cursor").mkdir()
        s_cmd = ["bash", str(SETUP_SCRIPT), str(self.target_path), "--hosts", "claude", "--no-auto-detect", "--teams", "none", "--non-interactive"]
        self.assertEqual(subprocess.run(s_cmd, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT).returncode, 0)
        u_force = ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--force", "--non-interactive"]
        self.assertEqual(subprocess.run(u_force, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT).returncode, 0)
        cfg1 = json.loads((self.target_path / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertFalse(cfg1["auto_detect_hosts"])
        self.assertEqual(cfg1["hosts"], ["claude"])
        self.assertFalse((self.target_path / ".cursor" / "rules" / "wf-base.mdc").exists())

        u_auto = ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--hosts=auto", "--non-interactive"]
        self.assertEqual(subprocess.run(u_auto, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT).returncode, 0)
        cfg2 = json.loads((self.target_path / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertTrue(cfg2["auto_detect_hosts"])
        self.assertEqual(cfg2["hosts"], ["claude", "cursor"])
        self.assertTrue((self.target_path / ".cursor" / "rules" / "wf-base.mdc").is_file())

        u_pin = ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--no-auto-detect", "--non-interactive"]
        self.assertEqual(subprocess.run(u_pin, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT).returncode, 0)
        cfg3 = json.loads((self.target_path / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertFalse(cfg3["auto_detect_hosts"])

    def test_setup_rerun_prunes_removed_teams_and_syncs_workrules(self):
        """Re-running setup.sh with changed --teams prunes deactivated team files and updates workrules.md."""
        for teams_val in ("none", "dev", "marketing"):
            cmd = ["bash", str(SETUP_SCRIPT), str(self.target_path), "--hosts", "claude", "--teams", teams_val, "--non-interactive"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertFalse((self.target_path / ".claude" / "agents" / "wf-programmer.md").exists())
        self.assertTrue((self.target_path / ".claude" / "agents" / "wf-marketer.md").is_file())
        wr_head = (self.target_path / "workforces" / "workrules.md").read_text(encoding="utf-8").split("## GitHub")[0]
        self.assertIn("  - marketing", wr_head)
        self.assertNotIn("  - dev", wr_head)
        self.assertNotIn("[]", wr_head)

    def test_update_creates_vscode_settings_and_handles_bracket_paths_and_bad_flags(self):
        """Bracketed paths, --hosts=copilot, post-setup .vscode/ detection, and non-zero unknown flags work."""
        ws = self.target_path / "client [v1] app"
        ws.mkdir(parents=True)
        res_s = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(ws), "--hosts=copilot", "--teams=none", "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_s.returncode, 0, res_s.stdout + res_s.stderr)
        self.assertFalse((ws / ".vscode" / "settings.json").exists())
        (ws / ".vscode").mkdir()
        res_u = subprocess.run(
            ["bash", str(UPDATE_SCRIPT), str(ws), "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_u.returncode, 0, res_u.stdout + res_u.stderr)
        self.assertTrue((ws / ".vscode" / "settings.json").is_file())
        bad_s = subprocess.run(["bash", str(SETUP_SCRIPT), str(ws), "--bogus"], capture_output=True, text=True, timeout=20)
        bad_u = subprocess.run(["bash", str(UPDATE_SCRIPT), str(ws), "--bogus"], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(bad_s.returncode, 0)
        self.assertNotEqual(bad_u.returncode, 0)

    def test_update_and_setup_preserve_existing_workforce_repo_type(self):
        """Legacy workrules.md (- type: workforce) and re-running setup.sh without --type preserve repo_type=workforce."""
        wf_dir = self.target_path / "workforces"
        wf_dir.mkdir(parents=True)
        (self.target_path / ".agents").mkdir(parents=True)
        (wf_dir / "workrules.md").write_text(
            "# Work Rules\n\n## Type\n- type: workforce\n\n## Installed Teams\n- installed_teams:\n  - dev\n",
            encoding="utf-8",
        )
        res_u = subprocess.run(
            ["bash", str(UPDATE_SCRIPT), str(self.target_path), "--force", "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_u.returncode, 0, res_u.stdout + res_u.stderr)
        cfg = json.loads((wf_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["repo_type"], "workforce")

        res_s = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(self.target_path), "--teams", "dev,marketing", "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_s.returncode, 0, res_s.stdout + res_s.stderr)
        cfg2 = json.loads((wf_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg2["repo_type"], "workforce")
        self.assertIn("- type: workforce", (wf_dir / "workrules.md").read_text(encoding="utf-8"))

    def test_setup_dry_run_count_parity_and_personal_repo_type(self):
        """setup.sh --dry Simulated file count matches live Compiled count, and repo_type='personal' is accepted."""
        import re

        dry_ws = self.target_path / "dry_parity"
        dry_ws.mkdir(parents=True)
        res_dry = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(dry_ws), "--hosts", "claude,cursor", "--teams", "dev", "--dry", "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_dry.returncode, 0, res_dry.stdout + res_dry.stderr)
        res_live = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(dry_ws), "--hosts", "claude,cursor", "--teams", "dev", "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_live.returncode, 0, res_live.stdout + res_live.stderr)
        dry_clean = re.sub(r"\x1b\[[0-9;]*m", "", res_dry.stdout)
        live_clean = re.sub(r"\x1b\[[0-9;]*m", "", res_live.stdout)
        m_dry = re.search(r"Simulated:\s*(\d+)\s+files to compile", dry_clean)
        m_live = re.search(r"Compiled:\s*(\d+)\s+files", live_clean)
        self.assertIsNotNone(m_dry, dry_clean)
        self.assertIsNotNone(m_live, live_clean)
        self.assertEqual(int(m_dry.group(1)), int(m_live.group(1)))

        pers_ws = self.target_path / "personal_ws"
        (pers_ws / "workforces").mkdir(parents=True)
        (pers_ws / "workforces" / "config.json").write_text(
            json.dumps({"hosts": ["claude"], "repo_type": "personal", "installed_teams": ["dev"]}),
            encoding="utf-8",
        )
        res_pers = subprocess.run(
            ["bash", str(SETUP_SCRIPT), str(pers_ws), "--teams", "dev", "--non-interactive"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        self.assertEqual(res_pers.returncode, 0, res_pers.stdout + res_pers.stderr)
        pers_cfg = json.loads((pers_ws / "workforces" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(pers_cfg["repo_type"], "personal")


if __name__ == "__main__":
    unittest.main()




