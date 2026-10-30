#!/usr/bin/env python3
"""
Workforces Manifest Resolver & File Tracker
Resolves the exact set of agents, rules, skills, workflows, and plugins to copy
or preserve based on core requirements and installed domain teams, tracks installed
files in workforces/.manifest.json, and safely prunes obsolete toolkit assets during updates.
"""

import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compile_assets as ca  # noqa: E402

CORE_AGENTS = {'wf-project-manager.md', 'wf-scribe.md'}
CORE_RULES = {
    'wf-base.md', 'wf-lean-execution.md', 'wf-mcp-protection.md',
    'wf-session-context.md', 'wf-file-integrity.md', 'wf-git-workflow.md',
}
CORE_SKILLS = {
    'wf-management', 'wf-memory-management', 'wf-task-tracker', 'wf-issue-tracker',
    'wf-session-context', 'wf-usage-tracker', 'wf-integrity-validator', 'wf-canvas',
    'wf-github-project-planning', 'wf-hypothesis-tracker',
    'wf-plan', 'wf-sync', 'wf-advisor', 'wf-ideate', 'wf-investigate',
    'wf-question-formulation', 'wf-update', 'wf-dashboard',
}
CORE_WORKFLOWS = set()
CORE_PLUGINS = {'wf-integrity-plugin'}

MANIFEST_REL_PATH = os.path.join("workforces", ".manifest.json")
_PROTECTED_USER_FILES = frozenset({
    os.path.normpath(os.path.join(".claude", "settings.json")),
    os.path.normpath(os.path.join(".vscode", "settings.json")),
})
_LEGACY_COPILOT_CATS = frozenset({"agents", "rules", "skills", "workflows", "plugins", "commands"})

LEGACY_OBSOLETE_SUBPATHS = [
    "agents/compliance.md",
    "agents/advisor.md",
    "skills/wf-work/SKILL.md",
    "agents/clean-coder.md",
    "agents/design-pilot.md",
    "agents/heartbeat.md",
    "agents/design-reviewer.md",
    "agents/feature-researcher.md",
    "agents/integrity-auditor.md",
    "agents/social-engager.md",
    "agents/designer.md",
    "agents/disruptor.md",
    "agents/growth.md",
    "agents/launcher.md",
    "agents/marketer.md",
    "agents/operations.md",
    "agents/programmer.md",
    "agents/project-manager.md",
    "agents/researcher.md",
    "agents/sales.md",
    "agents/scribe.md",
    "agents/social.md",
    "agents/unbundler.md",
    "docs/claude-scribe-prd.md",
    "plugins/workforce-integrity-plugin/hooks.json",
    "plugins/workforce-integrity-plugin/hooks/hooks.json",
    "plugins/workforce-integrity-plugin/plugin.json",
    "plugins/workforce-integrity-plugin/rules/file-integrity.md",
    "plugins/workforce-integrity-plugin/skills/integrity-validator/SKILL.md",
    "plugins/workforce-programming-plugin/hooks.json",
    "plugins/workforce-programming-plugin/hooks/hooks.json",
    "plugins/workforce-programming-plugin/plugin.json",
    "plugins/workforce-programming-plugin/rules/clean-coder.md",
    "plugins/workforce-social-plugin/plugin.json",
    "plugins/workforce-social-plugin/rules/social-engagement.md",
    "plugins/workforce-usage-plugin/plugin.json",
    "plugins/workforce-usage-plugin/hooks.json",
    "plugins/workforce-usage-plugin/hooks/hooks.json",
    "rules/base.md",
    "rules/clean-coder.md",
    "rules/design-standards.md",
    "rules/file-integrity.md",
    "rules/git-workflow.md",
    "rules/lean-execution.md",
    "rules/mcp-protection.md",
    "rules/session-context.md",
    "rules/social-engagement.md",
    "rules/token-parsimony.md",
    "skills/agent-parallelization/SKILL.md",
    "skills/ai-search-optimization/SKILL.md",
    "skills/brand-guidelines/SKILL.md",
    "skills/business-frameworks/SKILL.md",
    "skills/business-frameworks/references/connected-strategy.md",
    "skills/business-frameworks/references/dynamic-capabilities.md",
    "skills/business-frameworks/references/growth-loops.md",
    "skills/business-frameworks/references/jobs-to-be-done.md",
    "skills/business-frameworks/references/platform-strategy.md",
    "skills/business-frameworks/references/unit-economics.md",
    "skills/business-frameworks/references/value-stick.md",
    "skills/clean-coder/SKILL.md",
    "skills/code-graph/SKILL.md",
    "skills/code-graph/scripts/graph_indexer.py",
    "skills/code-graph/scripts/pre_impact_analyzer.py",
    "skills/code-graph/scripts/pre_tool_hook.py",
    "skills/codebase-improvement/SKILL.md",
    "skills/design-anti-patterns/SKILL.md",
    "skills/doc-generator/SKILL.md",
    "skills/feature-research/SKILL.md",
    "skills/github-project-planning/SKILL.md",
    "skills/hypothesis-tracker/SKILL.md",
    "skills/hypothesis-tracker/scripts/hypothesis.py",
    "skills/hypothesis-tracker/templates/hypothesis-template.md",
    "skills/image-workflow/SKILL.md",
    "skills/image-workflow/scripts/optimize_images.py",
    "skills/image-workflow/templates/json-image-duplicate-template.json",
    "skills/integrity-validator/SKILL.md",
    "skills/issue-tracker/SKILL.md",
    "skills/issue-tracker/scripts/report-issue.py",
    "skills/launch-playbook/SKILL.md",
    "skills/market-validation/SKILL.md",
    "skills/memory-management/SKILL.md",
    "skills/memory-management/templates/design-preferences-template.md",
    "skills/persona-management/SKILL.md",
    "skills/persona-management/scripts/manage_personas.py",
    "skills/post-code-review/SKILL.md",
    "skills/post-code-review/scripts/post_code_reviewer.py",
    "skills/post-code-review/scripts/post_tool_hook.py",
    "skills/pr-review/SKILL.md",
    "skills/session-context/SKILL.md",
    "skills/site-setup/SKILL.md",
    "skills/site-setup/templates/consultant-discovery-framework.md",
    "skills/site-setup/templates/quality-toolchain/dependabot.yml",
    "skills/site-setup/templates/quality-toolchain/dependency-cruiser.js",
    "skills/site-setup/templates/quality-toolchain/quality-ci.yml",
    "skills/site-setup/templates/quality-toolchain/stryker.config.json",
    "skills/social-engagement/SKILL.md",
    "skills/social-engagement/scripts/dashboard_generator.py",
    "skills/social-engagement/scripts/engagement_evaluator.py",
    "skills/social-engagement/scripts/social_crawler.py",
    "skills/social-engagement/scripts/social_indexer.py",
    "skills/social-engagement/scripts/test_social_engine.py",
    "skills/social-engagement/templates/persona-template.md",
    "skills/social-engagement/templates/reply-frameworks.md",
    "skills/task-tracker/SKILL.md",
    "skills/task-tracker/scripts/personal_sync.py",
    "skills/task-tracker/scripts/report-task.py",
    "skills/ui-ux-design/SKILL.md",
    "skills/usage-tracker/SKILL.md",
    "skills/usage-tracker/scripts/print_turn_summary.py",
    "skills/usage-tracker/scripts/track_usage.py",
    "skills/visual-design-fundamentals/SKILL.md",
    "skills/workforce-canvas/SKILL.md",
    "skills/workforce-canvas/scripts/heartbeat_watcher.py",
    "skills/workforce-canvas/scripts/server.py",
    "skills/workforce-canvas/scripts/session_registry.py",
    "skills/workforce-canvas/scripts/wait_for_message.py",
    "skills/workforce-canvas/web/canvas.css",
    "skills/workforce-canvas/web/canvas.js",
    "skills/workforce-canvas/web/index.html",
    "skills/workforce-management/SKILL.md",
    "skills/workforce-management/scripts/prune-team.py",
    "skills/workforce-management/scripts/prune_team.py",
    "skills/workforce-management/scripts/resolve_manifest.py",
    "skills/workforce-management/scripts/setup.sh",
    "skills/workforce-management/scripts/update.sh",
    "skills/workforce-management/scripts/validate-references.py",
    "skills/workforce-management/scripts/validate.py",
    "skills/workforce-management/templates/goal-template.md",
    "teams/compliance/file-integrity.md",
    "teams/compliance/mcp-protection.md",
    "teams/compliance/task.md",
    "teams/compliance/verify-integrity.md",
    "teams/design/brand-context.md",
    "teams/design/design-standards.md",
    "teams/design/site-setup.md",
    "teams/dev/clean-coder.md",
    "teams/dev/clean.md",
    "teams/dev/improve.md",
    "teams/dev/investigate.md",
    "teams/growth/design-standards.md",
    "teams/growth/feature.md",
    "teams/marketing/brand-context.md",
    "teams/marketing/design-standards.md",
    "teams/operations/base.md",
    "teams/operations/context.md",
    "teams/operations/session-context.md",
    "teams/operations/sync.md",
    "teams/operations/task.md",
    "teams/sales/advisor.md",
    "teams/social/social-engagement.md",
    "teams/social/social.md",
    "teams/skills/brand-guidelines/SKILL.md",
    "teams/skills/design-anti-patterns/SKILL.md",
    "teams/skills/ui-ux-design/SKILL.md",
    "teams/skills/visual-design-fundamentals/SKILL.md",
    "workflows/advisor.md",
    "workflows/brand-context.md",
    "workflows/clean.md",
    "workflows/context.md",
    "workflows/feature.md",
    "workflows/ideate.md",
    "workflows/image-duplicate.md",
    "workflows/improve.md",
    "workflows/investigate.md",
    "workflows/plan.md",
    "workflows/project-management.md",
    "workflows/question-formulation.md",
    "workflows/site-brief.md",
    "workflows/site-setup.md",
    "workflows/social.md",
    "workflows/sync.md",
    "workflows/task.md",
    "workflows/teams.md",
    "workflows/update-workforces.md",
    "workflows/validate-idea.md",
    "workflows/verify-integrity.md",
    "workflows/work.md",
    "workflows/wf-advisor.md",
    "workflows/wf-brand-context.md",
    "workflows/wf-canvas.md",
    "workflows/wf-clean.md",
    "workflows/wf-context.md",
    "workflows/wf-feature.md",
    "workflows/wf-ideate.md",
    "workflows/wf-image-duplicate.md",
    "workflows/wf-improve.md",
    "workflows/wf-investigate.md",
    "workflows/wf-launch.md",
    "workflows/wf-plan.md",
    "workflows/wf-project-management.md",
    "workflows/wf-question-formulation.md",
    "workflows/wf-site-setup.md",
    "workflows/wf-social.md",
    "workflows/wf-sync.md",
    "workflows/wf-task.md",
    "workflows/wf-teams.md",
    "workflows/wf-update.md",
    "workflows/wf-validate-idea.md",
    "workflows/wf-verify-integrity.md",
    "workflows/wf-work.md",
    "commands/advisor.md",
    "commands/brand-context.md",
    "commands/clean.md",
    "commands/context.md",
    "commands/feature.md",
    "commands/ideate.md",
    "commands/image-duplicate.md",
    "commands/improve.md",
    "commands/investigate.md",
    "commands/plan.md",
    "commands/project-management.md",
    "commands/question-formulation.md",
    "commands/site-setup.md",
    "commands/social.md",
    "commands/sync.md",
    "commands/task.md",
    "commands/teams.md",
    "commands/update-workforces.md",
    "commands/validate-idea.md",
    "commands/verify-integrity.md",
    "commands/work.md",
    "commands/wf-advisor.md",
    "commands/wf-brand-context.md",
    "commands/wf-canvas.md",
    "commands/wf-clean.md",
    "commands/wf-context.md",
    "commands/wf-feature.md",
    "commands/wf-ideate.md",
    "commands/wf-image-duplicate.md",
    "commands/wf-improve.md",
    "commands/wf-investigate.md",
    "commands/wf-launch.md",
    "commands/wf-plan.md",
    "commands/wf-project-management.md",
    "commands/wf-question-formulation.md",
    "commands/wf-site-setup.md",
    "commands/wf-social.md",
    "commands/wf-sync.md",
    "commands/wf-update-workforces.md",
    "commands/wf-task.md",
    "commands/wf-teams.md",
    "commands/wf-update.md",
    "commands/wf-validate-idea.md",
    "commands/wf-verify-integrity.md",
    "commands/wf-work.md",
    "workflows/wf-update-workforces.md",
    "workflows/workforces/tasks/20260822-073809-ideate-and-unbundle-atomic-saas-extractor.md",
    "workflows/workforces/tasks/20260822-073809-market-disruption-scout-disruptor-agent.md",
]

def _base_dir_to_host_id(base_dir: str, profiles: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Map an editor base directory path (e.g. '.agents', '.github/copilot') to canonical host id."""
    norm = os.path.normpath(base_dir).strip(os.sep)
    if norm == os.path.normpath(os.path.join(".github", "copilot")):
        return "copilot"
    for host_id, profile in profiles.items():
        if os.path.normpath(str(profile.get("base_dir", ""))).strip(os.sep) == norm:
            return host_id
    return ca.resolve_host_alias(norm.lstrip("."), profiles)


def find_hosts_dir_with_fallback(toolkit_root: str) -> str:
    """Locate host adapter JSON directory in toolkit_root or fall back to script's parent repo."""
    try:
        return ca.find_hosts_dir(toolkit_root)
    except FileNotFoundError:
        return ca.find_hosts_dir(str(Path(__file__).resolve().parents[3]))


def load_profiles_with_fallback(toolkit_root: str) -> Dict[str, Dict[str, Any]]:
    """Load host profiles from toolkit_root or fall back to script's parent toolkit root."""
    try:
        return ca.load_host_profiles(toolkit_root)
    except FileNotFoundError:
        return ca.load_host_profiles(str(Path(__file__).resolve().parents[3]))


def resolve_target_hosts(
    toolkit_root: str,
    target_dir: str,
    hosts_arg: Any = None,
    base_dir: Optional[str] = None,
    auto_detect: bool = True,
) -> List[str]:
    """Resolve ordered active AI host IDs from CLI/API args, saved config/manifest, or workspace."""
    profiles = load_profiles_with_fallback(toolkit_root)
    if isinstance(hosts_arg, (list, tuple, set)):
        chosen: List[str] = []
        for raw in hosts_arg:
            resolved = ca.resolve_host_alias(str(raw), profiles)
            if not resolved:
                raise ValueError(f"Unknown AI host '{raw}'. Supported: {', '.join(profiles)}")
            chosen.append(resolved)
        return ca._order_hosts(chosen) if chosen else ["antigravity"]
    arg_str = str(hosts_arg).strip() if hosts_arg is not None else ""
    if arg_str and arg_str.lower() != "auto":
        return ca.resolve_active_hosts(target_dir, profiles, hosts_arg=arg_str, auto_detect=auto_detect)
    if hosts_arg is None and base_dir:
        mapped = _base_dir_to_host_id(base_dir, profiles)
        if mapped:
            return [mapped]
    if ca.load_install_config(target_dir) is None:
        prev = load_installed_manifest(target_dir)
        prev_raw = prev.get("hosts") if isinstance(prev, dict) and isinstance(prev.get("hosts"), list) else []
        valid_prev = {h for h in (ca.resolve_host_alias(str(r), profiles) for r in prev_raw) if h}
        if valid_prev:
            if auto_detect:
                valid_prev.update(ca.detect_workspace_hosts(target_dir, profiles))
            return ca._order_hosts(valid_prev)
    return ca.resolve_active_hosts(target_dir, profiles, hosts_arg="auto", auto_detect=auto_detect)


def _first_configured_base_dir(
    cfg: Optional[Dict[str, Any]], profiles: Dict[str, Dict[str, Any]]
) -> Optional[str]:
    """Return base_dir of the first valid host in config.json, if present."""
    if not cfg or not isinstance(cfg.get("hosts"), list):
        return None
    for raw in cfg["hosts"]:
        hid = ca.resolve_host_alias(str(raw), profiles)
        if hid and hid in profiles:
            return str(profiles[hid]["base_dir"])
    return None


def detect_base_dir(target_dir: str) -> str:
    """Detect primary editor configuration directory in target_dir (backward-compatible)."""
    root = os.path.abspath(target_dir)
    try:
        profiles = load_profiles_with_fallback(root)
        configured = _first_configured_base_dir(ca.load_install_config(root), profiles)
        if configured:
            return configured
        detected = ca.detect_workspace_hosts(root, profiles)
        if detected:
            return str(profiles[detected[0]]["base_dir"])
    except OSError:
        pass
    for cand in (".agents", os.path.join(".github", "copilot"), ".claude", ".grok", ".cursor"):
        if os.path.isdir(os.path.join(root, cand)):
            return cand
    return ".agents"


_TEAM_DIR_CANDIDATES = (
    "teams",
    os.path.join(".agents", "teams"),
    os.path.join(".claude", "teams"),
    os.path.join(".grok", "teams"),
    os.path.join(".github", "copilot", "teams"),
    os.path.join(".cursor", "teams"),
)


def _has_team_packs(teams_dir: str) -> bool:
    """Return True if teams_dir contains at least one team pack manifest."""
    return any(
        os.path.isdir(d) and (os.path.isfile(os.path.join(d, "pack.json")) or os.path.isfile(os.path.join(d, "pack.md")))
        for d in glob.glob(os.path.join(teams_dir, "*"))
    )


def find_teams_dir(toolkit_root: str) -> str:
    """Find the primary directory containing team pack building blocks across source or host dirs."""
    root = os.path.abspath(toolkit_root)
    first_existing: Optional[str] = None
    for rel in _TEAM_DIR_CANDIDATES:
        cand = os.path.join(root, rel)
        if os.path.isdir(cand):
            if first_existing is None:
                first_existing = cand
            if _has_team_packs(cand):
                return cand
    return first_existing or os.path.join(root, "teams")


def _load_bundled_json_map(toolkit_root: str, filename: str, root_key: str) -> Dict[str, Dict[str, Any]]:
    """Load a bundled metadata map (plugins.json or teams.json) from wf-management/hosts/."""
    candidates: List[str] = []
    try:
        candidates.append(os.path.join(find_hosts_dir_with_fallback(toolkit_root), filename))
    except FileNotFoundError:
        pass
    candidates.append(str(Path(__file__).resolve().parent.parent / "hosts" / filename))
    for cand in dict.fromkeys(candidates):
        if os.path.isfile(cand):
            raw = ca._load_json_file(cand).get(root_key, {})
            if isinstance(raw, dict):
                return {k: v for k, v in raw.items() if isinstance(v, dict)}
    return {}


def get_available_teams(toolkit_root: str) -> List[str]:
    """Return sorted list of all available team names across disk dirs and bundled fallback."""
    root = os.path.abspath(toolkit_root)
    found: Set[str] = set(_load_bundled_json_map(root, "teams.json", "teams").keys())
    for rel in _TEAM_DIR_CANDIDATES:
        cand = os.path.join(root, rel)
        if not os.path.isdir(cand):
            continue
        for entry in glob.glob(os.path.join(cand, "*")):
            if os.path.isdir(entry) and (
                os.path.exists(os.path.join(entry, "pack.json")) or os.path.exists(os.path.join(entry, "pack.md"))
            ):
                found.add(os.path.basename(entry))
    return sorted(found)


def _workspace_custom_teams(root_dir: Optional[str]) -> Set[str]:
    """Return custom team names defined under <root_dir>/workforces/teams/*/{team.json,pack.json,pack.md}."""
    if not root_dir:
        return set()
    ws_teams_dir = os.path.join(os.path.abspath(root_dir), "workforces", "teams")
    if not os.path.isdir(ws_teams_dir):
        return set()
    markers = ("team.json", "pack.json", "pack.md")
    return {
        os.path.basename(d) for d in glob.glob(os.path.join(ws_teams_dir, "*"))
        if os.path.isdir(d) and any(os.path.isfile(os.path.join(d, m)) for m in markers)
    }


def _filter_valid_csv_teams(raw_csv: str, available_teams: Sequence[str], strip_chars: str) -> List[str]:
    """Split a comma-separated team string and retain valid team names."""
    items = [t.strip().strip(strip_chars) for t in raw_csv.split(',')]
    return [t for t in items if t and (not available_teams or t in available_teams)]


def _parse_workrules_teams(content: str, available_teams: Sequence[str]) -> Tuple[bool, List[str]]:
    """Extract (was_explicit, installed_teams) from workforces/workrules.md content."""
    found: List[str] = []
    explicit = False
    m_block = re.search(r'## Installed Teams\s*\n((?:\s*-\s*[^\n]+\n?)+)', content)
    if m_block:
        explicit = True
        for raw_line in m_block.group(1).splitlines():
            line = raw_line.strip()
            if not line.startswith('-'):
                continue
            val = line.lstrip('- ').strip().strip('\'\"')
            if val.startswith('installed_teams:'):
                raw_csv = val.replace('installed_teams:', '').strip().strip('[]\'\"')
                found.extend(_filter_valid_csv_teams(raw_csv, available_teams, '\'\"'))
            elif val and val != '[]' and (not available_teams or val in available_teams):
                found.append(val)
    if not found:
        m_inline = re.search(r'installed_teams:\s*\[?(.*?)\]?(\n|$)', content)
        if m_inline is not None:
            explicit = True
            found.extend(_filter_valid_csv_teams(m_inline.group(1).strip(), available_teams, '\'\"- '))
    return explicit, found


def _discover_installed_teams(target_dir: str, toolkit_root: Optional[str] = None) -> Tuple[bool, List[str]]:
    """Return (was_explicit, installed_teams) from config.json, workrules.md, .manifest.json, or workspace."""
    target_dir = os.path.abspath(target_dir)
    tk_eff = os.path.abspath(toolkit_root) if toolkit_root else target_dir
    valid_teams = sorted(
        set(get_available_teams(tk_eff)) | set(get_available_teams(target_dir))
        | _workspace_custom_teams(target_dir) | _workspace_custom_teams(tk_eff)
    )
    cfg_doc = ca.load_install_config(target_dir)
    if isinstance(cfg_doc, dict) and isinstance(cfg_doc.get("installed_teams"), list):
        raw_cfg = [str(t).strip() for t in cfg_doc["installed_teams"] if str(t).strip()]
        return True, sorted({t for t in raw_cfg if not valid_teams or t in valid_teams})
    workrules_path = os.path.join(target_dir, 'workforces', 'workrules.md')
    if os.path.isfile(workrules_path):
        try:
            with open(workrules_path, 'r', encoding='utf-8', errors='ignore') as fh:
                explicit, teams = _parse_workrules_teams(fh.read(), valid_teams)
            if explicit:
                return True, sorted(set(teams))
        except OSError:
            pass
    mf_doc = load_installed_manifest(target_dir)
    if isinstance(mf_doc, dict) and isinstance(mf_doc.get("installed_teams"), list):
        raw_mf = [str(t).strip() for t in mf_doc["installed_teams"] if str(t).strip()]
        return True, sorted({t for t in raw_mf if not valid_teams or t in valid_teams})
    ws_custom = sorted(_workspace_custom_teams(target_dir))
    return (True, ws_custom) if ws_custom else (False, [])


def get_installed_teams(target_dir: str, toolkit_root: Optional[str] = None) -> List[str]:
    """Parse config.json, workrules.md, or workspace team folders to discover installed teams."""
    return _discover_installed_teams(target_dir, toolkit_root)[1]


def _read_first_json_dict(paths: Iterable[str]) -> Optional[Dict[str, Any]]:
    """Return the first readable JSON object among candidate file paths."""
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return None


def get_team_pack_data(
    toolkit_root: str, team_name: str, target_dir: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Load pack.json, bundled teams.json, or workspace team.json metadata for a team."""
    roots = [os.path.abspath(toolkit_root)]
    if target_dir and os.path.abspath(target_dir) not in roots:
        roots.append(os.path.abspath(target_dir))
    pack_cands = [os.path.join(r, rel, team_name, "pack.json") for r in roots for rel in _TEAM_DIR_CANDIDATES]
    disk_pack = _read_first_json_dict(pack_cands)
    if disk_pack is not None:
        return disk_pack
    bundled = _load_bundled_json_map(roots[0], "teams.json", "teams").get(team_name)
    ws_cands = [
        os.path.join(r, "workforces", "teams", team_name, fn)
        for r in roots for fn in ("team.json", "pack.json")
    ]
    ws_pack = _read_first_json_dict(ws_cands)
    if bundled and ws_pack:
        return {**bundled, **ws_pack}
    return ws_pack if ws_pack is not None else bundled


def _resolve_team_selection(
    toolkit_root: str, target_dir: str, all_team_dirs: Sequence[str], teams_arg: Optional[str]
) -> List[str]:
    """Resolve normalized list of installed teams from CLI arg or workspace state."""
    valid_all = sorted(
        set(all_team_dirs) | _workspace_custom_teams(target_dir) | _workspace_custom_teams(toolkit_root)
    )
    if teams_arg is not None:
        teams_clean = str(teams_arg).strip().lower()
        if teams_clean in ('all', '*'):
            return sorted(set(all_team_dirs))
        if teams_clean in ('none', 'core', ''):
            return []
        picked = [
            t.strip().lower() for t in str(teams_arg).split(',')
            if t.strip() and (t.strip().lower() in valid_all or not valid_all)
        ]
        return sorted(set(picked))
    explicit, discovered = _discover_installed_teams(target_dir, toolkit_root)
    if not explicit and not discovered:
        discovered = [t for t in ('dev', 'design') if t in all_team_dirs]
    return sorted(set(discovered))


def ensure_md_ext(name: str) -> str:
    """Ensure a markdown asset name ends with .md."""
    return name if name.endswith(".md") else f"{name}.md"


def resolve_manifest(
    toolkit_root: str, target_dir: str, teams_arg: Optional[str] = None
) -> Dict[str, Any]:
    """Resolve all required agents, rules, skills, workflows, and plugins."""
    toolkit_root = os.path.abspath(toolkit_root)
    target_dir = os.path.abspath(target_dir)
    agents, rules = set(CORE_AGENTS), set(CORE_RULES)
    skills, workflows, plugins = set(CORE_SKILLS), set(CORE_WORKFLOWS), set(CORE_PLUGINS)
    installed_teams = _resolve_team_selection(
        toolkit_root, target_dir, get_available_teams(toolkit_root), teams_arg
    )
    for team_name in installed_teams:
        data = get_team_pack_data(toolkit_root, team_name, target_dir=target_dir) or {}
        agents |= {ensure_md_ext(a) for a in data.get('agents', [])}
        rules |= {ensure_md_ext(r) for r in data.get('rules', [])}
        skills |= set(data.get('skills', []))
        workflows |= {ensure_md_ext(w) for w in data.get('workflows', [])}
        plugins |= set(data.get('plugins', []))
    return {
        'installed_teams': installed_teams,
        'agents': sorted(agents),
        'rules': sorted(rules),
        'skills': sorted(skills),
        'workflows': sorted(workflows),
        'plugins': sorted(plugins),
        'teams': installed_teams,
    }

def _resolve_flat_paths(
    src_dir: Optional[str],
    items: Sequence[str],
    category: str,
    host_base: str,
    dirs_cfg: Dict[str, Any],
    target_dir: Optional[str] = None,
) -> List[str]:
    """Compute compiled relative target paths for flat assets (agents, rules, workflows)."""
    cfg = dirs_cfg.get(category)
    if not cfg:
        return []
    ext = cfg.get("ext", ".md")
    sub_path = cfg["path"]
    has_src = bool(src_dir and os.path.isdir(src_dir))
    paths: List[str] = []
    for item in items:
        stem = item[:-3] if item.endswith(".md") else item
        rel_out = os.path.normpath(os.path.join(host_base, sub_path, f"{stem}{ext}"))
        if has_src and os.path.isfile(os.path.join(str(src_dir), f"{stem}.md")):
            paths.append(rel_out)
        elif not has_src and target_dir and os.path.isfile(os.path.join(target_dir, rel_out)):
            paths.append(rel_out)
    return paths


def _bundled_host_profile_paths(
    toolkit_root: str, host_base: str, skills_subpath: str
) -> List[str]:
    """Return relative target paths for bundled host adapter profiles inside wf-management."""
    hosts_src = find_hosts_dir_with_fallback(toolkit_root)
    dst_hosts = os.path.join(host_base, skills_subpath, "wf-management", "hosts")
    bundled = [
        os.path.normpath(os.path.join(dst_hosts, fn))
        for fn in sorted(os.listdir(hosts_src))
        if fn.endswith(".json")
    ]
    abs_tk = os.path.abspath(toolkit_root)
    if os.path.isfile(os.path.join(abs_tk, "config", "capabilities.json")):
        bundled.append(os.path.normpath(os.path.join(dst_hosts, "capabilities.json")))
    if ca._collect_bundled_plugins_map(abs_tk) is not None:
        bundled.append(os.path.normpath(os.path.join(dst_hosts, "plugins.json")))
    if ca._collect_bundled_teams_map(abs_tk) is not None:
        bundled.append(os.path.normpath(os.path.join(dst_hosts, "teams.json")))
    return list(dict.fromkeys(bundled))


def _walk_clean_relpaths(root_dir: str, skip_names: Tuple[str, ...] = (".DS_Store",)) -> List[str]:
    """Return sorted relative file paths under root_dir, skipping caches and skip_names."""
    rels: List[str] = []
    for walk_root, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        valid = [fn for fn in sorted(filenames) if fn not in skip_names and not fn.endswith(".pyc")]
        for fn in valid:
            rels.append(os.path.relpath(os.path.join(walk_root, fn), root_dir))
    return rels


def _resolve_skill_paths(
    toolkit_root: str,
    skills_src: Optional[str],
    skill_names: Sequence[str],
    host_base: str,
    dirs_cfg: Dict[str, Any],
    target_dir: Optional[str] = None,
) -> List[str]:
    """Compute compiled relative target paths for skills and bundled host profiles."""
    cfg = dirs_cfg.get("skills")
    if not cfg:
        return []
    skill_filename = cfg.get("filename", "SKILL.md")
    skills_sub = cfg["path"]
    eff_src = skills_src if (skills_src and os.path.isdir(skills_src)) else (
        os.path.join(target_dir, host_base, skills_sub) if target_dir else None
    )
    if not eff_src or not os.path.isdir(eff_src):
        return []
    paths: List[str] = []
    for skill_name in skill_names:
        s_dir = os.path.join(eff_src, skill_name)
        if not os.path.isdir(s_dir):
            continue
        for rel_in_skill in _walk_clean_relpaths(s_dir, (".DS_Store", "skill.json")):
            out_rel = skill_filename if rel_in_skill == "SKILL.md" else rel_in_skill
            paths.append(os.path.normpath(os.path.join(host_base, skills_sub, skill_name, out_rel)))
        if skill_name == "wf-management":
            paths.extend(_bundled_host_profile_paths(toolkit_root, host_base, skills_sub))
    return paths


def _resolve_team_paths(
    teams_src: Optional[str],
    team_names: Sequence[str],
    host_base: str,
    dirs_cfg: Dict[str, Any],
    target_dir: Optional[str] = None,
) -> List[str]:
    """Compute compiled relative target paths for installed team pack directories."""
    cfg = dirs_cfg.get("teams")
    if not cfg:
        return []
    teams_sub = cfg["path"]
    eff_src = teams_src if (teams_src and os.path.isdir(teams_src)) else (
        os.path.join(target_dir, host_base, teams_sub) if target_dir else None
    )
    if not eff_src or not os.path.isdir(eff_src):
        return []
    paths: List[str] = []
    for team_name in team_names:
        t_dir = os.path.join(eff_src, team_name)
        if not os.path.isdir(t_dir):
            continue
        for rel_in_team in _walk_clean_relpaths(t_dir):
            paths.append(os.path.normpath(os.path.join(host_base, teams_sub, team_name, rel_in_team)))
    return paths


def _resolve_plugin_paths(
    plugins_src: Optional[str],
    plugin_names: Sequence[str],
    profile: Dict[str, Any],
    target_dir: Optional[str] = None,
) -> List[str]:
    """Compute compiled plugin/hook file paths, excluding shared user .claude/settings.json."""
    mode = profile.get("hooks_mode", "none")
    if mode in ("none", "claude_settings_json"):
        return []
    host_base = str(profile["base_dir"])
    plugins_sub = profile.get("dirs", {}).get("plugins", {}).get("path", "plugins")
    eff_src = plugins_src if (plugins_src and os.path.isdir(plugins_src)) else (
        os.path.join(target_dir, host_base, plugins_sub) if target_dir else None
    )
    if not eff_src or not os.path.isdir(eff_src):
        return []
    paths: List[str] = []
    has_hooks = False
    for pl_name in plugin_names:
        pjson = os.path.join(eff_src, pl_name, "plugin.json")
        if not os.path.isfile(pjson):
            continue
        meta = ca._load_json_file(pjson)
        out_name = str(meta.get("name", pl_name))
        paths.append(os.path.normpath(os.path.join(host_base, plugins_sub, out_name, "plugin.json")))
        if ca.compile_plugin_hooks_for_host(meta, profile) or os.path.isfile(os.path.join(eff_src, pl_name, "hooks.json")):
            has_hooks = True
            paths.append(os.path.normpath(os.path.join(host_base, plugins_sub, out_name, "hooks.json")))
    if mode == "grok_hooks_and_plugins" and has_hooks:
        paths.append(os.path.normpath(profile.get("hooks_target", os.path.join(".grok", "hooks.json"))))
    return paths


def _resolve_single_host_files(
    toolkit_root: str,
    target_dir: str,
    profile: Dict[str, Any],
    manifest: Dict[str, Any],
    src_dirs: Dict[str, Optional[str]],
) -> List[str]:
    """Resolve all compiled relative file paths for a single host profile."""
    host_base = str(profile["base_dir"])
    dirs_cfg = profile.get("dirs", {})
    files: List[str] = []
    for cat in ("agents", "rules", "workflows"):
        files.extend(_resolve_flat_paths(src_dirs[cat], manifest.get(cat, []), cat, host_base, dirs_cfg, target_dir))
    files.extend(_resolve_skill_paths(toolkit_root, src_dirs["skills"], manifest.get("skills", []), host_base, dirs_cfg, target_dir))
    files.extend(_resolve_team_paths(src_dirs["teams"], manifest.get("teams", []), host_base, dirs_cfg, target_dir))
    files.extend(_resolve_plugin_paths(src_dirs["plugins"], manifest.get("plugins", []), profile, target_dir))
    if profile.get("id") == "antigravity":
        for h_cand in (os.path.join(toolkit_root, "hooks.json"), os.path.join(toolkit_root, ".agents", "hooks.json")):
            if os.path.isfile(h_cand):
                files.append(os.path.normpath(os.path.join(host_base, "hooks.json")))
                break
    return files


def resolve_installed_file_paths(
    toolkit_root: str,
    target_dir: str,
    base_dir: Optional[str] = None,
    teams_arg: Optional[str] = None,
    hosts: Any = None,
    auto_detect: bool = True,
) -> List[str]:
    """Resolve complete sorted list of relative compiled file paths across all active hosts."""
    toolkit_root = os.path.abspath(toolkit_root)
    target_dir = os.path.abspath(target_dir)
    manifest = resolve_manifest(toolkit_root, target_dir, teams_arg)
    profiles = load_profiles_with_fallback(toolkit_root)
    active_hosts = resolve_target_hosts(
        toolkit_root, target_dir, hosts_arg=hosts, base_dir=base_dir, auto_detect=auto_detect
    )
    teams_src = find_teams_dir(toolkit_root)
    src_dirs = {
        cat: ca._find_source_dir(toolkit_root, cat)
        for cat in ("agents", "rules", "workflows", "skills", "plugins")
    }
    src_dirs["teams"] = teams_src if os.path.isdir(teams_src) else None
    installed: List[str] = []
    for hid in active_hosts:
        if hid in profiles:
            installed.extend(_resolve_single_host_files(toolkit_root, target_dir, profiles[hid], manifest, src_dirs))
    return sorted(set(installed))


def load_installed_manifest(target_dir: str) -> Optional[Dict[str, Any]]:
    """Load workforces/.manifest.json if it exists and is valid JSON."""
    manifest_path = os.path.join(target_dir, MANIFEST_REL_PATH)
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_installed_manifest(
    target_dir: str,
    version: Optional[str],
    installed_teams: Iterable[str],
    installed_files: Iterable[str],
    hosts: Optional[Sequence[str]] = None,
) -> str:
    """Save workforces/.manifest.json with version, active hosts, installed teams, and file paths."""
    target_dir = os.path.abspath(target_dir)
    manifest_path = os.path.join(target_dir, MANIFEST_REL_PATH)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    if hosts is None:
        resolved_hosts = resolve_target_hosts(target_dir, target_dir)
    else:
        profiles = load_profiles_with_fallback(target_dir)
        resolved_hosts = ca._order_hosts([ca.resolve_host_alias(h, profiles) or h for h in hosts])
    cleaned_files = [
        f for f in (os.path.normpath(p) for p in (installed_files or []))
        if f not in _PROTECTED_USER_FILES
    ]
    data = {
        "version": version or "unknown",
        "hosts": resolved_hosts,
        "installed_teams": sorted(set(installed_teams or [])),
        "installed_files": sorted(set(cleaned_files)),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(manifest_path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)
    return manifest_path

def get_known_legacy_obsolete_files(base_dir: str) -> List[str]:
    """Return relative paths of known historical Workforces files under base_dir."""
    return [os.path.normpath(os.path.join(base_dir, p)) for p in LEGACY_OBSOLETE_SUBPATHS]


def _git_historical_subpaths(toolkit_root: Optional[str]) -> List[str]:
    """Return historical asset subpaths from toolkit git log when available."""
    if not toolkit_root or not os.path.isdir(os.path.join(toolkit_root, '.git')):
        return []
    try:
        res = subprocess.run(
            ['git', '-C', toolkit_root, 'log', '--format=', '--name-only'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if res.returncode != 0:
        return []
    valid_roots = ('agents', 'workflows', 'rules', 'skills', 'plugins', 'teams')
    return [hp.strip() for hp in res.stdout.splitlines() if hp.strip() and hp.strip().split('/')[0] in valid_roots]


def _map_subpath_for_host(subpath: str, profile: Dict[str, Any]) -> List[str]:
    """Map a canonical toolkit subpath into host-compiled and raw legacy relative paths."""
    host_base = str(profile["base_dir"])
    dirs_cfg = profile.get("dirs", {})
    segs = subpath.replace("\\", "/").split("/")
    top = segs[0]
    mapped: List[str] = []
    if not (host_base == ".github" and top in ("workflows", "docs")):
        mapped.append(os.path.normpath(os.path.join(host_base, subpath)))
    cfg = dirs_cfg.get(top)
    if cfg and top in ("agents", "rules", "workflows") and len(segs) == 2 and segs[1].endswith(".md"):
        stem = segs[1][:-3]
        mapped.append(os.path.normpath(os.path.join(host_base, cfg["path"], f"{stem}{cfg.get('ext', '.md')}")))
    elif cfg and top in ("skills", "teams", "plugins") and len(segs) >= 2:
        mapped.append(os.path.normpath(os.path.join(host_base, cfg["path"], *segs[1:])))
    return mapped


def _walk_category_subpaths(src_dir: str, cat: str) -> List[str]:
    """Walk a single toolkit category directory and return canonical relative subpaths."""
    if not src_dir or not os.path.isdir(src_dir):
        return []
    found: List[str] = []
    for walk_root, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        valid_files = [f for f in filenames if f != ".DS_Store" and not f.endswith(".pyc")]
        for fn in valid_files:
            rel = os.path.relpath(os.path.join(walk_root, fn), src_dir).replace(os.sep, "/")
            found.append(f"{cat}/{rel}")
            if cat == "plugins" and fn == "plugin.json":
                pl_rel = os.path.dirname(rel)
                found.append(f"plugins/{pl_rel}/hooks.json" if pl_rel else "plugins/hooks.json")
    return found


def _collect_toolkit_source_subpaths(toolkit_root: Optional[str]) -> List[str]:
    """Collect current toolkit asset subpaths for detecting unmanifested legacy copies."""
    if not toolkit_root:
        return []
    root = os.path.abspath(toolkit_root)
    subpaths: List[str] = []
    for cat in ("agents", "rules", "workflows", "skills", "plugins"):
        subpaths.extend(_walk_category_subpaths(ca._find_source_dir(root, cat) or "", cat))
    subpaths.extend(_walk_category_subpaths(find_teams_dir(root), "teams"))
    return subpaths


def _collect_legacy_copilot_candidates(
    toolkit_root: Optional[str], historical_subpaths: Iterable[str]
) -> Set[str]:
    """Collect Workforces asset paths under legacy .github/copilot/{agents,rules,skills,workflows,plugins}."""
    legacy_base = os.path.join(".github", "copilot")
    combined = list(historical_subpaths) + _collect_toolkit_source_subpaths(toolkit_root)
    out: Set[str] = set()
    for sp in combined:
        top = sp.replace("\\", "/").split("/", 1)[0]
        if top in _LEGACY_COPILOT_CATS:
            out.add(os.path.normpath(os.path.join(legacy_base, sp)))
    return out


def _collect_multi_host_candidates(
    target_dir: str,
    active_hosts: Sequence[str],
    profiles: Dict[str, Dict[str, Any]],
    toolkit_root: Optional[str],
    explicit_base_dir: Optional[str] = None,
) -> Set[str]:
    """Collect candidate obsolete relative paths across active hosts, manifest, and legacy layouts."""
    candidates: Set[str] = set()
    prev_manifest = load_installed_manifest(target_dir)
    if isinstance(prev_manifest, dict):
        for pf in prev_manifest.get("installed_files", []):
            candidates.add(os.path.normpath(pf))
    hist = list(
        dict.fromkeys(
            list(LEGACY_OBSOLETE_SUBPATHS)
            + _git_historical_subpaths(toolkit_root)
            + _collect_toolkit_source_subpaths(toolkit_root)
        )
    )
    for hid in active_hosts:
        if hid in profiles:
            for hp in hist:
                candidates.update(_map_subpath_for_host(hp, profiles[hid]))
    if explicit_base_dir:
        for hp in hist:
            candidates.add(os.path.normpath(os.path.join(explicit_base_dir, hp)))
    if "copilot" in active_hosts:
        candidates.update(_collect_legacy_copilot_candidates(toolkit_root, hist))
    return candidates - _PROTECTED_USER_FILES


def _known_unprefixed_slugs(
    toolkit_root: Optional[str], category: str, fallback_items: Iterable[str]
) -> Set[str]:
    """Return unprefixed slugs corresponding to current wf-* skills or plugins."""
    names = set(fallback_items)
    if toolkit_root:
        for src in (os.path.join(toolkit_root, category), os.path.join(toolkit_root, ".agents", category)):
            if os.path.isdir(src):
                names.update(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)))
    return {n[3:] for n in names if n.startswith("wf-") and len(n) > 3}


def _scan_single_base_legacy(
    target_dir: str,
    base: str,
    unprefixed_plugins: Set[str],
    unprefixed_skills: Set[str],
    claude_active: bool,
) -> Set[str]:
    """Collect legacy skill/plugin directories under a single base path."""
    found: Set[str] = set()
    cp_base = os.path.join(".github", "copilot")
    plugins_dir = os.path.join(target_dir, base, "plugins")
    if os.path.isdir(plugins_dir):
        for entry in os.listdir(plugins_dir):
            is_legacy_pl = (entry.startswith("workforce-") and entry.endswith("-plugin")) or entry in unprefixed_plugins
            is_unused_wf = base in (".claude", cp_base) and entry.startswith("wf-") and entry.endswith("-plugin")
            if is_legacy_pl or (is_unused_wf and (claude_active or base != ".claude")):
                found.add(os.path.normpath(os.path.join(base, "plugins", entry)))
    skills_dir = os.path.join(target_dir, base, "skills")
    if os.path.isdir(skills_dir):
        for entry in os.listdir(skills_dir):
            is_legacy_sk = entry.startswith("workforce-") or entry in unprefixed_skills
            if is_legacy_sk or (base == cp_base and entry.startswith("wf-")):
                found.add(os.path.normpath(os.path.join(base, "skills", entry)))
    return found


def _scan_legacy_base_dirs(
    target_dir: str,
    scan_bases: Iterable[str],
    toolkit_root: Optional[str],
    claude_active: bool,
) -> Set[str]:
    """Collect legacy workforce-* and unprefixed skill/plugin dirs across active host bases."""
    extra_dirs: Set[str] = set()
    unprefixed_plugins = _known_unprefixed_slugs(toolkit_root, "plugins", CORE_PLUGINS)
    unprefixed_skills = _known_unprefixed_slugs(toolkit_root, "skills", CORE_SKILLS)
    for base in scan_bases:
        extra_dirs.update(
            _scan_single_base_legacy(target_dir, base, unprefixed_plugins, unprefixed_skills, claude_active)
        )
    return extra_dirs


_LEGACY_HOST_CAT_DIRS = frozenset({
    (".claude", "plugins"),
    (".claude", "workflows"),
    (".grok", "workflows"),
    (".cursor", "plugins"),
    (".cursor", "workflows"),
})


def _min_preserve_depth(rel_parts: Sequence[str]) -> int:
    """Return minimum path segment depth eligible for empty-directory deletion."""
    if len(rel_parts) >= 2 and rel_parts[0] == ".github" and rel_parts[1] == "copilot":
        if len(rel_parts) >= 3 and rel_parts[2] == "teams":
            return 4
        return 2
    if len(rel_parts) >= 2 and (rel_parts[0], rel_parts[1]) in _LEGACY_HOST_CAT_DIRS:
        return 2
    return 3


def _find_obsolete_empty_dirs(
    target_dir: str,
    scan_bases: Sequence[str],
    candidate_files: Iterable[str],
    current_set: Set[str],
    obsolete_files: Set[str],
    toolkit_root: Optional[str] = None,
    claude_active: bool = False,
) -> List[str]:
    """Identify effectively-empty legacy directories that contain no active or custom files."""
    candidate_dirs = _scan_legacy_base_dirs(target_dir, scan_bases, toolkit_root, claude_active)
    for rel_file in candidate_files:
        parts = rel_file.replace("\\", "/").split("/")
        min_depth = _min_preserve_depth(parts)
        for depth in range(min_depth, len(parts)):
            candidate_dirs.add(os.path.normpath("/".join(parts[:depth])))
    empty_dirs: List[str] = []
    protected_prefixes = [f + os.sep for f in (current_set | obsolete_files)]
    for cand_dir in sorted(candidate_dirs, key=lambda d: (d.count(os.sep), d)):
        if any(cand_dir == anc or cand_dir.startswith(anc + os.sep) for anc in empty_dirs):
            continue
        prefix = cand_dir + os.sep
        if cand_dir in current_set or any(p.startswith(prefix) for p in protected_prefixes):
            continue
        full_dir = os.path.join(target_dir, cand_dir)
        if os.path.isdir(full_dir) and not os.path.islink(full_dir) and _is_effectively_empty_dir(full_dir):
            empty_dirs.append(cand_dir)
    return empty_dirs


def _grok_hooks_has_user_keys(target_dir: str, grok_profile: Optional[Dict[str, Any]]) -> bool:
    """Return True if .grok/hooks.json exists and contains at least one non-Workforces key."""
    rel_hooks = (grok_profile or {}).get("hooks_target", os.path.join(".grok", "hooks.json"))
    hooks_path = os.path.join(target_dir, rel_hooks)
    if not os.path.isfile(hooks_path):
        return False
    try:
        raw = Path(hooks_path).read_text(encoding="utf-8").strip()
        data = json.loads(raw) if raw else {}
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and any(
        not ca.is_workforces_grok_ns(k, v) for k, v in data.items()
    )


def _protected_obsolete_paths(target_dir: str, profiles: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Return relative paths protected from whole-file deletion during obsolete pruning."""
    protected = set(_PROTECTED_USER_FILES)
    grok_prof = profiles.get("grok")
    if _grok_hooks_has_user_keys(target_dir, grok_prof):
        hooks_rel = os.path.normpath((grok_prof or {}).get("hooks_target", os.path.join(".grok", "hooks.json")))
        protected.add(hooks_rel)
    return protected


def _build_obsolete_scan_bases(
    profiles: Dict[str, Dict[str, Any]], active_hosts: Sequence[str], base_dir: Optional[str]
) -> List[str]:
    """Build host base directories to inspect for obsolete empty folders."""
    scan_bases = [str(profiles[h]["base_dir"]) for h in active_hosts if h in profiles]
    if "copilot" in active_hosts:
        scan_bases.append(os.path.join(".github", "copilot"))
    if base_dir and os.path.normpath(base_dir) not in scan_bases:
        scan_bases.append(os.path.normpath(base_dir))
    return scan_bases


def find_obsolete_files(
    target_dir: str,
    base_dir: Optional[str] = None,
    current_files: Optional[Iterable[str]] = None,
    toolkit_root: Optional[str] = None,
    hosts: Any = None,
    auto_detect: bool = True,
) -> List[str]:
    """Find obsolete Workforces files and empty legacy dirs across active hosts."""
    target_dir = os.path.abspath(target_dir)
    tk_root = os.path.abspath(toolkit_root) if toolkit_root else target_dir
    profiles = load_profiles_with_fallback(tk_root)
    active_hosts = resolve_target_hosts(tk_root, target_dir, hosts_arg=hosts, base_dir=base_dir, auto_detect=auto_detect)
    resolved_cur = (
        resolve_installed_file_paths(tk_root, target_dir, base_dir=base_dir, hosts=active_hosts, auto_detect=auto_detect)
        if current_files is None else current_files
    )
    current_set = {os.path.normpath(f) for f in resolved_cur}
    candidates = _collect_multi_host_candidates(target_dir, active_hosts, profiles, toolkit_root, base_dir)
    protected = _protected_obsolete_paths(target_dir, profiles)
    obsolete = {
        cand for cand in candidates
        if cand not in current_set and cand not in protected
        and (os.path.isfile(os.path.join(target_dir, cand)) or os.path.islink(os.path.join(target_dir, cand)))
    }
    scan_bases = _build_obsolete_scan_bases(profiles, active_hosts, base_dir)
    for empty_dir in _find_obsolete_empty_dirs(
        target_dir, scan_bases, candidates, current_set, obsolete, toolkit_root, claude_active=("claude" in active_hosts)
    ):
        obsolete.add(empty_dir)
    return sorted(f for f in obsolete if f not in current_set and f not in protected)


def _is_effectively_empty_dir(dir_path):
    """Return True if dir_path has no files other than __pycache__, .pyc, or .DS_Store."""
    for root, _, files in os.walk(dir_path):
        if "__pycache__" in os.path.relpath(root, dir_path).split(os.sep):
            continue
        for fn in files:
            if fn != ".DS_Store" and not fn.endswith(".pyc"):
                return False
    return True


def _cleanup_empty_parent_dirs(target_dir: str, dirs_to_check: Iterable[str]) -> None:
    """Remove emptied skill/plugin/team/legacy subdirectories while preserving active category roots."""
    for d in sorted(set(dirs_to_check), key=len, reverse=True):
        curr = d
        while curr and curr != target_dir and curr.startswith(target_dir + os.sep):
            rel_parts = os.path.relpath(curr, target_dir).replace("\\", "/").split("/")
            if len(rel_parts) < _min_preserve_depth(rel_parts):
                break
            if not os.path.isdir(curr):
                curr = os.path.dirname(curr)
                continue
            if _is_effectively_empty_dir(curr):
                shutil.rmtree(curr, ignore_errors=True)
                curr = os.path.dirname(curr)
            else:
                break


def _remove_obsolete_path(full_path: str) -> None:
    """Remove a single obsolete file or non-symlink directory."""
    if os.path.isdir(full_path) and not os.path.islink(full_path):
        shutil.rmtree(full_path)
    else:
        os.remove(full_path)


def _resolve_single_plugin_meta(
    pl_name: str,
    primary_src: Optional[str],
    bundled_map: Dict[str, Dict[str, Any]],
    fallback_src: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Resolve canonical plugin.json metadata (with hooks) for a single plugin."""
    chosen: Optional[Dict[str, Any]] = None
    if primary_src and os.path.isfile(os.path.join(primary_src, pl_name, "plugin.json")):
        chosen = ca._load_json_file(os.path.join(primary_src, pl_name, "plugin.json"))
    if (chosen is None or "hooks" not in chosen) and pl_name in bundled_map:
        chosen = bundled_map[pl_name]
    fb_json = os.path.join(fallback_src, pl_name, "plugin.json") if fallback_src else ""
    if (chosen is None or "hooks" not in chosen) and fb_json and os.path.isfile(fb_json):
        loaded = ca._load_json_file(fb_json)
        if chosen is None or "hooks" in loaded:
            chosen = loaded
    return chosen


def load_canonical_plugin_metas(toolkit_root: str, plugin_names: Sequence[str]) -> List[Dict[str, Any]]:
    """Load canonical plugin.json manifests (including hook specs) for plugin_names."""
    primary_src = ca._find_source_dir(os.path.abspath(toolkit_root), "plugins")
    fallback_src = ca._find_source_dir(str(Path(__file__).resolve().parents[3]), "plugins")
    bundled_map = _load_bundled_json_map(toolkit_root, "plugins.json", "plugins")
    metas = [_resolve_single_plugin_meta(pl, primary_src, bundled_map, fallback_src) for pl in plugin_names]
    return [m for m in metas if m]


def _has_orphaned_claude_hooks(
    settings_path: str, desired_by_phase: Dict[str, List[Dict[str, Any]]]
) -> bool:
    """Return True if .claude/settings.json contains any stale or orphaned Workforces hook rule."""
    try:
        raw_text = Path(settings_path).read_text(encoding="utf-8").strip()
        data = json.loads(raw_text) if raw_text else {}
    except (OSError, json.JSONDecodeError):
        return False
    hooks_obj = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks_obj, dict):
        return False
    for phase, rules in hooks_obj.items():
        if not isinstance(rules, list):
            continue
        wf_rules = [r for r in rules if ca._is_workforces_hook_rule(r)]
        if not wf_rules:
            continue
        desired = desired_by_phase.get(phase, [])
        if any(r not in desired for r in wf_rules) or len(wf_rules) > len(desired):
            return True
    return False


def _prune_orphaned_claude_hooks(
    target_dir: str,
    toolkit_root: Optional[str],
    active_hosts: Optional[Sequence[str]],
    active_plugins: Optional[Sequence[str]],
    dry_run: bool = False,
    quiet: bool = False,
) -> int:
    """Clean up orphaned wf-* hook entries in .claude/settings.json while preserving user hooks."""
    settings_rel = os.path.join(".claude", "settings.json")
    settings_path = os.path.join(target_dir, settings_rel)
    if not os.path.isfile(settings_path):
        return 0
    tk_root = os.path.abspath(toolkit_root) if toolkit_root else target_dir
    claude_profile = load_profiles_with_fallback(tk_root).get("claude")
    if not claude_profile:
        return 0
    hosts_list = list(active_hosts) if active_hosts is not None else resolve_target_hosts(tk_root, target_dir)
    metas: List[Dict[str, Any]] = []
    desired_by_phase: Dict[str, List[Dict[str, Any]]] = {}
    if "claude" in hosts_list:
        plugins_list = list(active_plugins) if active_plugins is not None else resolve_manifest(tk_root, target_dir)["plugins"]
        metas = load_canonical_plugin_metas(tk_root, plugins_list)
        for meta in metas:
            for phase, entries in ca.compile_plugin_hooks_for_host(meta, claude_profile).items():
                desired_by_phase.setdefault(phase, []).extend(entries)
    if not _has_orphaned_claude_hooks(settings_path, desired_by_phase):
        return 0
    changed, _ = ca.sync_claude_settings_hooks(target_dir, metas, claude_profile, dry_run=dry_run)
    if changed and not quiet:
        tag = "\033[1;33m[WOULD PRUNE HOOKS]\033[0m" if dry_run else "\033[0;31m[PRUNED HOOKS]\033[0m"
        print(f"  {tag} {settings_rel}")
    return int(changed)


def _desired_grok_hooks(
    target_dir: str,
    active_metas: Sequence[Dict[str, Any]],
    remaining_plugins: Sequence[str],
    grok_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute desired Workforces hook namespaces for .grok/hooks.json."""
    desired: Dict[str, Any] = {}
    covered: Set[str] = set()
    for meta in active_metas:
        compiled = ca.compile_plugin_hooks_for_host(meta, grok_profile)
        if compiled:
            desired[str(meta.get("hook_namespace", meta["name"]))] = compiled
            covered.add(str(meta.get("name", "")))
    for pl in remaining_plugins:
        if pl not in covered:
            disk_h = os.path.join(target_dir, ".grok", "plugins", pl, "hooks.json")
            if os.path.isfile(disk_h):
                desired.update(ca._load_json_file(disk_h))
    return desired


def sync_grok_hooks_file(
    target_dir: str,
    active_metas: Sequence[Dict[str, Any]],
    remaining_plugins: Sequence[str],
    grok_profile: Dict[str, Any],
    grok_active: bool = True,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """Idempotently re-sync Workforces namespaces in .grok/hooks.json while preserving user keys."""
    rel_hooks = grok_profile.get("hooks_target", os.path.join(".grok", "hooks.json"))
    hooks_dst = os.path.join(os.path.abspath(target_dir), rel_hooks)
    if not os.path.isfile(hooks_dst):
        return False, hooks_dst
    try:
        raw = Path(hooks_dst).read_text(encoding="utf-8").strip()
        original = json.loads(raw) if raw else {}
    except (OSError, json.JSONDecodeError):
        return False, hooks_dst
    if not isinstance(original, dict):
        return False, hooks_dst
    updated: Dict[str, Any] = {k: v for k, v in original.items() if not ca.is_workforces_grok_ns(k, v)}
    if grok_active:
        updated.update(_desired_grok_hooks(target_dir, active_metas, remaining_plugins, grok_profile))
    if updated == original:
        return False, hooks_dst
    if not dry_run:
        if updated:
            ca._write_text_if_changed(hooks_dst, json.dumps(updated, indent=2) + "\n", dry_run=False)
        else:
            os.remove(hooks_dst)
    return True, hooks_dst


def _prune_orphaned_grok_hooks(
    target_dir: str,
    toolkit_root: Optional[str],
    active_hosts: Optional[Sequence[str]],
    active_plugins: Optional[Sequence[str]],
    already_obsolete: Set[str],
    dry_run: bool = False,
    quiet: bool = False,
) -> int:
    """Clean up orphaned wf-* hook namespaces in .grok/hooks.json while preserving user keys."""
    tk_root = os.path.abspath(toolkit_root) if toolkit_root else target_dir
    grok_profile = load_profiles_with_fallback(tk_root).get("grok")
    if not grok_profile:
        return 0
    hooks_rel = os.path.normpath(grok_profile.get("hooks_target", os.path.join(".grok", "hooks.json")))
    if hooks_rel in already_obsolete or not os.path.isfile(os.path.join(target_dir, hooks_rel)):
        return 0
    hosts_list = list(active_hosts) if active_hosts is not None else resolve_target_hosts(tk_root, target_dir)
    grok_active = "grok" in hosts_list
    plugins_list = (
        list(active_plugins) if active_plugins is not None else resolve_manifest(tk_root, target_dir)["plugins"]
    ) if grok_active else []
    metas = load_canonical_plugin_metas(tk_root, plugins_list) if grok_active else []
    changed, _ = sync_grok_hooks_file(
        target_dir, metas, plugins_list, grok_profile, grok_active=grok_active, dry_run=dry_run
    )
    if changed and not quiet:
        tag = "\033[1;33m[WOULD PRUNE HOOKS]\033[0m" if dry_run else "\033[0;31m[PRUNED HOOKS]\033[0m"
        print(f"  {tag} {hooks_rel}")
    return int(changed)


def _prune_single_obsolete_entry(
    target_dir: str,
    f_rel: str,
    dry_run: bool,
    quiet: bool,
    dirs_to_check: Set[str],
) -> int:
    """Prune or simulate pruning one obsolete relative path and return 1 if processed."""
    norm_rel = os.path.normpath(f_rel)
    if norm_rel in _PROTECTED_USER_FILES:
        return 0
    full_path = os.path.abspath(os.path.join(target_dir, norm_rel))
    if not full_path.startswith(target_dir + os.sep) or not os.path.exists(full_path):
        return 0
    if dry_run:
        if not quiet:
            print(f"  \033[1;33m[WOULD PRUNE OBSOLETE]\033[0m {f_rel}")
        return 1
    try:
        _remove_obsolete_path(full_path)
        if not quiet:
            print(f"  \033[0;31m[PRUNED OBSOLETE]\033[0m {f_rel}")
        dirs_to_check.add(os.path.dirname(full_path))
        return 1
    except OSError as exc:
        if not quiet:
            print(f"  \033[0;31m[ERROR PRUNING]\033[0m {f_rel}: {exc}")
        return 0


def prune_obsolete_files(
    target_dir: str,
    obsolete_files: Iterable[str],
    dry_run: bool = False,
    quiet: bool = False,
    toolkit_root: Optional[str] = None,
    active_hosts: Optional[Sequence[str]] = None,
    active_plugins: Optional[Sequence[str]] = None,
) -> int:
    """Remove obsolete files, legacy directories, and orphaned Claude/Grok hooks safely."""
    target_dir = os.path.abspath(target_dir)
    obsolete_list = list(obsolete_files)
    obsolete_norm = {os.path.normpath(f) for f in obsolete_list}
    dirs_to_check: Set[str] = set()
    pruned_count = sum(
        _prune_single_obsolete_entry(target_dir, f_rel, dry_run, quiet, dirs_to_check)
        for f_rel in obsolete_list
    )
    if not dry_run and dirs_to_check:
        _cleanup_empty_parent_dirs(target_dir, dirs_to_check)
    pruned_count += _prune_orphaned_claude_hooks(
        target_dir, toolkit_root, active_hosts, active_plugins, dry_run=dry_run, quiet=quiet
    )
    pruned_count += _prune_orphaned_grok_hooks(
        target_dir, toolkit_root, active_hosts, active_plugins, obsolete_norm, dry_run=dry_run, quiet=quiet
    )
    return pruned_count


def _sanitize_bash_list(items: Iterable[Any]) -> str:
    """Format items as a shell-safe space-separated string."""
    cleaned = [re.sub(r'[^a-zA-Z0-9_./-]', '', str(item)) for item in items]
    return ' '.join(c for c in cleaned if c)


def _emit_bash_exports(manifest: Dict[str, Any], active_hosts: Sequence[str]) -> None:
    """Print bash variable exports for active hosts and allowed manifest assets."""
    print(f'ACTIVE_HOSTS="{_sanitize_bash_list(active_hosts)}"')
    print(f'INSTALLED_TEAMS_LIST="{_sanitize_bash_list(manifest["installed_teams"])}"')
    print(f'ALLOWED_AGENTS="{_sanitize_bash_list(manifest["agents"])}"')
    print(f'ALLOWED_RULES="{_sanitize_bash_list(manifest["rules"])}"')
    print(f'ALLOWED_SKILLS="{_sanitize_bash_list(manifest["skills"])}"')
    print(f'ALLOWED_WORKFLOWS="{_sanitize_bash_list(manifest["workflows"])}"')
    print(f'ALLOWED_PLUGINS="{_sanitize_bash_list(manifest["plugins"])}"')
    print(f'ALLOWED_TEAMS="{_sanitize_bash_list(manifest["teams"])}"')


def _build_cli_parser() -> argparse.ArgumentParser:
    """Construct CLI parser for resolve_manifest.py."""
    parser = argparse.ArgumentParser(description="Resolve workforce asset manifest by installed teams and AI hosts")
    parser.add_argument("--toolkit-root", default=None, help="Root of source workforces toolkit")
    parser.add_argument("--target", default=".", help="Root of target project")
    parser.add_argument("--hosts", "--editor", dest="hosts", default="auto", help="Comma-separated hosts, 'auto', or 'all'")
    parser.add_argument("--no-auto-detect", action="store_true", help="Disable auto-detecting workspace AI folders")
    parser.add_argument("--teams", default=None, help="Comma-separated teams (or 'all')")
    parser.add_argument("--format", choices=["json", "bash-export", "files"], default="json", help="Output format")
    parser.add_argument("--save-manifest", action="store_true", help="Save resolved manifest to workforces/.manifest.json")
    parser.add_argument("--version-hash", default="unknown", help="Version commit hash to record in manifest")
    parser.add_argument("--prune-obsolete", action="store_true", help="Prune obsolete toolkit files from target")
    parser.add_argument("--dry", "--dry-run", action="store_true", help="Show what would be pruned without deleting files")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress human-readable prune log lines")
    return parser


def _resolve_cli_toolkit_root(raw_toolkit_root: Optional[str], target_dir: str) -> str:
    """Resolve CLI toolkit_root, preferring CWD toolkit sources when present or target_dir offline."""
    if raw_toolkit_root is not None:
        return os.path.abspath(raw_toolkit_root)
    cwd = os.path.abspath(".")
    if ca._find_source_dir(cwd, "skills") or os.path.isdir(os.path.join(cwd, "config", "hosts")):
        return cwd
    return target_dir


def _run_prune_obsolete_cli(
    args: argparse.Namespace,
    target_dir: str,
    installed_files: Sequence[str],
    toolkit_root: str,
    active_hosts: Sequence[str],
    manifest: Dict[str, Any],
    auto_detect: bool,
) -> None:
    """Execute --prune-obsolete CLI mode and emit JSON summary when requested."""
    quiet_mode = args.quiet or ("--format" in sys.argv and args.format == "json")
    obsolete = find_obsolete_files(
        target_dir, None, installed_files, toolkit_root, hosts=active_hosts, auto_detect=auto_detect
    )
    pruned_count = prune_obsolete_files(
        target_dir, obsolete, dry_run=args.dry, quiet=quiet_mode,
        toolkit_root=toolkit_root, active_hosts=active_hosts, active_plugins=manifest["plugins"],
    )
    if args.format == "json" and ("--format" in sys.argv or not args.quiet):
        print(json.dumps({"hosts": active_hosts, "obsolete_files": obsolete, "pruned_count": pruned_count}, indent=2))


def main() -> None:
    """CLI entrypoint for manifest resolution, tracking, and multi-host pruning."""
    parser = _build_cli_parser()
    args = parser.parse_args()
    target_dir = os.path.abspath(args.target)
    toolkit_root = _resolve_cli_toolkit_root(args.toolkit_root, target_dir)
    auto_detect = not args.no_auto_detect
    try:
        active_hosts = resolve_target_hosts(toolkit_root, target_dir, hosts_arg=args.hosts, auto_detect=auto_detect)
    except ValueError as exc:
        parser.error(str(exc))
    manifest = resolve_manifest(toolkit_root, target_dir, args.teams)
    installed_files = resolve_installed_file_paths(
        toolkit_root, target_dir, teams_arg=args.teams, hosts=active_hosts, auto_detect=auto_detect
    )
    if args.prune_obsolete:
        _run_prune_obsolete_cli(args, target_dir, installed_files, toolkit_root, active_hosts, manifest, auto_detect)
        return
    if args.save_manifest:
        save_path = save_installed_manifest(
            target_dir, args.version_hash, manifest["installed_teams"], installed_files, hosts=active_hosts
        )
        if args.format == "json":
            print(json.dumps({"manifest_path": save_path, "hosts": active_hosts, "total_files": len(installed_files)}, indent=2))
        return
    if args.format == "json":
        print(json.dumps({**manifest, "hosts": active_hosts}, indent=2))
    elif args.format == "files":
        print(json.dumps(installed_files, indent=2))
    elif args.format == "bash-export":
        _emit_bash_exports(manifest, active_hosts)


if __name__ == "__main__":
    main()
