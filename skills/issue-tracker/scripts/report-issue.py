#!/usr/bin/env python3
"""
report-issue — Lightweight issue capture script for workforce agents.

Usage:
    python3 .agents/skills/issue-tracker/scripts/report-issue.py \
        --title "Dead code in utils.py" \
        --type bug \
        --severity P2 \
        --reporter clean-coder \
        --file src/utils.py \
        --description "Found unreachable function calculate_legacy_tax() at line 47." \
        --suggested-action "Remove calculate_legacy_tax() and its test stub."

Arguments:
    --title           Short title (required)
    --type            bug | debt | design | refactor | security | idea (default: bug)
    --severity        P0 | P1 | P2 | P3 (default: P2)
    --reporter        Name of the agent/workflow that found it (default: unknown)
    --file            Affected file path (optional)
    --description     Full description of the issue (required)
    --suggested-action  What should be done to fix it (optional)
    --out-dir         Path to inbox dir (default: workforces/issues/inbox)
    --force           Skip duplicate check and write regardless

Output:
    Writes a YAML-frontmatter markdown file to the inbox.
    Exits with a warning (code 1) if a similar issue already exists.
    Prints the file path on success.
"""

import argparse
import datetime
import difflib
import os
import re


def slugify(text: str) -> str:
    """Convert title to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def extract_title(filepath: str) -> str:
    """Pull the `title:` value from a YAML frontmatter block in an issue file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            in_frontmatter = False
            for line in f:
                line = line.rstrip()
                if line == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter and line.startswith("title:"):
                    # Strip quotes: title: "My Issue" or title: My Issue
                    return line.split("title:", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def find_similar_issues(
    new_title: str, search_dirs: list, threshold: float = 0.80
) -> list:
    """
    Return existing issue files whose title is >= threshold similar to new_title.
    Uses SequenceMatcher ratio on lowercased titles.
    """
    matches = []
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(directory, fname)
            existing_title = extract_title(fpath)
            if not existing_title:
                continue
            ratio = difflib.SequenceMatcher(
                None, new_title.lower(), existing_title.lower()
            ).ratio()
            if ratio >= threshold:
                matches.append((fpath, ratio))
    # Highest similarity first.
    return sorted(matches, key=lambda x: x[1], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report a deferred issue to the workforce inbox.")
    parser.add_argument("--title", required=True, help="Short issue title")
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
    parser.add_argument("--reporter", default="unknown", help="Agent or workflow that found the issue")
    parser.add_argument("--file", default="", help="Affected file path (optional)")
    parser.add_argument("--description", required=True, help="Full description of the issue")
    parser.add_argument("--suggested-action", default="", help="Recommended fix or next step")
    parser.add_argument(
        "--out-dir", default="workforces/issues/inbox",
        help="Output directory for issue files",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip duplicate check and write regardless",
    )

    args = parser.parse_args()

    inbox_dir = args.out_dir
    # Resolve sibling triaged/ dir relative to the inbox dir.
    triaged_dir = os.path.join(os.path.dirname(inbox_dir), "triaged")

    # Duplicate check — scan both inbox and triaged dirs before writing.
    if not args.force:
        similar = find_similar_issues(args.title, [inbox_dir, triaged_dir])
        if similar:
            print("⚠️  Similar issue(s) already exist — skipping to avoid duplicates:\n")
            for fpath, ratio in similar:
                existing_title = extract_title(fpath)
                location = "inbox" if inbox_dir in fpath else "triaged"
                print(f"   [{ratio:.0%} match] ({location}) {existing_title}")
                print(f"   → {fpath}\n")
            print("If this is genuinely different, re-run with --force to write anyway.")
            raise SystemExit(1)

    # Ensure output directory exists.
    os.makedirs(inbox_dir, exist_ok=True)

    # Build unique filename: YYYYMMDD-HHMMSS-<slug>.md
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)
    filename = f"{timestamp}-{slug}.md"
    filepath = os.path.join(inbox_dir, filename)

    content = f"""---
title: "{args.title}"
type: {args.type}
severity: {args.severity}
reporter: {args.reporter}
reported_at: {now.isoformat()}
status: inbox
file: "{args.file}"
triage_status: pending
github_issue: ~
---

# {args.title}

**Type:** `{args.type}` | **Severity:** `{args.severity}` | **Reporter:** `{args.reporter}`
**Reported:** {now.strftime("%Y-%m-%d %H:%M")}
{f"**Affected file:** `{args.file}`" if args.file else ""}

## Description

{args.description}

## Suggested Action

{args.suggested_action if args.suggested_action else "_No suggestion provided — PM to determine next step._"}

---

## Triage (PM fills in)

- **Decision:** _pending_
- **Assigned to:** _pending_
- **GitHub Issue:** _pending_
- **Notes:** _pending_
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Issue reported: {filepath}")


if __name__ == "__main__":
    main()
