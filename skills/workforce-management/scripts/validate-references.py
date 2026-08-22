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

    session_notes = []
    untracked_roadmaps = []

    if not os.path.exists(session_ctx_dir):
        return session_notes, untracked_roadmaps

    inbox_files = os.listdir(inbox_dir) if os.path.exists(inbox_dir) else []
    triaged_files = os.listdir(triaged_dir) if os.path.exists(triaged_dir) else []
    known_issue_slugs = [f.lower().replace(".md", "") for f in (inbox_files + triaged_files)]

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
        tracked_issues = meta.get("tracked_issues") or []
        tracked_strings = []
        for item in tracked_issues:
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


def audit_references(target_dir=".", fix=False):
    target_dir = os.path.abspath(target_dir)
    broken_refs = []
    pending_todos = []

    ignored_dirs = {".git", "node_modules", ".tmp", "scratch"}

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for file in files:
            if not file.endswith((".md", ".json")):
                continue

            filepath = os.path.join(root, file)
            rel_source = os.path.relpath(filepath, target_dir)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            # 1. Audit JSON Manifest References
            if file.endswith(".json"):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        for key in ["personas", "rules", "workflows", "agents", "skills"]:
                            for rel_ref in data.get(key, []):
                                target_path = os.path.normpath(os.path.join(root, rel_ref))
                                if not os.path.exists(target_path):
                                    # Fallback: check standard directory in target_dir (e.g. rules/, workflows/, agents/, skills/)
                                    candidates = [
                                        os.path.normpath(os.path.join(target_dir, key, rel_ref)),
                                        os.path.normpath(os.path.join(target_dir, key, rel_ref + ".md")),
                                        os.path.normpath(os.path.join(target_dir, rel_ref)),
                                        os.path.normpath(os.path.join(target_dir, rel_ref + ".md")),
                                        os.path.normpath(os.path.join(root, rel_ref + ".md"))
                                    ]
                                    if rel_ref.endswith(".md"):
                                        candidates.append(os.path.normpath(os.path.join(target_dir, key, rel_ref[:-3])))
                                    for c in candidates:
                                        if os.path.exists(c):
                                            target_path = c
                                            break
                                if not os.path.exists(target_path):
                                    broken_refs.append({
                                        "source": rel_source,
                                        "type": f"JSON {key}",
                                        "ref": rel_ref,
                                        "target": target_path
                                    })
                except Exception:
                    pass

            # 2. Audit Markdown Links & Explicit File Paths
            if file.endswith(".md"):
                # Match [text](path) or [text](file://...)
                matches = re.findall(r"\[([^\]]+)\]\((file://[^\s\)]+|[^\s\)]+)\)", content)
                for text, raw_link in matches:
                    if raw_link.startswith("http://") or raw_link.startswith("https://") or raw_link.startswith("#"):
                        continue
                    # Ignore placeholder docs example links
                    if "example" in raw_link or "path/to" in raw_link or "modifiedfile" in raw_link:
                        continue

                    clean_link = raw_link.replace("file://", "").split("#")[0]
                    if not clean_link:
                        continue

                    if clean_link.startswith("/"):
                        target_path = clean_link
                    else:
                        target_path = os.path.normpath(os.path.join(root, clean_link))

                    if not os.path.exists(target_path):
                        # Fallback: check relative to workspace root (e.g. for files copied under .agents/)
                        root_rel_path = os.path.normpath(os.path.join(target_dir, clean_link.replace("../", "")))
                        if os.path.exists(root_rel_path):
                            target_path = root_rel_path

                    if not os.path.exists(target_path):
                        broken_refs.append({
                            "source": rel_source,
                            "type": "Markdown Link",
                            "ref": raw_link,
                            "target": target_path
                        })

                # 3. Extract Unchecked TODO Tasks (- [ ])
                todos = re.findall(r"^\s*-\s*\[\s*\]\s+(.+)$", content, re.MULTILINE)
                for todo in todos:
                    pending_todos.append({
                        "source": rel_source,
                        "task": todo.strip()
                    })

    # 4. Audit Session Context Lineage & Roadmaps
    session_notes, untracked_roadmaps = audit_session_context(target_dir)

    # Print Audit Report
    print("=" * 60)
    print("  WORKFORCES INTEGRITY & REFERENCE AUDIT REPORT")
    print("=" * 60)

    if not broken_refs:
        print("  ✓ Zero dangling file references found!")
    else:
        print(f"  ❌ Found {len(broken_refs)} dangling file reference(s):")
        for item in broken_refs:
            print(f"     • [{item['source']}] → {item['type']}: {item['ref']}")
            if fix:
                os.makedirs(os.path.dirname(item['target']), exist_ok=True)
                filename = os.path.basename(item['target'])
                title = filename.replace(".md", "").replace("-", " ").title()
                header_type = "File"
                if "personas" in item['target']:
                    header_type = "Persona"
                elif "rules" in item['target']:
                    header_type = "Rule"
                elif "workflows" in item['target']:
                    header_type = "Workflow"

                stub_content = f"# {header_type}: {title}\n\nGenerated dependency for `{item['source']}`.\n\n## Overview\nAuto-created by integrity audit to fulfill reference dependency.\n"
                with open(item['target'], "w", encoding="utf-8") as f:
                    f.write(stub_content)
                print(f"       └─ Fixed: Created missing file -> {item['target']}")

    if session_notes:
        print(f"  ✓ Session context lineage active ({len(session_notes)} note(s) in workforces/session-context/)")
    else:
        print("  ⚠️ Session Lineage Warning: No session note found in workforces/session-context/")
        print("     └─ Remember to execute write_to_file to record session context before outputting final response.")

    if untracked_roadmaps:
        print(f"\n  ⚠️ Found {len(untracked_roadmaps)} untracked roadmap/feature item(s) in session context:")
        for item in untracked_roadmaps:
            print(f"     • [{item['source']}]: {item['item']}")
            print(f"       └─ Action: Run report-issue.py --title \"{item['item']}\" --type idea --sync-session")

    if pending_todos:
        print(f"\n  📋 Found {len(pending_todos)} pending subtask(s):")
        for item in pending_todos:
            print(f"     • [{item['source']}]: {item['task']}")

    print("=" * 60)
    return len(broken_refs)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    fix_flag = "--fix" in sys.argv
    broken_count = audit_references(target, fix=fix_flag)
    if broken_count > 0 and not fix_flag:
        sys.exit(1)
    sys.exit(0)
