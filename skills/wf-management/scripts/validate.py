#!/usr/bin/env python3
"""
Workforces Team Manifest & Agent Validator
Audits team manifests (team.json and pack.json) and custom agent schemas across
multi-editor installations (.agents/, .github/copilot/, .claude/, .grok/) and toolkit roots.
"""

import json
import os
import sys

EDITOR_REL_BASES = (
    ".agents",
    os.path.join(".github", "copilot"),
    ".claude",
    ".grok",
)


def _detect_editor_base(target_dir):
    """Return the first existing editor base path under target_dir, or target_dir."""
    for rel in EDITOR_REL_BASES:
        cand = os.path.join(target_dir, rel)
        if os.path.isdir(cand):
            return cand
    return target_dir


def _audit_legacy_team_json(target_dir, asset_base, team, team_path, manifest_path, fix):
    """Audit legacy team.json relative references across team, editor base, and workspace root."""
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"Error reading {manifest_path}: {exc}")
        return 1

    missing = []
    for key in ("personas", "rules", "workflows"):
        for rel in data.get(key, []):
            candidates = (
                os.path.join(team_path, rel),
                os.path.join(asset_base, rel),
                os.path.join(target_dir, rel),
            )
            if not any(os.path.exists(p) for p in candidates):
                missing.append((key, rel, candidates[0]))

    print(f"\n=== Team: {team} ({data.get('name', team)}) ===")
    if not missing:
        print("  ✓ All referenced personas, rules, and workflows exist!")
        return 0

    for key, rel, full_path in missing:
        print(f"  ❌ Missing [{key}]: {rel}")
        if fix:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            title = os.path.basename(rel).replace(".md", "").replace("-", " ").title()
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\nGenerated template for {key[:-1]}: {title}.\n")
            print(f"     └─ Generated: {rel}")
    return 0 if fix else len(missing)


def _audit_pack_json(asset_base, rel_label, team, pack_path):
    """Audit v2 pack.json references against the corresponding editor or toolkit base."""
    try:
        with open(pack_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"Error reading {pack_path}: {exc}")
        return 1

    wf_folder = "commands" if os.path.normpath(asset_base).endswith(".grok") else "workflows"
    checks = (
        ("agents", lambda item: os.path.join(asset_base, "agents", item if item.endswith(".md") else f"{item}.md")),
        ("rules", lambda item: os.path.join(asset_base, "rules", item if item.endswith(".md") else f"{item}.md")),
        ("workflows", lambda item: os.path.join(asset_base, wf_folder, item if item.endswith(".md") else f"{item}.md")),
        ("skills", lambda item: os.path.join(asset_base, "skills", item, "SKILL.md")),
        ("plugins", lambda item: os.path.join(asset_base, "plugins", item, "plugin.json")),
    )
    missing = []
    for key, build_path in checks:
        for item in data.get(key, []):
            expected = build_path(item)
            if not os.path.exists(expected):
                missing.append((key, item, expected))

    print(f"\n=== Team Pack ({rel_label}): {team} ({data.get('name', team)}) ===")
    if not missing:
        print("  ✓ All referenced agents, rules, skills, and plugins exist!")
        return 0
    for key, item, expected in missing:
        print(f"  ❌ Missing [{key}]: {item} (expected {expected})")
    return len(missing)


def audit_teams(target_dir=".", fix=False):
    """Audit all team manifests across workforces/, multi-editor dirs, and toolkit teams/."""
    default_base = _detect_editor_base(target_dir)
    candidates = [(os.path.join(target_dir, "workforces", "teams"), default_base)]
    for rel in EDITOR_REL_BASES:
        base = os.path.join(target_dir, rel)
        candidates.append((os.path.join(base, "teams"), base))
    candidates.append((os.path.join(target_dir, "teams"), target_dir))

    existing = [(tdir, abase) for tdir, abase in candidates if os.path.isdir(tdir)]
    if not existing:
        print(f"No teams directory found under {target_dir}")
        return 0

    unfixed_missing = 0
    for teams_dir, asset_base in existing:
        rel_label = os.path.relpath(teams_dir, target_dir)
        for team in sorted(os.listdir(teams_dir)):
            team_path = os.path.join(teams_dir, team)
            if not os.path.isdir(team_path):
                continue
            legacy_manifest = os.path.join(team_path, "team.json")
            pack_manifest = os.path.join(team_path, "pack.json")
            if os.path.isfile(legacy_manifest):
                unfixed_missing += _audit_legacy_team_json(
                    target_dir, asset_base, team, team_path, legacy_manifest, fix
                )
            if os.path.isfile(pack_manifest):
                unfixed_missing += _audit_pack_json(asset_base, rel_label, team, pack_manifest)
    return unfixed_missing


def _audit_single_agent_file(filepath, fname):
    """Validate YAML frontmatter schema for a single agent markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---"):
        print(f"  ❌ {fname}: Missing YAML frontmatter marker '---'")
        return 1
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"  ❌ {fname}: Invalid YAML frontmatter formatting")
        return 1
    frontmatter = parts[1]
    if "name:" not in frontmatter or "description:" not in frontmatter:
        print(f"  ❌ {fname}: Frontmatter missing required 'name' or 'description'")
        return 1
    print(f"  ✓ {fname}: Valid frontmatter schema")
    return 0


def audit_agents(target_dir="."):
    """Audit custom agent frontmatter across all existing editor and toolkit agent folders."""
    candidate_dirs = [os.path.join(target_dir, rel, "agents") for rel in EDITOR_REL_BASES]
    candidate_dirs.append(os.path.join(target_dir, "agents"))
    existing_dirs = [d for d in candidate_dirs if os.path.isdir(d)]
    if not existing_dirs:
        return 0

    issues = 0
    for agents_dir in existing_dirs:
        rel_dir = os.path.relpath(agents_dir, target_dir)
        print(f"\n=== Auditing Custom Agents ({rel_dir}/*.md) ===")
        for fname in sorted(os.listdir(agents_dir)):
            if fname.endswith(".md"):
                issues += _audit_single_agent_file(os.path.join(agents_dir, fname), fname)
    return issues


def main():
    pos_args = [a for a in sys.argv[1:] if not a.startswith("-")]
    target = pos_args[0] if pos_args else "."
    fix_flag = "--fix" in sys.argv
    team_issues = audit_teams(target, fix=fix_flag)
    agent_issues = audit_agents(target)
    total_issues = team_issues + agent_issues
    if total_issues > 0:
        print(f"\n⚠️ Total audit issues found: {total_issues}.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

