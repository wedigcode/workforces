#!/usr/bin/env python3
"""
report-issue — Issue & Feature Idea capture and evolution script for workforce agents.

Usage:
    # 1. Report a new issue/idea linked to a session:
    python3 .agents/skills/issue-tracker/scripts/report-issue.py \
        --title "Adopt soft pastel color palette" \
        --type design \
        --severity P2 \
        --reporter scribe \
        --session-id "022" \
        --session-file "workforces/session-context/022_2026-08-22_topic.md" \
        --file "src/styles/theme.css" \
        --description "Replace bright saturated colors with a soft pastel palette." \
        --suggested-action "Define pastel design tokens in theme.css" \
        --evolution-note "Initial request: switch to pastel tones for softer aesthetic." \
        --sync-session

    # 2. Update an existing issue with evolved decisions / requirements:
    python3 .agents/skills/issue-tracker/scripts/report-issue.py \
        --update "workforces/issues/inbox/20260822-071500-adopt-soft-pastel-color-palette.md" \
        --evolution-note "Pivoted from lavender tones to muted alpine sage for better contrast." \
        --sync-session

    # 3. Check for similar issues before creating:
    python3 .agents/skills/issue-tracker/scripts/report-issue.py \
        --find-similar "pastel color palette"
"""

import argparse
import datetime
import difflib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML-style frontmatter and body from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml = parts[1]
    body = parts[2].lstrip("\r\n")

    metadata: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    current_dict_in_list: Optional[Dict[str, Any]] = None

    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Handle list item start: "- ..."
        if stripped.startswith("- ") and current_list_key:
            item_text = stripped[2:].strip()
            if ":" in item_text:
                # Dict item in list: e.g. "- id: '123'"
                sub_k, sub_v = item_text.split(":", 1)
                sub_k = sub_k.strip()
                sub_v = sub_v.strip().strip('"').strip("'")
                current_dict_in_list = {sub_k: sub_v}
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(current_dict_in_list)
            else:
                # Scalar item in list: e.g. "- src/utils.py"
                current_dict_in_list = None
                val = item_text.strip('"').strip("'")
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(val)
            continue

        # Handle subsequent lines of dict in list: e.g. "  file: '...'"
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
                try:
                    if "." in val:
                        metadata[key] = float(val)
                    else:
                        metadata[key] = int(val)
                except ValueError:
                    metadata[key] = val

    return metadata, body


def dump_frontmatter(metadata: Dict[str, Any], body: str) -> str:
    """Format frontmatter dictionary and markdown body back into string."""
    lines = ["---"]
    for key, val in metadata.items():
        if val is None:
            lines.append(f"{key}: ~")
        elif isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, (int, float)):
            lines.append(f"{key}: {val}")
        elif isinstance(val, list):
            if not val:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in val:
                    if isinstance(item, dict):
                        # Nested dict in list
                        dict_items = list(item.items())
                        if dict_items:
                            first_k, first_v = dict_items[0]
                            lines.append(f"  - {first_k}: \"{first_v}\"")
                            for sub_k, sub_v in dict_items[1:]:
                                lines.append(f"    {sub_k}: \"{sub_v}\"")
                    else:
                        lines.append(f"  - \"{item}\"")
        else:
            # String value
            clean_str = str(val).replace('"', '\\"')
            lines.append(f'{key}: "{clean_str}"')
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


def extract_title(filepath: str) -> str:
    """Pull the `title:` value from a YAML frontmatter block in an issue file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            metadata, _ = parse_frontmatter(f.read())
            return str(metadata.get("title", ""))
    except OSError:
        pass
    return ""


def find_issue_by_identifier(identifier: str, search_dirs: List[str]) -> Optional[str]:
    """Find issue file by exact path, relative path, filename, or partial slug match."""
    # Direct path match
    if os.path.isfile(identifier):
        return os.path.abspath(identifier)

    # Check search dirs
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        direct = os.path.join(d, identifier)
        if os.path.isfile(direct):
            return os.path.abspath(direct)
        if not identifier.endswith(".md"):
            with_ext = direct + ".md"
            if os.path.isfile(with_ext):
                return os.path.abspath(with_ext)

        # Search for slug match in directory
        for fname in os.listdir(d):
            if not fname.endswith(".md"):
                continue
            if identifier.lower() in fname.lower():
                return os.path.abspath(os.path.join(d, fname))
    return None


def find_similar_issues(
    query_title: str, search_dirs: List[str], threshold: float = 0.70
) -> List[Tuple[str, float, Dict[str, Any]]]:
    """
    Return existing issue files whose title or content is similar to query_title.
    Returns list of (filepath, ratio, metadata).
    """
    matches = []
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(directory, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    meta, _ = parse_frontmatter(f.read())
                    title = meta.get("title", "")
                    if not title:
                        continue
                    ratio = difflib.SequenceMatcher(
                        None, query_title.lower(), str(title).lower()
                    ).ratio()
                    if ratio >= threshold or query_title.lower() in str(title).lower():
                        score = max(ratio, 0.85 if query_title.lower() in str(title).lower() else ratio)
                        matches.append((fpath, score, meta))
            except OSError:
                continue
    return sorted(matches, key=lambda x: x[1], reverse=True)


def build_issue_markdown(
    title: str,
    issue_type: str,
    severity: str,
    reporter: str,
    description: str,
    suggested_action: str = "",
    file_path: str = "",
    session_id: str = "",
    session_file: str = "",
    evolution_notes: Optional[List[str]] = None,
    created_at: Optional[datetime.datetime] = None,
    updated_at: Optional[datetime.datetime] = None,
    status: str = "inbox",
    triage_status: str = "pending",
    github_issue: Optional[str] = None,
) -> str:
    """Construct complete issue file markdown with frontmatter and lineage."""
    now = created_at or datetime.datetime.now()
    up_now = updated_at or now

    metadata: Dict[str, Any] = {
        "title": title,
        "type": issue_type,
        "severity": severity,
        "reporter": reporter,
        "reported_at": now.isoformat(),
        "updated_at": up_now.isoformat(),
        "status": status,
        "file": file_path or "",
        "session_id": session_id or None,
        "session_file": session_file or None,
        "triage_status": triage_status,
        "github_issue": github_issue,
    }

    session_origin_link = ""
    if session_file:
        session_origin_link = f"**Origin Session:** [{os.path.basename(session_file)}]({session_file})\n"

    evolution_lines = []
    if evolution_notes:
        for note in evolution_notes:
            evolution_lines.append(f"- {note}")
    else:
        evolution_lines.append(f"- **{now.strftime('%Y-%m-%d %H:%M')}:** Initial formulation: {description[:120]}")

    body = f"""# {title}

**Type:** `{issue_type}` | **Severity:** `{severity}` | **Reporter:** `{reporter}`  
**Reported:** {now.strftime("%Y-%m-%d %H:%M")} | **Updated:** {up_now.strftime("%Y-%m-%d %H:%M")}  
{session_origin_link}{f"**Affected file:** `{file_path}`" if file_path else ""}

## Description

{description}

## Suggested Action

{suggested_action if suggested_action else "_No suggestion provided — PM to determine next step._"}

## 🧠 Session Lineage & Deciding Factors

{chr(10).join(evolution_lines)}

---

## Triage (PM fills in)

- **Decision:** _pending_
- **Assigned to:** _pending_
- **GitHub Issue:** _pending_
- **Notes:** _pending_
"""

    return dump_frontmatter(metadata, body)


def sync_issue_to_session_file(
    session_file_path: str,
    issue_file_path: str,
    issue_meta: Dict[str, Any],
    evolution_summary: str = "",
) -> bool:
    """
    Ensure the session context markdown file lists the issue in frontmatter and body.
    """
    if not os.path.isfile(session_file_path):
        return False

    try:
        with open(session_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        issue_id = os.path.splitext(os.path.basename(issue_file_path))[0]
        title = issue_meta.get("title", issue_id)
        issue_type = issue_meta.get("type", "task")
        severity = issue_meta.get("severity", "P2")
        status = issue_meta.get("status", "inbox")

        # Update or append in frontmatter tracked_issues
        tracked = meta.get("tracked_issues")
        if not isinstance(tracked, list):
            tracked = []

        found = False
        new_tracked = []
        for item in tracked:
            if isinstance(item, dict) and (item.get("id") == issue_id or item.get("file") == issue_file_path):
                found = True
                new_tracked.append({
                    "id": issue_id,
                    "file": issue_file_path,
                    "title": title,
                    "type": issue_type,
                    "severity": severity,
                    "status": status,
                })
            else:
                new_tracked.append(item)

        if not found:
            new_tracked.append({
                "id": issue_id,
                "file": issue_file_path,
                "title": title,
                "type": issue_type,
                "severity": severity,
                "status": status,
            })

        meta["tracked_issues"] = new_tracked
        meta["updated_at"] = datetime.datetime.now().isoformat()

        # Update Markdown Body section: ## 📋 Tracked Issues & Feature Ideas
        section_header = "## 📋 Tracked Issues & Feature Ideas"
        summary_text = evolution_summary or issue_meta.get("description", "")[:100]
        issue_entry = f"- [{title}](file://{os.path.abspath(issue_file_path)}) (`{issue_type}` | {severity}) — {summary_text}"

        if section_header in body:
            # Replace existing entry or append
            parts = body.split(section_header, 1)
            before_sec = parts[0] + section_header + "\n"
            after_sec = parts[1]

            # Find next header ## or end
            next_header = re.search(r"\n##\s+", after_sec)
            if next_header:
                sec_content = after_sec[:next_header.start()]
                rest = after_sec[next_header.start():]
            else:
                sec_content = after_sec
                rest = ""

            # Check if this issue is already in sec_content
            lines = [l for l in sec_content.splitlines() if l.strip()]
            new_lines = []
            replaced = False
            for l in lines:
                if issue_id in l or title in l:
                    new_lines.append(issue_entry)
                    replaced = True
                else:
                    new_lines.append(l)
            if not replaced:
                new_lines.append(issue_entry)

            updated_sec = "\n" + "\n".join(new_lines) + "\n"
            body = before_sec + updated_sec + rest
        else:
            # Append before ## Key Files or at bottom
            insert_marker = "## 📁 Key Files & Code Symbols"
            if insert_marker in body:
                body = body.replace(
                    insert_marker,
                    f"{section_header}\n{issue_entry}\n\n{insert_marker}"
                )
            else:
                body = body.rstrip() + f"\n\n{section_header}\n{issue_entry}\n"

        new_content = dump_frontmatter(meta, body)
        with open(session_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"⚠️ Failed to sync issue to session file {session_file_path}: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report, update, and evolve deferred issues and feature ideas for workforce agents."
    )
    parser.add_argument("--title", help="Short issue/feature title")
    parser.add_argument(
        "--type", default="bug",
        choices=["bug", "debt", "design", "refactor", "security", "idea"],
        help="Issue type",
    )
    parser.add_argument(
        "--severity", default="P2",
        choices=["P0", "P1", "P2", "P3"],
        help="Severity/priority estimate",
    )
    parser.add_argument("--reporter", default="scribe", help="Agent or workflow that logged the issue")
    parser.add_argument("--file", default="", help="Affected file path (optional)")
    parser.add_argument("--description", default="", help="Full description of the issue or feature")
    parser.add_argument("--suggested-action", default="", help="Recommended fix, next step, or implementation spec")
    parser.add_argument("--session-id", default="", help="Associated session sequence ID (e.g. '022')")
    parser.add_argument("--session-file", default="", help="Path to session context markdown note")
    parser.add_argument(
        "--evolution-note",
        help="Decision note explaining requirement evolution, trade-offs, or changes discussed mid-session",
    )
    parser.add_argument(
        "--update",
        help="File path or ID/slug of an existing issue to update with new requirements or evolution notes",
    )
    parser.add_argument(
        "--find-similar",
        help="Search for existing issues similar to the given title string",
    )
    parser.add_argument(
        "--sync-session", action="store_true",
        help="Sync tracked issue metadata back into the active session context file",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--out-dir", default="workforces/issues/inbox",
        help="Output directory for new issue files",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip duplicate check and write regardless",
    )

    args = parser.parse_args()

    inbox_dir = args.out_dir
    triaged_dir = os.path.join(os.path.dirname(inbox_dir), "triaged")

    # MODE 1: Find Similar Issues
    if args.find_similar:
        results = find_similar_issues(args.find_similar, [inbox_dir, triaged_dir])
        if args.json:
            output = [
                {
                    "path": fpath,
                    "similarity": round(ratio, 2),
                    "title": meta.get("title", ""),
                    "type": meta.get("type", ""),
                    "severity": meta.get("severity", ""),
                    "session_id": meta.get("session_id"),
                }
                for fpath, ratio, meta in results
            ]
            print(json.dumps(output, indent=2))
        else:
            if not results:
                print(f"No similar issues found for '{args.find_similar}'.")
            else:
                print(f"🔍 Found {len(results)} matching issue(s):")
                for fpath, ratio, meta in results:
                    loc = "inbox" if inbox_dir in fpath else "triaged"
                    print(f"  - [{ratio:.0%}] ({loc}) {meta.get('title', '')}")
                    print(f"    Path: {fpath}")
                    if meta.get("session_id"):
                        print(f"    Session: #{meta.get('session_id')}")
        return

    # MODE 2: Update Existing Issue
    if args.update:
        target_file = find_issue_by_identifier(args.update, [inbox_dir, triaged_dir])
        if not target_file:
            print(f"❌ Error: Could not locate issue matching '{args.update}'", file=sys.stderr)
            sys.exit(1)

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        now = datetime.datetime.now()

        # Update metadata fields if explicitly provided
        if args.title:
            meta["title"] = args.title
        if args.type and args.type != "bug":
            meta["type"] = args.type
        if args.severity and args.severity != "P2":
            meta["severity"] = args.severity
        if args.reporter and args.reporter != "scribe":
            meta["reporter"] = args.reporter
        if args.file:
            meta["file"] = args.file
        if args.session_id:
            meta["session_id"] = args.session_id
        if args.session_file:
            meta["session_file"] = args.session_file
        meta["updated_at"] = now.isoformat()

        # Update description / suggested action in body if provided
        if args.description:
            desc_match = re.search(r"## Description\s*\n\n(.*?)(?=\n\n##|\Z)", body, re.DOTALL)
            if desc_match:
                body = body[:desc_match.start(1)] + args.description + body[desc_match.end(1):]

        if args.suggested_action:
            act_match = re.search(r"## Suggested Action\s*\n\n(.*?)(?=\n\n##|\Z)", body, re.DOTALL)
            if act_match:
                body = body[:act_match.start(1)] + args.suggested_action + body[act_match.end(1):]

        # Append evolution note if provided
        if args.evolution_note:
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** {args.evolution_note}"
            evo_header = "## 🧠 Session Lineage & Deciding Factors"
            if evo_header in body:
                parts = body.split(evo_header, 1)
                before = parts[0] + evo_header + "\n\n"
                after = parts[1].lstrip("\r\n")
                # Insert at top of list
                body = before + evo_entry + "\n" + after
            else:
                # Add section before ## Triage or at end
                if "## Triage" in body:
                    body = body.replace("## Triage", f"{evo_header}\n\n{evo_entry}\n\n---\n\n## Triage")
                else:
                    body = body.rstrip() + f"\n\n{evo_header}\n\n{evo_entry}\n"

        # Write updated content
        new_content = dump_frontmatter(meta, body)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Issue updated: {target_file}")

        # Sync back to session file if requested
        session_file = args.session_file or meta.get("session_file")
        if (args.sync_session or session_file) and session_file:
            sync_issue_to_session_file(
                session_file,
                target_file,
                meta,
                evolution_summary=args.evolution_note or "Updated requirements & decision factors"
            )
            print(f"🔗 Synced to session context: {session_file}")

        return

    # MODE 3: Create New Issue
    if not args.title or not args.description:
        print("❌ Error: --title and --description are required to report a new issue.", file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        sys.exit(1)

    # Check for duplicates unless --force
    if not args.force:
        similar = find_similar_issues(args.title, [inbox_dir, triaged_dir], threshold=0.75)
        if similar:
            print("⚠️  Similar issue(s) already exist — skipping to avoid duplicates:\n")
            for fpath, ratio, meta in similar:
                loc = "inbox" if inbox_dir in fpath else "triaged"
                print(f"   [{ratio:.0%} match] ({loc}) {meta.get('title', extract_title(fpath))}")
                print(f"   → {fpath}\n")
            print("💡 Options:")
            print(f"   - Update existing: python3 {sys.argv[0]} --update \"{similar[0][0]}\" --evolution-note \"...\"")
            print("   - Force create anyway: re-run with --force")
            sys.exit(1)

    os.makedirs(inbox_dir, exist_ok=True)
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)
    filename = f"{timestamp}-{slug}.md"
    filepath = os.path.join(inbox_dir, filename)

    evolution_notes = []
    if args.evolution_note:
        evolution_notes.append(f"**{now.strftime('%Y-%m-%d %H:%M')}:** {args.evolution_note}")

    content = build_issue_markdown(
        title=args.title,
        issue_type=args.type,
        severity=args.severity,
        reporter=args.reporter,
        description=args.description,
        suggested_action=args.suggested_action,
        file_path=args.file,
        session_id=args.session_id,
        session_file=args.session_file,
        evolution_notes=evolution_notes,
        created_at=now,
        updated_at=now,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Issue reported: {filepath}")

    if args.sync_session and args.session_file:
        meta_dict = {
            "title": args.title,
            "type": args.type,
            "severity": args.severity,
            "status": "inbox",
            "description": args.description,
        }
        sync_issue_to_session_file(
            args.session_file,
            filepath,
            meta_dict,
            evolution_summary=args.evolution_note or args.description[:100]
        )
        print(f"🔗 Synced to session context: {args.session_file}")


if __name__ == "__main__":
    main()
