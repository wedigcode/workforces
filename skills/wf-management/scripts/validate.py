#!/usr/bin/env python3
"""
Workforces Team Manifest, Agent & Canonical Sidecar Validator
Audits team manifests (team.json and pack.json), compiled host agent frontmatter,
and canonical sidecar JSON schemas across all 5 supported AI hosts and toolkit roots.
"""

import json
import os
import sys

EDITOR_REL_BASES = (
    ".agents",
    os.path.join(".github", "copilot"),
    ".github",
    ".claude",
    ".grok",
    ".cursor",
)
KNOWN_HOST_IDS = frozenset({"antigravity", "claude", "grok", "copilot", "cursor"})
CANONICAL_CAPABILITIES = frozenset(
    {"read", "search", "edit", "multi_edit", "execute", "web", "image", "delegate"}
)
VALID_HOOK_MODES = frozenset(
    {"plugin_bundles", "plugin_bundle", "claude_settings_json", "grok_hooks_and_plugins", "none"}
)
NO_PLUGIN_BUNDLE_BASES = frozenset({".claude", ".github", ".github/copilot", ".cursor"})


def _strip_asset_ext(item):
    """Strip compiled or canonical markdown extensions to recover the asset stem."""
    for ext in (".agent.md", ".instructions.md", ".prompt.md", ".mdc", ".md"):
        if item.endswith(ext):
            return item[: -len(ext)]
    return item


HOST_ID_TO_BASE = {
    "antigravity": ".agents",
    "claude": ".claude",
    "grok": ".grok",
    "copilot": ".github",
    "cursor": ".cursor",
}
COPILOT_SUBMARKERS = ("copilot", "agents", "instructions", "skills", "prompts", "copilot-instructions.md")


def _has_copilot_marker(target_dir):
    """Return True only when .github contains actual Copilot toolkit assets rather than CI-only workflows."""
    gh_dir = os.path.join(target_dir, ".github")
    return os.path.isdir(gh_dir) and any(os.path.exists(os.path.join(gh_dir, m)) for m in COPILOT_SUBMARKERS)


def _read_configured_hosts(cfg_path):
    """Read raw 'hosts' list from a JSON config/manifest file if valid."""
    if not os.path.isfile(cfg_path):
        return []
    try:
        data = json.loads(open(cfg_path, "r", encoding="utf-8").read())
    except (OSError, ValueError):
        return []
    hosts = data.get("hosts") if isinstance(data, dict) else None
    return hosts if isinstance(hosts, list) else []


def _detect_active_editor_bases(target_dir):
    """Return ordered list of active relative editor bases from config/manifest and real workspace markers."""
    bases = []
    for cfg_rel in (os.path.join("workforces", "config.json"), os.path.join("workforces", ".manifest.json")):
        for hid in _read_configured_hosts(os.path.join(target_dir, cfg_rel)):
            mapped = HOST_ID_TO_BASE.get(str(hid).strip().lower())
            if mapped and mapped not in bases:
                bases.append(mapped)
    marker_checks = (
        (".agents", os.path.isdir(os.path.join(target_dir, ".agents"))),
        (".claude", os.path.isdir(os.path.join(target_dir, ".claude"))),
        (".grok", os.path.isdir(os.path.join(target_dir, ".grok"))),
        (".github", _has_copilot_marker(target_dir)),
        (".cursor", os.path.isdir(os.path.join(target_dir, ".cursor"))),
    )
    for rel, present in marker_checks:
        if present and rel not in bases:
            bases.append(rel)
    return bases


def _detect_editor_base_rel(target_dir):
    """Return the primary active relative editor base under target_dir, or empty string."""
    bases = _detect_active_editor_bases(target_dir)
    return bases[0] if bases else ""


def _legacy_team_candidates(target_dir, asset_base, team_path, key, rel):
    """Build candidate file paths for a legacy team.json entry across host layouts."""
    stem = _strip_asset_ext(os.path.basename(rel))
    cands = [
        os.path.join(team_path, rel),
        os.path.join(asset_base, rel),
        os.path.join(target_dir, rel),
        os.path.join(asset_base, key, f"{stem}.md"),
    ]
    if key == "personas":
        cands.append(os.path.join(asset_base, "agents", f"{stem}.md"))
        cands.append(os.path.join(asset_base, "agents", f"{stem}.agent.md"))
    elif key == "rules":
        cands.append(os.path.join(asset_base, "instructions", f"{stem}.instructions.md"))
        cands.append(os.path.join(asset_base, "rules", f"{stem}.mdc"))
    elif key == "workflows":
        cands.append(os.path.join(asset_base, "commands", f"{stem}.md"))
        cands.append(os.path.join(asset_base, "prompts", f"{stem}.prompt.md"))
    return cands


def _all_legacy_candidates(target_dir, base_rels, team_path, key, rel):
    """Collect candidate paths across all active editor bases for one legacy team.json reference."""
    cands = []
    for brel in base_rels:
        asset_base = os.path.join(target_dir, brel) if brel else target_dir
        cands.extend(_legacy_team_candidates(target_dir, asset_base, team_path, key, rel))
    return cands


def _audit_legacy_team_json(target_dir, base_rels, team, team_path, manifest_path, fix):
    """Audit legacy team.json relative references across team, active editor bases, and workspace root."""
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"Error reading {manifest_path}: {exc}")
        return 1
    if not isinstance(data, dict):
        print(f"Error reading {manifest_path}: root must be JSON object")
        return 1
    missing = []
    for key in ("personas", "rules", "workflows"):
        for rel in data.get(key, []):
            cands = _all_legacy_candidates(target_dir, base_rels, team_path, key, rel)
            if not any(os.path.exists(p) for p in cands):
                missing.append((key, rel, cands[0]))
    print(f"\n=== Team: {team} ({data.get('name', team)}) ===")
    if not missing:
        print("  ✓ All referenced personas, rules, and workflows exist!")
        return 0
    for key, rel, full_path in missing:
        print(f"  ❌ Missing [{key}]: {rel}")
        if fix:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            title = _strip_asset_ext(os.path.basename(rel)).replace("-", " ").title()
            with open(full_path, "w", encoding="utf-8") as fh:
                fh.write(f"# {title}\n\nGenerated template for {key[:-1]}: {title}.\n")
            print(f"     └─ Generated: {rel}")
    return 0 if fix else len(missing)


def _expected_pack_candidates(target_dir, base_rel, key, item):
    """Return candidate paths for one pack.json item according to the host base layout."""
    norm_rel = base_rel.replace("\\", "/")
    base_dir = os.path.join(target_dir, base_rel) if base_rel else target_dir
    stem = _strip_asset_ext(item)
    legacy_cp = os.path.join(target_dir, ".github", "copilot")
    if key == "plugins":
        return [] if norm_rel in NO_PLUGIN_BUNDLE_BASES else [os.path.join(base_dir, "plugins", item, "plugin.json")]
    if key == "skills":
        cands = [os.path.join(base_dir, "skills", item, "SKILL.md")]
        return cands + ([os.path.join(legacy_cp, "skills", item, "SKILL.md")] if norm_rel == ".github" else [])
    if key == "agents":
        if norm_rel == ".github":
            return [os.path.join(base_dir, "agents", f"{stem}.agent.md"), os.path.join(legacy_cp, "agents", f"{stem}.md")]
        return [os.path.join(base_dir, "agents", f"{stem}.md")]
    if key == "rules":
        if norm_rel == ".github":
            return [os.path.join(base_dir, "instructions", f"{stem}.instructions.md"), os.path.join(legacy_cp, "rules", f"{stem}.md")]
        if norm_rel == ".cursor":
            return [os.path.join(base_dir, "rules", f"{stem}.mdc"), os.path.join(base_dir, "rules", f"{stem}.md")]
        return [os.path.join(base_dir, "rules", f"{stem}.md")]
    if norm_rel == ".github":
        return [os.path.join(base_dir, "prompts", f"{stem}.prompt.md"), os.path.join(legacy_cp, "workflows", f"{stem}.md")]
    if norm_rel in (".claude", ".grok", ".cursor"):
        return [os.path.join(base_dir, "commands", f"{stem}.md"), os.path.join(base_dir, "workflows", f"{stem}.md")]
    return [os.path.join(base_dir, "workflows", f"{stem}.md")]


def _audit_pack_json(target_dir, base_rels, rel_label, team, pack_path):
    """Audit v2 pack.json references against the corresponding host base(s) or toolkit base."""
    try:
        with open(pack_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"Error reading {pack_path}: {exc}")
        return 1
    if not isinstance(data, dict):
        print(f"Error reading {pack_path}: root must be JSON object")
        return 1
    missing = []
    for key in ("agents", "rules", "workflows", "skills", "plugins"):
        for item in data.get(key, []):
            cands = [p for brel in base_rels for p in _expected_pack_candidates(target_dir, brel, key, item)]
            if cands and not any(os.path.exists(p) for p in cands):
                missing.append((key, item, cands[0]))
    print(f"\n=== Team Pack ({rel_label}): {team} ({data.get('name', team)}) ===")
    if not missing:
        print("  ✓ All referenced agents, rules, skills, and plugins exist!")
        return 0
    for key, item, expected in missing:
        print(f"  ❌ Missing [{key}]: {item} (expected {expected})")
    return len(missing)


def _audit_single_team_dir(target_dir, base_rels, rel_label, team, team_path, fix):
    """Audit legacy team.json and/or v2 pack.json inside a single team directory."""
    issues = 0
    legacy_manifest = os.path.join(team_path, "team.json")
    pack_manifest = os.path.join(team_path, "pack.json")
    if os.path.isfile(legacy_manifest):
        issues += _audit_legacy_team_json(target_dir, base_rels, team, team_path, legacy_manifest, fix)
    if os.path.isfile(pack_manifest):
        issues += _audit_pack_json(target_dir, base_rels, rel_label, team, pack_manifest)
    return issues


def audit_teams(target_dir=".", fix=False):
    """Audit all team manifests across workforces/, multi-host dirs, and toolkit teams/."""
    active_bases = _detect_active_editor_bases(target_dir) or [""]
    specs = [
        (os.path.join(target_dir, "workforces", "teams"), active_bases),
        (os.path.join(target_dir, ".agents", "teams"), [".agents"]),
        (os.path.join(target_dir, ".github", "copilot", "teams"), [".github"]),
        (os.path.join(target_dir, ".claude", "teams"), [".claude"]),
        (os.path.join(target_dir, ".grok", "teams"), [".grok"]),
        (os.path.join(target_dir, ".cursor", "teams"), [".cursor"]),
        (os.path.join(target_dir, "teams"), [""]),
    ]
    existing = [(tdir, brels) for tdir, brels in specs if os.path.isdir(tdir)]
    if not existing:
        print(f"No teams directory found under {target_dir}")
        return 0
    unfixed_missing = 0
    for teams_dir, base_rels in existing:
        rel_label = os.path.relpath(teams_dir, target_dir)
        for team in sorted(os.listdir(teams_dir)):
            team_path = os.path.join(teams_dir, team)
            if os.path.isdir(team_path):
                unfixed_missing += _audit_single_team_dir(target_dir, base_rels, rel_label, team, team_path, fix)
    return unfixed_missing


def _audit_single_agent_file(filepath, fname):
    """Validate YAML frontmatter schema for a single agent markdown file (.md or .agent.md)."""
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()
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
    """Audit custom agent frontmatter across all existing host and toolkit agent folders."""
    candidate_dirs = [os.path.join(target_dir, rel, "agents") for rel in EDITOR_REL_BASES]
    candidate_dirs.append(os.path.join(target_dir, "agents"))
    existing_dirs = [d for d in candidate_dirs if os.path.isdir(d)]
    issues = 0
    for agents_dir in existing_dirs:
        rel_dir = os.path.relpath(agents_dir, target_dir)
        print(f"\n=== Auditing Custom Agents ({rel_dir}) ===")
        for fname in sorted(os.listdir(agents_dir)):
            if fname.endswith(".md"):
                issues += _audit_single_agent_file(os.path.join(agents_dir, fname), fname)
    return issues


def _validate_plugin_hook_entry(entry, phase, label):
    """Validate one canonical plugin hook entry and its matcher_capabilities."""
    if not isinstance(entry, dict):
        return [f"{label}: hook entry under '{phase}' must be a JSON object"]
    errors = []
    mcaps = entry.get("matcher_capabilities")
    if mcaps is not None:
        if not isinstance(mcaps, list):
            errors.append(f"{label}: 'matcher_capabilities' under '{phase}' must be a list")
        else:
            bad = [c for c in mcaps if not isinstance(c, str) or c not in CANONICAL_CAPABILITIES]
            if bad:
                errors.append(f"{label}: unknown matcher_capabilities {bad} under '{phase}'")
    return errors


def _validate_plugin_hooks_schema(hooks_obj, label):
    """Validate canonical plugin hooks phase dictionary and hook entries."""
    if hooks_obj is None:
        return []
    if not isinstance(hooks_obj, dict):
        return [f"{label}: 'hooks' must be a JSON object"]
    errors = []
    for phase, entries in hooks_obj.items():
        if not isinstance(entries, list):
            errors.append(f"{label}: hooks phase '{phase}' must map to a list")
            continue
        for entry in entries:
            errors.extend(_validate_plugin_hook_entry(entry, phase, label))
    return errors


def _validate_kind_specific_sidecar(data, expected_kind, label):
    """Validate kind-specific fields on agent, rule, skill, or plugin sidecar objects."""
    errors = []
    if expected_kind == "agent" and "skills" in data:
        skills = data["skills"]
        if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
            errors.append(f"{label}: 'skills' must be a list of strings")
    elif expected_kind == "rule":
        if "globs" in data and (not isinstance(data["globs"], list) or not all(isinstance(g, str) for g in data["globs"])):
            errors.append(f"{label}: 'globs' must be a list of strings")
        if "always_on" in data and not isinstance(data["always_on"], bool):
            errors.append(f"{label}: 'always_on' must be a boolean")
    elif expected_kind == "plugin":
        errors.extend(_validate_plugin_hooks_schema(data.get("hooks"), label))
    return errors


def _validate_sidecar_common(data, expected_kind, expected_name, paired_md, label):
    """Validate common fields, paired markdown file, capabilities, and host overrides on a sidecar."""
    if not isinstance(data, dict):
        return [f"{label}: sidecar root must be a JSON object"]
    errors = []
    if data.get("kind") != expected_kind:
        errors.append(f"{label}: expected kind '{expected_kind}', got {data.get('kind')!r}")
    if data.get("name") != expected_name or not str(data.get("description") or "").strip():
        errors.append(f"{label}: missing/mismatched 'name' ({expected_name}) or empty 'description'")
    if paired_md and not os.path.isfile(paired_md):
        errors.append(f"{label}: missing paired markdown file '{paired_md}'")
    caps = data.get("capabilities")
    if caps is not None:
        if not isinstance(caps, list):
            errors.append(f"{label}: 'capabilities' must be a list")
        else:
            bad_caps = [c for c in caps if not isinstance(c, str) or c not in CANONICAL_CAPABILITIES]
            if bad_caps:
                errors.append(f"{label}: unknown capabilities {bad_caps}")
    hosts_obj = data.get("hosts")
    if hosts_obj is not None:
        if not isinstance(hosts_obj, dict):
            errors.append(f"{label}: 'hosts' must be a JSON object")
        else:
            bad_hosts = [h for h in hosts_obj if h not in KNOWN_HOST_IDS or not isinstance(hosts_obj[h], dict)]
            if bad_hosts:
                errors.append(f"{label}: invalid host override keys {bad_hosts}")
    errors.extend(_validate_kind_specific_sidecar(data, expected_kind, label))
    return errors


def _audit_flat_sidecars(folder, expected_kind):
    """Validate agents/*.json or rules/*.json sidecars in toolkit source."""
    if not os.path.isdir(folder):
        return []
    errors = []
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(folder, fname)
        try:
            data = json.loads(open(fpath, "r", encoding="utf-8").read())
        except (OSError, ValueError) as exc:
            errors.append(f"{fpath}: invalid JSON ({exc})")
            continue
        stem = fname[:-5]
        paired = os.path.join(folder, f"{stem}.md")
        errors.extend(_validate_sidecar_common(data, expected_kind, stem, paired, fpath))
    return errors


def _audit_skill_and_plugin_sidecars(target_dir):
    """Validate skills/*/skill.json and canonical plugins/*/plugin.json sidecars."""
    errors = []
    skills_dir = os.path.join(target_dir, "skills")
    if os.path.isdir(skills_dir):
        for sname in sorted(os.listdir(skills_dir)):
            sjson = os.path.join(skills_dir, sname, "skill.json")
            if not os.path.isfile(sjson):
                continue
            data = json.loads(open(sjson, "r", encoding="utf-8").read())
            paired = os.path.join(skills_dir, sname, "SKILL.md")
            errors.extend(_validate_sidecar_common(data, "skill", sname, paired, sjson))
    plugins_dir = os.path.join(target_dir, "plugins")
    if os.path.isdir(plugins_dir):
        has_hosts_cfg = os.path.isdir(os.path.join(target_dir, "config", "hosts"))
        for pname in sorted(os.listdir(plugins_dir)):
            pjson = os.path.join(plugins_dir, pname, "plugin.json")
            if not os.path.isfile(pjson):
                continue
            data = json.loads(open(pjson, "r", encoding="utf-8").read())
            if not isinstance(data, dict) or "kind" in data or has_hosts_cfg:
                errors.extend(_validate_sidecar_common(data, "plugin", pname, None, pjson))
    return errors


def _audit_host_profiles(target_dir):
    """Validate config/hosts/*.json host adapter profiles when present."""
    hosts_dir = os.path.join(target_dir, "config", "hosts")
    if not os.path.isdir(hosts_dir):
        return []
    errors = []
    for fname in sorted(os.listdir(hosts_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(hosts_dir, fname)
        data = json.loads(open(fpath, "r", encoding="utf-8").read())
        if not isinstance(data, dict):
            errors.append(f"{fpath}: host profile root must be a JSON object")
            continue
        if data.get("id") not in KNOWN_HOST_IDS or not data.get("base_dir") or not isinstance(data.get("dirs"), dict):
            errors.append(f"{fpath}: invalid host profile id/base_dir/dirs")
        if data.get("hooks_mode") not in VALID_HOOK_MODES:
            errors.append(f"{fpath}: invalid hooks_mode {data.get('hooks_mode')!r}")
        for map_key in ("capability_map", "hook_capability_map"):
            cmap = data.get(map_key)
            if cmap is not None and not isinstance(cmap, dict):
                errors.append(f"{fpath}: '{map_key}' must be a JSON object")
                continue
            bad = [c for c in (cmap or {}) if c not in CANONICAL_CAPABILITIES]
            if bad:
                errors.append(f"{fpath}: unknown {map_key} keys {bad}")
    return errors


def audit_sidecars(target_dir="."):
    """Audit canonical sidecar JSON schemas and host adapter profiles if present."""
    errors = []
    errors.extend(_audit_flat_sidecars(os.path.join(target_dir, "agents"), "agent"))
    errors.extend(_audit_flat_sidecars(os.path.join(target_dir, "rules"), "rule"))
    try:
        errors.extend(_audit_skill_and_plugin_sidecars(target_dir))
        errors.extend(_audit_host_profiles(target_dir))
    except (OSError, ValueError) as exc:
        errors.append(f"Sidecar JSON parse failure: {exc}")
    for err in errors:
        print(f"  ❌ Sidecar schema error: {err}")
    return len(errors)


def main():
    pos_args = [a for a in sys.argv[1:] if not a.startswith("-")]
    target = pos_args[0] if pos_args else "."
    fix_flag = "--fix" in sys.argv
    team_issues = audit_teams(target, fix=fix_flag)
    agent_issues = audit_agents(target)
    sidecar_issues = audit_sidecars(target)
    total_issues = team_issues + agent_issues + sidecar_issues
    if total_issues > 0:
        print(f"\n⚠️ Total audit issues found: {total_issues}.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
