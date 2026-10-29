#!/usr/bin/env python3
"""
Workforces Multi-Host Team Pruner & Uninstaller
Safely removes team assets (agents, skills, rules, workflows, plugins, hooks) across all
active AI host directories (.agents/, .claude/, .github/, .grok/, .cursor/) while
programmatically preserving shared dependencies across remaining installed teams and
keeping workspace personas and historical context in workforces/ intact.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compile_assets as ca  # noqa: E402
from resolve_manifest import (  # noqa: E402
    _cleanup_empty_parent_dirs,
    detect_base_dir,  # noqa: F401 - re-exported for backward compatibility
    ensure_md_ext,
    get_installed_teams,
    get_team_pack_data,
    load_canonical_plugin_metas,
    load_profiles_with_fallback,
    resolve_installed_file_paths,
    resolve_manifest,
    resolve_target_hosts,
    save_installed_manifest,
    sync_grok_hooks_file,
)

# Terminal styling
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"


def update_workrules(target_dir: str, remaining_teams: Sequence[str], dry_run: bool = False) -> bool:
    """Update installed_teams in workforces/workrules.md."""
    workrules_path = os.path.join(target_dir, "workforces", "workrules.md")
    if not os.path.exists(workrules_path):
        return False
    with open(workrules_path, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    new_teams_yaml = "\n".join([f"  - {t}" for t in remaining_teams]) if remaining_teams else "  []"
    block_re = r'## Installed Teams\s*\n(?:\s*-\s*[^\n]+\n?|\s*\[\]\s*\n?)+'
    if re.search(block_re, content):
        new_block = f"## Installed Teams\n- installed_teams:\n{new_teams_yaml}\n"
        updated = re.sub(block_re, new_block, content)
    elif re.search(r'installed_teams:\s*\[?.*?\]?(\n|$)', content):
        updated = re.sub(
            r'installed_teams:\s*\[?.*?\]?(\n|$)',
            f"installed_teams: [{', '.join(remaining_teams)}]\n",
            content,
        )
    else:
        updated = content
    if updated == content:
        return False
    if not dry_run:
        with open(workrules_path, "w", encoding="utf-8") as fh:
            fh.write(updated)
    return True


def update_workstate(target_dir: str, team_name: str, dry_run: bool = False) -> bool:
    """Remove team entries from active tables or lists in workforces/workstate.md."""
    workstate_path = os.path.join(target_dir, "workforces", "workstate.md")
    if not os.path.exists(workstate_path):
        return False
    with open(workstate_path, "r", encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()
    has_active_header = "Active Teams" in "".join(lines)
    updated_lines: List[str] = []
    modified = False
    for line in lines:
        stripped = line.strip()
        if team_name in line and (has_active_header or "|" in line):
            if (stripped.startswith("|") and f"| {team_name} " in line) or (
                stripped.startswith("-") and team_name in line
            ):
                modified = True
                continue
        updated_lines.append(line)
    if modified and not dry_run:
        with open(workstate_path, "w", encoding="utf-8") as fh:
            fh.writelines(updated_lines)
    return modified


def _build_asset_deps(
    toolkit_root: str, target_dir: str, remaining_teams: Sequence[str]
) -> Dict[str, Dict[str, List[str]]]:
    """Map each remaining asset to the list of remaining teams that require it."""
    deps: Dict[str, Dict[str, List[str]]] = {
        k: {} for k in ("agents", "skills", "rules", "workflows", "plugins")
    }
    for rt in remaining_teams:
        rt_data = get_team_pack_data(toolkit_root, rt, target_dir=target_dir) or {}
        for a in rt_data.get("agents", []):
            deps["agents"].setdefault(ensure_md_ext(a), []).append(rt)
        for s in rt_data.get("skills", []):
            deps["skills"].setdefault(s, []).append(rt)
        for r in rt_data.get("rules", []):
            deps["rules"].setdefault(ensure_md_ext(r), []).append(rt)
        for w in rt_data.get("workflows", []):
            deps["workflows"].setdefault(ensure_md_ext(w), []).append(rt)
        for pl in rt_data.get("plugins", []):
            deps["plugins"].setdefault(pl, []).append(rt)
    return deps


def _remove_target(
    full_path: str, rel_label: str, kind_label: str, dry_run: bool, removed_parents: Set[str]
) -> int:
    """Delete an orphaned file or directory (or simulate in dry_run) and return 1 if present."""
    if not os.path.exists(full_path) and not os.path.islink(full_path):
        return 0
    if dry_run:
        print(f"  {YELLOW}[WOULD PRUNE {kind_label}]{NC} {rel_label}")
        return 1
    if os.path.isdir(full_path) and not os.path.islink(full_path):
        shutil.rmtree(full_path, ignore_errors=True)
    else:
        os.remove(full_path)
    removed_parents.add(os.path.dirname(full_path))
    print(f"  {RED}[PRUNED {kind_label}]{NC} {rel_label}")
    return 1


def _candidate_flat_paths(
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    category: str,
    canon_md: str,
) -> List[Tuple[str, str]]:
    """Return (full_path, rel_label) candidates across active hosts for a flat asset."""
    stem = canon_md[:-3] if canon_md.endswith(".md") else canon_md
    rels: List[str] = []
    for hid in active_hosts:
        profile = profiles.get(hid, {})
        cfg = profile.get("dirs", {}).get(category)
        if cfg:
            rels.append(os.path.join(str(profile["base_dir"]), cfg["path"], f"{stem}{cfg.get('ext', '.md')}"))
        if hid == "copilot":
            rels.append(os.path.join(".github", "copilot", category, canon_md))
        elif hid in ("claude", "grok", "cursor") and category == "workflows":
            rels.append(os.path.join(str(profile.get("base_dir", f".{hid}")), "workflows", canon_md))
    deduped = list(dict.fromkeys(rels))
    return [(os.path.join(target_dir, r), r) for r in deduped]


def _prune_flat_category(
    items: Sequence[str],
    category: str,
    kind_label: str,
    manifest: Dict[str, Any],
    asset_deps: Dict[str, Dict[str, List[str]]],
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    dry_run: bool,
    removed_parents: Set[str],
) -> Tuple[int, int]:
    """Prune or preserve flat assets (agents, rules, workflows) across all active hosts."""
    pruned = preserved = 0
    for raw in items:
        canon = ensure_md_ext(raw)
        if canon in manifest[category]:
            deps = asset_deps[category].get(canon, [])
            reason = f"needed by: {', '.join(deps)}" if deps else f"core {kind_label.lower()} requirement"
            print(f"  {GREEN}[PRESERVED {kind_label}]{NC} {canon} ({reason})")
            preserved += 1
            continue
        for full_p, rel_l in _candidate_flat_paths(target_dir, profiles, active_hosts, category, canon):
            pruned += _remove_target(full_p, rel_l, kind_label, dry_run, removed_parents)
    if category == "workflows" and pruned > 0 and not dry_run:
        for hid in active_hosts:
            cfg = profiles.get(hid, {}).get("dirs", {}).get("workflows")
            wf_dir = os.path.join(target_dir, str(profiles[hid]["base_dir"]), cfg["path"]) if cfg else ""
            if wf_dir and os.path.isdir(wf_dir) and not os.listdir(wf_dir):
                os.rmdir(wf_dir)
    return pruned, preserved


def _prune_skills_across_hosts(
    team_skills: Sequence[str],
    manifest: Dict[str, Any],
    asset_deps: Dict[str, Dict[str, List[str]]],
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    dry_run: bool,
    removed_parents: Set[str],
) -> Tuple[int, int]:
    """Prune or preserve skill directories across all active hosts."""
    pruned = preserved = 0
    for skill_name in team_skills:
        if skill_name in manifest["skills"]:
            deps = asset_deps["skills"].get(skill_name, [])
            reason = f"shared dependency needed by: {', '.join(deps)}" if deps else "core skill requirement"
            print(f"  {GREEN}[PRESERVED SKILL]{NC} {skill_name} ({reason})")
            preserved += 1
            continue
        rels = [
            os.path.join(str(profiles[h]["base_dir"]), profiles[h]["dirs"]["skills"]["path"], skill_name)
            for h in active_hosts if h in profiles and "skills" in profiles[h].get("dirs", {})
        ]
        if "copilot" in active_hosts:
            rels.append(os.path.join(".github", "copilot", "skills", skill_name))
        for rel in dict.fromkeys(rels):
            pruned += _remove_target(os.path.join(target_dir, rel), rel, "SKILL", dry_run, removed_parents)
    return pruned, preserved


def _resync_host_hooks(
    toolkit_root: str,
    target_dir: str,
    manifest: Dict[str, Any],
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    dry_run: bool,
) -> None:
    """Re-sync managed lifecycle hooks for Claude (.claude/settings.json) and Grok (.grok/hooks.json)."""
    active_metas = load_canonical_plugin_metas(toolkit_root, manifest["plugins"])
    if "claude" in active_hosts and "claude" in profiles:
        settings_path = os.path.join(target_dir, ".claude", "settings.json")
        if os.path.isfile(settings_path):
            ca.sync_claude_settings_hooks(target_dir, active_metas, profiles["claude"], dry_run=dry_run)
    if "grok" in active_hosts and "grok" in profiles:
        sync_grok_hooks_file(
            target_dir, active_metas, manifest["plugins"], profiles["grok"], grok_active=True, dry_run=dry_run
        )


def _prune_team_pack_dirs(
    team_clean: str,
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    dry_run: bool,
    removed_parents: Set[str],
) -> int:
    """Prune installed team pack directories (<base>/<teams_path>/<team>) across active hosts."""
    team_rels = [
        os.path.join(str(profiles[h]["base_dir"]), profiles[h]["dirs"]["teams"]["path"], team_clean)
        for h in active_hosts if h in profiles and "teams" in profiles[h].get("dirs", {})
    ]
    return sum(
        _remove_target(os.path.join(target_dir, r), r, "TEAM PACK", dry_run, removed_parents)
        for r in dict.fromkeys(team_rels)
    )


_LEGACY_PLUGIN_HOSTS = (
    ("claude", ".claude/plugins"),
    ("copilot", ".github/copilot/plugins"),
    ("cursor", ".cursor/plugins"),
)


def _prune_plugins_and_team_dirs(
    team_clean: str,
    team_plugins: Sequence[str],
    manifest: Dict[str, Any],
    asset_deps: Dict[str, Dict[str, List[str]]],
    toolkit_root: str,
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    dry_run: bool,
    removed_parents: Set[str],
) -> Tuple[int, int]:
    """Prune orphaned plugin dirs and team pack dirs across active hosts, then re-sync host hooks."""
    pruned = preserved = 0
    for pl in team_plugins:
        if pl in manifest["plugins"]:
            deps = asset_deps["plugins"].get(pl, [])
            reason = f"shared plugin needed by: {', '.join(deps)}" if deps else "core plugin requirement"
            print(f"  {GREEN}[PRESERVED PLUGIN]{NC} {pl} ({reason})")
            preserved += 1
            continue
        pl_rels = [
            os.path.join(str(profiles[h]["base_dir"]), profiles[h]["dirs"]["plugins"]["path"], pl)
            for h in active_hosts if h in profiles and "plugins" in profiles[h].get("dirs", {})
        ]
        pl_rels.extend(os.path.join(base_p, pl) for h, base_p in _LEGACY_PLUGIN_HOSTS if h in active_hosts)
        for rel in dict.fromkeys(pl_rels):
            pruned += _remove_target(os.path.join(target_dir, rel), rel, "PLUGIN", dry_run, removed_parents)
    _resync_host_hooks(toolkit_root, target_dir, manifest, profiles, active_hosts, dry_run)
    pruned += _prune_team_pack_dirs(team_clean, target_dir, profiles, active_hosts, dry_run, removed_parents)
    return pruned, preserved


def _evaluate_workspace_data(target_dir: str, team_clean: str, purge_data: bool, dry_run: bool) -> None:
    """Preserve or purge workspace team data under workforces/teams/<team> and preserve personas."""
    print(f"\n{BOLD}▸ Evaluating Workspace Layer (workforces/)...{NC}")
    ws_team_dir = os.path.join(target_dir, "workforces", "teams", team_clean)
    if os.path.exists(ws_team_dir):
        if purge_data:
            if dry_run:
                print(f"  {YELLOW}[WOULD PURGE WORKSPACE DATA]{NC} workforces/teams/{team_clean}")
            else:
                shutil.rmtree(ws_team_dir, ignore_errors=True)
                print(f"  {RED}[PURGED WORKSPACE DATA]{NC} workforces/teams/{team_clean}")
        else:
            print(f"  {GREEN}[PRESERVED WORKSPACE DATA]{NC} workforces/teams/{team_clean} (use --purge-data to remove)")
    if os.path.isdir(os.path.join(target_dir, "workforces", "personas")):
        print(f"  {GREEN}[PRESERVED WORKSPACE PERSONAS]{NC} workforces/personas/")


def _read_version_commit(target_dir: str) -> str:
    """Read commit hash from workforces/.version if present, else 'unknown'."""
    version_file = Path(target_dir) / "workforces" / ".version"
    if not version_file.is_file():
        return "unknown"
    try:
        lines = version_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "unknown"
    for line in lines:
        if line.startswith("commit:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _sync_registries(
    target_dir: str, toolkit_root: str, team_clean: str, remaining_teams: Sequence[str],
    profiles: Dict[str, Dict[str, Any]], active_hosts: Sequence[str], auto_detect: bool, dry_run: bool,
) -> None:
    """Update workrules.md, workstate.md, workforces/config.json, and workforces/.manifest.json."""
    print(f"\n{BOLD}▸ Updating Workspace Registry...{NC}")
    dry_label = "".join((YELLOW, "[WOULD UPDATE]", NC))
    live_label = "".join((GREEN, "[UPDATED]", NC))
    tag = dry_label if dry_run else live_label
    if update_workrules(target_dir, remaining_teams, dry_run=dry_run):
        print(f"  {tag} workforces/workrules.md (removed '{team_clean}' from installed_teams)")
    if update_workstate(target_dir, team_clean, dry_run=dry_run):
        print(f"  {tag} workforces/workstate.md (unregistered '{team_clean}')")
    existing_cfg = ca.load_install_config(target_dir)
    cfg_file = os.path.join(os.path.abspath(target_dir), ca.INSTALL_CONFIG_REL_PATH)
    if existing_cfg is not None or os.path.isfile(cfg_file):
        if not dry_run:
            cfg_dict = existing_cfg or {}
            auto_flag = auto_detect and bool(cfg_dict.get("auto_detect_hosts", True))
            repo_type = str(cfg_dict.get("repo_type") or ca.infer_repo_type(target_dir) or "project")
            ca.save_install_config(target_dir, active_hosts, repo_type, remaining_teams, profiles, auto_flag)
        print(f"  {tag} workforces/config.json")
    if not dry_run:
        teams_csv = ",".join(remaining_teams) if remaining_teams else "none"
        remaining_files = resolve_installed_file_paths(
            toolkit_root, target_dir, teams_arg=teams_csv, hosts=active_hosts, auto_detect=auto_detect
        )
        save_installed_manifest(
            target_dir, _read_version_commit(target_dir), remaining_teams, remaining_files, hosts=active_hosts
        )
        print(f"  {live_label} workforces/.manifest.json")


def _execute_host_pruning(
    team_clean: str,
    team_data: Dict[str, Any],
    manifest: Dict[str, Any],
    asset_deps: Dict[str, Dict[str, List[str]]],
    toolkit_root: str,
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    active_hosts: Sequence[str],
    dry_run: bool,
) -> Tuple[int, int]:
    """Execute asset pruning across all active host directories and clean empty parents."""
    pruned = preserved = 0
    removed_parents: Set[str] = set()
    for cat, label in (("agents", "AGENT"), ("rules", "RULE"), ("workflows", "WORKFLOW")):
        p_cnt, s_cnt = _prune_flat_category(
            team_data.get(cat, []), cat, label, manifest, asset_deps,
            target_dir, profiles, active_hosts, dry_run, removed_parents,
        )
        pruned, preserved = pruned + p_cnt, preserved + s_cnt
    p_cnt, s_cnt = _prune_skills_across_hosts(
        team_data.get("skills", []), manifest, asset_deps, target_dir, profiles, active_hosts, dry_run, removed_parents
    )
    pruned, preserved = pruned + p_cnt, preserved + s_cnt
    p_cnt, s_cnt = _prune_plugins_and_team_dirs(
        team_clean, team_data.get("plugins", []), manifest, asset_deps,
        toolkit_root, target_dir, profiles, active_hosts, dry_run, removed_parents,
    )
    pruned, preserved = pruned + p_cnt, preserved + s_cnt
    if not dry_run and removed_parents:
        _cleanup_empty_parent_dirs(target_dir, removed_parents)
    return pruned, preserved


def prune_team(
    team_name: str,
    target_dir: str = ".",
    toolkit_root: Optional[str] = None,
    purge_data: bool = False,
    dry_run: bool = False,
    hosts: Any = None,
    auto_detect: bool = True,
) -> bool:
    """Reference-count remaining teams and prune orphaned team assets across all active AI hosts."""
    target_dir = os.path.abspath(target_dir)
    toolkit_root = os.path.abspath(toolkit_root or target_dir)
    team_clean = (team_name or "").strip().lower()
    if not re.match(r"^[a-zA-Z0-9_-]+$", team_clean):
        print(f"{RED}Error: Invalid team identifier '{team_clean}'.{NC}")
        return False
    profiles = load_profiles_with_fallback(toolkit_root)
    active_hosts = resolve_target_hosts(toolkit_root, target_dir, hosts_arg=hosts, auto_detect=auto_detect)
    installed_teams = get_installed_teams(target_dir, toolkit_root)
    if team_clean not in installed_teams:
        print(f"{YELLOW}Warning: '{team_clean}' is not in installed_teams ({installed_teams}). Scanning anyway...{NC}")
    remaining_teams = [t for t in installed_teams if t != team_clean]
    manifest = resolve_manifest(toolkit_root, target_dir, ",".join(remaining_teams) if remaining_teams else "none")
    asset_deps = _build_asset_deps(toolkit_root, target_dir, remaining_teams)
    team_data = get_team_pack_data(toolkit_root, team_clean, target_dir=target_dir) or {}
    print(f"\n{BOLD}▸ Pruning Team '{team_clean}' Across Active Hosts ({', '.join(active_hosts)})...{NC}")
    pruned, preserved = _execute_host_pruning(
        team_clean, team_data, manifest, asset_deps, toolkit_root, target_dir, profiles, active_hosts, dry_run
    )
    _evaluate_workspace_data(target_dir, team_clean, purge_data, dry_run)
    _sync_registries(target_dir, toolkit_root, team_clean, remaining_teams, profiles, active_hosts, auto_detect, dry_run)
    rem_str = ", ".join(remaining_teams) or "core only"
    print(f"\n  {BOLD}Summary:{NC} Pruned {RED}{pruned}{NC} | Preserved {GREEN}{preserved}{NC} | Remaining: {CYAN}{rem_str}{NC}\n")
    return True


def main() -> None:
    """CLI entry point for multi-host team pruning."""
    parser = argparse.ArgumentParser(description="Prune uninstalled team assets across all active AI hosts")
    parser.add_argument("team", nargs="?", default=None, help="Name of team to uninstall (e.g. sales, marketing, dev)")
    parser.add_argument("--team", dest="team_opt", default=None, help="Name of team to uninstall")
    parser.add_argument("--target", default=".", help="Root of target project (default: current directory)")
    parser.add_argument("--toolkit-root", default=None, help="Root of source workforces toolkit")
    parser.add_argument("--hosts", "--editor", dest="hosts", default=None, help="Hosts: auto, all, or comma-separated list")
    parser.add_argument("--no-auto-detect", action="store_true", help="Disable workspace host directory auto-detection")
    parser.add_argument("--purge-data", action="store_true", help="Purge workspace custom team data in workforces/teams/<team>/")
    parser.add_argument("--dry", "--dry-run", action="store_true", help="Show what would be pruned without deleting files")
    parser.add_argument("--non-interactive", action="store_true", help="Run non-interactively")
    args = parser.parse_args()
    team_name = args.team_opt or args.team
    if not team_name:
        parser.error("A team name is required (e.g. 'prune_team.py marketing' or '--team marketing').")
    try:
        ok = prune_team(
            team_name=team_name,
            target_dir=args.target,
            toolkit_root=args.toolkit_root,
            purge_data=args.purge_data,
            dry_run=args.dry,
            hosts=args.hosts,
            auto_detect=not args.no_auto_detect,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

