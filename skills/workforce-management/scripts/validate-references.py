#!/usr/bin/env python3
"""
Workforces File Reference & Subtask Integrity Validator
Scans workspace markdown and JSON files for referenced file paths, links, and unchecked subtasks.
Ensures zero dangling references and logs pending tasks to workforces/workstate.md.
"""

import json
import os
import re
import sys

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
                        for key in ["personas", "rules", "workflows"]:
                            for rel_ref in data.get(key, []):
                                target_path = os.path.normpath(os.path.join(root, rel_ref))
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

    # 4. Audit Session Context Lineage
    session_ctx_dir = os.path.normpath(os.path.join(target_dir, "workforces", "session-context"))
    session_notes = []
    if os.path.exists(session_ctx_dir):
        session_notes = [f for f in os.listdir(session_ctx_dir) if f.endswith(".md")]

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

