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

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    fix_flag = "--fix" in sys.argv
    missing_count = audit_teams(target, fix=fix_flag)
    if missing_count > 0 and not fix_flag:
        print(f"\n⚠️ Total missing referenced files: {missing_count}. Run with --fix to generate stub files.")
        sys.exit(1)
    sys.exit(0)
