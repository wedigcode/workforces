#!/usr/bin/env python3
"""
Workforces Manifest Resolver
Resolves the exact set of agents, rules, skills, workflows, and plugins to copy
based on core requirements and installed domain teams.
"""

import os
import sys
import json
import glob
import re
import argparse

def resolve_manifest(toolkit_root, target_dir, teams_arg=None):
    toolkit_root = os.path.abspath(toolkit_root)
    target_dir = os.path.abspath(target_dir)

    # Core assets (Always included for every workforce / project)
    core_agents = {'advisor.md', 'project-manager.md', 'scribe.md'}
    core_rules = {'base.md', 'mcp-protection.md', 'session-context.md'}
    core_skills = {'workforce-management', 'memory-management', 'issue-tracker', 'session-context', 'usage-tracker'}
    core_workflows = {'work.md', 'plan.md', 'sync.md', 'task.md', 'advisor.md', 'teams.md', 'question-formulation.md', 'update-workforces.md', 'verify-integrity.md'}
    core_plugins = {'workforce-usage-plugin'}

    # Determine available upstream teams
    teams_dir = os.path.join(toolkit_root, 'teams')
    if not os.path.isdir(teams_dir):
        # Fallback to .agents/teams if inside target repo
        alt_teams = os.path.join(toolkit_root, '.agents', 'teams')
        if os.path.isdir(alt_teams):
            teams_dir = alt_teams

    all_team_dirs = [os.path.basename(d) for d in glob.glob(os.path.join(teams_dir, '*')) if os.path.isdir(d) and os.path.exists(os.path.join(d, 'pack.json')) or os.path.exists(os.path.join(d, 'pack.md'))]

    installed_teams = []
    if teams_arg:
        teams_clean = teams_arg.strip().lower()
        if teams_clean in ('all', '*'):
            installed_teams = all_team_dirs
        elif teams_clean in ('none', 'core'):
            installed_teams = []
        else:
            for t in teams_arg.split(','):
                t = t.strip().lower()
                if t in all_team_dirs:
                    installed_teams.append(t)
    else:
        # Check target workrules.md for installed_teams
        workrules_path = os.path.join(target_dir, 'workforces', 'workrules.md')
        if os.path.exists(workrules_path):
            with open(workrules_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                m = re.search(r'installed_teams:\s*\[?(.*?)\]?(\n|$)', content)
                if m and m.group(1).strip():
                    raw = m.group(1).strip()
                    for t in raw.split(','):
                        t = t.strip().strip('\'\"- ')
                        if t in all_team_dirs:
                            installed_teams.append(t)
        
        # Fallback: check existing team folders in target workspace
        if not installed_teams:
            target_teams_dir = os.path.join(target_dir, 'workforces', 'teams')
            if os.path.isdir(target_teams_dir):
                installed_teams = [os.path.basename(d) for d in glob.glob(os.path.join(target_teams_dir, '*')) if os.path.isdir(d) and os.path.basename(d) in all_team_dirs]
        
        # Default baseline if still empty
        if not installed_teams:
            installed_teams = [t for t in ['dev', 'design'] if t in all_team_dirs]

    installed_teams = sorted(list(set(installed_teams)))

    for t in installed_teams:
        pack_json = os.path.join(teams_dir, t, 'pack.json')
        if os.path.exists(pack_json):
            try:
                with open(pack_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for a in data.get('agents', []):
                        core_agents.add(a if a.endswith('.md') else f'{a}.md')
                    for r in data.get('rules', []):
                        core_rules.add(r if r.endswith('.md') else f'{r}.md')
                    for s in data.get('skills', []):
                        core_skills.add(s)
                    for w in data.get('workflows', []):
                        core_workflows.add(w if w.endswith('.md') else f'{w}.md')
                    for pl in data.get('plugins', []):
                        core_plugins.add(pl)
            except Exception:
                pass

    return {
        'installed_teams': installed_teams,
        'agents': sorted(list(core_agents)),
        'rules': sorted(list(core_rules)),
        'skills': sorted(list(core_skills)),
        'workflows': sorted(list(core_workflows)),
        'plugins': sorted(list(core_plugins)),
        'teams': installed_teams
    }

def main():
    parser = argparse.ArgumentParser(description="Resolve workforce asset manifest by installed teams")
    parser.add_argument("--toolkit-root", default=".", help="Root of source workforces toolkit")
    parser.add_argument("--target", default=".", help="Root of target project")
    parser.add_argument("--teams", default=None, help="Comma-separated teams (or 'all')")
    parser.add_argument("--format", choices=["json", "bash-export"], default="json", help="Output format")

    args = parser.parse_args()
    manifest = resolve_manifest(args.toolkit_root, args.target, args.teams)

    if args.format == "json":
        print(json.dumps(manifest, indent=2))
    elif args.format == "bash-export":
        print(f"INSTALLED_TEAMS_LIST=\"{' '.join(manifest['installed_teams'])}\"")
        print(f"ALLOWED_AGENTS=\"{' '.join(manifest['agents'])}\"")
        print(f"ALLOWED_RULES=\"{' '.join(manifest['rules'])}\"")
        print(f"ALLOWED_SKILLS=\"{' '.join(manifest['skills'])}\"")
        print(f"ALLOWED_WORKFLOWS=\"{' '.join(manifest['workflows'])}\"")
        print(f"ALLOWED_PLUGINS=\"{' '.join(manifest['plugins'])}\"")
        print(f"ALLOWED_TEAMS=\"{' '.join(manifest['teams'])}\"")

if __name__ == "__main__":
    main()
