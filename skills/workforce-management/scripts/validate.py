#!/usr/bin/env python3
"""
Workforces Team Manifest Validator & Auditor
Checks that all personas, rules, and workflows referenced in workforces/teams/*/team.json exist on disk.
Optionally generates stub templates for missing files if --fix is passed.
"""

import json
import os
import sys

def audit_teams(target_dir=".", fix=False):
    candidate_dirs = [
        os.path.join(target_dir, "workforces", "teams"),
        os.path.join(target_dir, ".agents", "teams")
    ]
    teams_dirs = [d for d in candidate_dirs if os.path.exists(d)]
    if not teams_dirs:
        print(f"No teams directory found at {os.path.join(target_dir, 'workforces', 'teams')}")
        return 0

    total_missing = 0
    scanned_teams = set()

    for teams_dir in teams_dirs:
        for team in sorted(os.listdir(teams_dir)):
            if team in scanned_teams:
                continue
            team_path = os.path.join(teams_dir, team)
            if not os.path.isdir(team_path):
                continue
            manifest_path = os.path.join(team_path, "team.json")
            if not os.path.exists(manifest_path):
                continue

            scanned_teams.add(team)
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error reading {manifest_path}: {e}")
                continue

            missing = []
            for key in ["personas", "rules", "workflows"]:
                for rel in data.get(key, []):
                    full_path = os.path.join(team_path, rel)
                    alt_path = os.path.join(target_dir, rel)
                    if not os.path.exists(full_path) and not os.path.exists(alt_path):
                        missing.append((key, rel, full_path))

            print(f"\n=== Team: {team} ({data.get('name', team)}) ===")

            if not missing:
                print("  ✓ All referenced personas, rules, and workflows exist!")
            else:
                total_missing += len(missing)
                for key, rel, full_path in missing:
                    print(f"  ❌ Missing [{key}]: {rel}")
                    if fix:
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        filename = os.path.basename(rel)
                        title = filename.replace(".md", "").replace("-", " ").title()
                        content = f"# {title}\n\nGenerated template for {key[:-1]}: {title}.\n"
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"     └─ Generated: {rel}")

    return total_missing

def audit_agents(target_dir="."):
    candidate_dirs = [
        os.path.join(target_dir, ".agents", "agents"),
        os.path.join(target_dir, "agents")
    ]
    agents_dir = next((d for d in candidate_dirs if os.path.exists(d)), None)
    if not agents_dir:
        return 0

    issues = 0
    print("\n=== Auditing Custom Agents (.agents/agents/*.md) ===")
    for fname in sorted(os.listdir(agents_dir)):
        if not fname.endswith(".md"):
            continue
        filepath = os.path.join(agents_dir, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            print(f"  ❌ {fname}: Missing YAML frontmatter marker '---'")
            issues += 1
            continue

        parts = content.split("---", 2)
        if len(parts) < 3:
            print(f"  ❌ {fname}: Invalid YAML frontmatter formatting")
            issues += 1
            continue

        frontmatter = parts[1]
        has_name = "name:" in frontmatter
        has_desc = "description:" in frontmatter
        has_tools = "tools:" in frontmatter

        if not (has_name and has_desc):
            print(f"  ❌ {fname}: Frontmatter missing required 'name' or 'description'")
            issues += 1
        else:
            print(f"  ✓ {fname}: Valid frontmatter schema")

    return issues

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    fix_flag = "--fix" in sys.argv
    team_missing = audit_teams(target, fix=fix_flag)
    agent_issues = audit_agents(target)
    total_issues = team_missing + agent_issues
    if total_issues > 0 and not fix_flag:
        print(f"\n⚠️ Total audit issues found: {total_issues}.")
        sys.exit(1)
    sys.exit(0)
