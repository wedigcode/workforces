#!/usr/bin/env python3
"""
Workforces Team Pruner & Uninstaller
Safely removes team assets (agents, skills, rules, workflows, plugins) from the active
editor layer (.agents/) to eliminate prompt/context bloat, while programmatically
preserving shared dependencies across remaining installed teams and keeping workspace
personas and historical context in workforces/ intact.
"""

import os
import sys
import shutil
import re
import argparse
from resolve_manifest import (
    resolve_manifest,
    resolve_installed_file_paths,
    load_installed_manifest,
    save_installed_manifest,
    get_installed_teams,
    get_team_pack_data,
    find_teams_dir,
    CORE_AGENTS,
    CORE_RULES,
    CORE_SKILLS,
    CORE_WORKFLOWS,
    CORE_PLUGINS
)

# Terminal styling
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

def detect_base_dir(target_dir):
    """Detects the editor configuration directory in the target project."""
    target_dir = os.path.abspath(target_dir)
    if os.path.isdir(os.path.join(target_dir, ".agents")):
        return ".agents"
    if os.path.isdir(os.path.join(target_dir, ".github", "copilot")):
        return os.path.join(".github", "copilot")
    if os.path.isdir(os.path.join(target_dir, ".claude")):
        return ".claude"
    if os.path.isdir(os.path.join(target_dir, ".grok")):
        return ".grok"
    return ".agents"

def update_workrules(target_dir, remaining_teams, dry_run=False):
    """Updates installed_teams in workforces/workrules.md."""
    workrules_path = os.path.join(target_dir, "workforces", "workrules.md")
    if not os.path.exists(workrules_path):
        return False

    with open(workrules_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    new_teams_yaml = "\n".join([f"  - {t}" for t in remaining_teams]) if remaining_teams else "  []"
    
    # Replace block if exists
    if re.search(r'## Installed Teams\s*\n(?:\s*-\s*[^\n]+\n?)+', content):
        new_block = f"## Installed Teams\n- installed_teams:\n{new_teams_yaml}\n"
        updated_content = re.sub(
            r'## Installed Teams\s*\n(?:\s*-\s*[^\n]+\n?)+',
            new_block,
            content
        )
    elif re.search(r'installed_teams:\s*\[?.*?\]?(\n|$)', content):
        new_line = f"installed_teams: [{', '.join(remaining_teams)}]\n"
        updated_content = re.sub(r'installed_teams:\s*\[?.*?\]?(\n|$)', new_line, content)
    else:
        updated_content = content

    if updated_content != content:
        if not dry_run:
            with open(workrules_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
        return True
    return False

def update_workstate(target_dir, team_name, dry_run=False):
    """Removes team entries from active tables or lists in workforces/workstate.md."""
    workstate_path = os.path.join(target_dir, "workforces", "workstate.md")
    if not os.path.exists(workstate_path):
        return False

    with open(workstate_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    updated_lines = []
    modified = False
    for line in lines:
        if team_name in line and ("Active Teams" in "".join(lines) or "|" in line):
            # Check if this line is a table row or bullet for this team
            if line.strip().startswith("|") and f"| {team_name} " in line:
                modified = True
                continue
            if line.strip().startswith("-") and f"{team_name}" in line:
                modified = True
                continue
        updated_lines.append(line)

    if modified:
        if not dry_run:
            with open(workstate_path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
        return True
    return False

def prune_team(team_name, target_dir=".", toolkit_root=None, purge_data=False, dry_run=False):
    """
    Main pruning routine. Computes dynamic reference counts across remaining
    teams, removes orphaned assets from active editor layer, and preserves workspace data.
    """
    target_dir = os.path.abspath(target_dir)
    if not toolkit_root:
        # Default toolkit root to target_dir or parent if in workforces repo
        toolkit_root = target_dir

    toolkit_root = os.path.abspath(toolkit_root)
    base_dir_rel = detect_base_dir(target_dir)
    base_dir = os.path.join(target_dir, base_dir_rel)

    team_clean = team_name.strip().lower()
    if not re.match(r'^[a-zA-Z0-9_-]+$', team_clean):
        print(f"{RED}Error: Invalid team identifier '{team_clean}'. Only alphanumeric characters, hyphens, and underscores are allowed.{NC}")
        return False

    installed_teams = get_installed_teams(target_dir, toolkit_root)

    print("")
    print(f"{BOLD}{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"  {BOLD}Workforces Team Pruner & Uninstaller{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"  Target:    {CYAN}{target_dir}{NC}")
    print(f"  Layer:     {CYAN}{base_dir_rel}/{NC}")
    print(f"  Team:      {YELLOW}{team_clean}{NC}")
    print(f"  Purge Data:{RED if purge_data else GREEN} {purge_data}{NC}")
    if dry_run:
        print(f"  {YELLOW}Mode: DRY RUN — no files will be deleted{NC}")
    print("")

    if team_clean not in installed_teams:
        print(f"{YELLOW}Warning: Team '{team_clean}' is not currently in installed_teams ({', '.join(installed_teams) or 'none'}).{NC}")
        print("Checking if any orphaned pack definitions exist...")

    # Compute remaining teams
    remaining_teams = [t for t in installed_teams if t != team_clean]

    # Resolve allowed/required manifest for remaining teams
    manifest = resolve_manifest(
        toolkit_root=toolkit_root,
        target_dir=target_dir,
        teams_arg=','.join(remaining_teams) if remaining_teams else 'none'
    )

    # Build dependency map of which remaining teams require which assets
    asset_deps = {
        'agents': {},
        'skills': {},
        'rules': {},
        'workflows': {},
        'plugins': {}
    }

    for rt in remaining_teams:
        rt_data = get_team_pack_data(toolkit_root, rt)
        if not rt_data:
            continue
        for a in rt_data.get('agents', []):
            a_norm = a if a.endswith('.md') else f'{a}.md'
            asset_deps['agents'].setdefault(a_norm, []).append(rt)
        for s in rt_data.get('skills', []):
            asset_deps['skills'].setdefault(s, []).append(rt)
        for r in rt_data.get('rules', []):
            r_norm = r if r.endswith('.md') else f'{r}.md'
            asset_deps['rules'].setdefault(r_norm, []).append(rt)
        for w in rt_data.get('workflows', []):
            w_norm = w if w.endswith('.md') else f'{w}.md'
            asset_deps['workflows'].setdefault(w_norm, []).append(rt)
        for pl in rt_data.get('plugins', []):
            asset_deps['plugins'].setdefault(pl, []).append(rt)

    # Load target team data
    target_team_data = get_team_pack_data(toolkit_root, team_clean) or {}
    
    pruned_count = 0
    preserved_count = 0

    print(f"{BOLD}▸ Evaluating Toolkit Layer Assets ({base_dir_rel}/)...{NC}")

    # 1. Agents in toolkit layer
    team_agents = target_team_data.get('agents', [])
    for a in team_agents:
        a_file = a if a.endswith('.md') else f'{a}.md'
        target_path = os.path.join(base_dir, 'agents', a_file)
        if a_file in manifest['agents']:
            deps = asset_deps['agents'].get(a_file, [])
            dep_str = f"needed by: {', '.join(deps)}" if deps else "core agent requirement"
            print(f"  {GREEN}[PRESERVED AGENT]{NC} {base_dir_rel}/agents/{a_file} ({dep_str})")
            preserved_count += 1
        else:
            if os.path.exists(target_path):
                if dry_run:
                    print(f"  {YELLOW}[WOULD PRUNE AGENT]{NC} {base_dir_rel}/agents/{a_file}")
                else:
                    os.remove(target_path)
                    print(f"  {RED}[PRUNED AGENT]{NC} {base_dir_rel}/agents/{a_file}")
                pruned_count += 1

    # 2. Skills
    team_skills = target_team_data.get('skills', [])
    for s in team_skills:
        target_skill_dir = os.path.join(base_dir, 'skills', s)
        if s in manifest['skills']:
            deps = asset_deps['skills'].get(s, [])
            dep_str = f"shared dependency needed by: {', '.join(deps)}" if deps else "core skill requirement"
            print(f"  {GREEN}[PRESERVED SKILL]{NC} {base_dir_rel}/skills/{s} ({dep_str})")
            preserved_count += 1
        else:
            if os.path.exists(target_skill_dir):
                if dry_run:
                    print(f"  {YELLOW}[WOULD PRUNE SKILL]{NC} {base_dir_rel}/skills/{s}")
                else:
                    shutil.rmtree(target_skill_dir, ignore_errors=True)
                    print(f"  {RED}[PRUNED SKILL]{NC} {base_dir_rel}/skills/{s}")
                pruned_count += 1

    # 3. Rules
    team_rules = target_team_data.get('rules', [])
    for r in team_rules:
        r_file = r if r.endswith('.md') else f'{r}.md'
        target_rule_path = os.path.join(base_dir, 'rules', r_file)
        if r_file in manifest['rules']:
            deps = asset_deps['rules'].get(r_file, [])
            dep_str = f"shared rule needed by: {', '.join(deps)}" if deps else "core rule requirement"
            print(f"  {GREEN}[PRESERVED RULE]{NC} {base_dir_rel}/rules/{r_file} ({dep_str})")
            preserved_count += 1
        else:
            if os.path.exists(target_rule_path):
                if dry_run:
                    print(f"  {YELLOW}[WOULD PRUNE RULE]{NC} {base_dir_rel}/rules/{r_file}")
                else:
                    os.remove(target_rule_path)
                    print(f"  {RED}[PRUNED RULE]{NC} {base_dir_rel}/rules/{r_file}")
                pruned_count += 1

    # 4. Workflows
    wf_folder = "commands" if base_dir_rel == ".grok" else "workflows"
    team_workflows = target_team_data.get('workflows', [])
    for w in team_workflows:
        w_file = w if w.endswith('.md') else f'{w}.md'
        target_wf_path = os.path.join(base_dir, wf_folder, w_file)
        if w_file in manifest['workflows']:
            deps = asset_deps['workflows'].get(w_file, [])
            dep_str = f"shared workflow needed by: {', '.join(deps)}" if deps else "core workflow requirement"
            print(f"  {GREEN}[PRESERVED WORKFLOW]{NC} {base_dir_rel}/{wf_folder}/{w_file} ({dep_str})")
            preserved_count += 1
        else:
            if os.path.exists(target_wf_path):
                if dry_run:
                    print(f"  {YELLOW}[WOULD PRUNE WORKFLOW]{NC} {base_dir_rel}/{wf_folder}/{w_file}")
                else:
                    os.remove(target_wf_path)
                    print(f"  {RED}[PRUNED WORKFLOW]{NC} {base_dir_rel}/{wf_folder}/{w_file}")
                pruned_count += 1

    # Clean empty workflows directory if no workflows remain
    if not dry_run:
        wf_dir_full = os.path.join(base_dir, wf_folder)
        if os.path.isdir(wf_dir_full):
            try:
                if not os.listdir(wf_dir_full):
                    os.rmdir(wf_dir_full)
            except Exception:
                pass

    # 5. Plugins
    team_plugins = target_team_data.get('plugins', [])
    for pl in team_plugins:
        target_plugin_dir = os.path.join(base_dir, 'plugins', pl)
        if pl in manifest['plugins']:
            deps = asset_deps['plugins'].get(pl, [])
            dep_str = f"shared plugin needed by: {', '.join(deps)}" if deps else "core plugin requirement"
            print(f"  {GREEN}[PRESERVED PLUGIN]{NC} {base_dir_rel}/plugins/{pl} ({dep_str})")
            preserved_count += 1
        else:
            if os.path.exists(target_plugin_dir):
                if dry_run:
                    print(f"  {YELLOW}[WOULD PRUNE PLUGIN]{NC} {base_dir_rel}/plugins/{pl}")
                else:
                    shutil.rmtree(target_plugin_dir, ignore_errors=True)
                    print(f"  {RED}[PRUNED PLUGIN]{NC} {base_dir_rel}/plugins/{pl}")
                pruned_count += 1

    # 6. Team Pack building block
    toolkit_team_dir = os.path.join(base_dir, 'teams', team_clean)
    if os.path.exists(toolkit_team_dir):
        if dry_run:
            print(f"  {YELLOW}[WOULD PRUNE TEAM PACK]{NC} {base_dir_rel}/teams/{team_clean}")
        else:
            shutil.rmtree(toolkit_team_dir, ignore_errors=True)
            print(f"  {RED}[PRUNED TEAM PACK]{NC} {base_dir_rel}/teams/{team_clean}")
        pruned_count += 1

    # ─── Workspace Layer Evaluation (workforces/) ───
    print("")
    print(f"{BOLD}▸ Evaluating Workspace Layer (workforces/)...{NC}")
    
    ws_team_dir = os.path.join(target_dir, "workforces", "teams", team_clean)
    if os.path.exists(ws_team_dir):
        if purge_data:
            if dry_run:
                print(f"  {YELLOW}[WOULD PURGE WORKSPACE DATA]{NC} workforces/teams/{team_clean}")
            else:
                shutil.rmtree(ws_team_dir, ignore_errors=True)
                print(f"  {RED}[PURGED WORKSPACE DATA]{NC} workforces/teams/{team_clean}")
        else:
            print(f"  {GREEN}[PRESERVED WORKSPACE DATA]{NC} workforces/teams/{team_clean} (configs and custom personas preserved; use --purge-data to remove)")

    personas_dir = os.path.join(target_dir, "workforces", "personas")
    if os.path.isdir(personas_dir):
        print(f"  {GREEN}[PRESERVED WORKSPACE PERSONAS]{NC} workforces/personas/ (author/audience voice profiles preserved)")

    # ─── Registry Updates ───
    print("")
    print(f"{BOLD}▸ Updating Workspace Registry...{NC}")
    
    workrules_updated = update_workrules(target_dir, remaining_teams, dry_run=dry_run)
    if workrules_updated:
        if dry_run:
            print(f"  {YELLOW}[WOULD UPDATE]{NC} workforces/workrules.md (removed '{team_clean}' from installed_teams)")
        else:
            print(f"  {GREEN}[UPDATED]{NC} workforces/workrules.md (removed '{team_clean}' from installed_teams)")

    workstate_updated = update_workstate(target_dir, team_clean, dry_run=dry_run)
    if workstate_updated:
        if dry_run:
            print(f"  {YELLOW}[WOULD UPDATE]{NC} workforces/workstate.md (unregistered '{team_clean}')")
        else:
            print(f"  {GREEN}[UPDATED]{NC} workforces/workstate.md (unregistered '{team_clean}')")

    # Update workforces/.manifest.json
    if not dry_run:
        version_hash = "unknown"
        version_file = os.path.join(target_dir, "workforces", ".version")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as vf:
                    for l in vf:
                        if l.startswith("commit:"):
                            version_hash = l.split(":", 1)[1].strip()
            except Exception:
                pass
        remaining_files = resolve_installed_file_paths(
            toolkit_root=toolkit_root,
            target_dir=target_dir,
            base_dir=base_dir_rel,
            teams_arg=','.join(remaining_teams) if remaining_teams else 'none'
        )
        save_installed_manifest(
            target_dir=target_dir,
            version=version_hash,
            installed_teams=remaining_teams,
            installed_files=remaining_files
        )
        print(f"  {GREEN}[UPDATED]{NC} workforces/.manifest.json")

    print("")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"  {BOLD}Prune Summary:{NC}")
    print(f"  Pruned:    {RED}{pruned_count}{NC} runtime assets from {base_dir_rel}/")
    print(f"  Preserved: {GREEN}{preserved_count}{NC} shared/core dependencies")
    print(f"  Remaining: {CYAN}{', '.join(remaining_teams) or 'core only'}{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print("")
    return True

def main():
    parser = argparse.ArgumentParser(description="Prune uninstalled team assets and eliminate prompt bloat while preserving shared dependencies and workspace context")
    parser.add_argument("team", nargs="?", default=None, help="Name of team to uninstall (e.g. sales, marketing, growth)")
    parser.add_argument("--team", dest="team_opt", default=None, help="Name of team to uninstall")
    parser.add_argument("--target", default=".", help="Root of target project (default: current directory)")
    parser.add_argument("--toolkit-root", default=None, help="Root of source workforces toolkit")
    parser.add_argument("--purge-data", action="store_true", help="Purge workspace custom team data and artifacts in workforces/teams/<team>/")
    parser.add_argument("--dry", "--dry-run", action="store_true", help="Show what would be pruned without deleting files")
    parser.add_argument("--non-interactive", action="store_true", help="Run non-interactively")

    args = parser.parse_args()
    team_name = args.team_opt or args.team
    if not team_name:
        parser.error("A team name is required (e.g. 'prune_team.py marketing' or '--team marketing').")

    prune_team(
        team_name=team_name,
        target_dir=args.target,
        toolkit_root=args.toolkit_root,
        purge_data=args.purge_data,
        dry_run=args.dry
    )

if __name__ == "__main__":
    main()
