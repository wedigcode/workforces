#!/usr/bin/env python3
"""
TDD Unit & Integration Suite: Multi-AI Frontmatter Compiler & Host Mapper
Tests canonical sidecar JSON compilation, capability-to-tool mapping, host-specific
overrides, relative link extension rewriting, non-destructive Claude settings.json
hook merging, multi-host auto-detection, and persistent workforces/config.json state.
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "wf-management" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import compile_assets as ca  # noqa: E402


def _parse_simple_fm(text: str):
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if not match:
        return None
    return match.group(1)


class TestMultiHostCompiler(unittest.TestCase):
    """Verifies compile_assets.py across Antigravity, Claude, Grok, Copilot, and Cursor."""

    def setUp(self):
        self.profiles = ca.load_host_profiles(str(REPO_ROOT))
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_all_five_host_profiles_and_aliases(self):
        """All 5 AI host profiles load and resolve aliases accurately."""
        for expected in ("antigravity", "claude", "grok", "copilot", "cursor"):
            self.assertIn(expected, self.profiles)
        self.assertEqual(ca.resolve_host_alias("gemini", self.profiles), "antigravity")
        self.assertEqual(ca.resolve_host_alias("vscode", self.profiles), "copilot")
        self.assertEqual(ca.resolve_host_alias("github-copilot", self.profiles), "copilot")
        self.assertEqual(ca.resolve_host_alias("claude-code", self.profiles), "claude")
        self.assertEqual(ca.resolve_host_alias("grok-build", self.profiles), "grok")
        self.assertIsNone(ca.resolve_host_alias("nonexistent-ai", self.profiles))

    def test_agent_capability_and_trait_compilation_across_hosts(self):
        """Capabilities and background_only compile into each AI's native schema without leaking."""
        designer = json.loads((REPO_ROOT / "agents" / "wf-designer.json").read_text(encoding="utf-8"))
        scribe = json.loads((REPO_ROOT / "agents" / "wf-scribe.json").read_text(encoding="utf-8"))

        # 1. Antigravity: includes generate_image on designer, mainAgent=False on scribe
        ag_des = ca.compile_agent_frontmatter(designer, self.profiles["antigravity"])
        self.assertIn("generate_image", ag_des["tools"])
        self.assertTrue(ag_des["mainAgent"])
        self.assertEqual(ag_des["commandExecutionPolicy"], "sandbox")
        ag_scr = ca.compile_agent_frontmatter(scribe, self.profiles["antigravity"])
        self.assertFalse(ag_scr["mainAgent"])
        self.assertTrue(ag_scr["subagent"])

        # 2. Claude: maps to Read/Write/Edit/MultiEdit/Bash/Task, omits unsupported image tool, no mainAgent
        cl_des = ca.compile_agent_frontmatter(designer, self.profiles["claude"])
        self.assertIn("Read", cl_des["tools"])
        self.assertIn("MultiEdit", cl_des["tools"])
        self.assertIn("Task", cl_des["tools"])
        self.assertNotIn("generate_image", cl_des["tools"])
        self.assertNotIn("mainAgent", cl_des)
        self.assertNotIn("commandExecutionPolicy", cl_des)

        # 3. Grok: maps to allowed-tools including image_gen and spawn_subagent
        gr_des = ca.compile_agent_frontmatter(designer, self.profiles["grok"])
        self.assertIn("image_gen", gr_des["allowed-tools"])
        self.assertIn("spawn_subagent", gr_des["allowed-tools"])
        gr_scr = ca.compile_agent_frontmatter(scribe, self.profiles["grok"])
        self.assertFalse(gr_scr["user-invocable"])

        # 4. Copilot: deduplicated coarse tools ["read", "search", "edit", "execute", "agent"]
        cp_des = ca.compile_agent_frontmatter(designer, self.profiles["copilot"])
        self.assertEqual(cp_des["tools"], ["read", "search", "edit", "execute", "agent"])
        self.assertTrue(cp_des["user-invocable"])
        cp_scr = ca.compile_agent_frontmatter(scribe, self.profiles["copilot"])
        self.assertFalse(cp_scr["user-invocable"])

        # 5. Cursor: derives readonly=False for writer agents, readonly=True for read-only, is_background=True for scribe
        cu_des = ca.compile_agent_frontmatter(designer, self.profiles["cursor"])
        self.assertFalse(cu_des["readonly"])
        self.assertFalse(cu_des["is_background"])
        cu_scr = ca.compile_agent_frontmatter(scribe, self.profiles["cursor"])
        self.assertTrue(cu_scr["is_background"])

        readonly_agent = {
            "kind": "agent",
            "name": "wf-auditor",
            "description": "Read-only auditor",
            "capabilities": ["read", "search"],
            "skills": [],
            "background_only": False,
            "hosts": {
                "claude": {"maxTurns": 20, "permissionMode": "plan"},
                "copilot": {"target": "vscode"},
            },
        }
        cu_ro = ca.compile_agent_frontmatter(readonly_agent, self.profiles["cursor"])
        self.assertTrue(cu_ro["readonly"])
        cl_ro = ca.compile_agent_frontmatter(readonly_agent, self.profiles["claude"])
        self.assertEqual(cl_ro["maxTurns"], 20)
        self.assertEqual(cl_ro["permissionMode"], "plan")
        cp_ro = ca.compile_agent_frontmatter(readonly_agent, self.profiles["copilot"])
        self.assertEqual(cp_ro["target"], "vscode")

    def test_rule_frontmatter_and_relative_link_rewriting(self):
        """Rules compile proper host frontmatter and rewrite relative .md links to host extensions."""
        base_rule = json.loads((REPO_ROOT / "rules" / "wf-base.json").read_text(encoding="utf-8"))
        base_md = (REPO_ROOT / "rules" / "wf-base.md").read_text(encoding="utf-8")
        design_rule = json.loads((REPO_ROOT / "rules" / "wf-design-standards.json").read_text(encoding="utf-8"))
        design_md = (REPO_ROOT / "rules" / "wf-design-standards.md").read_text(encoding="utf-8")

        # Copilot: .instructions.md + applyTo: "**" + rewritten relative links
        cp_base_out = ca.compile_markdown_asset(base_md, base_rule, "rules", self.profiles["copilot"])
        self.assertIn('applyTo: "**"', cp_base_out)
        self.assertIn("(wf-git-workflow.instructions.md)", cp_base_out)
        self.assertIn("(wf-lean-execution.instructions.md)", cp_base_out)

        cp_design_out = ca.compile_markdown_asset(design_md, design_rule, "rules", self.profiles["copilot"])
        self.assertIn("(../agents/wf-designer.agent.md)", cp_design_out)
        self.assertIn("(../skills/wf-design-anti-patterns/SKILL.md)", cp_design_out)

        # Cursor: .mdc + alwaysApply: true/false + rewritten .mdc rule links
        cu_base_out = ca.compile_markdown_asset(base_md, base_rule, "rules", self.profiles["cursor"])
        self.assertIn("alwaysApply: true", cu_base_out)
        self.assertIn("(wf-git-workflow.mdc)", cu_base_out)

        cu_design_out = ca.compile_markdown_asset(design_md, design_rule, "rules", self.profiles["cursor"])
        self.assertIn("alwaysApply: false", cu_design_out)

        # Claude: always_on rule omits Antigravity 'trigger: always_on'; scoped rule emits 'paths:'
        cl_base_out = ca.compile_markdown_asset(base_md, base_rule, "rules", self.profiles["claude"])
        self.assertNotIn("trigger: always_on", cl_base_out)
        scoped_rule = {
            "kind": "rule",
            "name": "wf-ts",
            "description": "TS rule",
            "always_on": False,
            "globs": ["src/**/*.ts", "src/**/*.tsx"],
            "hosts": {},
        }
        cl_scoped_fm = ca.compile_rule_frontmatter(scoped_rule, self.profiles["claude"])
        self.assertEqual(cl_scoped_fm["paths"], ["src/**/*.ts", "src/**/*.tsx"])

    def test_claude_settings_hooks_non_destructive_merge_and_prune(self):
        """Claude settings.json hook sync preserves user keys/hooks and updates/prunes wf-* hooks."""
        settings_dir = self.target / ".claude"
        settings_dir.mkdir(parents=True)
        settings_file = settings_dir / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "env": {"FOO": "bar"},
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Bash",
                                "hooks": [{"type": "command", "command": "echo custom-user-hook"}],
                            }
                        ]
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        prog_plugin = json.loads(
            (REPO_ROOT / "plugins" / "wf-programming-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        changed, _ = ca.sync_claude_settings_hooks(
            str(self.target), [prog_plugin], self.profiles["claude"], dry_run=False
        )
        self.assertTrue(changed)
        merged = json.loads(settings_file.read_text(encoding="utf-8"))
        self.assertEqual(merged["env"]["FOO"], "bar")
        pre_rules = merged["hooks"]["PreToolUse"]
        self.assertEqual(len(pre_rules), 2)
        self.assertTrue(any("custom-user-hook" in json.dumps(r) for r in pre_rules))
        wf_rule = [r for r in pre_rules if "pre_tool_hook.py" in json.dumps(r)][0]
        self.assertEqual(wf_rule["matcher"], "Write|Edit|MultiEdit")

        # Re-running with identical plugins is idempotent (changed == False)
        changed_again, _ = ca.sync_claude_settings_hooks(
            str(self.target), [prog_plugin], self.profiles["claude"], dry_run=False
        )
        self.assertFalse(changed_again)

        # Pruning all wf plugins leaves custom-user-hook intact
        pruned_change, _ = ca.sync_claude_settings_hooks(
            str(self.target), [], self.profiles["claude"], dry_run=False
        )
        self.assertTrue(pruned_change)
        after_prune = json.loads(settings_file.read_text(encoding="utf-8"))
        self.assertEqual(len(after_prune["hooks"]["PreToolUse"]), 1)
        self.assertIn("custom-user-hook", json.dumps(after_prune["hooks"]["PreToolUse"]))
        self.assertNotIn("pre_tool_hook.py", json.dumps(after_prune))

    def test_multi_host_autodetect_config_and_full_compile(self):
        """Auto-detects multiple AI folders, persists workforces/config.json, and compiles all 5 hosts."""
        (self.target / ".claude").mkdir()
        (self.target / ".cursor").mkdir()
        (self.target / ".vscode").mkdir()

        detected = ca.detect_workspace_hosts(str(self.target), self.profiles)
        self.assertEqual(detected, ["claude", "copilot", "cursor"])

        resolved = ca.resolve_active_hosts(str(self.target), self.profiles, hosts_arg="auto")
        self.assertEqual(resolved, ["claude", "copilot", "cursor"])

        cfg_path = ca.save_install_config(
            str(self.target),
            hosts=resolved,
            repo_type="project",
            installed_teams=["dev"],
            profiles=self.profiles,
        )
        self.assertTrue(os.path.isfile(cfg_path))
        loaded_cfg = ca.load_install_config(str(self.target))
        self.assertEqual(loaded_cfg["hosts"], ["claude", "copilot", "cursor"])

        # Add .agents later -> auto-detect unions saved hosts + newly detected .agents!
        (self.target / ".agents").mkdir()
        union_hosts = ca.resolve_active_hosts(str(self.target), self.profiles, hosts_arg="auto")
        self.assertEqual(union_hosts, ["antigravity", "claude", "copilot", "cursor"])

        # Compile minimal manifest across all 5 hosts simultaneously
        manifest = {
            "agents": ["wf-programmer.md", "wf-scribe.md"],
            "rules": ["wf-base.md", "wf-design-standards.md"],
            "skills": ["wf-management", "wf-plan"],
            "workflows": [],
            "plugins": ["wf-programming-plugin"],
            "teams": ["dev"],
        }
        all_five = ["antigravity", "claude", "grok", "copilot", "cursor"]
        summary = ca.install_compiled_hosts(
            str(REPO_ROOT), str(self.target), all_five, manifest, dry_run=False
        )
        self.assertGreater(summary["written"], 0)

        # Verify compiled files exist in each host's native folder & extension
        self.assertTrue((self.target / ".agents" / "agents" / "wf-programmer.md").is_file())
        self.assertTrue((self.target / ".claude" / "agents" / "wf-programmer.md").is_file())
        self.assertTrue((self.target / ".claude" / "settings.json").is_file())
        self.assertTrue((self.target / ".grok" / "agents" / "wf-programmer.md").is_file())
        self.assertTrue((self.target / ".grok" / "hooks.json").is_file())
        self.assertTrue((self.target / ".github" / "agents" / "wf-programmer.agent.md").is_file())
        self.assertTrue((self.target / ".github" / "instructions" / "wf-base.instructions.md").is_file())
        self.assertTrue((self.target / ".cursor" / "rules" / "wf-base.mdc").is_file())
        # Verify offline host profiles bundled into wf-management skill
        self.assertTrue(
            (self.target / ".claude" / "skills" / "wf-management" / "hosts" / "claude.json").is_file()
        )


class TestMultiHostManifestAndPrune(unittest.TestCase):
    """Verifies multi-host resolve_manifest.py and prune_team.py integration."""

    def setUp(self):
        import prune_team as pt
        import resolve_manifest as rm

        self.rm = rm
        self.pt = pt
        self.profiles = ca.load_host_profiles(str(REPO_ROOT))
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target = Path(self.temp_dir.name)
        (self.target / "workforces").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resolve_manifest_multi_host_installed_files_parity(self):
        """resolve_installed_file_paths matches compile_assets across all 5 hosts and omits .claude/settings.json."""
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev,design")
        all_five = ["antigravity", "claude", "grok", "copilot", "cursor"]
        compiled_summary = ca.install_compiled_hosts(
            str(REPO_ROOT), str(self.target), all_five, manifest, dry_run=True
        )
        resolved_files = self.rm.resolve_installed_file_paths(
            str(REPO_ROOT), str(self.target), teams_arg="dev,design", hosts="all"
        )

        self.assertEqual(resolved_files, compiled_summary["installed_files"])
        self.assertIn(".github/agents/wf-programmer.agent.md", resolved_files)
        self.assertIn(".github/instructions/wf-base.instructions.md", resolved_files)
        self.assertIn(".github/copilot/teams/dev/pack.json", resolved_files)
        self.assertIn(".cursor/rules/wf-base.mdc", resolved_files)
        self.assertIn(".grok/hooks.json", resolved_files)
        self.assertIn(".claude/skills/wf-management/hosts/claude.json", resolved_files)
        self.assertNotIn(".claude/settings.json", resolved_files)
        self.assertFalse(any(p.endswith("/skill.json") for p in resolved_files))

    def test_resolve_manifest_cli_hosts_no_autodetect_and_manifest_persistence(self):
        """CLI supports --hosts, --editor, --no-auto-detect, ACTIVE_HOSTS bash-export, and saves hosts in .manifest.json."""
        import subprocess

        ca.save_install_config(
            str(self.target),
            hosts=["claude"],
            repo_type="project",
            installed_teams=["dev"],
            profiles=self.profiles,
        )
        (self.target / ".cursor").mkdir(parents=True)

        # Auto-detect enabled: unions config ['claude'] + workspace ['.cursor']
        auto_hosts = self.rm.resolve_target_hosts(
            str(REPO_ROOT), str(self.target), hosts_arg="auto", auto_detect=True
        )
        self.assertEqual(auto_hosts, ["claude", "cursor"])

        # --no-auto-detect: strictly uses saved config ['claude']
        pinned_hosts = self.rm.resolve_target_hosts(
            str(REPO_ROOT), str(self.target), hosts_arg="auto", auto_detect=False
        )
        self.assertEqual(pinned_hosts, ["claude"])

        script_path = SCRIPTS_DIR / "resolve_manifest.py"
        bash_res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--toolkit-root",
                str(REPO_ROOT),
                "--target",
                str(self.target),
                "--hosts",
                "claude,copilot",
                "--teams",
                "dev",
                "--format",
                "bash-export",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(bash_res.returncode, 0, bash_res.stderr)
        self.assertIn('ACTIVE_HOSTS="claude copilot"', bash_res.stdout)
        self.assertIn("ALLOWED_AGENTS=", bash_res.stdout)

        save_res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--toolkit-root",
                str(REPO_ROOT),
                "--target",
                str(self.target),
                "--editor",
                "claude,cursor",
                "--teams",
                "dev",
                "--save-manifest",
                "--version-hash",
                "abc999",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(save_res.returncode, 0, save_res.stderr)
        saved_manifest = self.rm.load_installed_manifest(str(self.target))
        self.assertEqual(saved_manifest["hosts"], ["claude", "cursor"])
        self.assertEqual(saved_manifest["version"], "abc999")
        self.assertTrue(any(f.startswith(".cursor/rules/") and f.endswith(".mdc") for f in saved_manifest["installed_files"]))

        bad_res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--toolkit-root",
                str(REPO_ROOT),
                "--target",
                str(self.target),
                "--hosts",
                "imaginary-ai",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertNotEqual(bad_res.returncode, 0)
        self.assertNotIn("Traceback (most recent call last):", bad_res.stderr)

    def test_multi_host_obsolete_pruning_legacy_copilot_and_claude_hooks(self):
        """Prunes obsolete files across active hosts, legacy .github/copilot/*, and orphaned .claude/settings.json hooks."""
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="none")
        active_hosts = ["claude", "copilot", "cursor"]
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), active_hosts, manifest, dry_run=False)
        ca.save_install_config(str(self.target), active_hosts, "project", [], self.profiles)

        # Inject legacy .github/copilot/{agents,rules,skills,workflows,plugins} + custom user bot
        legacy_cp = [
            self.target / ".github" / "copilot" / "agents" / "wf-programmer.md",
            self.target / ".github" / "copilot" / "rules" / "wf-base.md",
            self.target / ".github" / "copilot" / "skills" / "wf-plan" / "SKILL.md",
            self.target / ".github" / "copilot" / "workflows" / "wf-plan.md",
            self.target / ".github" / "copilot" / "plugins" / "wf-programming-plugin" / "hooks.json",
        ]
        for path in legacy_cp:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Legacy Copilot\n", encoding="utf-8")

        custom_cp_bot = self.target / ".github" / "copilot" / "agents" / "my-custom-bot.md"
        custom_cp_bot.write_text("# User Custom Bot\n", encoding="utf-8")

        # Inject stale compiled Cursor/Copilot files and accidental .claude/settings.json in prior manifest
        stale_mdc = self.target / ".cursor" / "rules" / "wf-retired.mdc"
        stale_agent = self.target / ".github" / "agents" / "wf-retired.agent.md"
        stale_mdc.write_text("# Retired\n", encoding="utf-8")
        stale_agent.write_text("# Retired\n", encoding="utf-8")

        # Inject custom user setting + orphaned wf-programming hook into .claude/settings.json
        settings_path = self.target / ".claude" / "settings.json"
        settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        settings_data["env"] = {"KEEP_USER": "yes"}
        settings_data.setdefault("hooks", {}).setdefault("PreToolUse", []).extend(
            [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "echo keep-user-hook"}],
                },
                {
                    "matcher": "Write|Edit|MultiEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .claude/skills/wf-code-graph/scripts/pre_tool_hook.py",
                        }
                    ],
                },
            ]
        )
        settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")

        self.rm.save_installed_manifest(
            str(self.target),
            "old-ver",
            ["dev"],
            [
                ".cursor/rules/wf-retired.mdc",
                ".github/agents/wf-retired.agent.md",
                ".claude/settings.json",
            ],
            hosts=active_hosts,
        )

        current_files = self.rm.resolve_installed_file_paths(
            str(REPO_ROOT), str(self.target), teams_arg="none", hosts=active_hosts
        )
        obsolete = self.rm.find_obsolete_files(
            str(self.target), None, current_files, str(REPO_ROOT), hosts=active_hosts
        )
        self.assertNotIn(".claude/settings.json", obsolete)
        self.assertIn(".cursor/rules/wf-retired.mdc", obsolete)
        self.assertIn(".github/agents/wf-retired.agent.md", obsolete)
        for p in legacy_cp:
            self.assertIn(str(p.relative_to(self.target)), obsolete)
        self.assertNotIn(str(custom_cp_bot.relative_to(self.target)), obsolete)

        # Dry run leaves disk untouched
        dry_count = self.rm.prune_obsolete_files(
            str(self.target),
            obsolete,
            dry_run=True,
            quiet=True,
            toolkit_root=str(REPO_ROOT),
            active_hosts=active_hosts,
            active_plugins=manifest["plugins"],
        )
        self.assertGreater(dry_count, len(legacy_cp))
        self.assertTrue(stale_mdc.is_file())
        self.assertIn("pre_tool_hook.py", settings_path.read_text(encoding="utf-8"))

        # Live prune removes obsolete files and orphaned hook while preserving user assets
        live_count = self.rm.prune_obsolete_files(
            str(self.target),
            obsolete,
            dry_run=False,
            quiet=True,
            toolkit_root=str(REPO_ROOT),
            active_hosts=active_hosts,
            active_plugins=manifest["plugins"],
        )
        self.assertEqual(live_count, dry_count)
        for p in legacy_cp:
            self.assertFalse(p.exists(), f"Expected legacy Copilot asset pruned: {p}")
        self.assertFalse(stale_mdc.exists())
        self.assertFalse(stale_agent.exists())
        self.assertTrue(custom_cp_bot.is_file())
        self.assertTrue(settings_path.is_file())
        cleaned_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(cleaned_settings["env"]["KEEP_USER"], "yes")
        self.assertIn("keep-user-hook", json.dumps(cleaned_settings["hooks"]))
        self.assertNotIn("pre_tool_hook.py", json.dumps(cleaned_settings["hooks"]))
        self.assertIn("validate-references.py", json.dumps(cleaned_settings["hooks"]))

    def test_prune_team_across_all_five_hosts_and_hook_resync(self):
        """prune_team removes orphaned team assets (.agent.md, .instructions.md, .mdc) and resyncs hooks across all 5 hosts."""
        all_five = ["antigravity", "claude", "grok", "copilot", "cursor"]
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - design\n  - dev\n  - marketing\n",
            encoding="utf-8",
        )
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="design,dev,marketing")
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), all_five, manifest, dry_run=False)
        ca.save_install_config(str(self.target), all_five, "project", ["design", "dev", "marketing"], self.profiles)

        # Add a custom user hook into .claude/settings.json alongside compiled wf-integrity + wf-programming
        settings_path = self.target / ".claude" / "settings.json"
        settings_obj = json.loads(settings_path.read_text(encoding="utf-8"))
        settings_obj["hooks"]["PreToolUse"].insert(
            0, {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo user-guard"}]}
        )
        settings_path.write_text(json.dumps(settings_obj, indent=2), encoding="utf-8")

        # Dry run must not mutate files, hooks, or config
        self.assertTrue(
            self.pt.prune_team("dev", target_dir=str(self.target), toolkit_root=str(REPO_ROOT), dry_run=True)
        )
        self.assertTrue((self.target / ".github" / "agents" / "wf-programmer.agent.md").is_file())
        self.assertTrue((self.target / ".cursor" / "rules" / "wf-clean-coder.mdc").is_file())
        self.assertIn("pre_tool_hook.py", settings_path.read_text(encoding="utf-8"))
        self.assertIn("wf-programming", (self.target / ".grok" / "hooks.json").read_text(encoding="utf-8"))

        # Live prune of 'dev' across all 5 hosts
        self.assertTrue(
            self.pt.prune_team("dev", target_dir=str(self.target), toolkit_root=str(REPO_ROOT), dry_run=False)
        )

        # Orphaned dev assets gone on every host
        self.assertFalse((self.target / ".agents" / "agents" / "wf-programmer.md").exists())
        self.assertFalse((self.target / ".claude" / "agents" / "wf-programmer.md").exists())
        self.assertFalse((self.target / ".grok" / "agents" / "wf-programmer.md").exists())
        self.assertFalse((self.target / ".github" / "agents" / "wf-programmer.agent.md").exists())
        self.assertFalse((self.target / ".cursor" / "agents" / "wf-programmer.md").exists())

        self.assertFalse((self.target / ".github" / "instructions" / "wf-clean-coder.instructions.md").exists())
        self.assertFalse((self.target / ".cursor" / "rules" / "wf-clean-coder.mdc").exists())
        self.assertFalse((self.target / ".github" / "skills" / "wf-clean-coder").exists())
        self.assertFalse((self.target / ".github" / "copilot" / "teams" / "dev").exists())
        self.assertFalse((self.target / ".cursor" / "teams" / "dev").exists())
        self.assertFalse((self.target / ".agents" / "plugins" / "wf-programming-plugin").exists())
        self.assertFalse((self.target / ".grok" / "plugins" / "wf-programming-plugin").exists())

        # Shared/remaining team assets preserved across hosts
        self.assertTrue((self.target / ".github" / "agents" / "wf-designer.agent.md").is_file())
        self.assertTrue((self.target / ".github" / "instructions" / "wf-design-standards.instructions.md").is_file())
        self.assertTrue((self.target / ".cursor" / "rules" / "wf-design-standards.mdc").is_file())
        self.assertTrue((self.target / ".claude" / "skills" / "wf-brand-guidelines" / "SKILL.md").is_file())

        # Grok hooks.json & Claude settings.json re-synced without wf-programming
        grok_hooks = json.loads((self.target / ".grok" / "hooks.json").read_text(encoding="utf-8"))
        self.assertNotIn("wf-programming", grok_hooks)
        self.assertIn("wf-integrity", grok_hooks)

        claude_after = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("user-guard", json.dumps(claude_after["hooks"]))
        self.assertNotIn("pre_tool_hook.py", json.dumps(claude_after["hooks"]))
        self.assertIn("validate-references.py", json.dumps(claude_after["hooks"]))

        # Config and manifest updated consistently
        updated_cfg = ca.load_install_config(str(self.target))
        self.assertEqual(updated_cfg["installed_teams"], ["design", "marketing"])
        self.assertEqual(updated_cfg["hosts"], all_five)
        updated_manifest = self.rm.load_installed_manifest(str(self.target))
        self.assertEqual(updated_manifest["installed_teams"], ["design", "marketing"])
        self.assertEqual(updated_manifest["hosts"], all_five)
        self.assertNotIn(".github/agents/wf-programmer.agent.md", updated_manifest["installed_files"])

    def test_prune_team_custom_workflow_prompt_extensions_across_hosts(self):
        """prune_team removes compiled workflow files (.prompt.md on copilot, commands/*.md on claude/grok/cursor)."""
        all_five = ["antigravity", "claude", "grok", "copilot", "cursor"]
        custom_team = "customflow"
        ws_team_dir = self.target / "workforces" / "teams" / custom_team
        ws_team_dir.mkdir(parents=True, exist_ok=True)
        (ws_team_dir / "team.json").write_text(
            json.dumps({"id": custom_team, "workflows": ["wf-demo.md"]}), encoding="utf-8"
        )
        (self.target / "workforces" / "workrules.md").write_text(
            f"# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - {custom_team}\n",
            encoding="utf-8",
        )
        ca.save_install_config(str(self.target), all_five, "project", [custom_team], self.profiles)

        wf_targets = [
            self.target / ".agents" / "workflows" / "wf-demo.md",
            self.target / ".claude" / "commands" / "wf-demo.md",
            self.target / ".grok" / "commands" / "wf-demo.md",
            self.target / ".github" / "prompts" / "wf-demo.prompt.md",
            self.target / ".cursor" / "commands" / "wf-demo.md",
        ]
        for wf_file in wf_targets:
            wf_file.parent.mkdir(parents=True, exist_ok=True)
            wf_file.write_text("# Demo Flow\n", encoding="utf-8")

        self.assertTrue(
            self.pt.prune_team(custom_team, target_dir=str(self.target), toolkit_root=str(self.target), dry_run=False)
        )
        for wf_file in wf_targets:
            self.assertFalse(wf_file.exists(), f"Expected workflow file pruned: {wf_file}")

    def test_offline_consumer_prune_team_without_toolkit_root_or_agents_dir(self):
        """prune_team without toolkit_root in a non-.agents workspace preserves manifest tracking for remaining hosts."""
        non_agents_hosts = ["claude", "grok", "copilot", "cursor"]
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - design\n  - dev\n",
            encoding="utf-8",
        )
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="design,dev")
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), non_agents_hosts, manifest, dry_run=False)
        ca.save_install_config(str(self.target), non_agents_hosts, "project", ["design", "dev"], self.profiles)

        self.assertFalse((self.target / ".agents").exists())
        self.assertTrue(self.pt.prune_team("dev", target_dir=str(self.target)))

        self.assertFalse((self.target / ".github" / "agents" / "wf-programmer.agent.md").exists())
        self.assertFalse((self.target / ".cursor" / "rules" / "wf-clean-coder.mdc").exists())
        self.assertTrue((self.target / ".github" / "agents" / "wf-designer.agent.md").is_file())
        self.assertTrue((self.target / ".cursor" / "rules" / "wf-design-standards.mdc").is_file())

        saved = self.rm.load_installed_manifest(str(self.target))
        self.assertEqual(saved["hosts"], non_agents_hosts)
        self.assertIn(".github/agents/wf-designer.agent.md", saved["installed_files"])
        self.assertIn(".cursor/rules/wf-design-standards.mdc", saved["installed_files"])
        self.assertIn(".grok/hooks.json", saved["installed_files"])
        self.assertNotIn(".github/agents/wf-programmer.agent.md", saved["installed_files"])

    def test_deactivating_host_prunes_its_files_and_cleans_claude_hooks(self):
        """Deactivating claude and copilot via CLI prunes their files and cleans wf-* hooks while keeping user settings."""
        import subprocess

        initial_hosts = ["claude", "copilot", "cursor"]
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev")
        summary = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), initial_hosts, manifest, dry_run=False)
        self.rm.save_installed_manifest(
            str(self.target), "v1", ["dev"], summary["installed_files"], hosts=initial_hosts
        )

        settings_path = self.target / ".claude" / "settings.json"
        settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        settings_data["env"] = {"USER_SECRET": "42"}
        settings_data["hooks"]["PreToolUse"].insert(
            0, {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo keep-me"}]}
        )
        settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")

        rm_script = SCRIPTS_DIR / "resolve_manifest.py"
        res = subprocess.run(
            [
                sys.executable,
                str(rm_script),
                "--toolkit-root",
                str(REPO_ROOT),
                "--target",
                str(self.target),
                "--hosts",
                "cursor",
                "--teams",
                "dev",
                "--prune-obsolete",
                "--quiet",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse((self.target / ".github" / "agents" / "wf-programmer.agent.md").exists())
        self.assertFalse((self.target / ".claude" / "agents" / "wf-programmer.md").exists())
        self.assertTrue((self.target / ".cursor" / "agents" / "wf-programmer.md").is_file())
        self.assertTrue(settings_path.is_file())

        after_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(after_settings["env"]["USER_SECRET"], "42")
        self.assertIn("keep-me", json.dumps(after_settings["hooks"]))
        self.assertNotIn("pre_tool_hook.py", json.dumps(after_settings["hooks"]))
        self.assertNotIn("validate-references.py", json.dumps(after_settings["hooks"]))

        # Boundary: prune_team CLI rejects invalid team identifier and unknown --hosts without traceback
        pt_script = SCRIPTS_DIR / "prune_team.py"
        for bad_args in (["../escape"], ["dev", "--hosts", "unknown-host"]):
            bad = subprocess.run(
                [sys.executable, str(pt_script), "--target", str(self.target)] + bad_args,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertNotIn("Traceback (most recent call last):", bad.stderr)

    def test_installed_consumer_scripts_preserve_claude_and_grok_core_hooks_offline(self):
        """Installed consumer prune_team.py and resolve_manifest.py preserve core wf-integrity hooks offline."""
        import subprocess

        hosts = ["claude", "grok"]
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - design\n  - dev\n",
            encoding="utf-8",
        )
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="design,dev")
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), hosts, manifest, dry_run=False)
        ca.save_install_config(str(self.target), hosts, "project", ["design", "dev"], self.profiles)

        # Inject custom user hooks into both .claude/settings.json and .grok/hooks.json
        settings_path = self.target / ".claude" / "settings.json"
        s_data = json.loads(settings_path.read_text(encoding="utf-8"))
        s_data["hooks"]["PreToolUse"].insert(
            0, {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo offline-user-guard"}]}
        )
        settings_path.write_text(json.dumps(s_data, indent=2), encoding="utf-8")

        grok_hooks_path = self.target / ".grok" / "hooks.json"
        g_data = json.loads(grok_hooks_path.read_text(encoding="utf-8"))
        g_data["custom-user-ns"] = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo grok-user"}]}]}
        grok_hooks_path.write_text(json.dumps(g_data, indent=2), encoding="utf-8")

        # Execute the INSTALLED prune_team.py inside <target>/.claude/skills/... (outside REPO_ROOT!)
        installed_pt = self.target / ".claude" / "skills" / "wf-management" / "scripts" / "prune_team.py"
        res_pt = subprocess.run(
            [sys.executable, str(installed_pt), "dev", "--target", str(self.target)],
            capture_output=True,
            text=True,
            timeout=25,
            cwd=str(self.target),
        )
        self.assertEqual(res_pt.returncode, 0, res_pt.stderr + res_pt.stdout)

        claude_after = json.loads(settings_path.read_text(encoding="utf-8"))
        claude_hooks_str = json.dumps(claude_after.get("hooks", {}))
        self.assertIn("offline-user-guard", claude_hooks_str)
        self.assertNotIn("pre_tool_hook.py", claude_hooks_str)
        self.assertIn("validate-references.py", claude_hooks_str)

        grok_after = json.loads(grok_hooks_path.read_text(encoding="utf-8"))
        self.assertNotIn("wf-programming", grok_after)
        self.assertIn("wf-integrity", grok_after)
        self.assertIn("custom-user-ns", grok_after)

        # Also run the INSTALLED resolve_manifest.py --prune-obsolete offline
        installed_rm = self.target / ".claude" / "skills" / "wf-management" / "scripts" / "resolve_manifest.py"
        res_rm = subprocess.run(
            [sys.executable, str(installed_rm), "--target", str(self.target), "--prune-obsolete", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=25,
            cwd=str(self.target),
        )
        self.assertEqual(res_rm.returncode, 0, res_rm.stderr + res_rm.stdout)
        self.assertIn("validate-references.py", settings_path.read_text(encoding="utf-8"))
        self.assertIn("wf-integrity", json.loads(grok_hooks_path.read_text(encoding="utf-8")))

    def test_pruning_last_team_stays_core_only_on_subsequent_resolve_manifest(self):
        """Uninstalling the last team keeps installed_teams=[] instead of resurrecting ['design', 'dev']."""
        with tempfile.TemporaryDirectory() as fresh_tmp:
            fresh_manifest = self.rm.resolve_manifest(str(REPO_ROOT), fresh_tmp)
            self.assertEqual(fresh_manifest["installed_teams"], ["design", "dev"])

        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n",
            encoding="utf-8",
        )
        ca.save_install_config(str(self.target), ["claude"], "project", ["dev"], self.profiles)
        self.assertTrue(self.pt.prune_team("dev", target_dir=str(self.target), toolkit_root=str(REPO_ROOT)))

        self.assertEqual(self.rm.get_installed_teams(str(self.target), str(REPO_ROOT)), [])
        resolved_after = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target))
        self.assertEqual(resolved_after["installed_teams"], [])
        self.assertNotIn("wf-programmer.md", resolved_after["agents"])
        self.assertNotIn("wf-designer.md", resolved_after["agents"])

    def test_custom_workspace_team_coexists_with_standard_teams(self):
        """Custom team in workforces/teams/<id>/team.json is discovered alongside standard toolkit teams."""
        custom_dir = self.target / "workforces" / "teams" / "customflow"
        custom_dir.mkdir(parents=True, exist_ok=True)
        (custom_dir / "team.json").write_text(
            json.dumps({"id": "customflow", "workflows": ["wf-demo.md"]}), encoding="utf-8"
        )
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n  - customflow\n",
            encoding="utf-8",
        )
        ca.save_install_config(str(self.target), ["copilot", "claude"], "project", ["dev", "customflow"], self.profiles)

        teams = self.rm.get_installed_teams(str(self.target), str(REPO_ROOT))
        self.assertEqual(teams, ["customflow", "dev"])
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target))
        self.assertIn("wf-programmer.md", manifest["agents"])
        self.assertIn("wf-demo.md", manifest["workflows"])

    def test_prune_obsolete_resyncs_grok_hooks_and_prunes_nongit_claude_plugins(self):
        """prune_obsolete_files cleans orphaned .grok/hooks.json entries and unmanifested non-git .claude/plugins/*."""
        import shutil

        # Part A: Grok hook namespace cleanup during resolve_manifest prune_obsolete_files
        m_both = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev,design")
        s_grok = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["grok"], m_both, dry_run=False)
        self.rm.save_installed_manifest(str(self.target), "v1", ["dev", "design"], s_grok["installed_files"], hosts=["grok"])

        grok_hooks_file = self.target / ".grok" / "hooks.json"
        g_raw = json.loads(grok_hooks_file.read_text(encoding="utf-8"))
        g_raw["user-custom-hook"] = {"PostToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "echo ok"}]}]}
        grok_hooks_file.write_text(json.dumps(g_raw, indent=2), encoding="utf-8")

        cur_design = self.rm.resolve_installed_file_paths(str(REPO_ROOT), str(self.target), teams_arg="design", hosts=["grok"])
        obs_grok = self.rm.find_obsolete_files(str(self.target), None, cur_design, str(REPO_ROOT), hosts=["grok"])
        m_design = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="design")

        dry_cnt = self.rm.prune_obsolete_files(
            str(self.target), obs_grok, dry_run=True, quiet=True,
            toolkit_root=str(REPO_ROOT), active_hosts=["grok"], active_plugins=m_design["plugins"],
        )
        self.assertIn("wf-programming", json.loads(grok_hooks_file.read_text(encoding="utf-8")))
        live_cnt = self.rm.prune_obsolete_files(
            str(self.target), obs_grok, dry_run=False, quiet=True,
            toolkit_root=str(REPO_ROOT), active_hosts=["grok"], active_plugins=m_design["plugins"],
        )
        self.assertEqual(live_cnt, dry_cnt)
        after_grok = json.loads(grok_hooks_file.read_text(encoding="utf-8"))
        self.assertNotIn("wf-programming", after_grok)
        self.assertIn("wf-integrity", after_grok)
        self.assertIn("user-custom-hook", after_grok)

        # Part B: Non-git toolkit_root still detects unmanifested .claude/plugins/wf-* files & cleans empty .claude/plugins
        with tempfile.TemporaryDirectory() as tk_tmp, tempfile.TemporaryDirectory() as ws_tmp:
            tk_dir, ws_dir = Path(tk_tmp), Path(ws_tmp)
            for sub in ("agents", "rules", "skills", "plugins", "teams", "config"):
                shutil.copytree(REPO_ROOT / sub, tk_dir / sub)
            stale_pl = ws_dir / ".claude" / "plugins" / "wf-programming-plugin" / "plugin.json"
            stale_pl.parent.mkdir(parents=True)
            stale_pl.write_text("{}", encoding="utf-8")

            cur_cl = self.rm.resolve_installed_file_paths(str(tk_dir), str(ws_dir), teams_arg="dev", hosts=["claude"])
            obs_cl = self.rm.find_obsolete_files(str(ws_dir), None, cur_cl, str(tk_dir), hosts=["claude"])
            self.assertIn(".claude/plugins/wf-programming-plugin/plugin.json", obs_cl)
            self.rm.prune_obsolete_files(
                str(ws_dir), obs_cl, dry_run=False, quiet=True, toolkit_root=str(tk_dir), active_hosts=["claude"]
            )
            self.assertFalse(stale_pl.exists())
            self.assertFalse((ws_dir / ".claude" / "plugins").exists())

    def test_grok_user_hooks_preserved_on_recompile_and_deactivation(self):
        """Grok hooks.json preserves non-Workforces namespaces on re-compile and host deactivation."""
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev")
        s_init = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["grok", "cursor"], manifest, dry_run=False)
        self.rm.save_installed_manifest(
            str(self.target), "v1", ["dev"], s_init["installed_files"], hosts=["grok", "cursor"]
        )

        grok_hooks_path = self.target / ".grok" / "hooks.json"
        g_data = json.loads(grok_hooks_path.read_text(encoding="utf-8"))
        g_data["custom-user-ns"] = {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo keep-grok-user"}]}]
        }
        grok_hooks_path.write_text(json.dumps(g_data, indent=2), encoding="utf-8")

        # Re-compiling grok must preserve custom-user-ns
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["grok", "cursor"], manifest, dry_run=False)
        after_recompile = json.loads(grok_hooks_path.read_text(encoding="utf-8"))
        self.assertIn("custom-user-ns", after_recompile)
        self.assertIn("wf-programming", after_recompile)

        # Deactivating grok while custom-user-ns is present strips wf-* namespaces without deleting the file
        cur_cursor = self.rm.resolve_installed_file_paths(
            str(REPO_ROOT), str(self.target), teams_arg="dev", hosts=["cursor"]
        )
        obs = self.rm.find_obsolete_files(str(self.target), None, cur_cursor, str(REPO_ROOT), hosts=["cursor"])
        self.assertNotIn(".grok/hooks.json", obs)
        self.rm.prune_obsolete_files(
            str(self.target), obs, dry_run=False, quiet=True,
            toolkit_root=str(REPO_ROOT), active_hosts=["cursor"], active_plugins=manifest["plugins"],
        )
        self.assertTrue(grok_hooks_path.is_file())
        after_deact = json.loads(grok_hooks_path.read_text(encoding="utf-8"))
        self.assertEqual(list(after_deact.keys()), ["custom-user-ns"])

        # When only wf-* namespaces exist (no user keys), deactivating grok removes .grok/hooks.json cleanly
        grok_hooks_path.unlink()
        s_wf_only = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["grok", "cursor"], manifest, dry_run=False)
        self.rm.save_installed_manifest(
            str(self.target), "v2", ["dev"], s_wf_only["installed_files"], hosts=["grok", "cursor"]
        )
        obs_wf_only = self.rm.find_obsolete_files(str(self.target), None, cur_cursor, str(REPO_ROOT), hosts=["cursor"])
        self.assertIn(".grok/hooks.json", obs_wf_only)
        self.rm.prune_obsolete_files(
            str(self.target), obs_wf_only, dry_run=False, quiet=True,
            toolkit_root=str(REPO_ROOT), active_hosts=["cursor"], active_plugins=manifest["plugins"],
        )
        self.assertFalse(grok_hooks_path.exists())

    def test_find_obsolete_files_default_current_files_and_auto_detect_flag(self):
        """find_obsolete_files with current_files=None preserves active assets and honors auto_detect=False."""
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev")
        summary = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["claude"], manifest, dry_run=False)
        ca.save_install_config(str(self.target), ["claude"], "project", ["dev"], self.profiles, auto_detect_hosts=True)
        self.rm.save_installed_manifest(str(self.target), "v1", ["dev"], summary["installed_files"], hosts=["claude"])

        # Add an unconfigured .cursor folder with a legacy file; auto_detect=False must ignore .cursor
        stale_cursor = self.target / ".cursor" / "agents" / "clean-coder.md"
        stale_cursor.parent.mkdir(parents=True, exist_ok=True)
        stale_cursor.write_text("# Legacy\n", encoding="utf-8")

        obsolete_pinned = self.rm.find_obsolete_files(
            str(self.target), toolkit_root=str(REPO_ROOT), auto_detect=False
        )
        self.assertEqual(obsolete_pinned, [])
        self.assertNotIn(".claude/agents/wf-project-manager.md", obsolete_pinned)
        self.assertNotIn(".claude/agents/wf-programmer.md", obsolete_pinned)

        obsolete_auto = self.rm.find_obsolete_files(
            str(self.target), toolkit_root=str(REPO_ROOT), auto_detect=True
        )
        self.assertIn(".cursor/agents/clean-coder.md", obsolete_auto)
        self.assertNotIn(".claude/agents/wf-project-manager.md", obsolete_auto)

    def test_offline_claude_prune_without_teams_dir_and_config_precedence(self):
        """Offline consumer prune_team works even without <host>/teams/ and config.json overrides stale workrules.md."""
        import shutil
        import subprocess

        # Stale workrules.md says [sales], while authoritative config.json says [design, dev]
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - sales\n",
            encoding="utf-8",
        )
        ca.save_install_config(
            str(self.target), ["claude"], "project", ["design", "dev"], self.profiles, auto_detect_hosts=True
        )
        self.assertEqual(self.rm.get_installed_teams(str(self.target), str(REPO_ROOT)), ["design", "dev"])

        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target))
        self.assertEqual(manifest["installed_teams"], ["design", "dev"])
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["claude"], manifest, dry_run=False)

        # Simulate brownfield/minimal install lacking .claude/teams/ entirely
        shutil.rmtree(self.target / ".claude" / "teams")
        (self.target / ".cursor").mkdir(parents=True)

        installed_pt = self.target / ".claude" / "skills" / "wf-management" / "scripts" / "prune_team.py"
        res = subprocess.run(
            [sys.executable, str(installed_pt), "dev", "--target", str(self.target), "--no-auto-detect"],
            capture_output=True,
            text=True,
            timeout=25,
            cwd=str(self.target),
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertFalse((self.target / ".claude" / "agents" / "wf-programmer.md").exists())
        self.assertFalse((self.target / ".claude" / "skills" / "wf-clean-coder").exists())
        self.assertTrue((self.target / ".claude" / "agents" / "wf-designer.md").is_file())
        self.assertTrue((self.target / ".claude" / "skills" / "wf-brand-guidelines" / "SKILL.md").is_file())

        cfg_after = ca.load_install_config(str(self.target))
        self.assertEqual(cfg_after["installed_teams"], ["design"])
        self.assertEqual(cfg_after["hosts"], ["claude"])
        self.assertFalse(cfg_after["auto_detect_hosts"])


class TestMultiHostValidators(unittest.TestCase):
    """Verifies validate.py and validate-references.py across all 5 host layouts and sidecar JSON schemas."""

    def setUp(self):
        self.validate_py = SCRIPTS_DIR / "validate.py"
        self.validate_refs_py = SCRIPTS_DIR / "validate-references.py"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ws = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_py_passes_repo_root_and_catches_invalid_sidecar_schemas(self):
        """validate.py validates all 64 canonical sidecars in REPO_ROOT and rejects malformed sidecar metadata."""
        import subprocess

        root_res = subprocess.run(
            [sys.executable, str(self.validate_py), str(REPO_ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(root_res.returncode, 0, root_res.stdout + root_res.stderr)

        # Bad agent sidecar: unknown capability + unknown host override
        bad_ws = self.ws / "bad_sidecars"
        (bad_ws / "agents").mkdir(parents=True)
        (bad_ws / "agents" / "wf-broken.md").write_text(
            "---\nname: wf-broken\ndescription: Broken\n---\n# Broken\n", encoding="utf-8"
        )
        (bad_ws / "agents" / "wf-broken.json").write_text(
            json.dumps(
                {
                    "kind": "agent",
                    "name": "wf-broken",
                    "description": "Broken",
                    "capabilities": ["read", "telepathy"],
                    "hosts": {"nonexistent_host": {}},
                }
            ),
            encoding="utf-8",
        )
        bad_res = subprocess.run(
            [sys.executable, str(self.validate_py), str(bad_ws)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(bad_res.returncode, 0)
        self.assertIn("telepathy", bad_res.stdout)

        # Bad skill sidecar missing paired SKILL.md
        bad_skill_ws = self.ws / "bad_skill_sidecar"
        (bad_skill_ws / "skills" / "wf-orphan").mkdir(parents=True)
        (bad_skill_ws / "skills" / "wf-orphan" / "skill.json").write_text(
            json.dumps({"kind": "skill", "name": "wf-orphan", "description": "Orphan"}),
            encoding="utf-8",
        )
        bad_sk_res = subprocess.run(
            [sys.executable, str(self.validate_py), str(bad_skill_ws)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(bad_sk_res.returncode, 0)

    def test_validate_and_validate_references_across_copilot_and_cursor_extensions(self):
        """validate.py and validate-references.py audit .agent.md, .instructions.md, .prompt.md, and .mdc files."""
        import subprocess

        # Missing frontmatter in .github/agents/*.agent.md must fail validate.py
        cp_ws = self.ws / "copilot_bad_agent"
        (cp_ws / ".github" / "agents").mkdir(parents=True)
        (cp_ws / ".github" / "agents" / "wf-broken.agent.md").write_text("# No frontmatter\n", encoding="utf-8")
        cp_bad = subprocess.run(
            [sys.executable, str(self.validate_py), str(cp_ws)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(cp_bad.returncode, 0)

        # Broken markdown link inside Cursor .mdc rule must be caught by validate-references.py
        cu_ws = self.ws / "cursor_mdc_broken"
        (cu_ws / ".cursor" / "rules").mkdir(parents=True)
        (cu_ws / ".cursor" / "rules" / "wf-base.mdc").write_text(
            "---\ndescription: Base\nalwaysApply: true\n---\n\nSee [missing](missing-rule.mdc).\n",
            encoding="utf-8",
        )
        vr_bad = subprocess.run(
            [sys.executable, str(self.validate_refs_py), str(cu_ws)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(vr_bad.returncode, 0)
        self.assertIn("missing-rule.mdc", vr_bad.stdout)

        # --fix on Cursor & Copilot pack.json generates host-native .mdc / .instructions.md / .agent.md stubs
        fix_ws = self.ws / "multi_host_pack_fix"
        (fix_ws / ".cursor" / "teams" / "dev").mkdir(parents=True)
        (fix_ws / ".cursor" / "teams" / "dev" / "pack.json").write_text(
            json.dumps({"name": "dev", "rules": ["wf-custom.md"], "workflows": ["wf-flow"]}),
            encoding="utf-8",
        )
        (fix_ws / ".github" / "copilot" / "teams" / "dev").mkdir(parents=True)
        (fix_ws / ".github" / "copilot" / "teams" / "dev" / "pack.json").write_text(
            json.dumps({"name": "dev", "agents": ["wf-bot"], "rules": ["wf-custom.md"], "workflows": ["wf-flow"]}),
            encoding="utf-8",
        )
        vr_fix = subprocess.run(
            [sys.executable, str(self.validate_refs_py), str(fix_ws), "--fix"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(vr_fix.returncode, 0, vr_fix.stdout + vr_fix.stderr)
        self.assertTrue((fix_ws / ".cursor" / "rules" / "wf-custom.mdc").is_file())
        self.assertTrue((fix_ws / ".cursor" / "commands" / "wf-flow.md").is_file())
        self.assertTrue((fix_ws / ".github" / "agents" / "wf-bot.agent.md").is_file())
        self.assertTrue((fix_ws / ".github" / "instructions" / "wf-custom.instructions.md").is_file())
        self.assertTrue((fix_ws / ".github" / "prompts" / "wf-flow.prompt.md").is_file())

        # Subsequent validate.py on fix_ws must also pass
        v_after_fix = subprocess.run(
            [sys.executable, str(self.validate_py), str(fix_ws)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(v_after_fix.returncode, 0, v_after_fix.stdout + v_after_fix.stderr)
        self.assertTrue((fix_ws / ".cursor" / "rules" / "wf-custom.mdc").read_text(encoding="utf-8").startswith("---\n"))
        self.assertTrue((fix_ws / ".github" / "instructions" / "wf-custom.instructions.md").read_text(encoding="utf-8").startswith("---\n"))

    def test_validators_resolve_workforces_teams_pack_with_github_ci_workflows(self):
        """Cursor workspace with .github/workflows/ci.yml and workforces/teams/custom/pack.json passes both validators."""
        import subprocess
        import resolve_manifest as rm

        ws = self.ws / "cursor_with_ci"
        ws.mkdir(parents=True)
        profiles = ca.load_host_profiles(str(REPO_ROOT))
        manifest = rm.resolve_manifest(str(REPO_ROOT), str(ws), teams_arg="none")
        ca.install_compiled_hosts(str(REPO_ROOT), str(ws), ["cursor"], manifest, dry_run=False)
        ca.save_install_config(str(ws), ["cursor"], "project", [], profiles)
        (ws / ".github" / "workflows").mkdir(parents=True)
        (ws / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
        custom_team = ws / "workforces" / "teams" / "custom"
        custom_team.mkdir(parents=True)
        (custom_team / "pack.json").write_text(
            json.dumps({"id": "custom", "name": "Custom", "agents": ["wf-project-manager"], "rules": ["wf-base"], "skills": ["wf-plan"]}),
            encoding="utf-8",
        )
        r_val = subprocess.run([sys.executable, str(self.validate_py), str(ws)], capture_output=True, text=True, timeout=20)
        r_ref = subprocess.run([sys.executable, str(self.validate_refs_py), str(ws)], capture_output=True, text=True, timeout=20)
        self.assertEqual(r_val.returncode, 0, r_val.stdout + r_val.stderr)
        self.assertEqual(r_ref.returncode, 0, r_ref.stdout + r_ref.stderr)

    def test_validate_sidecar_rejects_malformed_types_and_bad_plugin_matcher_caps(self):
        """validate.py rejects invalid plugin matcher_capabilities and non-dict hosts overrides without tracebacks."""
        import subprocess

        bad_ws = self.ws / "bad_sidecars"
        (bad_ws / "config" / "hosts").mkdir(parents=True)
        (bad_ws / "plugins" / "wf-bad").mkdir(parents=True)
        (bad_ws / "plugins" / "wf-bad" / "plugin.json").write_text(
            json.dumps({"kind": "plugin", "name": "wf-bad", "description": "Bad", "hooks": {"PostToolUse": [{"matcher_capabilities": ["telepathy"], "hooks": []}]}}),
            encoding="utf-8",
        )
        (bad_ws / "agents").mkdir()
        (bad_ws / "agents" / "wf-bad.md").write_text("---\nname: wf-bad\ndescription: Bad\n---\n", encoding="utf-8")
        (bad_ws / "agents" / "wf-bad.json").write_text(
            json.dumps({"kind": "agent", "name": "wf-bad", "description": "Bad", "hosts": ["claude"]}),
            encoding="utf-8",
        )
        res = subprocess.run([sys.executable, str(self.validate_py), str(bad_ws)], capture_output=True, text=True, timeout=20)
        self.assertEqual(res.returncode, 1)
        self.assertNotIn("Traceback", res.stderr)
        self.assertIn("unknown matcher_capabilities", res.stdout)
        self.assertIn("'hosts' must be a JSON object", res.stdout)

    def test_validate_references_catches_broken_wf_links_on_all_teams_and_partial_installs(self):
        """validate-references.py catches broken wf-* links on --teams all and bogus wf-* typos on partial installs."""
        import subprocess
        import resolve_manifest as rm

        profiles = ca.load_host_profiles(str(REPO_ROOT))

        # 1. Full --teams all install must catch any broken intra-host wf-* link
        ws_all = self.ws / "full_teams_broken_wf"
        ws_all.mkdir(parents=True)
        m_all = rm.resolve_manifest(str(REPO_ROOT), str(ws_all), teams_arg="all")
        s_all = ca.install_compiled_hosts(str(REPO_ROOT), str(ws_all), ["claude"], m_all, dry_run=False)
        rm.save_installed_manifest(str(ws_all), "v1", m_all["installed_teams"], s_all["installed_files"], hosts=["claude"])
        clean_res = subprocess.run([sys.executable, str(self.validate_refs_py), str(ws_all)], capture_output=True, text=True, timeout=25)
        self.assertEqual(clean_res.returncode, 0, clean_res.stdout + clean_res.stderr)

        cc_skill = ws_all / ".claude" / "skills" / "wf-clean-coder" / "SKILL.md"
        cc_skill.write_text(
            cc_skill.read_text(encoding="utf-8") + "\nSee [bad](../../agents/wf-nonexistent-typo.md).\n",
            encoding="utf-8",
        )
        broken_all = subprocess.run([sys.executable, str(self.validate_refs_py), str(ws_all)], capture_output=True, text=True, timeout=25)
        self.assertEqual(broken_all.returncode, 1, "Expected broken wf-* link to fail on --teams all workspace")
        self.assertIn("wf-nonexistent-typo.md", broken_all.stdout)

        # 2. Partial --teams dev install allows uninstalled canonical peer (wf-marketer) but rejects nonexistent wf-* typo
        ws_dev = self.ws / "partial_dev_typo"
        ws_dev.mkdir(parents=True)
        m_dev = rm.resolve_manifest(str(REPO_ROOT), str(ws_dev), teams_arg="dev")
        s_dev = ca.install_compiled_hosts(str(REPO_ROOT), str(ws_dev), ["claude"], m_dev, dry_run=False)
        ca.save_install_config(str(ws_dev), ["claude"], "project", m_dev["installed_teams"], profiles)
        rm.save_installed_manifest(str(ws_dev), "v1", m_dev["installed_teams"], s_dev["installed_files"], hosts=["claude"])

        dev_skill = ws_dev / ".claude" / "skills" / "wf-clean-coder" / "SKILL.md"
        orig_text = dev_skill.read_text(encoding="utf-8")
        dev_skill.write_text(orig_text + "\nOptional cross-pack peer: [Marketer](../../agents/wf-marketer.md).\n", encoding="utf-8")
        ok_peer = subprocess.run([sys.executable, str(self.validate_refs_py), str(ws_dev)], capture_output=True, text=True, timeout=25)
        self.assertEqual(ok_peer.returncode, 0, ok_peer.stdout + ok_peer.stderr)

        dev_skill.write_text(orig_text + "\nTypo link: [Ghost](../../agents/wf-nonexistent-typo.md).\n", encoding="utf-8")
        bad_typo = subprocess.run([sys.executable, str(self.validate_refs_py), str(ws_dev)], capture_output=True, text=True, timeout=25)
        self.assertEqual(bad_typo.returncode, 1, "Expected nonexistent wf-* typo to fail even on partial-team install")
        self.assertIn("wf-nonexistent-typo.md", bad_typo.stdout)


class TestCompilerAndPruneEdgeCases(unittest.TestCase):
    """Covers dry-run vs live write count parity and corrupt/partial config & settings resilience."""

    def setUp(self):
        import prune_team as pt
        import resolve_manifest as rm

        self.pt = pt
        self.rm = rm
        self.profiles = ca.load_host_profiles(str(REPO_ROOT))
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target = Path(self.temp_dir.name)
        (self.target / "workforces").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_written_count_matches_live_compile_across_all_hosts(self):
        """dry_run=True and dry_run=False report identical file write counts without double-counting wf-management/hosts."""
        all_five = ["antigravity", "claude", "grok", "copilot", "cursor"]
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev")
        dry_summary = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), all_five, manifest, dry_run=True)
        live_summary = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), all_five, manifest, dry_run=False)
        self.assertEqual(dry_summary["written"], live_summary["written"])
        self.assertEqual(sorted(dry_summary["installed_files"]), sorted(live_summary["installed_files"]))

    def test_corrupt_claude_settings_and_corrupt_or_partial_config_resilience(self):
        """Malformed .claude/settings.json and corrupt/partial workforces/config.json do not crash or clobber state."""
        manifest = self.rm.resolve_manifest(str(REPO_ROOT), str(self.target), teams_arg="dev,design")

        # 4a: Corrupt and non-dict .claude/settings.json must not raise or overwrite user file
        settings_path = self.target / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        for idx, bad_raw in enumerate(("{corrupt json", "[]")):
            settings_path.write_text(bad_raw, encoding="utf-8")
            summary = ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["claude"], manifest, dry_run=False)
            self.assertGreater(len(summary["installed_files"]), 0)
            self.assertEqual(summary["written"] > 0, idx == 0)
            self.assertEqual(settings_path.read_text(encoding="utf-8"), bad_raw)

        # Heal settings.json and verify empty hosts + auto_detect_hosts=false falls back to detected .claude, not .agents
        settings_path.write_text("{}", encoding="utf-8")
        cfg_path = self.target / "workforces" / "config.json"
        cfg_path.write_text(json.dumps({"hosts": [], "auto_detect_hosts": False}), encoding="utf-8")
        resolved_hosts = ca.resolve_active_hosts(str(self.target), self.profiles, auto_detect=True)
        self.assertEqual(resolved_hosts, ["claude"])

        # 4b & 4c: Corrupt workforces/config.json is healed by prune_team and preserves repo_type='workforce'
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Type\n- type: workforce\n\n## Installed Teams\n- installed_teams:\n  - design\n  - dev\n",
            encoding="utf-8",
        )
        ca.install_compiled_hosts(str(REPO_ROOT), str(self.target), ["claude"], manifest, dry_run=False)
        cfg_path.write_text("{corrupt", encoding="utf-8")
        self.assertTrue(self.pt.prune_team("dev", target_dir=str(self.target), toolkit_root=str(REPO_ROOT)))
        healed = ca.load_install_config(str(self.target))
        self.assertIsNotNone(healed)
        self.assertEqual(healed["repo_type"], "workforce")
        self.assertEqual(healed["installed_teams"], ["design"])

        # Partial config.json omitting repo_type also preserves inferred repo_type='workforce'
        (self.target / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Type\n- type: workforce\n\n## Installed Teams\n- installed_teams:\n  - design\n  - dev\n",
            encoding="utf-8",
        )
        cfg_path.write_text(json.dumps({"hosts": ["claude"], "installed_teams": ["design", "dev"]}), encoding="utf-8")
        self.assertTrue(self.pt.prune_team("dev", target_dir=str(self.target), toolkit_root=str(REPO_ROOT)))
        after_partial = ca.load_install_config(str(self.target))
        self.assertEqual(after_partial["repo_type"], "workforce")


if __name__ == "__main__":
    unittest.main()


