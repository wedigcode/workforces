#!/usr/bin/env python3
"""
Test Suite: Workforces Phase 2 Modernization End-to-End Test Suite
Authoritative opaque-box verification across Tiers 1 through 4:
  - Tier 1: Feature Coverage (R1, R2, R3)
  - Tier 2: Boundary & Corner Cases (R4, CLI robustness, BVA)
  - Tier 3: Cross-Feature Interactions (R2, R3, R4 team pack & manifest integration)
  - Tier 4: Real-World Scenarios (Greenfield setup, brownfield migration, multi-editor parity)
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
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"
TEAMS_DIR = REPO_ROOT / "teams"
PLUGINS_DIR = REPO_ROOT / "plugins"
SCRIPTS_DIR = SKILLS_DIR / "workforce-management" / "scripts"

SETUP_SCRIPT = SCRIPTS_DIR / "setup.sh"
UPDATE_SCRIPT = SCRIPTS_DIR / "update.sh"
RESOLVE_MANIFEST_SCRIPT = SCRIPTS_DIR / "resolve_manifest.py"
PRUNE_TEAM_SCRIPT = SCRIPTS_DIR / "prune_team.py"
VALIDATE_REFERENCES_SCRIPT = SCRIPTS_DIR / "validate-references.py"
PERSONAL_SYNC_SCRIPT = SKILLS_DIR / "task-tracker" / "scripts" / "personal_sync.py"

# Authoritative Constants derived from PROJECT.md and ORIGINAL_REQUEST.md
EXPECTED_SKILL_COUNT = 37
EXPECTED_EXECUTION_AGENTS = {
    "programmer.md",
    "designer.md",
    "marketer.md",
    "researcher.md",
    "social.md",
    "sales.md",
    "growth.md",
    "operations.md",
    "launcher.md",
    "scribe.md",
    "project-manager.md",
    "unbundler.md",
    "disruptor.md",
}
EXPECTED_AGENT_COUNT = 13


def parse_yaml_frontmatter(content: str) -> Optional[Dict[str, str]]:
    """
    Parse YAML frontmatter enclosed by --- delimiters without third-party dependencies.
    Returns a dictionary of key-value pairs or None if no valid frontmatter exists.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)
    fields: Dict[str, str] = {}

    pattern = re.compile(r"^([a-zA-Z0-9_-]+):[ \t]*(.*)$", re.MULTILINE)
    matches = list(pattern.finditer(fm_text))
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        val_start = m.end()
        val_end = matches[i + 1].start() if i + 1 < len(matches) else len(fm_text)
        raw_val = m.group(2) + "\n" + fm_text[val_start:val_end]
        val = raw_val.strip()
        if val.startswith(">-") or val.startswith(">") or val.startswith("|"):
            val = re.sub(r"^[>|]-?\s*", "", val).strip()
        fields[key] = val

    return fields


def parse_agent_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse YAML frontmatter of an agent markdown file, supporting strings,
    booleans, and list items.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)
    fields: Dict[str, Any] = {}

    pattern = re.compile(r"^([a-zA-Z0-9_-]+):[ \t]*(.*)$", re.MULTILINE)
    matches = list(pattern.finditer(fm_text))
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        val_start = m.end()
        val_end = matches[i + 1].start() if i + 1 < len(matches) else len(fm_text)
        raw_val = (m.group(2) + "\n" + fm_text[val_start:val_end]).strip()

        # Parse boolean values
        if raw_val.lower() == "true":
            fields[key] = True
        elif raw_val.lower() == "false":
            fields[key] = False
        # Parse list items (- item)
        elif "\n-" in raw_val or raw_val.startswith("-"):
            items = []
            for line in raw_val.splitlines():
                line = line.strip()
                if line.startswith("-"):
                    items.append(line[1:].strip().strip("\"'"))
            fields[key] = items
        else:
            clean_val = raw_val
            if clean_val.startswith(">-") or clean_val.startswith(">") or clean_val.startswith("|"):
                clean_val = re.sub(r"^[>|]-?\s*", "", clean_val).strip()
            fields[key] = clean_val.strip("\"'")

    return fields


# ==============================================================================
# TIER 1: FEATURE COVERAGE (Requirement R1, R2, R3)
# ==============================================================================

class TestPhase2Tier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 Feature Coverage:
    - R1: YAML frontmatter on all 37 skills, no slash commands
    - R2: Deletion of compliance.md & advisor.md, exactly 13 execution agents remain
    - R3: Retirement of wf-work, task query consolidation in wf-sync & task-tracker
    """

    def test_all_37_skills_frontmatter_presence_and_validity(self):
        """Verify all skills under skills/ (exactly 37, excluding wf-work) have valid frontmatter."""
        skill_dirs = [d for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
        skill_names = {d.name for d in skill_dirs}

        # Requirement R3: wf-work must not be present
        self.assertNotIn(
            "wf-work",
            skill_names,
            "Legacy orchestrator 'skills/wf-work' must be completely removed in Phase 2.",
        )

        # Requirement R1 & Acceptance Criteria: exactly 37 skills
        self.assertEqual(
            len(skill_dirs),
            EXPECTED_SKILL_COUNT,
            f"Expected exactly {EXPECTED_SKILL_COUNT} skills under skills/, found {len(skill_dirs)}: {sorted(skill_names)}",
        )

        # Verify each skill contains SKILL.md with valid name and non-empty description
        for s_dir in skill_dirs:
            skill_file = s_dir / "SKILL.md"
            self.assertTrue(
                skill_file.is_file(),
                f"Missing SKILL.md in skill directory: {s_dir.name}",
            )
            content = skill_file.read_text(encoding="utf-8")
            fm = parse_yaml_frontmatter(content)
            self.assertIsNotNone(
                fm,
                f"Invalid or missing YAML frontmatter in {skill_file}",
            )
            self.assertEqual(
                fm.get("name"),
                s_dir.name,
                f"Frontmatter name '{fm.get('name')}' does not match directory '{s_dir.name}'",
            )
            desc = fm.get("description", "")
            self.assertTrue(
                bool(desc and desc.strip()),
                f"Skill '{s_dir.name}' has empty or missing description in frontmatter",
            )
            self.assertGreaterEqual(
                len(desc.strip()),
                40,
                f"Skill '{s_dir.name}' description too brief ({len(desc.strip())} chars); must provide rich semantic context",
            )

    def test_zero_slash_command_triggers_in_skill_descriptions(self):
        """Verify zero occurrences of slash commands ('Triggers on /wf-', '/wf-') in skill descriptions."""
        skill_dirs = [d for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
        violations = []

        slash_trigger_pattern = re.compile(r"(Triggers on /|/wf-[a-z0-9_-]+)", re.IGNORECASE)

        for s_dir in skill_dirs:
            if s_dir.name == "wf-work":
                continue  # Covered by test_complete_removal_of_wf_work_skill
            skill_file = s_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            content = skill_file.read_text(encoding="utf-8")
            fm = parse_yaml_frontmatter(content)
            if not fm:
                continue
            desc = fm.get("description", "")
            if slash_trigger_pattern.search(desc):
                violations.append((s_dir.name, desc))

        self.assertEqual(
            violations,
            [],
            f"Found {len(violations)} skills with tautological slash-command triggers in description: "
            f"{[v[0] for v in violations]}",
        )

    def test_deletion_of_compliance_pseudo_agent(self):
        """Verify agents/compliance.md is deleted and file integrity capability is preserved in integrity-validator."""
        compliance_agent = AGENTS_DIR / "compliance.md"
        self.assertFalse(
            compliance_agent.exists(),
            f"Pseudo-agent {compliance_agent} must be deleted per Requirement R2.",
        )

        # Capability must be preserved in integrity-validator skill
        integrity_skill = SKILLS_DIR / "integrity-validator" / "SKILL.md"
        self.assertTrue(
            integrity_skill.is_file(),
            f"File integrity capability must be retained under {integrity_skill}",
        )

    def test_deletion_of_advisor_agent(self):
        """Verify agents/advisor.md is deleted and strategic advisory is consolidated in skills/wf-advisor/."""
        advisor_agent = AGENTS_DIR / "advisor.md"
        self.assertFalse(
            advisor_agent.exists(),
            f"Persona conflict {advisor_agent} must be deleted per Requirement R2.",
        )

        # Strategic advisory must be retained as universal skill
        wf_advisor_skill = SKILLS_DIR / "wf-advisor" / "SKILL.md"
        self.assertTrue(
            wf_advisor_skill.is_file(),
            f"Strategic advisory must be retained as universal skill under {wf_advisor_skill}",
        )

    def test_exactly_13_specialized_execution_agents_remain(self):
        """Verify agents/ contains exactly the 13 specialized execution agents with valid frontmatter."""
        agent_files = sorted(AGENTS_DIR.glob("*.md"))
        agent_names = {f.name for f in agent_files}

        self.assertEqual(
            agent_names,
            EXPECTED_EXECUTION_AGENTS,
            f"Agent inventory mismatch. Expected: {sorted(EXPECTED_EXECUTION_AGENTS)}, Found: {sorted(agent_names)}",
        )
        self.assertEqual(
            len(agent_files),
            EXPECTED_AGENT_COUNT,
            f"Expected exactly {EXPECTED_AGENT_COUNT} execution agents, found {len(agent_files)}",
        )

        # Validate schema of each execution agent
        for a_path in agent_files:
            content = a_path.read_text(encoding="utf-8")
            fm = parse_agent_frontmatter(content)
            self.assertIsNotNone(fm, f"Agent {a_path.name} has invalid YAML frontmatter")
            self.assertEqual(
                fm.get("name"),
                a_path.stem,
                f"Agent name '{fm.get('name')}' does not match file stem '{a_path.stem}'",
            )
            self.assertTrue(
                fm.get("subagent") is True,
                f"Agent {a_path.name} must declare 'subagent: true'",
            )
            tools = fm.get("tools", [])
            self.assertIsInstance(tools, list)
            self.assertGreaterEqual(
                len(tools),
                1,
                f"Agent {a_path.name} must have a dedicated tools list",
            )

    def test_complete_removal_of_wf_work_skill(self):
        """Verify skills/wf-work/ directory is completely removed."""
        wf_work_dir = SKILLS_DIR / "wf-work"
        self.assertFalse(
            wf_work_dir.exists(),
            f"Directory {wf_work_dir} must be completely deleted in Phase 2.",
        )

    def test_task_query_consolidation_in_wf_sync_and_task_tracker(self):
        """Verify task queries, standups, and backlog triage are handled by wf-sync and task-tracker."""
        wf_sync_skill = SKILLS_DIR / "wf-sync" / "SKILL.md"
        self.assertTrue(wf_sync_skill.is_file(), "skills/wf-sync/SKILL.md must exist")
        sync_fm = parse_yaml_frontmatter(wf_sync_skill.read_text(encoding="utf-8"))
        self.assertIsNotNone(sync_fm)
        sync_desc = sync_fm.get("description", "").lower()

        # wf-sync must cover standup, sync, backlog, or task triage
        sync_keywords = ["standup", "sync", "status", "triage", "backlog", "progress"]
        has_sync_kw = any(kw in sync_desc for kw in sync_keywords)
        self.assertTrue(
            has_sync_kw,
            f"wf-sync description must address standup/sync/triage/backlog workflows. Got: {sync_desc}",
        )

        # task-tracker must exist with script
        task_tracker_skill = SKILLS_DIR / "task-tracker" / "SKILL.md"
        self.assertTrue(task_tracker_skill.is_file(), "skills/task-tracker/SKILL.md must exist")
        self.assertTrue(
            PERSONAL_SYNC_SCRIPT.is_file(),
            f"Expected personal_sync.py at {PERSONAL_SYNC_SCRIPT}",
        )

    def test_task_query_consolidation_to_sync_and_tracker(self):
        """Verify task queries, standups, and backlog triage are handled by wf-sync and task-tracker."""
        return self.test_task_query_consolidation_in_wf_sync_and_task_tracker()


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (Requirement R4, CLI Robustness)
# ==============================================================================

class TestPhase2Tier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2 Boundary & Corner Cases:
    - CLI invocations with missing, empty, or malformed options
    - setup.sh --dry flag handling and side-effect freedom
    - validate-references.py edge cases: clean workspace, synthetic broken link, empty dir
    - personal_sync.py non-git directory handling
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_empty_and_missing_arguments_fail_cleanly(self):
        """Verify resolve_manifest.py and prune_team.py handle empty/missing arguments cleanly without unhandled crashes."""
        # 1. resolve_manifest.py with unrecognized argument
        res_resolve = subprocess.run(
            [sys.executable, str(RESOLVE_MANIFEST_SCRIPT), "--unrecognized-test-flag"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=REPO_ROOT,
        )
        self.assertNotEqual(
            res_resolve.returncode,
            0,
            "resolve_manifest.py with unrecognized argument should exit with non-zero code",
        )
        self.assertNotIn(
            "Traceback (most recent call last):",
            res_resolve.stderr,
            f"resolve_manifest.py crashed with unhandled exception: {res_resolve.stderr}",
        )

        # 2. prune_team.py without arguments
        res_prune = subprocess.run(
            [sys.executable, str(PRUNE_TEAM_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=REPO_ROOT,
        )
        self.assertNotEqual(
            res_prune.returncode,
            0,
            "prune_team.py without arguments should exit with non-zero code",
        )
        self.assertNotIn(
            "Traceback (most recent call last):",
            res_prune.stderr,
            f"prune_team.py crashed with unhandled exception: {res_prune.stderr}",
        )

    def test_setup_dry_run_flag_execution_and_side_effect_freedom(self):
        """Verify setup.sh --dry runs successfully without creating files in target directory."""
        # Ensure target directory starts completely empty
        initial_contents = list(self.target_path.iterdir())
        self.assertEqual(initial_contents, [], "Test target directory must start empty")

        res = subprocess.run(
            [
                "bash",
                str(SETUP_SCRIPT),
                str(self.target_path),
                "--type",
                "project",
                "--editor",
                "antigravity",
                "--teams",
                "dev",
                "--dry",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            res.returncode,
            0,
            f"setup.sh --dry failed with returncode {res.returncode}.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )
        self.assertNotIn(
            "Unknown option: --dry",
            res.stdout,
            "setup.sh should recognize --dry option without displaying 'Unknown option'",
        )

        # Side-effect freedom: verify no files or directories were created
        after_contents = list(self.target_path.iterdir())
        self.assertEqual(
            after_contents,
            [],
            f"setup.sh --dry violated side-effect freedom! Created files/dirs: {after_contents}",
        )

    def test_setup_dry_run_with_custom_editor_targets(self):
        """Verify setup.sh --dry works across various editor targets."""
        for editor in ["antigravity", "copilot", "claude", "grok"]:
            with self.subTest(editor=editor):
                editor_target = self.target_path / f"test_{editor}"
                editor_target.mkdir(parents=True, exist_ok=True)
                res = subprocess.run(
                    [
                        "bash",
                        str(SETUP_SCRIPT),
                        str(editor_target),
                        "--type",
                        "project",
                        "--editor",
                        editor,
                        "--teams",
                        "all",
                        "--dry",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=REPO_ROOT,
                )
                self.assertEqual(
                    res.returncode,
                    0,
                    f"setup.sh --editor {editor} --dry failed.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
                )
                self.assertEqual(
                    list(editor_target.iterdir()),
                    [],
                    f"setup.sh --editor {editor} --dry wrote files into target directory!",
                )

    def test_validate_references_clean_workspace_exit_code_zero(self):
        """Verify validate-references.py returns exit code 0 when no dangling references exist."""
        # Create a clean mock workspace with valid reciprocal markdown links
        clean_dir = self.target_path / "clean_workspace"
        clean_dir.mkdir(parents=True, exist_ok=True)
        (clean_dir / "index.md").write_text("# Home\nSee [Guide](guide.md)\n", encoding="utf-8")
        (clean_dir / "guide.md").write_text("# Guide\nBack to [Home](index.md)\n", encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(VALIDATE_REFERENCES_SCRIPT), str(clean_dir)],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            res.returncode,
            0,
            f"validate-references.py should exit 0 on clean workspace.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )
        self.assertIn("Zero dangling file references found", res.stdout)

    def test_validate_references_detects_synthetic_broken_link(self):
        """Verify validate-references.py detects a broken link and exits with non-zero returncode."""
        broken_dir = self.target_path / "broken_workspace"
        broken_dir.mkdir(parents=True, exist_ok=True)
        (broken_dir / "page.md").write_text(
            "# Broken Page\nBroken link to [Missing](non_existent_file.md)\n",
            encoding="utf-8",
        )

        res = subprocess.run(
            [sys.executable, str(VALIDATE_REFERENCES_SCRIPT), str(broken_dir)],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=REPO_ROOT,
        )

        self.assertNotEqual(
            res.returncode,
            0,
            "validate-references.py should exit non-zero when broken link exists",
        )
        self.assertIn("non_existent_file.md", res.stdout + res.stderr)

    def test_validate_references_empty_workspace(self):
        """Verify validate-references.py handles an empty directory without crashing."""
        empty_dir = self.target_path / "empty_workspace"
        empty_dir.mkdir(parents=True, exist_ok=True)

        res = subprocess.run(
            [sys.executable, str(VALIDATE_REFERENCES_SCRIPT), str(empty_dir)],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            res.returncode,
            0,
            f"validate-references.py crashed on empty directory.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )

    def test_personal_sync_edge_cases(self):
        """Verify personal_sync.py handles --help and non-git directories gracefully."""
        # Test help
        res_help = subprocess.run(
            [sys.executable, str(PERSONAL_SYNC_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res_help.returncode, 0)
        self.assertIn("usage", res_help.stdout.lower())

        # Test non-git directory with --format json flag
        res_json = subprocess.run(
            [sys.executable, str(PERSONAL_SYNC_SCRIPT), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(self.target_path),
        )
        self.assertEqual(
            res_json.returncode,
            0,
            f"personal_sync.py failed in non-git directory.\nSTDOUT: {res_json.stdout}\nSTDERR: {res_json.stderr}",
        )
        try:
            data = json.loads(res_json.stdout)
            self.assertIsInstance(data, dict)
        except json.JSONDecodeError:
            self.fail(f"personal_sync.py did not return valid JSON in non-git dir: {res_json.stdout}")


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS (Requirement R2, R3, R4)
# ==============================================================================

class TestPhase2Tier3CrossFeatureInteractions(unittest.TestCase):
    """
    Tier 3 Cross-Feature Interactions:
    - Team pack manifests integrity and agent referential lineage
    - compliance pack has zero agents
    - advisor pack has no advisor agent (contains unbundler, disruptor)
    - resolve_manifest.py CORE_AGENTS and CORE_SKILLS exclude retired assets
    - resolve_manifest.py prune obsolete asset integration
    - Plugin hooks schema and integrity hook execution
    """

    def test_team_pack_manifests_integrity_and_agent_lineage(self):
        """Verify all teams/*/pack.json files are valid JSON, reference existing agents and skills."""
        pack_files = list(TEAMS_DIR.glob("*/pack.json"))
        self.assertGreaterEqual(len(pack_files), 5, "Expected team packs under teams/")

        valid_agents = {f.stem for f in AGENTS_DIR.glob("*.md")}
        valid_skills = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")}

        for pack_path in pack_files:
            team_name = pack_path.parent.name
            with self.subTest(team=team_name):
                content = pack_path.read_text(encoding="utf-8")
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as err:
                    self.fail(f"Invalid JSON in {pack_path}: {err}")

                agents = data.get("agents", [])
                skills = data.get("skills", [])

                # Every agent listed must exist in agents/*.md
                for agent in agents:
                    self.assertIn(
                        agent,
                        valid_agents,
                        f"Team pack '{team_name}' references non-existent agent '{agent}' in agents/",
                    )

                # Every skill listed must exist in skills/*/SKILL.md
                for skill in skills:
                    self.assertIn(
                        skill,
                        valid_skills,
                        f"Team pack '{team_name}' references non-existent skill '{skill}' in skills/",
                    )

    def test_compliance_team_pack_has_zero_agents(self):
        """Verify teams/compliance/pack.json declares 'agents': [] per Requirement R2."""
        compliance_pack = TEAMS_DIR / "compliance" / "pack.json"
        self.assertTrue(compliance_pack.is_file(), f"Missing {compliance_pack}")
        data = json.loads(compliance_pack.read_text(encoding="utf-8"))

        agents = data.get("agents", None)
        self.assertEqual(
            agents,
            [],
            f"teams/compliance/pack.json must have 'agents': [], got: {agents}",
        )
        self.assertIn(
            "integrity-validator",
            data.get("skills", []),
            "teams/compliance/pack.json must include 'integrity-validator' skill",
        )

    def test_advisor_team_pack_has_no_advisor_agent(self):
        """Verify teams/advisor/pack.json does not reference 'advisor' agent per Requirement R2."""
        advisor_pack = TEAMS_DIR / "advisor" / "pack.json"
        self.assertTrue(advisor_pack.is_file(), f"Missing {advisor_pack}")
        data = json.loads(advisor_pack.read_text(encoding="utf-8"))

        agents = data.get("agents", [])
        self.assertNotIn(
            "advisor",
            agents,
            f"teams/advisor/pack.json must not reference retired 'advisor' agent, got: {agents}",
        )
        self.assertIn(
            "wf-advisor",
            data.get("skills", []),
            "teams/advisor/pack.json must include 'wf-advisor' universal skill",
        )

    def test_resolve_manifest_excludes_retired_agents_and_skills(self):
        """Verify resolve_manifest.py CORE_AGENTS and CORE_SKILLS exclude retired assets."""
        content = RESOLVE_MANIFEST_SCRIPT.read_text(encoding="utf-8")

        # Parse CORE_AGENTS
        core_agents_match = re.search(r"CORE_AGENTS\s*=\s*\{([^}]+)\}", content)
        self.assertIsNotNone(core_agents_match, "CORE_AGENTS definition not found in resolve_manifest.py")
        core_agents = {item.strip().strip("'\"") for item in core_agents_match.group(1).split(",")}

        self.assertNotIn(
            "advisor.md",
            core_agents,
            "CORE_AGENTS in resolve_manifest.py must not include 'advisor.md'",
        )
        self.assertNotIn(
            "compliance.md",
            core_agents,
            "CORE_AGENTS in resolve_manifest.py must not include 'compliance.md'",
        )

        # Parse CORE_SKILLS
        core_skills_match = re.search(r"CORE_SKILLS\s*=\s*\{([^}]+)\}", content, re.DOTALL)
        self.assertIsNotNone(core_skills_match, "CORE_SKILLS definition not found in resolve_manifest.py")
        core_skills = {item.strip().strip("'\"") for item in core_skills_match.group(1).replace("\n", "").split(",") if item.strip()}

        self.assertNotIn(
            "wf-work",
            core_skills,
            "CORE_SKILLS in resolve_manifest.py must not include 'wf-work'",
        )

    def test_resolve_manifest_prune_obsolete_assets_integration(self):
        """Verify resolve_manifest.py includes retired Phase 2 assets in obsolete paths."""
        content = RESOLVE_MANIFEST_SCRIPT.read_text(encoding="utf-8")
        obsolete_match = re.search(r"LEGACY_OBSOLETE_SUBPATHS\s*=\s*\[(.*?)\]", content, re.DOTALL)
        self.assertIsNotNone(obsolete_match, "LEGACY_OBSOLETE_SUBPATHS not found in resolve_manifest.py")

        obsolete_block = obsolete_match.group(1)
        self.assertTrue(
            "compliance.md" in obsolete_block or "agents/compliance.md" in obsolete_block,
            "LEGACY_OBSOLETE_SUBPATHS should register 'agents/compliance.md' for automatic pruning",
        )
        self.assertTrue(
            "advisor.md" in obsolete_block or "agents/advisor.md" in obsolete_block,
            "LEGACY_OBSOLETE_SUBPATHS should register 'agents/advisor.md' for automatic pruning",
        )

    def test_plugin_hooks_schema_and_integrity_hook_execution(self):
        """Verify workforce-integrity-plugin hooks.json triggers validate-references.py on PostToolUse."""
        integrity_hooks = PLUGINS_DIR / "workforce-integrity-plugin" / "hooks.json"
        self.assertTrue(
            integrity_hooks.is_file(),
            f"Expected hooks.json at {integrity_hooks}",
        )
        data = json.loads(integrity_hooks.read_text(encoding="utf-8"))
        self.assertIn("workforce-integrity", data)
        post_tool_list = data["workforce-integrity"].get("PostToolUse", [])
        self.assertGreaterEqual(len(post_tool_list), 1)

        all_commands = []
        for entry in post_tool_list:
            for hook in entry.get("hooks", []):
                all_commands.append(hook.get("command", ""))

        hook_commands = " ".join(all_commands)
        self.assertIn(
            "validate-references.py",
            hook_commands,
            "workforce-integrity-plugin hook command must invoke validate-references.py",
        )


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOAD SCENARIOS (End-to-End Workflows)
# ==============================================================================

class TestPhase2Tier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4 Real-World Workload Scenarios:
    - Greenfield workspace setup with antigravity editor
    - Multi-editor target distribution verification (copilot, claude, grok)
    - Brownfield update with legacy artifact pruning
    - Full repository reference lineage validation
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fresh_project_workspace_setup_antigravity(self):
        """Verify clean project initialization: correct structure, manifest tracking, zero retired assets."""
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
            f"Fresh project setup failed.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )

        # Assert .manifest.json exists and is valid
        manifest_path = self.target_path / "workforces" / ".manifest.json"
        self.assertTrue(manifest_path.is_file(), f"Expected manifest at {manifest_path}")
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        installed_files = manifest_data.get("installed_files", [])

        # Assert no retired assets installed in filesystem
        installed_wf_work = self.target_path / ".agents" / "skills" / "wf-work"
        self.assertFalse(
            installed_wf_work.exists(),
            f"Retired skill 'wf-work' was installed in target workspace at {installed_wf_work}",
        )

        installed_compliance = self.target_path / ".agents" / "agents" / "compliance.md"
        self.assertFalse(
            installed_compliance.exists(),
            f"Retired pseudo-agent 'compliance.md' was installed at {installed_compliance}",
        )

        installed_advisor = self.target_path / ".agents" / "agents" / "advisor.md"
        self.assertFalse(
            installed_advisor.exists(),
            f"Retired agent 'advisor.md' was installed at {installed_advisor}",
        )

        # Assert no retired assets in manifest tracking
        for file_entry in installed_files:
            self.assertNotIn("wf-work", file_entry, f"Manifest tracks retired asset: {file_entry}")
            self.assertNotIn("compliance.md", file_entry, f"Manifest tracks retired agent: {file_entry}")
            self.assertNotIn("advisor.md", file_entry, f"Manifest tracks retired agent: {file_entry}")

        # Assert active modern assets exist
        wf_sync_skill = self.target_path / ".agents" / "skills" / "wf-sync" / "SKILL.md"
        self.assertTrue(
            wf_sync_skill.is_file(),
            f"Expected core skill wf-sync to be installed at {wf_sync_skill}",
        )

        project_manager_agent = self.target_path / ".agents" / "agents" / "project-manager.md"
        self.assertTrue(
            project_manager_agent.is_file(),
            f"Expected core agent project-manager to be installed at {project_manager_agent}",
        )

    def test_multi_editor_distribution_targets(self):
        """Verify setup.sh scaffolds correct directory structures for vscode/copilot, claude, grok, and antigravity."""
        editor_expectations = {
            "vscode": Path(".github") / "copilot",
            "claude": Path(".claude"),
            "grok": Path(".grok"),
            "antigravity": Path(".agents"),
        }

        for editor, rel_base in editor_expectations.items():
            with self.subTest(editor=editor):
                ed_dir = self.target_path / f"target_{editor}"
                ed_dir.mkdir(parents=True, exist_ok=True)

                res = subprocess.run(
                    [
                        "bash",
                        str(SETUP_SCRIPT),
                        str(ed_dir),
                        "--type",
                        "project",
                        "--editor",
                        editor,
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
                    f"setup.sh failed for editor '{editor}'.\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
                )

                base_path = ed_dir / rel_base
                self.assertTrue(
                    base_path.is_dir(),
                    f"Expected editor root {base_path} to be created for '{editor}'",
                )

                manifest_file = ed_dir / "workforces" / ".manifest.json"
                self.assertTrue(
                    manifest_file.is_file(),
                    f"Expected manifest at {manifest_file} for editor '{editor}'",
                )

    def test_brownfield_update_prunes_legacy_artifacts(self):
        """Verify update.sh removes stale legacy assets (wf-work, compliance.md, advisor.md) from target workspace."""
        # 1. Initial setup of a workspace
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

        # 2. Inject artificial legacy assets into the installed workspace
        legacy_files = [
            self.target_path / ".agents" / "skills" / "wf-work" / "SKILL.md",
            self.target_path / ".agents" / "agents" / "compliance.md",
            self.target_path / ".agents" / "agents" / "advisor.md",
            self.target_path / ".agents" / "workflows" / "wf-obsolete.md",
        ]

        for p in legacy_files:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# Legacy File\nDeprecated content.\n", encoding="utf-8")
            self.assertTrue(p.is_file())

        # Register injected legacy files in workforces/.manifest.json
        manifest_path = self.target_path / "workforces" / ".manifest.json"
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for p in legacy_files:
            rel_p = str(p.relative_to(self.target_path))
            if rel_p not in manifest_data["installed_files"]:
                manifest_data["installed_files"].append(rel_p)
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

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
            f"update.sh failed.\nSTDOUT: {res_update.stdout}\nSTDERR: {res_update.stderr}",
        )

        # 4. Verify all legacy files have been pruned
        for p in legacy_files:
            self.assertFalse(
                p.exists(),
                f"Legacy file {p} should have been pruned by update.sh, but still exists!",
            )

        # 5. Verify active core assets remain intact
        active_skill = self.target_path / ".agents" / "skills" / "wf-sync" / "SKILL.md"
        self.assertTrue(
            active_skill.is_file(),
            f"Active skill {active_skill} was erroneously removed during update!",
        )

    def test_full_repository_reference_lineage_clean(self):
        """Verify entire repository passes validate-references.py with zero dangling references."""
        res = subprocess.run(
            [sys.executable, str(VALIDATE_REFERENCES_SCRIPT), "./"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )

        self.assertEqual(
            res.returncode,
            0,
            f"Repository contains dangling references!\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )
        self.assertIn(
            "Zero dangling file references found",
            res.stdout,
            "Expected 'Zero dangling file references found' in validator output",
        )


if __name__ == "__main__":
    unittest.main()
