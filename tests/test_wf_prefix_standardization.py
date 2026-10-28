#!/usr/bin/env python3
"""
Tests for wf- prefix standardization across skills, agents, rules, plugins,
team packs, brownfield update.sh migrations, and canvas agent resolution.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
CANVAS_SCRIPTS = REPO_ROOT / "skills" / "wf-canvas" / "scripts"
USAGE_SCRIPTS = REPO_ROOT / "skills" / "wf-usage-tracker" / "scripts"
UPDATE_SH = REPO_ROOT / "skills" / "wf-management" / "scripts" / "update.sh"

for _p in (CANVAS_SCRIPTS, USAGE_SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import server  # noqa: E402
import track_usage  # noqa: E402


def _parse_frontmatter(text: str) -> Dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip().strip("'\"")
    return result


class TestWfPrefixStandardization(unittest.TestCase):
    """Enforces wf- naming invariants across all repository primitives."""

    def test_all_skills_have_wf_prefix_without_workforce_stutter(self):
        skill_dirs = sorted(
            d for d in (REPO_ROOT / "skills").iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        self.assertEqual(len(skill_dirs), 39)
        for s_dir in skill_dirs:
            self.assertTrue(s_dir.name.startswith("wf-"), f"Unprefixed skill dir: {s_dir.name}")
            self.assertFalse(s_dir.name.startswith("wf-workforce-"), f"Stuttered skill dir: {s_dir.name}")
            fm = _parse_frontmatter((s_dir / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(fm.get("name"), s_dir.name)

    def test_all_agents_have_wf_prefix(self):
        agent_files = sorted((REPO_ROOT / "agents").glob("*.md"))
        self.assertEqual(len(agent_files), 13)
        for a_file in agent_files:
            self.assertTrue(a_file.stem.startswith("wf-"), f"Unprefixed agent: {a_file.name}")
            fm = _parse_frontmatter(a_file.read_text(encoding="utf-8"))
            self.assertEqual(fm.get("name"), a_file.stem)

    def test_all_rules_have_wf_prefix(self):
        rule_files = sorted((REPO_ROOT / "rules").glob("*.md"))
        self.assertEqual(len(rule_files), 9)
        for r_file in rule_files:
            self.assertTrue(r_file.stem.startswith("wf-"), f"Unprefixed rule: {r_file.name}")

    def test_all_plugins_and_hook_namespaces_have_wf_prefix(self):
        plugin_dirs = sorted(
            d for d in (REPO_ROOT / "plugins").iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        self.assertEqual(len(plugin_dirs), 3)
        for p_dir in plugin_dirs:
            self.assertTrue(p_dir.name.startswith("wf-"), f"Unprefixed plugin dir: {p_dir.name}")
            self.assertFalse(p_dir.name.startswith("wf-workforce-"))
            p_json = json.loads((p_dir / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(p_json.get("name"), p_dir.name)
            hooks_file = p_dir / "hooks.json"
            if hooks_file.exists():
                hooks_json = json.loads(hooks_file.read_text(encoding="utf-8"))
                for key in hooks_json:
                    self.assertTrue(key.startswith("wf-"), f"Unprefixed hook key: {key}")

    def test_all_team_packs_reference_existing_wf_assets(self):
        pack_files = sorted((REPO_ROOT / "teams").glob("*/pack.json"))
        self.assertEqual(len(pack_files), 10)
        for pack_file in pack_files:
            data = json.loads(pack_file.read_text(encoding="utf-8"))
            for agent in data.get("agents", []):
                self.assertTrue(agent.startswith("wf-"))
                self.assertTrue((REPO_ROOT / "agents" / f"{agent}.md").is_file())
            for rule in data.get("rules", []):
                self.assertTrue(rule.startswith("wf-"))
                self.assertTrue((REPO_ROOT / "rules" / rule).is_file())
            for skill in data.get("skills", []):
                self.assertTrue(skill.startswith("wf-"))
                self.assertTrue((REPO_ROOT / "skills" / skill / "SKILL.md").is_file())
            for plugin in data.get("plugins", []):
                self.assertTrue(plugin.startswith("wf-"))
                self.assertTrue((REPO_ROOT / "plugins" / plugin / "plugin.json").is_file())

    def test_canvas_resolve_task_agent_edge_cases(self):
        self.assertEqual(server.resolve_task_agent({}), "@wf-programmer")
        self.assertEqual(server.resolve_task_agent({"type": "unknown", "team": "unknown"}), "@wf-programmer")
        self.assertEqual(server.resolve_task_agent({"team": "advisor"}), "@wf-project-manager")
        self.assertEqual(server.resolve_task_agent({"team": "compliance"}), "@wf-operations")
        self.assertEqual(server.resolve_task_agent({"delegated_to": "@wf-programmer"}), "@wf-programmer")
        self.assertEqual(server.resolve_task_agent({"delegated_to": "@programmer"}), "@wf-programmer")
        self.assertEqual(server.resolve_task_agent({"assignee": "@designer"}), "@wf-designer")
        self.assertEqual(server.resolve_task_agent({"delegated_to": "@compliance"}), "@wf-operations")
        self.assertEqual(server.resolve_task_agent({"delegated_to": "@advisor"}), "@wf-project-manager")
        self.assertEqual(server.resolve_task_agent({"delegated_to": "@my-custom-bot"}), "@my-custom-bot")
        self.assertEqual(server.resolve_task_agent({"assignee": "@human", "team": "dev"}), "@wf-programmer")
        self.assertEqual(server.resolve_task_agent({"assignee": "@me", "team": "design"}), "@wf-designer")
        self.assertEqual(server.resolve_task_agent({"assignee": "@user", "team": "marketing"}), "@wf-marketer")

    def test_canvas_save_comment_normalizes_and_routes_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            tasks_dir = ws / "workforces" / "tasks"
            tasks_dir.mkdir(parents=True)
            t1 = tasks_dir / "task-human.md"
            t1.write_text(
                "---\nid: task-human\ntitle: Design hero\nassignee: '@human'\nteam: design\n---\nBody\n",
                encoding="utf-8",
            )
            res1 = server.save_comment(ws, {"target_id": "task-human", "comment": "Make hero bolder", "author": "@human"})
            self.assertEqual(res1.get("dispatched_agent"), "@wf-designer")

            t2 = tasks_dir / "task-legacy.md"
            t2.write_text(
                "---\nid: task-legacy\ntitle: Fix API\ndelegated_to: '@programmer'\n---\nBody\n",
                encoding="utf-8",
            )
            res2 = server.save_comment(ws, {"target_id": "task-legacy", "comment": "Refactor endpoint", "author": "@human"})
            self.assertEqual(res2.get("dispatched_agent"), "@wf-programmer")

    def test_usage_tracker_detects_all_wf_skills_without_path_false_positives(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "transcript.jsonl"
            records = [
                {
                    "type": "USER_INPUT",
                    "content": "Inspect /Users/dev/workforces/README.md and run /wf-dashboard then /wf-clean-coder",
                }
            ]
            transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
            metrics = track_usage.parse_transcript_file(str(transcript))
            self.assertIn("/wf-dashboard", metrics["workflows_triggered"])
            self.assertIn("/wf-clean-coder", metrics["workflows_triggered"])
            self.assertNotIn("/work", metrics["workflows_triggered"])

    def test_no_stale_unprefixed_commands_or_paths_in_assets(self):
        scan_files = (
            list((REPO_ROOT / "agents").glob("*.md"))
            + list((REPO_ROOT / "rules").glob("*.md"))
            + list((REPO_ROOT / "teams").glob("*/*.md"))
            + list((REPO_ROOT / "skills").glob("*/SKILL.md"))
            + list((REPO_ROOT / "skills").glob("*/scripts/*.py"))
            + list((REPO_ROOT / "skills").glob("*/web/*.js"))
        )
        forbidden = [
            (r"(?<![a-zA-Z0-9_/-])@advisor\b", "stale @advisor mention"),
            (r"(?<![a-zA-Z0-9_/.}-])/teams\b", "retired /teams command"),
            (r"/context\s+save\b", "retired /context save command"),
            (r"(?<![a-zA-Z0-9_/-])/sync\s+--strategy", "unprefixed /sync --strategy command"),
            (r"skills/workforce-canvas/", "stale skills/workforce-canvas/ path"),
        ]
        exempt_names = {"resolve_manifest.py", "validate-references.py", "server.py"}
        for fpath in scan_files:
            if fpath.name in exempt_names:
                continue
            text = fpath.read_text(encoding="utf-8")
            for pattern, label in forbidden:
                self.assertIsNone(
                    re.search(pattern, text),
                    f"Found {label} in {fpath.relative_to(REPO_ROOT)}",
                )

    def test_plugin_hooks_work_across_editors_and_plugin_cwd(self):
        integrity_hooks = json.loads((REPO_ROOT / "plugins" / "wf-integrity-plugin" / "hooks.json").read_text(encoding="utf-8"))
        integrity_cmd = integrity_hooks["wf-integrity"]["PostToolUse"][0]["hooks"][0]["command"]
        prog_hooks = json.loads((REPO_ROOT / "plugins" / "wf-programming-plugin" / "hooks.json").read_text(encoding="utf-8"))
        pre_cmd = prog_hooks["wf-programming"]["PreToolUse"][0]["hooks"][0]["command"]

        # 1. Consumer .claude workspace (no .agents or top-level skills/)
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            claude_scripts = ws / ".claude" / "skills" / "wf-management" / "scripts"
            claude_scripts.mkdir(parents=True)
            shutil.copy2(REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate-references.py", claude_scripts / "validate-references.py")
            (ws / "workforces" / "session-context").mkdir(parents=True)
            (ws / "README.md").write_text("Broken [missing](docs/missing-target.md)\n", encoding="utf-8")

            res = subprocess.run(integrity_cmd, shell=True, cwd=ws, input="{}", capture_output=True, text=True, timeout=30)
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
            self.assertTrue((ws / "docs" / "missing-target.md").is_file(), "Hook failed to locate .claude script or fix root ref")

            cg_scripts = ws / ".claude" / "skills" / "wf-code-graph" / "scripts"
            cg_scripts.mkdir(parents=True)
            for fname in ("pre_tool_hook.py", "pre_impact_analyzer.py", "graph_indexer.py"):
                shutil.copy2(REPO_ROOT / "skills" / "wf-code-graph" / "scripts" / fname, cg_scripts / fname)
            payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(ws / "README.md")}})
            res_pre = subprocess.run(pre_cmd, shell=True, cwd=ws, input=payload, capture_output=True, text=True, timeout=30)
            self.assertEqual(res_pre.returncode, 0, res_pre.stderr + res_pre.stdout)

        # 2. Antigravity plugin cwd (.agents/plugins/wf-integrity-plugin) must audit workspace root, not plugin folder
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            ag_scripts = ws / ".agents" / "skills" / "wf-management" / "scripts"
            plugin_cwd = ws / ".agents" / "plugins" / "wf-integrity-plugin"
            ag_scripts.mkdir(parents=True)
            plugin_cwd.mkdir(parents=True)
            shutil.copy2(REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate-references.py", ag_scripts / "validate-references.py")
            (ws / "README.md").write_text("Broken [missing](docs/from-plugin-cwd.md)\n", encoding="utf-8")

            res2 = subprocess.run(integrity_cmd, shell=True, cwd=plugin_cwd, input="{}", capture_output=True, text=True, timeout=30)
            self.assertEqual(res2.returncode, 0, res2.stderr + res2.stdout)
            self.assertTrue((ws / "docs" / "from-plugin-cwd.md").is_file(), "Hook executed from plugin cwd failed to scan workspace root")


class TestBrownfieldPrefixMigration(unittest.TestCase):
    """Verifies update.sh cleanly migrates pre-wf- consumer workspaces."""

    def _seed_legacy_workspace(self, ws_root: Path, with_manifest: bool, base_rel: str = ".agents") -> None:
        base = ws_root / base_rel
        (base / "agents").mkdir(parents=True)
        (base / "rules").mkdir(parents=True)
        (base / "skills" / "clean-coder" / "scripts" / "__pycache__").mkdir(parents=True)
        (base / "skills" / "workforce-management" / "scripts").mkdir(parents=True)
        (base / "plugins" / "workforce-programming-plugin").mkdir(parents=True)
        (ws_root / "workforces").mkdir(parents=True)

        (base / "agents" / "programmer.md").write_text("# Old\n", encoding="utf-8")
        (base / "rules" / "base.md").write_text("# Old Base\n", encoding="utf-8")
        (base / "skills" / "clean-coder" / "SKILL.md").write_text("# Old\n", encoding="utf-8")
        (base / "skills" / "clean-coder" / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"0")
        (base / "skills" / "workforce-management" / "SKILL.md").write_text("# Old\n", encoding="utf-8")
        (base / "plugins" / "workforce-programming-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        (ws_root / "GEMINI.md").write_text("Refer to `.agents/rules/base.md` and `wf-sync`.\n", encoding="utf-8")
        (ws_root / "CLAUDE.md").write_text("Refer to `.claude/rules/base.md`.\n", encoding="utf-8")
        (ws_root / "AGENTS.md").write_text("Refer to `.grok/rules/base.md`.\n", encoding="utf-8")
        (ws_root / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n",
            encoding="utf-8",
        )
        # Custom user-authored skill and agent that must NOT be deleted
        (base / "agents" / "my-custom-bot.md").write_text("# Custom Bot\n", encoding="utf-8")
        (base / "skills" / "my-custom-skill").mkdir(parents=True)
        (base / "skills" / "my-custom-skill" / "SKILL.md").write_text("# Custom Skill\n", encoding="utf-8")

        if with_manifest:
            manifest = {
                "installed_files": [
                    f"{base_rel}/agents/programmer.md",
                    f"{base_rel}/rules/base.md",
                    f"{base_rel}/skills/clean-coder/SKILL.md",
                    f"{base_rel}/skills/workforce-management/SKILL.md",
                    f"{base_rel}/plugins/workforce-programming-plugin/plugin.json",
                ]
            }
            (ws_root / "workforces" / ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def _assert_migrated_cleanly(self, ws_root: Path, base_rel: str = ".agents") -> None:
        base = ws_root / base_rel
        self.assertFalse((base / "agents" / "programmer.md").exists())
        self.assertFalse((base / "rules" / "base.md").exists())
        self.assertFalse((base / "skills" / "clean-coder").exists())
        self.assertFalse((base / "skills" / "workforce-management").exists())
        self.assertFalse((base / "plugins" / "workforce-programming-plugin").exists())

        self.assertTrue((base / "agents" / "wf-programmer.md").is_file())
        self.assertTrue((base / "rules" / "wf-base.md").is_file())
        self.assertTrue((base / "skills" / "wf-clean-coder" / "SKILL.md").is_file())
        self.assertTrue((base / "skills" / "wf-management" / "SKILL.md").is_file())
        self.assertTrue((base / "plugins" / "wf-programming-plugin" / "plugin.json").is_file())
        self.assertIn(".agents/rules/wf-base.md", (ws_root / "GEMINI.md").read_text(encoding="utf-8"))
        self.assertIn(".claude/rules/wf-base.md", (ws_root / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn(".grok/rules/wf-base.md", (ws_root / "AGENTS.md").read_text(encoding="utf-8"))

        # Custom user files preserved
        self.assertTrue((base / "agents" / "my-custom-bot.md").is_file())
        self.assertTrue((base / "skills" / "my-custom-skill" / "SKILL.md").is_file())

    def test_migration_with_prior_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws_root = Path(tmp)
            self._seed_legacy_workspace(ws_root, with_manifest=True)
            res = subprocess.run(
                ["bash", str(UPDATE_SH), str(ws_root), "--non-interactive", "--force"],
                capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
            )
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
            self._assert_migrated_cleanly(ws_root)

    def test_migration_without_prior_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws_root = Path(tmp)
            self._seed_legacy_workspace(ws_root, with_manifest=False)
            res = subprocess.run(
                ["bash", str(UPDATE_SH), str(ws_root), "--non-interactive", "--force"],
                capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
            )
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
            self._assert_migrated_cleanly(ws_root)

    def test_consumer_remote_clone_update_preserves_editor_base(self):
        """Running installed update.sh (no .git in toolkit dir) in .claude/.grok/.github/copilot must not create .agents/."""
        with tempfile.TemporaryDirectory() as upstream_tmp:
            upstream = Path(upstream_tmp).resolve() / "upstream-workforces"
            upstream.mkdir()
            for item in ("agents", "rules", "skills", "plugins", "teams", "README.md", "GEMINI.md"):
                src = REPO_ROOT / item
                dst = upstream / item
                if src.is_dir():
                    shutil.copytree(src, dst)
                elif src.is_file():
                    shutil.copy2(src, dst)
            subprocess.run(["git", "init", "-q"], cwd=upstream, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=upstream, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=upstream, check=True)
            subprocess.run(["git", "add", "."], cwd=upstream, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "snapshot"], cwd=upstream, check=True)

            for base_rel in (".claude", ".grok", ".github/copilot"):
                with self.subTest(editor_base=base_rel), tempfile.TemporaryDirectory() as ws_tmp:
                    ws_root = Path(ws_tmp)
                    self._seed_legacy_workspace(ws_root, with_manifest=False, base_rel=base_rel)
                    installed_scripts = ws_root / base_rel / "skills" / "wf-management" / "scripts"
                    shutil.copytree(REPO_ROOT / "skills" / "wf-management" / "scripts", installed_scripts)

                    env = os.environ.copy()
                    env["WORKFORCES_REPO"] = f"file://{upstream}"
                    res = subprocess.run(
                        ["bash", str(installed_scripts / "update.sh"), str(ws_root), "--non-interactive", "--force"],
                        capture_output=True, text=True, timeout=60, cwd=ws_root, env=env,
                    )
                    self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
                    self.assertFalse(
                        (ws_root / ".agents").exists(),
                        f"Remote-clone update.sh polluted {base_rel} workspace with spurious .agents/ directory!",
                    )
                    self._assert_migrated_cleanly(ws_root, base_rel=base_rel)

            # Verify clone failure exits non-zero and does NOT overwrite workforces/.version with 'unknown'
            with tempfile.TemporaryDirectory() as ws_tmp:
                ws_root = Path(ws_tmp)
                self._seed_legacy_workspace(ws_root, with_manifest=False, base_rel=".claude")
                version_file = ws_root / "workforces" / ".version"
                version_file.write_text("commit: abc1234\ndate: 2026-10-01\n", encoding="utf-8")
                installed_scripts = ws_root / ".claude" / "skills" / "wf-management" / "scripts"
                shutil.copytree(REPO_ROOT / "skills" / "wf-management" / "scripts", installed_scripts)
                bad_env = os.environ.copy()
                bad_env["WORKFORCES_REPO"] = f"file://{upstream}-nonexistent"
                res_bad = subprocess.run(
                    ["bash", str(installed_scripts / "update.sh"), str(ws_root), "--non-interactive", "--force"],
                    capture_output=True, text=True, timeout=30, cwd=ws_root, env=bad_env,
                )
                self.assertNotEqual(res_bad.returncode, 0)
                self.assertIn("commit: abc1234", version_file.read_text(encoding="utf-8"))

    def test_empty_legacy_dirs_pruned_and_custom_dirs_preserved(self):
        """Empty legacy workforce-*-plugin and unprefixed skill dirs must be pruned even without --force."""
        head_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            ws_root = Path(tmp)
            base = ws_root / ".agents"
            # Pre-install current toolkit first so core dirs exist
            (ws_root / "workforces").mkdir(parents=True)
            (ws_root / "workforces" / "workrules.md").write_text(
                "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n",
                encoding="utf-8",
            )
            init_res = subprocess.run(
                ["bash", str(UPDATE_SH), str(ws_root), "--non-interactive", "--force"],
                capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
            )
            self.assertEqual(init_res.returncode, 0, init_res.stderr + init_res.stdout)
            self.assertIn(head_hash, (ws_root / "workforces" / ".version").read_text(encoding="utf-8"))

            # Simulate leftover empty / junk-only legacy directories while version hash already matches HEAD
            (base / "plugins" / "workforce-programming-plugin").mkdir(parents=True)
            (base / "plugins" / "workforce-usage-plugin").mkdir(parents=True)
            (base / "plugins" / "workforce-integrity-plugin").mkdir(parents=True)
            (base / "plugins" / "workforce-integrity-plugin" / ".DS_Store").write_bytes(b"junk")
            (base / "skills" / "clean-coder" / "__pycache__").mkdir(parents=True)
            (base / "skills" / "clean-coder" / "__pycache__" / "mod.pyc").write_bytes(b"0")

            # Custom user directories (one empty, one legacy dir with custom user file) must survive
            (base / "plugins" / "my-custom-empty-plugin").mkdir(parents=True)
            (base / "plugins" / "workforce-social-plugin").mkdir(parents=True)
            (base / "plugins" / "workforce-social-plugin" / "custom-user-note.md").write_text("keep\n", encoding="utf-8")

            # Run update.sh WITHOUT --force to prove obsolete dirs trigger cleanup even at matching hash
            res = subprocess.run(
                ["bash", str(UPDATE_SH), str(ws_root), "--non-interactive"],
                capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
            )
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
            self.assertFalse((base / "plugins" / "workforce-programming-plugin").exists())
            self.assertFalse((base / "plugins" / "workforce-usage-plugin").exists())
            self.assertFalse((base / "plugins" / "workforce-integrity-plugin").exists())
            self.assertFalse((base / "skills" / "clean-coder").exists())
            self.assertTrue((base / "plugins" / "my-custom-empty-plugin").is_dir())
            self.assertTrue((base / "plugins" / "workforce-social-plugin" / "custom-user-note.md").is_file())

    def test_update_sh_dry_run_creates_zero_directories_or_files(self):
        """update.sh --dry must not mkdir skills/, plugins/, or teams/ or mutate any file."""
        with tempfile.TemporaryDirectory() as tmp:
            ws_root = Path(tmp)
            (ws_root / ".claude" / "agents").mkdir(parents=True)
            (ws_root / ".claude" / "agents" / "programmer.md").write_text("# Legacy\n", encoding="utf-8")
            (ws_root / "workforces").mkdir(parents=True)
            (ws_root / "workforces" / "workrules.md").write_text(
                "# Work Rules\n\n## Installed Teams\n- installed_teams:\n  - dev\n",
                encoding="utf-8",
            )

            def snapshot(root: Path):
                return sorted(str(p.relative_to(root)) for p in root.rglob("*"))

            before = snapshot(ws_root)
            res = subprocess.run(
                ["bash", str(UPDATE_SH), str(ws_root), "--dry", "--force", "--non-interactive"],
                capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
            )
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
            after = snapshot(ws_root)
            self.assertEqual(before, after, f"--dry mutated workspace paths: {set(after) ^ set(before)}")


class TestRemainingPrefixGaps(unittest.TestCase):
    """Covers docs/skills wf- accuracy, canvas /api/state normalization, and multi-editor validate.py."""

    def test_no_nonexistent_wf_commands_or_stale_refs_in_docs_and_skills(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/wf-consult", readme)

        launch_pack = (REPO_ROOT / "teams" / "launch" / "pack.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?<![a-zA-Z0-9_-])/?wf-launch(?!-playbook)\b", launch_pack))
        self.assertIn("wf-launch-playbook", launch_pack)
        self.assertIn("@wf-launcher", launch_pack)

        gemini_md = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")
        self.assertIn("/wf-plan", gemini_md)
        self.assertIn("/wf-sync", gemini_md)
        self.assertIn("/wf-advisor", gemini_md)
        self.assertIn("@wf-programmer", gemini_md)

        # No unprefixed markdown link labels pointing to wf-* files
        md_files = (
            list((REPO_ROOT / "agents").glob("*.md"))
            + list((REPO_ROOT / "rules").glob("*.md"))
            + list((REPO_ROOT / "teams").glob("*/*.md"))
            + list((REPO_ROOT / "skills").glob("*/SKILL.md"))
        )
        link_re = re.compile(r"\[`?([a-z][a-z0-9-]+)`?\]\(([^)]*wf-[a-z0-9-]+\.md)\)")
        for md in md_files:
            text = md.read_text(encoding="utf-8")
            for match in link_re.finditer(text):
                label, target = match.group(1), match.group(2)
                self.assertTrue(
                    label.startswith("wf-"),
                    f"Unprefixed link label [{label}]({target}) in {md.relative_to(REPO_ROOT)}",
                )

        # Team pack docs must not list retired unprefixed workflow bullets
        for rel in ("teams/design/pack.md", "teams/marketing/pack.md", "teams/social/pack.md"):
            txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("- `brand-context`", txt, rel)
            self.assertNotIn("- `social`", txt, rel)

        # Skills and tracker scripts must use wf-* reporter names, not clean/advisor/scribe
        for s_file in list((REPO_ROOT / "skills").glob("*/SKILL.md")) + list((REPO_ROOT / "skills").glob("*/scripts/*.py")):
            txt = s_file.read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"--reporter\s+(clean|advisor|scribe)\b", txt),
                f"Stale unprefixed --reporter in {s_file.relative_to(REPO_ROOT)}",
            )
            self.assertNotIn('default="scribe"', txt, str(s_file.relative_to(REPO_ROOT)))
            self.assertNotIn("default: `scribe`", txt, str(s_file.relative_to(REPO_ROOT)))

    def test_report_task_and_issue_default_reporter_is_wf_scribe(self):
        report_task = REPO_ROOT / "skills" / "wf-task-tracker" / "scripts" / "report-task.py"
        report_issue = REPO_ROOT / "skills" / "wf-issue-tracker" / "scripts" / "report-issue.py"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            t_res = subprocess.run(
                [sys.executable, str(report_task), "--title", "Prefix task", "--type", "dev", "--description", "Task body"],
                cwd=ws, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(t_res.returncode, 0, t_res.stderr + t_res.stdout)
            task_files = list((ws / "workforces" / "tasks").glob("*.md"))
            self.assertEqual(len(task_files), 1)
            self.assertRegex(task_files[0].read_text(encoding="utf-8"), r'reporter:\s*"?wf-scribe"?')

            i_res = subprocess.run(
                [sys.executable, str(report_issue), "--title", "Prefix issue", "--type", "bug", "--description", "Issue body"],
                cwd=ws, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(i_res.returncode, 0, i_res.stderr + i_res.stdout)
            issue_files = list((ws / "workforces" / "issues" / "inbox").glob("*.md"))
            self.assertEqual(len(issue_files), 1)
            self.assertRegex(issue_files[0].read_text(encoding="utf-8"), r'reporter:\s*"?wf-scribe"?')

    def test_canvas_state_normalizes_task_and_hypothesis_handles(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            tasks_dir = ws / "workforces" / "tasks"
            hyp_running = ws / "workforces" / "hypotheses" / "running"
            hyp_draft = ws / "workforces" / "hypotheses" / "draft"
            tasks_dir.mkdir(parents=True)
            hyp_running.mkdir(parents=True)
            hyp_draft.mkdir(parents=True)

            (tasks_dir / "t1.md").write_text(
                "---\nid: t1\ntitle: Legacy handles\nstatus: review\nassignee: '@programmer'\n"
                "delegated_to: programmer\nreporter: scribe\nreviewer: designer\n---\nBody\n",
                encoding="utf-8",
            )
            (tasks_dir / "t2.md").write_text(
                "---\nid: t2\ntitle: Nullish tilde\nstatus: todo\nassignee: ~\ndelegated_to: ~\nreporter: developer\n---\nBody\n",
                encoding="utf-8",
            )
            (tasks_dir / "t3.md").write_text(
                "---\nid: t3\ntitle: Human owned\nstatus: in_progress\nassignee: '@me'\ndelegated_to: unassigned\nreporter: '@human'\n---\nBody\n",
                encoding="utf-8",
            )
            (ws / "workforces" / "hypotheses" / "h1.md").write_text(
                "---\nid: h1\ntitle: Root hyp\nstatus: testing\nowner: '@growth'\n---\nBody\n",
                encoding="utf-8",
            )
            (hyp_running / "h2.md").write_text(
                "---\nid: h2\ntitle: Running hyp\nstatus: running\nowner: sales\n---\nBody\n",
                encoding="utf-8",
            )
            (hyp_draft / "h3.md").write_text(
                "---\nid: h3\ntitle: Draft hyp\nowner: marketing\n---\nBody\n",
                encoding="utf-8",
            )

            dummy = object.__new__(server.WorkforceCanvasHandler)
            dummy.root_dir = ws
            state = dummy.handle_get_state()

            by_id = {t["id"]: t for t in state["tasks"]}
            self.assertEqual(by_id["t1"]["assignee"], "@wf-programmer")
            self.assertEqual(by_id["t1"]["delegated_to"], "@wf-programmer")
            self.assertEqual(by_id["t1"]["reporter"], "@wf-scribe")
            self.assertEqual(by_id["t1"]["reviewer"], "@wf-designer")

            self.assertEqual(by_id["t2"]["assignee"], "")
            self.assertEqual(by_id["t2"]["delegated_to"], "")
            self.assertEqual(by_id["t2"]["reporter"], "@wf-programmer")
            self.assertEqual(by_id["t2"]["reviewer"], "")

            self.assertEqual(by_id["t3"]["assignee"], "@me")
            self.assertEqual(by_id["t3"]["delegated_to"], "")
            self.assertEqual(by_id["t3"]["reporter"], "@human")

            hyps = {h["id"]: h for h in state["hypotheses"]}
            self.assertEqual(set(hyps.keys()), {"h1", "h2", "h3"})
            self.assertEqual(hyps["h1"]["owner"], "@wf-growth")
            self.assertEqual(hyps["h2"]["owner"], "@wf-sales")
            self.assertEqual(hyps["h3"]["owner"], "@wf-marketer")
            self.assertEqual(hyps["h3"]["status"], "draft")

    def test_validate_py_supports_multi_editor_agents_and_teams(self):
        validate_py = REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate.py"

        # 1. Valid .claude workspace with pack.json and wf-programmer agent
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            base = ws / ".claude"
            (base / "agents").mkdir(parents=True)
            (base / "rules").mkdir(parents=True)
            (base / "skills" / "wf-clean-coder").mkdir(parents=True)
            (base / "plugins" / "wf-programming-plugin").mkdir(parents=True)
            (base / "teams" / "dev").mkdir(parents=True)

            (base / "agents" / "wf-programmer.md").write_text("---\nname: wf-programmer\ndescription: Dev\n---\n", encoding="utf-8")
            (base / "rules" / "wf-clean-coder.md").write_text("# Rule\n", encoding="utf-8")
            (base / "skills" / "wf-clean-coder" / "SKILL.md").write_text("---\nname: wf-clean-coder\ndescription: Skill\n---\n", encoding="utf-8")
            (base / "plugins" / "wf-programming-plugin" / "plugin.json").write_text('{"name": "wf-programming-plugin"}', encoding="utf-8")
            (base / "teams" / "dev" / "pack.json").write_text(
                json.dumps({
                    "name": "dev",
                    "agents": ["wf-programmer"],
                    "rules": ["wf-clean-coder.md"],
                    "skills": ["wf-clean-coder"],
                    "plugins": ["wf-programming-plugin"],
                }),
                encoding="utf-8",
            )
            ok = subprocess.run([sys.executable, str(validate_py), str(ws)], capture_output=True, text=True, timeout=20)
            self.assertEqual(ok.returncode, 0, ok.stderr + ok.stdout)

        # 2. Invalid .grok agent frontmatter must fail
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".grok" / "agents").mkdir(parents=True)
            (ws / ".grok" / "agents" / "wf-broken.md").write_text("# Missing frontmatter\n", encoding="utf-8")
            bad = subprocess.run([sys.executable, str(validate_py), str(ws)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(bad.returncode, 0)

        # 3. Missing pack.json asset in .github/copilot/teams must fail
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".github" / "copilot" / "teams" / "dev").mkdir(parents=True)
            (ws / ".github" / "copilot" / "teams" / "dev" / "pack.json").write_text(
                json.dumps({"name": "dev", "agents": ["wf-programmer"]}),
                encoding="utf-8",
            )
            bad_pack = subprocess.run([sys.executable, str(validate_py), str(ws)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(bad_pack.returncode, 0)

        # 4. Legacy team.json under .claude/teams fails without --fix, succeeds and creates stub with --fix
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            team_dir = ws / ".claude" / "teams" / "ops"
            team_dir.mkdir(parents=True)
            (team_dir / "team.json").write_text(
                json.dumps({"name": "Ops", "personas": ["ops-lead.md"]}),
                encoding="utf-8",
            )
            no_fix = subprocess.run([sys.executable, str(validate_py), str(ws)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(no_fix.returncode, 0)
            with_fix = subprocess.run([sys.executable, str(validate_py), "--fix", str(ws)], capture_output=True, text=True, timeout=20)
            self.assertEqual(with_fix.returncode, 0, with_fix.stderr + with_fix.stdout)
            self.assertTrue((team_dir / "ops-lead.md").is_file())

    def test_shallow_clone_prunes_all_legacy_files_and_empty_legacy_dirs(self) -> None:
        """Shallow-clone (gitless) toolkit updates must prune all historical files and empty legacy dirs."""
        resolve_py = REPO_ROOT / "skills" / "wf-management" / "scripts" / "resolve_manifest.py"
        setup_sh = REPO_ROOT / "skills" / "wf-management" / "scripts" / "setup.sh"
        update_sh = REPO_ROOT / "skills" / "wf-management" / "scripts" / "update.sh"

        with tempfile.TemporaryDirectory() as shallow_src_tmp, tempfile.TemporaryDirectory() as ws_tmp:
            shallow_root = Path(shallow_src_tmp)
            for folder in ("agents", "rules", "skills", "plugins", "teams"):
                shutil.copytree(REPO_ROOT / folder, shallow_root / folder)

            ws = Path(ws_tmp)
            base = ws / ".agents"
            for rel_file in (
                "plugins/workforce-programming-plugin/hooks/hooks.json",
                "plugins/workforce-integrity-plugin/hooks/hooks.json",
                "plugins/workforce-usage-plugin/hooks/hooks.json",
                "skills/workforce-canvas/scripts/heartbeat_watcher.py",
                "agents/heartbeat.md",
                "rules/token-parsimony.md",
            ):
                p = base / rel_file
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("legacy\n", encoding="utf-8")

            for empty_rel in (
                "skills/plan",
                "skills/advisor",
                "skills/sync",
                "skills/dashboard",
                "plugins/workforce-retired-plugin",
                "plugins/my-custom-empty-plugin",
                "skills/my-custom-skill",
            ):
                (base / empty_rel).mkdir(parents=True, exist_ok=True)

            res = subprocess.run(
                [
                    sys.executable,
                    str(resolve_py),
                    "--target",
                    str(ws),
                    "--teams",
                    "dev",
                    "--toolkit-root",
                    str(shallow_root),
                    "--prune-obsolete",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            for pruned_rel in (
                "plugins/workforce-programming-plugin",
                "plugins/workforce-integrity-plugin",
                "plugins/workforce-usage-plugin",
                "plugins/workforce-retired-plugin",
                "skills/workforce-canvas",
                "skills/plan",
                "skills/advisor",
                "skills/sync",
                "skills/dashboard",
                "agents/heartbeat.md",
                "rules/token-parsimony.md",
            ):
                self.assertFalse((base / pruned_rel).exists(), f"Expected shallow-clone prune of {pruned_rel}")
            self.assertTrue((base / "plugins" / "my-custom-empty-plugin").is_dir())
            self.assertTrue((base / "skills" / "my-custom-skill").is_dir())

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            setup_res = subprocess.run(
                ["bash", str(setup_sh), str(ws), "--editor", "antigravity", "--teams", "dev", "--non-interactive"],
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(setup_res.returncode, 0, setup_res.stderr)

            legacy_plugin = ws / ".agents" / "plugins" / "workforce-retired-plugin"
            legacy_skill = ws / ".agents" / "skills" / "plan"
            legacy_plugin.mkdir(parents=True)
            legacy_skill.mkdir(parents=True)

            env = os.environ.copy()
            env["WORKFORCES_UPDATE_SOURCE_DIR"] = str(REPO_ROOT)

            # --dry-run alias must perform zero mutations
            dry_res = subprocess.run(
                ["bash", str(update_sh), str(ws), "--dry-run", "--non-interactive"],
                capture_output=True,
                text=True,
                env=env,
                timeout=45,
            )
            self.assertEqual(dry_res.returncode, 0, dry_res.stderr + dry_res.stdout)
            self.assertTrue(legacy_plugin.is_dir())
            self.assertTrue(legacy_skill.is_dir())

            # Live update WITHOUT --force on partial-team install must detect HAS_OBSOLETE and prune
            live_res = subprocess.run(
                ["bash", str(update_sh), str(ws), "--non-interactive"],
                capture_output=True,
                text=True,
                env=env,
                timeout=45,
            )
            self.assertEqual(live_res.returncode, 0, live_res.stderr + live_res.stdout)
            self.assertFalse(legacy_plugin.exists())
            self.assertFalse(legacy_skill.exists())

    def test_canvas_server_normalizes_tilde_and_legacy_handles_in_mutations(self) -> None:
        """update_task_file, create_task_file, and save_comment must normalize ~, human, and legacy handles."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            tasks_dir = ws / "workforces" / "tasks"
            tasks_dir.mkdir(parents=True)

            # 1. Task with YAML null `delegated_to: ~` and `assignee: "@user"` transitioned to in_progress
            tilde_task = tasks_dir / "20261027-tilde-delegate.md"
            tilde_task.write_text(
                '---\n'
                'id: "task-tilde"\n'
                'title: "Fix Tilde Delegation"\n'
                'type: "dev"\n'
                'status: "todo"\n'
                'assignee: "@user"\n'
                'delegated_to: ~\n'
                '---\nBody\n',
                encoding="utf-8",
            )
            updated = server.update_task_file(ws, "20261027-tilde-delegate.md", {"status": "in_progress"})
            self.assertEqual(updated.get("delegated_to"), "@wf-programmer")
            self.assertEqual(updated.get("assignee"), "@wf-programmer")

            # 2. Explicit legacy handle in update_task_file is normalized to @wf-*
            legacy_task = tasks_dir / "20261027-legacy-delegate.md"
            legacy_task.write_text(
                '---\n'
                'id: "task-legacy"\n'
                'title: "Design Banner"\n'
                'type: "design"\n'
                'status: "todo"\n'
                'delegated_to: "@designer"\n'
                '---\nBody\n',
                encoding="utf-8",
            )
            updated_legacy = server.update_task_file(
                ws, "20261027-legacy-delegate.md", {"status": "in_progress", "delegated_to": "@designer"}
            )
            self.assertEqual(updated_legacy.get("delegated_to"), "@wf-designer")
            self.assertEqual(updated_legacy.get("assignee"), "@wf-designer")

            # 3. create_task_file normalizes legacy reporter and assignee
            created = server.create_task_file(
                ws,
                {
                    "title": "Audit Copy",
                    "type": "marketing",
                    "reporter": "scribe",
                    "assignee": "marketer",
                    "status": "todo",
                },
            )
            self.assertEqual(created.get("reporter"), "@wf-scribe")
            self.assertEqual(created.get("assignee"), "@wf-marketer")

            # 4. save_comment dispatches human inquiries from @user and directives from @me
            comment_res = server.save_comment(
                ws,
                {
                    "target_id": "task-tilde",
                    "target_type": "task",
                    "comment": "Please check edge cases?",
                    "author": "@user",
                },
            )
            self.assertEqual(comment_res.get("dispatched_agent"), "@wf-researcher")

            directive_res = server.save_comment(
                ws,
                {
                    "target_id": "task-tilde",
                    "target_type": "task",
                    "comment": "Add rate limit retry backoff",
                    "author": "@me",
                },
            )
            self.assertEqual(directive_res.get("dispatched_agent"), "@wf-programmer")

    def test_canvas_js_resolves_human_and_team_agent_badges_and_hypothesis_owner(self) -> None:
        """canvas.js must never render human handles as bot badges, must resolve team agents, and must render hypothesis owners."""
        canvas_js = (REPO_ROOT / "skills" / "wf-canvas" / "web" / "canvas.js").read_text(encoding="utf-8")
        self.assertIn("resolveTaskAgentBadge", canvas_js)
        self.assertRegex(canvas_js, r"renderHypothesesStage[\s\S]*?h\.owner")

        if shutil.which("node"):
            check_script = (
                "const fs = require('fs');\n"
                f"const src = fs.readFileSync({json.dumps(str(REPO_ROOT / 'skills' / 'wf-canvas' / 'web' / 'canvas.js'))}, 'utf8');\n"
                "const m = src.match(/function resolveTaskAgentBadge\\([\\s\\S]*?\\n  \\}/);\n"
                "if (!m) { console.error('Missing resolveTaskAgentBadge'); process.exit(2); }\n"
                "const fn = new Function(m[0] + '; return resolveTaskAgentBadge;')();\n"
                "const r1 = fn({ assignee: '@user', delegated_to: '', team: 'marketing' });\n"
                "const r2 = fn({ assignee: '@me', delegated_to: '~', team: 'design' });\n"
                "const r3 = fn({ assignee: 'sales', delegated_to: '', team: 'dev' });\n"
                "console.log(JSON.stringify([r1, r2, r3]));\n"
            )
            node_res = subprocess.run(["node", "-e", check_script], capture_output=True, text=True, timeout=15)
            self.assertEqual(node_res.returncode, 0, node_res.stderr)
            self.assertEqual(json.loads(node_res.stdout.strip()), ["@wf-marketer", "@wf-designer", "@wf-sales"])

    def test_validate_py_supports_stem_rules_grok_commands_and_editor_team_json(self) -> None:
        """validate.py must accept rule stems, .grok/commands workflows, and editor-base team.json references."""
        validate_py = REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate.py"

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            grok = ws / ".grok"
            (grok / "rules").mkdir(parents=True)
            (grok / "commands").mkdir(parents=True)
            (grok / "teams" / "dev").mkdir(parents=True)
            (grok / "rules" / "wf-clean-coder.md").write_text("# Rule\n", encoding="utf-8")
            (grok / "commands" / "wf-plan.md").write_text("# Command\n", encoding="utf-8")
            (grok / "teams" / "dev" / "pack.json").write_text(
                json.dumps({"name": "dev", "rules": ["wf-clean-coder"], "workflows": ["wf-plan"]}),
                encoding="utf-8",
            )

            claude = ws / ".claude"
            (claude / "rules").mkdir(parents=True)
            (claude / "teams" / "ops").mkdir(parents=True)
            (claude / "rules" / "wf-base.md").write_text("# Base\n", encoding="utf-8")
            (claude / "teams" / "ops" / "team.json").write_text(
                json.dumps({"name": "Ops", "rules": ["rules/wf-base.md"]}),
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(validate_py), str(ws)], capture_output=True, text=True, timeout=20)
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_fresh_consumer_installs_pass_validate_and_validate_references(self) -> None:
        """Fresh setup.sh consumer workspaces across editors and team subsets must pass validate.py and validate-references.py."""
        setup_sh = REPO_ROOT / "skills" / "wf-management" / "scripts" / "setup.sh"
        validate_py = REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate.py"
        validate_refs_py = REPO_ROOT / "skills" / "wf-management" / "scripts" / "validate-references.py"

        matrix = [
            ("vscode", "marketing"),
            ("claude", "advisor"),
            ("grok", "dev"),
            ("antigravity", "all"),
        ]
        for editor, teams in matrix:
            with tempfile.TemporaryDirectory() as tmp:
                ws = Path(tmp)
                s_res = subprocess.run(
                    ["bash", str(setup_sh), str(ws), "--editor", editor, "--teams", teams, "--non-interactive"],
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                self.assertEqual(s_res.returncode, 0, f"{editor}/{teams} setup failed: {s_res.stderr}")

                vr_res = subprocess.run(
                    [sys.executable, str(validate_refs_py), str(ws)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    vr_res.returncode,
                    0,
                    f"{editor}/{teams} validate-references failed:\n{vr_res.stdout}\n{vr_res.stderr}",
                )

                v_res = subprocess.run(
                    [sys.executable, str(validate_py), str(ws)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    v_res.returncode,
                    0,
                    f"{editor}/{teams} validate.py failed:\n{v_res.stdout}\n{v_res.stderr}",
                )


if __name__ == "__main__":
    unittest.main()
