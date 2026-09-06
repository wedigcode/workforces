#!/usr/bin/env python3
"""
Workforces Manifest Resolver & File Tracker
Resolves the exact set of agents, rules, skills, workflows, and plugins to copy
or preserve based on core requirements and installed domain teams, tracks installed
files in workforces/.manifest.json, and safely prunes obsolete toolkit assets during updates.
"""

import os
import sys
import json
import glob
import re
import argparse
import datetime

CORE_AGENTS = {'project-manager.md', 'scribe.md'}
CORE_RULES = {'base.md', 'mcp-protection.md', 'session-context.md', 'file-integrity.md', 'git-workflow.md'}
CORE_SKILLS = {
    'workforce-management', 'memory-management', 'task-tracker', 'issue-tracker',
    'session-context', 'usage-tracker', 'integrity-validator', 'workforce-canvas',
    'github-project-planning', 'hypothesis-tracker',
    'wf-plan', 'wf-sync', 'wf-advisor', 'wf-ideate', 'wf-investigate',
    'wf-question-formulation'
}
CORE_WORKFLOWS = set()
CORE_PLUGINS = {'workforce-usage-plugin', 'workforce-integrity-plugin'}

MANIFEST_REL_PATH = os.path.join("workforces", ".manifest.json")

LEGACY_OBSOLETE_SUBPATHS = [
    "agents/compliance.md",
    "agents/advisor.md",
    "skills/wf-work/SKILL.md",
    "agents/clean-coder.md",
    "agents/design-pilot.md",
    "agents/design-reviewer.md",
    "agents/feature-researcher.md",
    "agents/integrity-auditor.md",
    "agents/social-engager.md",
    "plugins/workforce-integrity-plugin/rules/file-integrity.md",
    "plugins/workforce-integrity-plugin/skills/integrity-validator/SKILL.md",
    "plugins/workforce-programming-plugin/rules/clean-coder.md",
    "plugins/workforce-social-plugin/rules/social-engagement.md",
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
    "commands/wf-task.md",
    "commands/wf-teams.md",
    "commands/wf-update.md",
    "commands/wf-validate-idea.md",
    "commands/wf-verify-integrity.md",
    "commands/wf-work.md",
    "commands/wf-update-workforces.md",
    "workflows/wf-update-workforces.md",
    "workflows/workforces/tasks/20260822-073809-ideate-and-unbundle-atomic-saas-extractor.md",
    "workflows/workforces/tasks/20260822-073809-market-disruption-scout-disruptor-agent.md",
]

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

def resolve_installed_file_paths(toolkit_root, target_dir, base_dir=None, teams_arg=None):
    """
    Resolves the complete list of relative file paths installed/managed by workforces
    under the editor base directory (e.g. .agents/agents/project-manager.md, .agents/skills/clean-coder/SKILL.md).
    """
    toolkit_root = os.path.abspath(toolkit_root)
    target_dir = os.path.abspath(target_dir)
    if not base_dir:
        base_dir = detect_base_dir(target_dir)

    manifest = resolve_manifest(toolkit_root, target_dir, teams_arg)
    installed_files = []

    # 1. Agents
    agents_src = os.path.join(toolkit_root, 'agents')
    if not os.path.isdir(agents_src):
        alt_agents = os.path.join(toolkit_root, '.agents', 'agents')
        if os.path.isdir(alt_agents):
            agents_src = alt_agents
    if os.path.isdir(agents_src):
        for a in manifest.get('agents', []):
            if os.path.exists(os.path.join(agents_src, a)):
                installed_files.append(os.path.normpath(os.path.join(base_dir, 'agents', a)))

    # 2. Workflows
    workflows_src = os.path.join(toolkit_root, 'workflows')
    if not os.path.isdir(workflows_src):
        alt_wf = os.path.join(toolkit_root, '.agents', 'workflows')
        if os.path.isdir(alt_wf):
            workflows_src = alt_wf
    if os.path.isdir(workflows_src):
        wf_folder = "commands" if base_dir.endswith(".grok") else "workflows"
        for w in manifest.get('workflows', []):
            if os.path.exists(os.path.join(workflows_src, w)):
                installed_files.append(os.path.normpath(os.path.join(base_dir, wf_folder, w)))

    # 3. Rules
    rules_src = os.path.join(toolkit_root, 'rules')
    if not os.path.isdir(rules_src):
        alt_rules = os.path.join(toolkit_root, '.agents', 'rules')
        if os.path.isdir(alt_rules):
            rules_src = alt_rules
    if os.path.isdir(rules_src):
        for r in manifest.get('rules', []):
            if os.path.exists(os.path.join(rules_src, r)):
                installed_files.append(os.path.normpath(os.path.join(base_dir, 'rules', r)))

    # 4. Skills
    skills_src = os.path.join(toolkit_root, 'skills')
    if not os.path.isdir(skills_src):
        alt_skills = os.path.join(toolkit_root, '.agents', 'skills')
        if os.path.isdir(alt_skills):
            skills_src = alt_skills
    if os.path.isdir(skills_src):
        for s in manifest.get('skills', []):
            s_dir = os.path.join(skills_src, s)
            if os.path.isdir(s_dir):
                for root, _, filenames in os.walk(s_dir):
                    if '__pycache__' in root:
                        continue
                    for fn in filenames:
                        if fn.endswith('.pyc') or fn == '.DS_Store':
                            continue
                        full_src = os.path.join(root, fn)
                        rel = os.path.relpath(full_src, skills_src)
                        installed_files.append(os.path.normpath(os.path.join(base_dir, 'skills', rel)))

    # 5. Plugins
    plugins_src = os.path.join(toolkit_root, 'plugins')
    if not os.path.isdir(plugins_src):
        alt_plugins = os.path.join(toolkit_root, '.agents', 'plugins')
        if os.path.isdir(alt_plugins):
            plugins_src = alt_plugins
    if os.path.isdir(plugins_src):
        for pl in manifest.get('plugins', []):
            pl_dir = os.path.join(plugins_src, pl)
            if os.path.isdir(pl_dir):
                for root, _, filenames in os.walk(pl_dir):
                    if '__pycache__' in root:
                        continue
                    for fn in filenames:
                        if fn.endswith('.pyc') or fn == '.DS_Store':
                            continue
                        full_src = os.path.join(root, fn)
                        rel = os.path.relpath(full_src, plugins_src)
                        installed_files.append(os.path.normpath(os.path.join(base_dir, 'plugins', rel)))

    # 6. Teams building blocks
    teams_src = find_teams_dir(toolkit_root)
    if os.path.isdir(teams_src):
        for t in manifest.get('teams', []):
            t_dir = os.path.join(teams_src, t)
            if os.path.isdir(t_dir):
                for root, _, filenames in os.walk(t_dir):
                    if '__pycache__' in root:
                        continue
                    for fn in filenames:
                        if fn.endswith('.pyc') or fn == '.DS_Store':
                            continue
                        full_src = os.path.join(root, fn)
                        rel = os.path.relpath(full_src, teams_src)
                        installed_files.append(os.path.normpath(os.path.join(base_dir, 'teams', rel)))

    # 7. Optional root hooks configuration (only if source provides it)
    hooks_src = os.path.join(toolkit_root, 'hooks.json')
    if not os.path.isfile(hooks_src):
        alt_hooks = os.path.join(toolkit_root, '.agents', 'hooks.json')
        if os.path.isfile(alt_hooks):
            hooks_src = alt_hooks
    if os.path.isfile(hooks_src):
        installed_files.append(os.path.normpath(os.path.join(base_dir, 'hooks.json')))

    return sorted(list(set(installed_files)))

def load_installed_manifest(target_dir):
    """Loads workforces/.manifest.json if it exists."""
    manifest_path = os.path.join(target_dir, MANIFEST_REL_PATH)
    if not os.path.exists(manifest_path):
        return None
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def save_installed_manifest(target_dir, version, installed_teams, installed_files):
    """Saves workforces/.manifest.json with version, installed teams, and file paths."""
    target_dir = os.path.abspath(target_dir)
    manifest_path = os.path.join(target_dir, MANIFEST_REL_PATH)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    data = {
        "version": version or "unknown",
        "installed_teams": sorted(list(set(installed_teams or []))),
        "installed_files": sorted(list(set(installed_files or []))),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return manifest_path

def get_known_legacy_obsolete_files(base_dir):
    """Returns list of relative paths under base_dir of known historical Workforces files that were relocated or deleted."""
    return [os.path.normpath(os.path.join(base_dir, p)) for p in LEGACY_OBSOLETE_SUBPATHS]

def find_obsolete_files(target_dir, base_dir, current_files, toolkit_root=None):
    """
    Finds obsolete files in target_dir that were installed by Workforces in past versions
    or match known obsolete Workforces files, but are no longer in current_files.
    Strictly preserves user-created custom files.
    """
    target_dir = os.path.abspath(target_dir)
    current_set = set(os.path.normpath(f) for f in current_files)
    obsolete = set()

    # 1. Check previous manifest if present
    prev_manifest = load_installed_manifest(target_dir)
    if prev_manifest and isinstance(prev_manifest, dict):
        prev_files = prev_manifest.get('installed_files', [])
        for pf in prev_files:
            norm_pf = os.path.normpath(pf)
            if norm_pf not in current_set and os.path.exists(os.path.join(target_dir, norm_pf)):
                obsolete.add(norm_pf)

    # 2. Check known legacy obsolete files (for legacy installations without .manifest.json)
    legacy_candidates = get_known_legacy_obsolete_files(base_dir)
    for lf in legacy_candidates:
        norm_lf = os.path.normpath(lf)
        if norm_lf not in current_set and os.path.exists(os.path.join(target_dir, norm_lf)):
            obsolete.add(norm_lf)

    # 3. If toolkit_root is a git repository, check historical files
    if toolkit_root and os.path.isdir(os.path.join(toolkit_root, '.git')):
        try:
            import subprocess
            cmd = ['git', '-C', toolkit_root, 'log', '--format=', '--name-only']
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0:
                hist_paths = set(l.strip() for l in res.stdout.splitlines() if l.strip())
                for hp in hist_paths:
                    top_dir = hp.split('/')[0]
                    if top_dir in ('agents', 'workflows', 'rules', 'skills', 'plugins', 'teams'):
                        candidate_rel = os.path.normpath(os.path.join(base_dir, hp))
                        if candidate_rel not in current_set and os.path.exists(os.path.join(target_dir, candidate_rel)):
                            obsolete.add(candidate_rel)
        except Exception:
            pass

    # Final filter: NEVER include any current file
    return sorted([f for f in obsolete if f not in current_set])

def prune_obsolete_files(target_dir, obsolete_files, dry_run=False):
    """
    Removes obsolete files and cleans up any parent directories that become empty.
    Returns the number of pruned files.
    """
    target_dir = os.path.abspath(target_dir)
    pruned_count = 0
    dirs_to_check = set()

    for f_rel in obsolete_files:
        full_path = os.path.abspath(os.path.join(target_dir, f_rel))
        if not full_path.startswith(target_dir + os.sep):
            continue
        if not os.path.exists(full_path):
            continue
        if dry_run:
            print(f"  \033[1;33m[WOULD PRUNE OBSOLETE]\033[0m {f_rel}")
            pruned_count += 1
        else:
            try:
                os.remove(full_path)
                print(f"  \033[0;31m[PRUNED OBSOLETE]\033[0m {f_rel}")
                pruned_count += 1
                dirs_to_check.add(os.path.dirname(full_path))
            except Exception as e:
                print(f"  \033[0;31m[ERROR PRUNING]\033[0m {f_rel}: {e}")

    if not dry_run and dirs_to_check:
        # Clean up empty parent directories up to base_dir
        sorted_dirs = sorted(list(dirs_to_check), key=len, reverse=True)
        for d in sorted_dirs:
            curr = d
            while curr and curr != target_dir and curr.startswith(target_dir):
                try:
                    if os.path.isdir(curr) and not os.listdir(curr):
                        os.rmdir(curr)
                        curr = os.path.dirname(curr)
                    else:
                        break
                except Exception:
                    break

    return pruned_count

def main():
    parser = argparse.ArgumentParser(description="Resolve workforce asset manifest by installed teams")
    parser.add_argument("--toolkit-root", default=".", help="Root of source workforces toolkit")
    parser.add_argument("--target", default=".", help="Root of target project")
    parser.add_argument("--teams", default=None, help="Comma-separated teams (or 'all')")
    parser.add_argument("--format", choices=["json", "bash-export", "files"], default="json", help="Output format")
    parser.add_argument("--save-manifest", action="store_true", help="Save resolved manifest to workforces/.manifest.json")
    parser.add_argument("--version-hash", default="unknown", help="Version commit hash to record in manifest")
    parser.add_argument("--prune-obsolete", action="store_true", help="Prune obsolete toolkit files from target")
    parser.add_argument("--dry", "--dry-run", action="store_true", help="Show what would be pruned without deleting files")

    args = parser.parse_args()
    toolkit_root = os.path.abspath(args.toolkit_root)
    target_dir = os.path.abspath(args.target)
    base_dir = detect_base_dir(target_dir)

    manifest = resolve_manifest(toolkit_root, target_dir, args.teams)
    installed_files = resolve_installed_file_paths(toolkit_root, target_dir, base_dir, args.teams)

    if args.prune_obsolete:
        obsolete = find_obsolete_files(target_dir, base_dir, installed_files, toolkit_root)
        pruned_count = prune_obsolete_files(target_dir, obsolete, dry_run=args.dry)
        if args.format == "json":
            print(json.dumps({"obsolete_files": obsolete, "pruned_count": pruned_count}, indent=2))
        return

    if args.save_manifest:
        save_path = save_installed_manifest(
            target_dir=target_dir,
            version=args.version_hash,
            installed_teams=manifest['installed_teams'],
            installed_files=installed_files
        )
        if args.format == "json":
            print(json.dumps({"manifest_path": save_path, "total_files": len(installed_files)}, indent=2))
        return

    if args.format == "json":
        print(json.dumps(manifest, indent=2))
    elif args.format == "files":
        print(json.dumps(installed_files, indent=2))
    elif args.format == "bash-export":
        def sanitize_bash(items):
            clean = []
            for item in items:
                sanitized = re.sub(r'[^a-zA-Z0-9_./-]', '', str(item))
                if sanitized:
                    clean.append(sanitized)
            return ' '.join(clean)

        print(f"INSTALLED_TEAMS_LIST=\"{sanitize_bash(manifest['installed_teams'])}\"")
        print(f"ALLOWED_AGENTS=\"{sanitize_bash(manifest['agents'])}\"")
        print(f"ALLOWED_RULES=\"{sanitize_bash(manifest['rules'])}\"")
        print(f"ALLOWED_SKILLS=\"{sanitize_bash(manifest['skills'])}\"")
        print(f"ALLOWED_WORKFLOWS=\"{sanitize_bash(manifest['workflows'])}\"")
        print(f"ALLOWED_PLUGINS=\"{sanitize_bash(manifest['plugins'])}\"")
        print(f"ALLOWED_TEAMS=\"{sanitize_bash(manifest['teams'])}\"")

if __name__ == "__main__":
    main()
