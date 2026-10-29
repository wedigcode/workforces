#!/usr/bin/env python3
"""
Workforces File Reference & Subtask Integrity Validator
Scans workspace markdown and JSON files for referenced file paths, links, unchecked subtasks,
and verifies session context issue tracking lineage for roadmap items.
Ensures zero dangling references, tracked subtasks, and automated issue inbox capture.
"""

import json
import os
import re
import sys

EDITOR_BASES = ("", ".agents", ".github/copilot", ".github", ".claude", ".grok", ".cursor")
RUNTIME_SESSION_DIRS = (
    "workforces/session-context",
    "workforces/sessions",
    ".agents/workforces/session-context",
    ".agents/workforces/sessions",
    ".agents/session-context",
)
SIDECAR_KINDS = frozenset({"agent", "rule", "skill", "plugin"})


def _strip_ref_ext(name):
    """Strip host-specific or canonical markdown extensions to obtain the clean stem."""
    for ext in (".agent.md", ".instructions.md", ".prompt.md", ".mdc", ".md"):
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


HOST_ID_TO_BASE = {
    "antigravity": ".agents",
    "claude": ".claude",
    "grok": ".grok",
    "copilot": ".github",
    "cursor": ".cursor",
}
COPILOT_SUBMARKERS = ("copilot", "agents", "instructions", "skills", "prompts", "copilot-instructions.md")


def _has_copilot_workspace_marker(target_dir):
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


def _active_workspace_bases(target_dir):
    """Return ordered list of active host editor bases in target_dir from config/manifest and markers."""
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
        (".github", _has_copilot_workspace_marker(target_dir)),
        (".cursor", os.path.isdir(os.path.join(target_dir, ".cursor"))),
    )
    for rel, present in marker_checks:
        if present and rel not in bases:
            bases.append(rel)
    return bases


def detect_editor_base(path, target_dir):
    """Return the installed editor base prefix for a path, if any."""
    rel_path = os.path.relpath(path, target_dir).replace("\\", "/")
    for base in sorted((b for b in EDITOR_BASES if b), key=len, reverse=True):
        if rel_path == base or rel_path.startswith(base + "/"):
            return base
    return ""


def build_pack_fix_target(target_dir, editor_base, key, rel_ref):
    """Build the auto-fix target path for a missing pack.json reference."""
    norm_eb = (editor_base or "").replace("\\", "/")
    if norm_eb in (".github", ".github/copilot"):
        gh_base = os.path.join(target_dir, ".github")
        if key == "skills":
            return os.path.normpath(os.path.join(gh_base, "skills", rel_ref, "SKILL.md"))
        stem = _strip_ref_ext(rel_ref)
        gh_map = {
            "agents": ("agents", f"{stem}.agent.md"),
            "rules": ("instructions", f"{stem}.instructions.md"),
            "workflows": ("prompts", f"{stem}.prompt.md"),
        }
        subdir, fname = gh_map.get(key, (key, f"{stem}.md"))
        return os.path.normpath(os.path.join(gh_base, subdir, fname))
    base_dir = os.path.join(target_dir, norm_eb) if norm_eb else target_dir
    if key == "skills":
        return os.path.normpath(os.path.join(base_dir, "skills", rel_ref, "SKILL.md"))
    stem = _strip_ref_ext(rel_ref)
    if norm_eb == ".cursor" and key == "rules":
        return os.path.normpath(os.path.join(base_dir, "rules", f"{stem}.mdc"))
    subdir = "commands" if key == "workflows" and norm_eb in (".claude", ".grok", ".cursor") else key
    return os.path.normpath(os.path.join(base_dir, subdir, f"{stem}.md"))


def is_excluded_runtime_dir(path, target_dir):
    """Return True when a directory is one of the runtime-only session trees."""
    rel_path = os.path.relpath(path, target_dir).replace("\\", "/")
    return any(rel_path == excluded or rel_path.startswith(excluded + "/") for excluded in RUNTIME_SESSION_DIRS)


CANONICAL_TEAM_PACKS = frozenset({
    "advisor", "compliance", "design", "dev", "growth", "launch", "marketing", "operations", "sales", "social"
})
_PEER_SUBPATH_RE = re.compile(
    r"^(agents|skills|rules|instructions|workflows|commands|prompts|plugins)/(wf-[a-z0-9-]+)"
    r"(?:\.(?:agent\.md|instructions\.md|prompt\.md|mdc|md)|/SKILL\.md|/plugin\.json)$"
)


def _extract_peer_subpath(rel_target, source_editor_base):
    """Strip matching host prefix from rel_target if within the same host family."""
    prefixes = (".github/copilot/", ".github/") if source_editor_base in (".github", ".github/copilot") else (f"{source_editor_base}/",)
    for pref in prefixes:
        if rel_target.startswith(pref):
            return rel_target[len(pref):]
    return None


def _collect_pack_stems(packs_dict):
    """Extract normalized wf-* asset stems across all team pack entries."""
    stems = set()
    for pack in packs_dict.values():
        items = sum(((pack.get(c) or []) for c in ("agents", "rules", "skills", "workflows", "plugins")), [])
        stems.update(_strip_ref_ext(str(item)) for item in items)
    return stems


def _known_canonical_peer_stems(target_dir, source_editor_base):
    """Return set of known canonical wf-* asset stems from bundled teams.json/plugins.json."""
    stems = set()
    eb_root = ".github" if source_editor_base == ".github/copilot" else source_editor_base
    hosts_dir = os.path.join(target_dir, eb_root, "skills", "wf-management", "hosts")
    for fname, top_key in (("teams.json", "teams"), ("plugins.json", "plugins")):
        fpath = os.path.join(hosts_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                payload = json.load(fh).get(top_key) or {}
        except (OSError, ValueError):
            continue
        found = {_strip_ref_ext(k) for k in payload} if top_key == "plugins" else _collect_pack_stems(payload)
        stems.update(found)
    return stems


def _is_uninstalled_cross_pack_peer(target_dir, source_editor_base, target_path):
    """Return True if target_path is a real canonical wf-* peer omitted by a partial-team consumer install."""
    manifest_path = os.path.join(target_dir, "workforces", ".manifest.json")
    if not os.path.isfile(manifest_path):
        return False
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        return False
    installed_teams = set(manifest.get("installed_teams") or [])
    if CANONICAL_TEAM_PACKS.issubset(installed_teams):
        return False
    rel_target = os.path.relpath(target_path, target_dir).replace("\\", "/")
    subpath = _extract_peer_subpath(rel_target, source_editor_base)
    match = _PEER_SUBPATH_RE.match(subpath) if subpath else None
    if not match:
        return False
    known_stems = _known_canonical_peer_stems(target_dir, source_editor_base)
    if known_stems and match.group(2) not in known_stems:
        return False
    installed_files = {p.replace("\\", "/") for p in (manifest.get("installed_files") or [])}
    return rel_target not in installed_files


def _record_if_missing_markdown_target(broken_refs, target_dir, root, rel_source, raw_link, target_path):
    """Append a broken Markdown Link entry unless target_path exists or is an uninstalled peer."""
    if os.path.exists(target_path):
        return
    source_eb = detect_editor_base(root, target_dir)
    if source_eb and _is_uninstalled_cross_pack_peer(target_dir, source_eb, target_path):
        return
    broken_refs.append({
        "source": rel_source,
        "type": "Markdown Link",
        "ref": raw_link,
        "target": target_path
    })


def _build_stub_content(target_path, source_rel):
    """Generate valid stub markdown (including host-native YAML frontmatter)."""
    norm_target = target_path.replace("\\", "/")
    filename = os.path.basename(target_path)
    slug = os.path.basename(os.path.dirname(target_path)) if filename == "SKILL.md" else _strip_ref_ext(filename)
    title = slug.replace("-", " ").title()
    header_type = "File"
    folder_labels = (
        ("personas", "Persona"), ("rules", "Rule"), ("instructions", "Rule"),
        ("workflows", "Workflow"), ("commands", "Command"), ("prompts", "Prompt"),
        ("skills", "Skill"), ("agents", "Agent"),
    )
    for folder, label in folder_labels:
        if f"/{folder}/" in norm_target:
            header_type = label
            break
    frontmatter = ""
    desc = f"Generated {header_type.lower()} dependency for {source_rel}."
    if norm_target.endswith(".mdc"):
        frontmatter = f"---\ndescription: {desc}\nalwaysApply: true\n---\n\n"
    elif norm_target.endswith(".instructions.md"):
        frontmatter = f"---\ndescription: {desc}\napplyTo: '**'\n---\n\n"
    elif norm_target.endswith(".prompt.md") or header_type in ("Agent", "Skill"):
        frontmatter = f"---\nname: {slug}\ndescription: {desc}\n---\n\n"
    return f"{frontmatter}# {header_type}: {title}\n\nGenerated dependency for `{source_rel}`.\n\n## Overview\nAuto-created by integrity audit to fulfill reference dependency.\n"


def parse_frontmatter(content):
    """Extract YAML-style frontmatter and body from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml = parts[1]
    body = parts[2].lstrip("\r\n")

    metadata = {}
    current_list_key = None
    current_dict_in_list = None

    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Handle list item start: "- ..."
        if stripped.startswith("- ") and current_list_key:
            item_text = stripped[2:].strip()
            if ":" in item_text:
                sub_k, sub_v = item_text.split(":", 1)
                sub_k = sub_k.strip()
                sub_v = sub_v.strip().strip('"').strip("'")
                current_dict_in_list = {sub_k: sub_v}
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(current_dict_in_list)
            else:
                current_dict_in_list = None
                val = item_text.strip('"').strip("'")
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(val)
            continue

        # Handle subsequent lines of dict in list: e.g. "  title: '...'"
        if (line.startswith("  ") or line.startswith("\t")) and current_dict_in_list is not None and ":" in line:
            sub_k, sub_v = stripped.split(":", 1)
            sub_k = sub_k.strip()
            sub_v = sub_v.strip().strip('"').strip("'")
            current_dict_in_list[sub_k] = sub_v
            continue

        if ":" in line:
            current_dict_in_list = None
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            if val == "" or val == "~" or val == "null":
                metadata[key] = None
                current_list_key = key
            elif val.startswith("[") and val.endswith("]"):
                current_list_key = None
                raw_items = val[1:-1].split(",")
                metadata[key] = [item.strip().strip('"').strip("'") for item in raw_items if item.strip()]
            elif val.startswith('"') and val.endswith('"'):
                current_list_key = None
                metadata[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                current_list_key = None
                metadata[key] = val[1:-1]
            elif val.lower() == "true":
                current_list_key = None
                metadata[key] = True
            elif val.lower() == "false":
                current_list_key = None
                metadata[key] = False
            else:
                current_list_key = None
                metadata[key] = val

    return metadata, body


def audit_session_context(target_dir):
    """
    Audits session context files in workforces/session-context/ for untracked roadmap items
    and validates issue tracker lineage.
    """
    session_ctx_dir = os.path.normpath(os.path.join(target_dir, "workforces", "session-context"))
    inbox_dir = os.path.normpath(os.path.join(target_dir, "workforces", "issues", "inbox"))
    triaged_dir = os.path.normpath(os.path.join(target_dir, "workforces", "issues", "triaged"))
    completed_dir = os.path.normpath(os.path.join(target_dir, "workforces", "issues", "completed"))

    session_notes = []
    untracked_roadmaps = []

    if not os.path.exists(session_ctx_dir):
        return session_notes, untracked_roadmaps

    inbox_files = os.listdir(inbox_dir) if os.path.exists(inbox_dir) else []
    triaged_files = os.listdir(triaged_dir) if os.path.exists(triaged_dir) else []
    completed_files = os.listdir(completed_dir) if os.path.exists(completed_dir) else []
    known_issue_slugs = [f.lower().replace(".md", "") for f in (inbox_files + triaged_files + completed_files)]

    for note in sorted(os.listdir(session_ctx_dir)):
        if not note.endswith(".md") or note == ".gitkeep":
            continue
        note_path = os.path.join(session_ctx_dir, note)
        rel_note = os.path.relpath(note_path, target_dir)
        session_notes.append(note)

        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        meta, body = parse_frontmatter(content)
        raw_tt = meta.get("tracked_tasks") or []
        raw_ti = meta.get("tracked_issues") or []
        tt = [raw_tt] if isinstance(raw_tt, str) else list(raw_tt)
        ti = [raw_ti] if isinstance(raw_ti, str) else list(raw_ti)
        tracked_tasks = [x for x in tt if x] + [x for x in ti if x]
        tracked_strings = []
        for item in tracked_tasks:
            if isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, str):
                        tracked_strings.append(v.lower())
            elif isinstance(item, str):
                tracked_strings.append(item.lower())

        # Check for roadmap or feature horizon headings
        roadmap_match = re.search(
            r'##\s+.*(?:Roadmap|Proposed Horizons|Feature Horizons|Winning SaaS Concepts|Problem-to-Solution Lineage)',
            body,
            re.IGNORECASE
        )
        if roadmap_match:
            roadmap_section = body[roadmap_match.start():]
            next_h2 = re.search(r'\n##\s+', roadmap_section[4:])
            if next_h2:
                roadmap_section = roadmap_section[:next_h2.start() + 4]

            # Find phase items (e.g. - **Phase 1: ...**, - **Horizon 1: ...**, - **Concept 1: ...**)
            phase_items = re.findall(r'^\s*-\s*\*\*([^\*:]+)(?::\s*([^\*]+))?\*\*', roadmap_section, re.MULTILINE)
            if phase_items:
                for phase_label, phase_name in phase_items:
                    full_name = f"{phase_label}: {phase_name}".strip(": ") if phase_name else phase_label.strip()
                    matched = any(
                        full_name.lower() in t or t in full_name.lower() or
                        (phase_name and phase_name.lower() in t)
                        for t in tracked_strings
                    )
                    if not matched:
                        slug_cand = re.sub(r'[^a-z0-9]+', '-', full_name.lower()).strip('-')
                        matched = any(slug_cand in k or k in slug_cand for k in known_issue_slugs)
                    if not matched:
                        untracked_roadmaps.append({
                            "source": rel_note,
                            "item": full_name
                        })
            elif not tracked_strings and not inbox_files:
                untracked_roadmaps.append({
                    "source": rel_note,
                    "item": f"Roadmap Section without tracked inbox issues ({roadmap_match.group(0).strip()})"
                })

    return session_notes, untracked_roadmaps


_RENAMED_WORKFLOW_MAP = {
    "wf-task": "wf-task-tracker",
    "task": "wf-task-tracker",
    "wf-feature": "wf-feature-research",
    "feature": "wf-feature-research",
    "wf-context": "wf-session-context",
    "context": "wf-session-context",
    "wf-site-setup": "wf-site-setup",
    "site-setup": "wf-site-setup",
    "wf-image-duplicate": "wf-image-workflow",
    "image-duplicate": "wf-image-workflow",
}
_PLACEHOLDER_SUBSTRINGS = ("example", "path/to", "modifiedfile", "...", "{{", "}}", "{%")
_PLACEHOLDER_WORDS = frozenset({"path", "url", "uri", "target", "filepath", "filename"})


def _pack_json_candidates(target_dir, pack_editor_base, key, rel_ref):
    """Return candidate paths for a pack.json reference strictly within its host base."""
    primary = build_pack_fix_target(target_dir, pack_editor_base, key, rel_ref)
    norm_eb = (pack_editor_base or "").replace("\\", "/")
    stem = _strip_ref_ext(rel_ref)
    if norm_eb in (".github", ".github/copilot"):
        legacy_cp = os.path.join(target_dir, ".github", "copilot")
        if key == "skills":
            return [primary, os.path.normpath(os.path.join(legacy_cp, "skills", rel_ref, "SKILL.md"))]
        return [
            primary,
            os.path.normpath(os.path.join(legacy_cp, key, rel_ref)),
            os.path.normpath(os.path.join(legacy_cp, key, f"{stem}.md")),
            os.path.normpath(os.path.join(target_dir, ".github", rel_ref)),
        ]
    base_dir = os.path.join(target_dir, norm_eb) if norm_eb else target_dir
    if key == "skills":
        return [primary]
    return [
        primary,
        os.path.normpath(os.path.join(base_dir, key, rel_ref)),
        os.path.normpath(os.path.join(base_dir, key, f"{stem}.md")),
        os.path.normpath(os.path.join(base_dir, rel_ref)),
        os.path.normpath(os.path.join(base_dir, f"{rel_ref}.md")),
    ]


def _non_pack_json_candidates(target_dir, root, key, rel_ref):
    """Return fallback candidate paths for legacy team.json or generic manifest references."""
    stem = _strip_ref_ext(rel_ref)
    cands = [
        os.path.normpath(os.path.join(root, rel_ref)),
        os.path.normpath(os.path.join(target_dir, key, rel_ref)),
        os.path.normpath(os.path.join(target_dir, key, f"{stem}.md")),
        os.path.normpath(os.path.join(target_dir, rel_ref)),
        os.path.normpath(os.path.join(target_dir, f"{rel_ref}.md")),
        os.path.normpath(os.path.join(root, f"{rel_ref}.md")),
    ]
    for base in (".agents", ".github", ".claude", ".grok", ".cursor"):
        cands.append(build_pack_fix_target(target_dir, base, key, rel_ref))
    if key == "skills":
        cands.append(os.path.normpath(os.path.join(target_dir, "skills", rel_ref, "SKILL.md")))
    return cands


def _check_single_json_ref(broken_refs, target_dir, root, rel_source, is_pack_json, key, rel_ref):
    """Validate one string reference inside pack.json or team.json and record if missing."""
    if is_pack_json:
        pack_eb = detect_editor_base(root, target_dir)
        norm_src = rel_source.replace("\\", "/")
        if pack_eb:
            bases = [pack_eb]
        elif norm_src.startswith("workforces/teams/"):
            bases = _active_workspace_bases(target_dir) or [""]
        else:
            bases = [""]
        cands = [c for b in bases for c in _pack_json_candidates(target_dir, b, key, rel_ref)]
        if not any(os.path.exists(c) for c in cands):
            broken_refs.append({"source": rel_source, "type": f"JSON {key}", "ref": rel_ref, "target": cands[0]})
        return
    cands = _non_pack_json_candidates(target_dir, root, key, rel_ref)
    if not any(os.path.exists(c) for c in cands):
        broken_refs.append({"source": rel_source, "type": f"JSON {key}", "ref": rel_ref, "target": cands[0]})


def _audit_json_manifest(broken_refs, target_dir, root, file, rel_source, content):
    """Parse JSON file and audit pack.json or legacy manifest asset references."""
    try:
        data = json.loads(content)
    except (OSError, ValueError):
        return
    if not isinstance(data, dict) or data.get("kind") in SIDECAR_KINDS:
        return
    is_pack_json = file == "pack.json"
    for key in ("personas", "rules", "workflows", "agents", "skills"):
        items = data.get(key)
        if not isinstance(items, list):
            continue
        for rel_ref in items:
            if isinstance(rel_ref, str):
                _check_single_json_ref(broken_refs, target_dir, root, rel_source, is_pack_json, key, rel_ref)


def _resolve_legacy_workflow_link(target_dir, clean_link):
    """Fallback resolution for historical notes referencing workflows migrated to skills."""
    wf_stem = _strip_ref_ext(os.path.basename(clean_link))
    prefixed_stem = wf_stem if wf_stem.startswith("wf-") else f"wf-{wf_stem}"
    mapped = _RENAMED_WORKFLOW_MAP.get(wf_stem)
    stems = [prefixed_stem, wf_stem] + ([mapped] if mapped else [])
    bases = ("skills", ".agents/skills", ".github/skills", ".claude/skills", ".grok/skills", ".cursor/skills")
    for stem in stems:
        for base in bases:
            cand = os.path.normpath(os.path.join(target_dir, base, stem, "SKILL.md"))
            if os.path.exists(cand):
                return cand
    return None


def _resolve_markdown_link_target(target_dir, root, raw_link):
    """Return resolved target_path for a markdown link, or None if link should be ignored."""
    if raw_link.startswith(("http://", "https://", "#", "mailto:")):
        return None
    if any(tok in raw_link for tok in _PLACEHOLDER_SUBSTRINGS) or raw_link.strip().lower() in _PLACEHOLDER_WORDS:
        return None
    clean_link = raw_link.replace("file://", "").split("#")[0]
    if not clean_link:
        return None
    target_path = clean_link if clean_link.startswith("/") else os.path.normpath(os.path.join(root, clean_link))
    if not os.path.exists(target_path):
        root_rel = os.path.normpath(os.path.join(target_dir, clean_link.replace("../", "")))
        if os.path.exists(root_rel):
            target_path = root_rel
    if not os.path.exists(target_path) and "workflows" in clean_link:
        wf_resolved = _resolve_legacy_workflow_link(target_dir, clean_link)
        if wf_resolved:
            target_path = wf_resolved
    return target_path


def _audit_markdown_links_and_todos(broken_refs, pending_todos, target_dir, root, rel_source, content):
    """Audit markdown links and unchecked TODO checkboxes in a .md or .mdc file."""
    md_content = re.sub(r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?\n[ \t]*\1[ \t]*$", "", content)
    md_content = re.sub(r"```[\s\S]*?```", "", md_content)
    md_content = re.sub(r"~~~[\s\S]*?~~~", "", md_content)
    md_content = re.sub(r"(`+)(.*?)\1", "", md_content)
    for _, raw_link in re.findall(r"\[([^\]]*)\]\((file://[^\s\)]+|[^\s\)]+)\)", md_content):
        target_path = _resolve_markdown_link_target(target_dir, root, raw_link)
        if target_path is not None:
            _record_if_missing_markdown_target(broken_refs, target_dir, root, rel_source, raw_link, target_path)
    for todo in re.findall(r"^\s*-\s*\[\s*\]\s+(.+)$", content, re.MULTILINE):
        pending_todos.append({"source": rel_source, "task": todo.strip()})


def _print_broken_and_apply_fixes(broken_refs, fix):
    """Print broken reference summary and optionally auto-generate missing stub files."""
    if not broken_refs:
        print("  ✓ Zero dangling file references found!")
        return
    print(f"  ❌ Found {len(broken_refs)} dangling file reference(s):")
    for item in broken_refs:
        print(f"     • [{item['source']}] → {item['type']}: {item['ref']}")
        if fix:
            os.makedirs(os.path.dirname(item["target"]), exist_ok=True)
            with open(item["target"], "w", encoding="utf-8") as fh:
                fh.write(_build_stub_content(item["target"], item["source"]))
            print(f"       └─ Fixed: Created missing file -> {item['target']}")


def _print_audit_report(broken_refs, session_notes, untracked_roadmaps, pending_todos, fix):
    """Render the full integrity, session lineage, and pending subtask audit report."""
    print("=" * 60)
    print("  WORKFORCES INTEGRITY & REFERENCE AUDIT REPORT")
    print("=" * 60)
    _print_broken_and_apply_fixes(broken_refs, fix)
    if session_notes:
        print(f"  ✓ Session context lineage active ({len(session_notes)} note(s) in workforces/session-context/)")
    else:
        print("  ⚠️ Session Lineage Warning: No session note found in workforces/session-context/")
        print("     └─ Remember to execute write_to_file to record session context before outputting final response.")
    if untracked_roadmaps:
        print(f"\n  ⚠️ Found {len(untracked_roadmaps)} untracked roadmap/feature item(s) in session context:")
        for item in untracked_roadmaps:
            print(f"     • [{item['source']}]: {item['item']}")
            print(f"       └─ Action: Run report-task.py --title \"{item['item']}\" --type idea --sync-session")
    if pending_todos:
        print(f"\n  📋 Found {len(pending_todos)} pending subtask(s):")
        for item in pending_todos:
            print(f"     • [{item['source']}]: {item['task']}")
    print("=" * 60)


def _audit_single_workspace_file(broken_refs, pending_todos, target_dir, root, file):
    """Read and audit one .md, .mdc, or .json file inside the workspace walk."""
    if not file.endswith((".md", ".mdc", ".json")):
        return
    filepath = os.path.join(root, file)
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return
    rel_source = os.path.relpath(filepath, target_dir)
    if file.endswith(".json"):
        _audit_json_manifest(broken_refs, target_dir, root, file, rel_source, content)
    if file.endswith((".md", ".mdc")):
        _audit_markdown_links_and_todos(broken_refs, pending_todos, target_dir, root, rel_source, content)


def audit_references(target_dir=".", fix=False):
    """Walk target_dir, audit JSON/Markdown/.mdc references & session lineage, and return broken count."""
    target_dir = os.path.abspath(target_dir)
    broken_refs = []
    pending_todos = []
    ignored_dirs = {".git", "node_modules", ".tmp", "scratch", ".worktrees"}
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [
            d for d in dirs
            if d not in ignored_dirs
            and "teamwork_preview_" not in d
            and not is_excluded_runtime_dir(os.path.join(root, d), target_dir)
        ]
        for file in files:
            _audit_single_workspace_file(broken_refs, pending_todos, target_dir, root, file)
    session_notes, untracked_roadmaps = audit_session_context(target_dir)
    _print_audit_report(broken_refs, session_notes, untracked_roadmaps, pending_todos, fix)
    return len(broken_refs)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    fix_flag = "--fix" in sys.argv
    broken_count = audit_references(target, fix=fix_flag)
    if broken_count > 0 and not fix_flag:
        sys.exit(1)
    sys.exit(0)
