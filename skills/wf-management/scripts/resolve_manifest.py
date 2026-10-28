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
    "skills/jules-integration/SKILL.md",
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
    """Returns list of relative paths of known historical Workforces files that were relocated or deleted."""
    candidates = []
    for p in LEGACY_OBSOLETE_SUBPATHS:
        candidates.append(os.path.normpath(os.path.join(base_dir, p)))
    return candidates

def _git_historical_subpaths(toolkit_root):
    """Return historical asset subpaths from toolkit git log when available."""
    if not toolkit_root or not os.path.isdir(os.path.join(toolkit_root, '.git')):
        return []
    import subprocess
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


def _collect_historical_candidates(target_dir, base_dir, toolkit_root):
    """Collect normalized relative paths from previous manifest, legacy list, and git history."""
    candidates = set(os.path.normpath(p) for p in get_known_legacy_obsolete_files(base_dir))
    prev_manifest = load_installed_manifest(target_dir)
    if prev_manifest and isinstance(prev_manifest, dict):
        for pf in prev_manifest.get('installed_files', []):
            candidates.add(os.path.normpath(pf))
    for hp in _git_historical_subpaths(toolkit_root):
        candidates.add(os.path.normpath(os.path.join(base_dir, hp)))
    return candidates


def _known_unprefixed_slugs(toolkit_root, category, fallback_items):
    """Return unprefixed slugs corresponding to current wf-* skills or plugins."""
    names = set(fallback_items)
    if toolkit_root:
        for src in (os.path.join(toolkit_root, category), os.path.join(toolkit_root, ".agents", category)):
            if os.path.isdir(src):
                names.update(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)))
    return {n[3:] for n in names if n.startswith("wf-") and len(n) > 3}


def _collect_legacy_dir_candidates(target_dir, base_dir, toolkit_root):
    """Collect candidate legacy workforce-*-plugin and unprefixed skill/plugin directories."""
    extra_dirs = set()
    unprefixed_plugins = _known_unprefixed_slugs(toolkit_root, "plugins", CORE_PLUGINS)
    unprefixed_skills = _known_unprefixed_slugs(toolkit_root, "skills", CORE_SKILLS)

    plugins_dir = os.path.join(target_dir, base_dir, "plugins")
    if os.path.isdir(plugins_dir):
        for entry in os.listdir(plugins_dir):
            if (entry.startswith("workforce-") and entry.endswith("-plugin")) or entry in unprefixed_plugins:
                extra_dirs.add(os.path.normpath(os.path.join(base_dir, "plugins", entry)))

    skills_dir = os.path.join(target_dir, base_dir, "skills")
    if os.path.isdir(skills_dir):
        for entry in os.listdir(skills_dir):
            if entry.startswith("workforce-") or entry in unprefixed_skills:
                extra_dirs.add(os.path.normpath(os.path.join(base_dir, "skills", entry)))
    return extra_dirs


def _find_obsolete_empty_dirs(target_dir, base_dir, candidate_files, current_set, obsolete_files, toolkit_root=None):
    """Identify effectively-empty legacy directories that contain no active or custom files."""
    candidate_dirs = _collect_legacy_dir_candidates(target_dir, base_dir, toolkit_root)
    for rel_file in candidate_files:
        parts = rel_file.replace("\\", "/").split("/")
        min_depth = 4 if parts[0] == ".github" else 3
        for depth in range(min_depth, len(parts)):
            candidate_dirs.add(os.path.normpath("/".join(parts[:depth])))

    empty_dirs = []
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


def find_obsolete_files(target_dir, base_dir, current_files, toolkit_root=None):
    """
    Finds obsolete files and empty legacy directories in target_dir that were installed
    by Workforces in past versions, while strictly preserving user-created custom files/dirs.
    """
    target_dir = os.path.abspath(target_dir)
    current_set = set(os.path.normpath(f) for f in current_files)
    candidates = _collect_historical_candidates(target_dir, base_dir, toolkit_root)

    obsolete = set()
    for cand in candidates:
        full_cand = os.path.join(target_dir, cand)
        if cand not in current_set and (os.path.isfile(full_cand) or os.path.islink(full_cand)):
            obsolete.add(cand)

    for empty_dir in _find_obsolete_empty_dirs(target_dir, base_dir, candidates, current_set, obsolete, toolkit_root):
        obsolete.add(empty_dir)

    return sorted([f for f in obsolete if f not in current_set])

def _is_effectively_empty_dir(dir_path):
    """Return True if dir_path has no files other than __pycache__, .pyc, or .DS_Store."""
    for root, _, files in os.walk(dir_path):
        if "__pycache__" in os.path.relpath(root, dir_path).split(os.sep):
            continue
        for fn in files:
            if fn != ".DS_Store" and not fn.endswith(".pyc"):
                return False
    return True


def _cleanup_empty_parent_dirs(target_dir, dirs_to_check):
    """Remove emptied skill/plugin/team subdirectories while preserving category roots."""
    import shutil
    for d in sorted(list(dirs_to_check), key=len, reverse=True):
        curr = d
        while curr and curr != target_dir and curr.startswith(target_dir + os.sep):
            rel_parts = os.path.relpath(curr, target_dir).replace("\\", "/").split("/")
            min_depth = 4 if rel_parts[0] == ".github" else 3
            if len(rel_parts) < min_depth:
                break
            if not os.path.isdir(curr):
                curr = os.path.dirname(curr)
                continue
            if _is_effectively_empty_dir(curr):
                shutil.rmtree(curr, ignore_errors=True)
                curr = os.path.dirname(curr)
            else:
                break


def _remove_obsolete_path(full_path):
    """Remove a single obsolete file or non-symlink directory."""
    import shutil
    if os.path.isdir(full_path) and not os.path.islink(full_path):
        shutil.rmtree(full_path)
    else:
        os.remove(full_path)


def prune_obsolete_files(target_dir, obsolete_files, dry_run=False, quiet=False):
    """Removes obsolete files or legacy directories and cleans up emptied parents."""
    target_dir = os.path.abspath(target_dir)
    pruned_count = 0
    dirs_to_check = set()

    for f_rel in obsolete_files:
        full_path = os.path.abspath(os.path.join(target_dir, f_rel))
        if not full_path.startswith(target_dir + os.sep) or not os.path.exists(full_path):
            continue
        if dry_run:
            if not quiet:
                print(f"  \033[1;33m[WOULD PRUNE OBSOLETE]\033[0m {f_rel}")
            pruned_count += 1
            continue
        try:
            _remove_obsolete_path(full_path)
            if not quiet:
                print(f"  \033[0;31m[PRUNED OBSOLETE]\033[0m {f_rel}")
            pruned_count += 1
            dirs_to_check.add(os.path.dirname(full_path))
        except OSError as e:
            if not quiet:
                print(f"  \033[0;31m[ERROR PRUNING]\033[0m {f_rel}: {e}")

    if not dry_run and dirs_to_check:
        _cleanup_empty_parent_dirs(target_dir, dirs_to_check)
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
        is_json = "--format" in sys.argv and args.format == "json"
        obsolete = find_obsolete_files(target_dir, base_dir, installed_files, toolkit_root)
        pruned_count = prune_obsolete_files(target_dir, obsolete, dry_run=args.dry, quiet=is_json)
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
