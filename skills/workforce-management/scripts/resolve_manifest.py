#!/usr/bin/env python3
"""
Workforces Manifest Resolver
Resolves the exact set of agents, rules, skills, workflows, and plugins to copy
or preserve based on core requirements and installed domain teams.
"""

import os
import sys
import json
import glob
import re
import argparse

CORE_AGENTS = {'advisor.md', 'project-manager.md', 'scribe.md'}
CORE_RULES = {'base.md', 'mcp-protection.md', 'session-context.md'}
CORE_SKILLS = {'workforce-management', 'memory-management', 'issue-tracker', 'session-context', 'usage-tracker'}
CORE_WORKFLOWS = {'work.md', 'plan.md', 'sync.md', 'task.md', 'advisor.md', 'ideate.md', 'teams.md', 'question-formulation.md', 'update-workforces.md', 'verify-integrity.md'}
CORE_PLUGINS = {'workforce-usage-plugin'}

def find_teams_dir(toolkit_root):
    """Finds the directory containing team pack building blocks."""
    toolkit_root = os.path.abspath(toolkit_root)
    teams_dir = os.path.join(toolkit_root, 'teams')
    if not os.path.isdir(teams_dir):
        alt_teams = os.path.join(toolkit_root, '.agents', 'teams')
        if os.path.isdir(alt_teams):
            teams_dir = alt_teams
    return teams_dir

def get_available_teams(toolkit_root):
    """Returns a list of all available team names in the toolkit."""
    teams_dir = find_teams_dir(toolkit_root)
    if not os.path.isdir(teams_dir):
        return []
    return sorted([
        os.path.basename(d) for d in glob.glob(os.path.join(teams_dir, '*'))
        if os.path.isdir(d) and (os.path.exists(os.path.join(d, 'pack.json')) or os.path.exists(os.path.join(d, 'pack.md')))
    ])

def get_installed_teams(target_dir, toolkit_root=None):
    """Parses workforces/workrules.md or workspace team folders to discover installed teams."""
    target_dir = os.path.abspath(target_dir)
    available_teams = get_available_teams(toolkit_root or target_dir)
    installed_teams = []

    workrules_path = os.path.join(target_dir, 'workforces', 'workrules.md')
    if os.path.exists(workrules_path):
        try:
            with open(workrules_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for bulleted list under ## Installed Teams
                m_block = re.search(r'## Installed Teams\s*\n((?:\s*-\s*[^\n]+\n?)+)', content)
                if m_block:
                    for line in m_block.group(1).splitlines():
                        line = line.strip()
                        if line.startswith('-'):
                            val = line.lstrip('- ').strip().strip('\'\"')
                            if val.startswith('installed_teams:'):
                                val = val.replace('installed_teams:', '').strip().strip('[]\'\"')
                                if val:
                                    for t in val.split(','):
                                        t = t.strip().strip('\'\"')
                                        if t and (not available_teams or t in available_teams):
                                            installed_teams.append(t)
                            elif val and val != '[]' and (not available_teams or val in available_teams):
                                installed_teams.append(val)
                
                # Fallback check inline installed_teams: [...]
                if not installed_teams:
                    m = re.search(r'installed_teams:\s*\[?(.*?)\]?(\n|$)', content)
                    if m and m.group(1).strip():
                        raw = m.group(1).strip()
                        for t in raw.split(','):
                            t = t.strip().strip('\'\"- ')
                            if t and (not available_teams or t in available_teams):
                                installed_teams.append(t)
        except Exception:
            pass

    if not installed_teams:
        target_teams_dir = os.path.join(target_dir, 'workforces', 'teams')
        if os.path.isdir(target_teams_dir):
            installed_teams = [
                os.path.basename(d) for d in glob.glob(os.path.join(target_teams_dir, '*'))
                if os.path.isdir(d) and (not available_teams or os.path.basename(d) in available_teams)
            ]

    return sorted(list(set(installed_teams)))

def get_team_pack_data(toolkit_root, team_name):
    """Loads pack.json or team.json metadata for a specific team."""
    teams_dir = find_teams_dir(toolkit_root)
    pack_json = os.path.join(teams_dir, team_name, 'pack.json')
    if not os.path.exists(pack_json):
        # Check custom workspace team manifest
        alt_json = os.path.join(toolkit_root, 'workforces', 'teams', team_name, 'team.json')
        if os.path.exists(alt_json):
            pack_json = alt_json
        else:
            return None

    try:
        with open(pack_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def resolve_manifest(toolkit_root, target_dir, teams_arg=None):
    """Resolves all required agents, rules, skills, workflows, and plugins."""
    toolkit_root = os.path.abspath(toolkit_root)
    target_dir = os.path.abspath(target_dir)

    core_agents = set(CORE_AGENTS)
    core_rules = set(CORE_RULES)
    core_skills = set(CORE_SKILLS)
    core_workflows = set(CORE_WORKFLOWS)
    core_plugins = set(CORE_PLUGINS)

    all_team_dirs = get_available_teams(toolkit_root)

    installed_teams = []
    if teams_arg is not None:
        teams_clean = str(teams_arg).strip().lower()
        if teams_clean in ('all', '*'):
            installed_teams = all_team_dirs
        elif teams_clean in ('none', 'core', ''):
            installed_teams = []
        else:
            for t in str(teams_arg).split(','):
                t = t.strip().lower()
                if t in all_team_dirs or not all_team_dirs:
                    installed_teams.append(t)
    else:
        installed_teams = get_installed_teams(target_dir, toolkit_root)
        if not installed_teams:
            installed_teams = [t for t in ['dev', 'design'] if t in all_team_dirs]

    installed_teams = sorted(list(set(installed_teams)))

    for t in installed_teams:
        data = get_team_pack_data(toolkit_root, t)
        if data:
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
