#!/usr/bin/env python3
"""
hypothesis.py — Scientific Hypothesis & Experiment Tracker for workforce agents.

Manages business, growth, marketing, sales, and product experiments. Tracks hypotheses
against strategic goals, monitors leading vs. lagging KPIs, calculates weekly pacing,
and enforces kill/pivot criteria.

Usage:
    # 1. Create a new hypothesis:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py \
        --create \
        --title "Cold Outreach Video Teasers for Tech Founders" \
        --owner sales \
        --supporting-teams marketing growth \
        --goal-id "Q1-KR2" \
        --goal-title "Acquire 25 pilot enterprise customers" \
        --statement "We believe that sending personalized 30s Loom audits to Series A CTOs will achieve a 12% reply rate and 8 demo bookings within 3 weeks." \
        --timeframe-weeks 3 \
        --kill-threshold "Reply rate < 3% after 100 sends" \
        --pivot-plan "Kill campaign and revert to plain-text problem-first cadences" \
        --metrics '[{"name":"Sends","type":"leading","baseline":0,"target":100,"current":0,"unit":"count"},{"name":"Reply Rate","type":"leading","baseline":1.5,"target":12.0,"current":1.5,"unit":"%"},{"name":"Demo Bookings","type":"lagging","baseline":0,"target":8,"current":0,"unit":"count"}]' \
        --session-id "024" \
        --session-file "workforces/session-context/024_2026-08-23_topic.md" \
        --sync-session

    # 2. Update progress / weekly pacing / telemetry:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py \
        --update "workforces/hypotheses/running/HYP-20260823-01.md" \
        --current-week 2 \
        --metrics-data "Sends=65,Reply Rate=8.2,Demo Bookings=4" \
        --insight "CTOs who responded noted they skipped video and read first 2 lines. Shortening text for batch 3." \
        --sync-session

    # 3. List active hypotheses with pacing:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py --list --status running

    # 4. Generate structured review for /sync --strategy:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py --review

    # 5. Enforce Kill / Sunset:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py \
        --kill "workforces/hypotheses/running/HYP-20260823-01.md" \
        --rationale "Reply rate plateaued at 2.1% after 120 sends. Kill threshold reached." \
        --sync-session

    # 6. Enforce Pivot:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py \
        --pivot "workforces/hypotheses/running/HYP-20260823-01.md" \
        --rationale "Pivoted from video audits to interactive ROI calculator widget based on prospect feedback." \
        --sync-session

    # 7. Validate & Scale:
    python3 skills/hypothesis-tracker/scripts/hypothesis.py \
        --validate "workforces/hypotheses/running/HYP-20260823-01.md" \
        --rationale "Target exceeded: 14% reply rate and 10 bookings in 3 weeks. Scaling budget." \
        --sync-session
"""

import argparse
import datetime
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
    return text[:50]


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown."""
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

        # Handle list items
        if stripped.startswith("- ") and current_list_key:
            item_text = stripped[2:].strip()
            if ":" in item_text:
                sub_k, sub_v = item_text.split(":", 1)
                sub_k = sub_k.strip()
                sub_v = sub_v.strip().strip('"').strip("'")
                # Try number conversion
                sub_val: Any = sub_v
                try:
                    if "." in sub_v:
                        sub_val = float(sub_v)
                    else:
                        sub_val = int(sub_v)
                except ValueError:
                    pass
                current_dict_in_list = {sub_k: sub_val}
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

        # Handle dict inside list attributes
        if (line.startswith("  ") or line.startswith("\t")) and current_dict_in_list is not None and ":" in line:
            sub_k, sub_v = stripped.split(":", 1)
            sub_k = sub_k.strip()
            sub_v = sub_v.strip().strip('"').strip("'")
            sub_val = sub_v
            try:
                if "." in sub_v:
                    sub_val = float(sub_v)
                else:
                    sub_val = int(sub_v)
            except ValueError:
                pass
            current_dict_in_list[sub_k] = sub_val
            continue

        # Handle top-level keys
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            current_dict_in_list = None
            if not v:
                current_list_key = k
                metadata[k] = []
            else:
                current_list_key = None
                clean_v = v.strip('"').strip("'")
                if clean_v.lower() == "true":
                    metadata[k] = True
                elif clean_v.lower() == "false":
                    metadata[k] = False
                elif clean_v.lower() in ("null", "~", "none"):
                    metadata[k] = None
                else:
                    try:
                        if "." in clean_v:
                            metadata[k] = float(clean_v)
                        else:
                            metadata[k] = int(clean_v)
                    except ValueError:
                        metadata[k] = clean_v

    return metadata, body


def serialize_frontmatter(metadata: Dict[str, Any]) -> str:
    """Serialize dictionary to clean YAML frontmatter."""
    lines = ["---"]
    for k, v in metadata.items():
        if v is None:
            lines.append(f"{k}: ~")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                if isinstance(item, dict):
                    first = True
                    for sub_k, sub_v in item.items():
                        if first:
                            if isinstance(sub_v, (int, float)):
                                lines.append(f"  - {sub_k}: {sub_v}")
                            elif isinstance(sub_v, bool):
                                lines.append(f"  - {sub_k}: {str(sub_v).lower()}")
                            elif sub_v is None:
                                lines.append(f"  - {sub_k}: ~")
                            else:
                                lines.append(f"  - {sub_k}: \"{sub_v}\"")
                            first = False
                        else:
                            if isinstance(sub_v, (int, float)):
                                lines.append(f"    {sub_k}: {sub_v}")
                            elif isinstance(sub_v, bool):
                                lines.append(f"    {sub_k}: {str(sub_v).lower()}")
                            elif sub_v is None:
                                lines.append(f"    {sub_k}: ~")
                            else:
                                lines.append(f"    {sub_k}: \"{sub_v}\"")
                else:
                    lines.append(f"  - \"{item}\"")
        else:
            str_v = str(v).replace('"', '\\"')
            lines.append(f"{k}: \"{str_v}\"")
    lines.append("---")
    return "\n".join(lines)


def find_workspace_root(start_dir: Optional[str] = None) -> str:
    """Find workforce project root directory containing workforces/."""
    current = os.path.abspath(start_dir or os.getcwd())
    while current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, "workforces")):
            return current
        if os.path.isfile(os.path.join(current, "workrules.md")):
            return current
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        current = os.path.dirname(current)
    return os.path.abspath(start_dir or os.getcwd())


def ensure_hypothesis_directories(root_dir: str) -> Dict[str, str]:
    """Ensure all hypothesis subdirectories exist."""
    base = os.path.join(root_dir, "workforces", "hypotheses")
    dirs = {
        "base": base,
        "draft": os.path.join(base, "draft"),
        "running": os.path.join(base, "running"),
        "validated": os.path.join(base, "validated"),
        "invalidated": os.path.join(base, "invalidated"),
        "pivoted": os.path.join(base, "pivoted"),
    }
    for p in dirs.values():
        os.makedirs(p, exist_ok=True)
    return dirs


def calculate_metric_pacing(
    baseline: float, target: float, current: float, current_week: int, timeframe_weeks: int
) -> Tuple[float, str, str]:
    """Calculate progress %, pacing status, and visual badge."""
    delta_total = target - baseline
    if delta_total == 0:
        progress_pct = 100.0 if current >= target else 0.0
    else:
        progress_pct = ((current - baseline) / delta_total) * 100.0

    timeframe_weeks = max(1, timeframe_weeks)
    expected_pct = (current_week / timeframe_weeks) * 100.0

    if progress_pct >= expected_pct * 0.9:
        pacing = "on_track"
        badge = "🟢 On Track"
    elif progress_pct >= expected_pct * 0.6:
        pacing = "at_risk"
        badge = "🟡 At Risk"
    else:
        if current_week >= timeframe_weeks:
            pacing = "kill_recommended"
            badge = "💀 Target Missed (Kill / Pivot)"
        else:
            pacing = "off_track"
            badge = "🔴 Off Track"

    return progress_pct, pacing, badge


def format_metrics_table(metrics: List[Dict[str, Any]], current_week: int, timeframe_weeks: int) -> str:
    """Format markdown metrics telemetry table."""
    rows = []
    for m in metrics:
        name = m.get("name", "Metric")
        m_type = str(m.get("type", "leading")).capitalize()
        baseline = float(m.get("baseline", 0))
        target = float(m.get("target", 0))
        current = float(m.get("current", 0))
        unit = m.get("unit", "")

        prog_pct, _, badge = calculate_metric_pacing(baseline, target, current, current_week, timeframe_weeks)

        b_str = f"{baseline:g}{unit}" if unit == "%" else f"{baseline:g} {unit}".strip()
        t_str = f"{target:g}{unit}" if unit == "%" else f"{target:g} {unit}".strip()
        c_str = f"{current:g}{unit}" if unit == "%" else f"{current:g} {unit}".strip()

        rows.append(f"| {name} | {m_type} | {b_str} | {t_str} | {c_str} | {prog_pct:.1f}% | {badge} |")

    return "\n".join(rows) if rows else "| No metrics defined | — | — | — | — | — | — |"


def generate_next_hypothesis_id(root_dir: str) -> str:
    """Generate sequential hypothesis ID like HYP-20260823-01."""
    today_str = datetime.date.today().strftime("%Y%m%d")
    base_dir = os.path.join(root_dir, "workforces", "hypotheses")

    existing_files: List[str] = []
    if os.path.exists(base_dir):
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.startswith(f"HYP-{today_str}-") and f.endswith(".md"):
                    existing_files.append(f)

    next_seq = len(existing_files) + 1
    return f"HYP-{today_str}-{next_seq:02d}"


def create_hypothesis(args: argparse.Namespace, root_dir: str) -> str:
    """Create a new hypothesis file and store in workforces/hypotheses/."""
    dirs = ensure_hypothesis_directories(root_dir)

    hyp_id = args.id or generate_next_hypothesis_id(root_dir)
    title = args.title.strip()
    status = args.status or "running"
    owner = args.owner.lstrip("@").strip()
    supporting = [t.lstrip("@").strip() for t in (args.supporting_teams or [])]

    now = datetime.datetime.now().isoformat()
    now_short = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    timeframe_weeks = max(1, int(args.timeframe_weeks or 3))
    current_week = max(1, int(args.current_week or 1))

    target_date = (datetime.date.today() + datetime.timedelta(weeks=timeframe_weeks)).strftime("%Y-%m-%d")

    # Parse metrics
    metrics_list: List[Dict[str, Any]] = []
    if args.metrics:
        try:
            metrics_list = json.loads(args.metrics)
        except Exception:
            # Fallback parse comma separated format: Name:target:unit
            for part in args.metrics.split(","):
                part = part.strip()
                if ":" in part:
                    p_items = part.split(":")
                    metrics_list.append({
                        "name": p_items[0],
                        "type": "leading",
                        "baseline": 0,
                        "target": float(p_items[1]) if len(p_items) > 1 else 100,
                        "current": float(p_items[2]) if len(p_items) > 2 else 0,
                        "unit": p_items[3] if len(p_items) > 3 else "count",
                        "pacing": "on_track"
                    })

    if not metrics_list:
        metrics_list = [
            {"name": "Primary Outcome", "type": "leading", "baseline": 0, "target": 100, "current": 0, "unit": "%", "pacing": "on_track"}
        ]

    # Calculate initial pacing
    for m in metrics_list:
        _, p_status, _ = calculate_metric_pacing(
            float(m.get("baseline", 0)),
            float(m.get("target", 0)),
            float(m.get("current", 0)),
            current_week,
            timeframe_weeks
        )
        m["pacing"] = p_status

    session_id = args.session_id or ""
    session_file = args.session_file or ""
    session_file_basename = os.path.basename(session_file) if session_file else "session"
    session_file_link = f"file://{os.path.abspath(session_file)}" if session_file else "#"

    metadata: Dict[str, Any] = {
        "id": hyp_id,
        "title": title,
        "status": status,
        "owner": owner,
        "supporting_teams": supporting,
        "goal_id": args.goal_id or "OKR-GEN",
        "goal_title": args.goal_title or "General Objective",
        "timeframe_weeks": timeframe_weeks,
        "current_week": current_week,
        "started_at": now,
        "updated_at": now,
        "target_completion": target_date,
        "session_id": session_id,
        "session_file": session_file,
        "kill_threshold": args.kill_threshold or "Target achievement < 20% by end of timeframe",
        "pivot_plan": args.pivot_plan or "Evaluate alternative hypothesis and reallocate resources",
        "metrics": metrics_list,
    }

    metrics_table = format_metrics_table(metrics_list, current_week, timeframe_weeks)

    statement = args.statement or f"We believe that executing '{title}' will achieve our key target metrics within {timeframe_weeks} weeks."

    body = f"""
# {hyp_id}: {title}

**Owner:** `@{owner}` | **Status:** `{status}` (Week {current_week} of {timeframe_weeks})  
**Related Goal:** `{metadata['goal_id']}` — {metadata['goal_title']}  
**Timeframe:** {timeframe_weeks} weeks (Target: {target_date})  
**Origin Session:** [{session_file_basename}]({session_file_link})

---

## 🔬 Scientific Hypothesis Statement

> {statement}

---

## 📊 Progress & Pacing Telemetry

| Metric | Type | Baseline | Target | Current | Progress | Pacing |
|:---|:---|:---|:---|:---|:---|:---|
{metrics_table}

---

## 🛑 Kill Criteria & Pivot Contingency

- **Kill Threshold:** {metadata['kill_threshold']}
- **Contingency / Pivot Plan:** {metadata['pivot_plan']}

---

## 💡 Emerging Insights, Adjustments & Decisions

- **{now_short}:** Hypothesis initialized and launched as `{status}`.
"""

    frontmatter = serialize_frontmatter(metadata)
    full_content = f"{frontmatter}\n{body.lstrip()}"

    target_sub = dirs.get(status, dirs["running"])
    filename = f"{hyp_id}_{slugify(title)}.md"
    file_path = os.path.join(target_sub, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"✅ Created hypothesis {hyp_id} at {file_path}")

    if args.sync_session and session_file:
        sync_session_context(root_dir, session_file, hyp_id, title, status, "created", f"Launched hypothesis `{hyp_id}`: {title}")

    return file_path


def find_hypothesis_file(root_dir: str, identifier: str) -> Optional[str]:
    """Find hypothesis file by path, ID (HYP-...), or slug."""
    if os.path.isfile(identifier):
        return os.path.abspath(identifier)

    base = os.path.join(root_dir, "workforces", "hypotheses")
    if not os.path.exists(base):
        return None

    for root, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".md"):
                continue
            if identifier in f or f == identifier or f.startswith(identifier):
                return os.path.join(root, f)

    return None


def update_hypothesis(args: argparse.Namespace, root_dir: str) -> Optional[str]:
    """Update hypothesis metrics, pacing, decision log, or status."""
    file_path = find_hypothesis_file(root_dir, args.update or args.file)
    if not file_path or not os.path.exists(file_path):
        print(f"❌ Error: Hypothesis file not found for '{args.update or args.file}'", file=sys.stderr)
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    metadata, body = parse_frontmatter(content)
    if not metadata:
        print(f"❌ Error: Failed to parse frontmatter in {file_path}", file=sys.stderr)
        return None

    dirs = ensure_hypothesis_directories(root_dir)
    now_short = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    metadata["updated_at"] = datetime.datetime.now().isoformat()

    # Update current week if provided
    if args.current_week is not None:
        metadata["current_week"] = int(args.current_week)

    timeframe_weeks = int(metadata.get("timeframe_weeks", 3))
    current_week = int(metadata.get("current_week", 1))

    # Update metrics if provided
    metrics = metadata.get("metrics", [])
    if args.metrics_data:
        # e.g. "Sends=65,Reply Rate=8.2,Demo Bookings=4"
        updates: Dict[str, float] = {}
        for pair in args.metrics_data.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                try:
                    updates[k.strip().lower()] = float(v.strip())
                except ValueError:
                    pass

        for m in metrics:
            m_name_lower = str(m.get("name", "")).lower()
            if m_name_lower in updates:
                m["current"] = updates[m_name_lower]

    # Recalculate pacing
    for m in metrics:
        _, p_status, _ = calculate_metric_pacing(
            float(m.get("baseline", 0)),
            float(m.get("target", 0)),
            float(m.get("current", 0)),
            current_week,
            timeframe_weeks
        )
        m["pacing"] = p_status
    metadata["metrics"] = metrics

    # Append decision/insight note
    decision_notes = []
    if args.insight:
        decision_notes.append(f"- **{now_short} (Week {current_week}):** {args.insight.strip()}")
    if args.rationale:
        decision_notes.append(f"- **{now_short} (Decision):** {args.rationale.strip()}")

    # Handle status change
    old_status = metadata.get("status", "running")
    new_status = args.status or old_status
    if args.kill:
        new_status = "invalidated"
        if not args.rationale:
            decision_notes.append(f"- **{now_short} (Killed):** Experiment invalidated and stopped per kill criteria.")
    elif args.pivot:
        new_status = "pivoted"
        if not args.rationale:
            decision_notes.append(f"- **{now_short} (Pivoted):** Experiment pivoted to contingency approach.")
    elif args.validate:
        new_status = "validated"
        if not args.rationale:
            decision_notes.append(f"- **{now_short} (Validated):** Experiment targets achieved. Recommended for scale.")

    metadata["status"] = new_status

    # Re-render body table
    metrics_table = format_metrics_table(metrics, current_week, timeframe_weeks)

    # Replace telemetry table in body
    table_pattern = r"(\| Metric \| Type \|.*?)(?=\n---|\n##|\Z)"
    new_table_block = f"| Metric | Type | Baseline | Target | Current | Progress | Pacing |\n|:---|:---|:---|:---|:---|:---|:---|\n{metrics_table}"

    if re.search(table_pattern, body, re.DOTALL):
        body = re.sub(table_pattern, new_table_block, body, flags=re.DOTALL)

    # Append notes to decisions section
    if decision_notes:
        notes_str = "\n".join(decision_notes)
        if "## 💡 Emerging Insights, Adjustments & Decisions" in body:
            body = body.replace(
                "## 💡 Emerging Insights, Adjustments & Decisions",
                f"## 💡 Emerging Insights, Adjustments & Decisions\n{notes_str}"
            )
        else:
            body += f"\n\n## 💡 Emerging Insights, Adjustments & Decisions\n{notes_str}\n"

    # Update header status string in body
    body = re.sub(
        r"\*\*Status:\*\* `[^`]+` \(Week \d+ of \d+\)",
        f"**Status:** `{new_status}` (Week {current_week} of {timeframe_weeks})",
        body
    )

    frontmatter = serialize_frontmatter(metadata)
    full_content = f"{frontmatter}\n{body.lstrip()}"

    # Check if target directory needs to change based on status
    target_dir = dirs.get(new_status, dirs["running"])
    current_dir = os.path.dirname(file_path)

    new_file_path = file_path
    if os.path.abspath(target_dir) != os.path.abspath(current_dir):
        new_file_path = os.path.join(target_dir, os.path.basename(file_path))
        if os.path.exists(file_path):
            os.remove(file_path)

    with open(new_file_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"✅ Updated hypothesis {metadata.get('id')} (Status: {new_status}) at {new_file_path}")

    session_file = args.session_file or metadata.get("session_file")
    if args.sync_session and session_file:
        sync_session_context(
            root_dir,
            session_file,
            metadata.get("id", "HYP"),
            metadata.get("title", ""),
            new_status,
            "updated",
            args.insight or args.rationale or f"Updated `{metadata.get('id')}` telemetry (Status: {new_status})"
        )

    return new_file_path


def list_hypotheses(args: argparse.Namespace, root_dir: str) -> None:
    """List hypotheses with status, pacing, owner, and metrics."""
    base = os.path.join(root_dir, "workforces", "hypotheses")
    if not os.path.exists(base):
        print("No hypotheses directory found.")
        return

    items: List[Dict[str, Any]] = []
    for root, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file_handle:
                meta, _ = parse_frontmatter(file_handle.read())
                if meta:
                    meta["_path"] = path
                    items.append(meta)

    # Apply filters
    if args.status:
        items = [i for i in items if i.get("status") == args.status]
    if args.owner:
        owner_clean = args.owner.lstrip("@")
        items = [i for i in items if i.get("owner") == owner_clean]
    if args.goal_id:
        items = [i for i in items if i.get("goal_id") == args.goal_id]

    if getattr(args, "json", False):
        print(json.dumps(items, indent=2))
        return

    if not items:
        print("🔍 No matching hypotheses found.")
        return

    print(f"\n🔬 Active Hypotheses & Strategic Experiments ({len(items)} found)\n")
    print(f"| ID | Status | Owner | Goal | Timeframe | Leading Metric Pacing | Title |")
    print(f"|:---|:---|:---|:---|:---|:---|:---|")

    for item in sorted(items, key=lambda x: str(x.get("id", ""))):
        h_id = item.get("id", "HYP")
        status = item.get("status", "running")
        owner = f"@{item.get('owner', 'team')}"
        goal = item.get("goal_id", "—")
        tf = f"W{item.get('current_week', 1)}/{item.get('timeframe_weeks', 1)}"
        title = item.get("title", "")

        # Pacing badge from first metric
        metrics = item.get("metrics", [])
        badge = "⚪ Pending"
        if metrics:
            first_m = metrics[0]
            _, _, badge = calculate_metric_pacing(
                float(first_m.get("baseline", 0)),
                float(first_m.get("target", 0)),
                float(first_m.get("current", 0)),
                int(item.get("current_week", 1)),
                int(item.get("timeframe_weeks", 1))
            )

        print(f"| {h_id} | `{status}` | {owner} | `{goal}` | {tf} | {badge} | {title} |")
    print()


def generate_sync_review(root_dir: str) -> str:
    """Generate structured hypothesis & experiment review for /sync --strategy."""
    base = os.path.join(root_dir, "workforces", "hypotheses")
    if not os.path.exists(base):
        return "*(No active hypotheses in `workforces/hypotheses/`)*\n"

    running_items: List[Dict[str, Any]] = []
    review_items: List[Dict[str, Any]] = []

    for root, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file_handle:
                meta, _ = parse_frontmatter(file_handle.read())
                if not meta:
                    continue
                meta["_path"] = path
                st = meta.get("status", "running")
                if st in ("running", "draft"):
                    running_items.append(meta)
                elif st in ("validated", "invalidated", "pivoted"):
                    review_items.append(meta)

    lines = [
        "### 🔬 Strategic Hypotheses & Growth Experiments",
        "",
        "| ID | Owner | Goal | Week | Leading KPI Progress | Status / Pacing | Action / Kill Trigger |",
        "|:---|:---|:---|:---|:---|:---|:---|",
    ]

    if not running_items:
        lines.append("| — | — | — | — | — | No active running experiments | Run `hypothesis.py --create` |")
    else:
        for item in running_items:
            h_id = item.get("id", "HYP")
            owner = f"@{item.get('owner', 'team')}"
            goal = item.get("goal_id", "—")
            tf = f"W{item.get('current_week', 1)}/{item.get('timeframe_weeks', 1)}"
            title = item.get("title", "")
            metrics = item.get("metrics", [])
            kill_thresh = item.get("kill_threshold", "—")

            kpi_str = "No metrics"
            badge = "🟢 On Track"
            if metrics:
                m0 = metrics[0]
                b = float(m0.get("baseline", 0))
                t = float(m0.get("target", 0))
                c = float(m0.get("current", 0))
                u = m0.get("unit", "")
                prog, _, badge = calculate_metric_pacing(b, t, c, int(item.get("current_week", 1)), int(item.get("timeframe_weeks", 1)))
                kpi_str = f"{m0.get('name')}: {c:g}/{t:g}{u} ({prog:.0f}%)"

            lines.append(f"| **{h_id}** | {owner} | `{goal}` | {tf} | {kpi_str} | {badge} | *Kill if:* {kill_thresh} |")

    lines.append("")
    return "\n".join(lines)


def sync_session_context(
    root_dir: str,
    session_file: str,
    hyp_id: str,
    title: str,
    status: str,
    action: str,
    note: str
) -> None:
    """Synchronize hypothesis update with active session context note."""
    if not os.path.isabs(session_file):
        session_file = os.path.join(root_dir, session_file)

    if not os.path.exists(session_file):
        return

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        if not meta:
            return

        # Ensure tracked_hypotheses list exists in session frontmatter
        if not isinstance(meta.get("tracked_hypotheses"), list):
            meta["tracked_hypotheses"] = []

        # Find or add hypothesis entry
        found = False
        for entry in meta["tracked_hypotheses"]:
            if isinstance(entry, dict) and entry.get("id") == hyp_id:
                entry["status"] = status
                entry["title"] = title
                found = True
                break

        if not found:
            meta["tracked_hypotheses"].append({
                "id": hyp_id,
                "title": title,
                "status": status
            })

        meta["updated_at"] = datetime.datetime.now().isoformat()
        now_short = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Append to Deciding Factors or Hypotheses section in session body
        entry_text = f"- **{now_short} (Hypothesis {action.capitalize()}):** `{hyp_id}` ({title}) $\\rightarrow$ `{status}`: {note}"

        if "## 🔬 Strategic Hypotheses & Experiments" in body:
            body = body.replace(
                "## 🔬 Strategic Hypotheses & Experiments",
                f"## 🔬 Strategic Hypotheses & Experiments\n{entry_text}"
            )
        elif "## 🧠 Deciding Factors" in body:
            body = body.replace(
                "## 🧠 Deciding Factors",
                f"## 🧠 Deciding Factors\n{entry_text}"
            )
        else:
            body += f"\n\n## 🔬 Strategic Hypotheses & Experiments\n{entry_text}\n"

        new_frontmatter = serialize_frontmatter(meta)
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(f"{new_frontmatter}\n{body.lstrip()}")

    except Exception as e:
        print(f"⚠️ Warning: Failed to sync session context at {session_file}: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hypothesis & Experiment Tracker")
    parser.add_argument("--create", action="store_true", help="Create a new hypothesis")
    parser.add_argument("--update", type=str, help="Update an existing hypothesis by file or ID")
    parser.add_argument("--list", action="store_true", help="List hypotheses")
    parser.add_argument("--review", action="store_true", help="Generate sync review section")
    parser.add_argument("--kill", type=str, help="Enforce kill criteria on hypothesis")
    parser.add_argument("--pivot", type=str, help="Pivot hypothesis with contingency plan")
    parser.add_argument("--validate", type=str, help="Validate hypothesis as successful")

    parser.add_argument("--title", type=str, help="Hypothesis title")
    parser.add_argument("--id", type=str, help="Hypothesis ID (e.g. HYP-20260823-01)")
    parser.add_argument("--owner", type=str, default="growth", help="Owning team/agent (e.g. sales, growth, marketing)")
    parser.add_argument("--supporting-teams", nargs="*", help="Supporting teams")
    parser.add_argument("--goal-id", type=str, help="Related Goal ID (e.g. Q1-KR1)")
    parser.add_argument("--goal-title", type=str, help="Related Goal Title")
    parser.add_argument("--statement", type=str, help="Scientific hypothesis statement")
    parser.add_argument("--timeframe-weeks", type=int, default=3, help="Duration in weeks")
    parser.add_argument("--current-week", type=int, default=1, help="Current elapsed week")
    parser.add_argument("--kill-threshold", type=str, help="Kill threshold criteria")
    parser.add_argument("--pivot-plan", type=str, help="Contingency / pivot plan")
    parser.add_argument("--metrics", type=str, help="JSON list of metric dictionaries")
    parser.add_argument("--metrics-data", type=str, help="Key=Value updates for metrics e.g. 'Sends=50,Replies=5'")
    parser.add_argument("--status", type=str, help="Status (draft, running, validated, invalidated, pivoted)")
    parser.add_argument("--insight", type=str, help="Emerging insight note")
    parser.add_argument("--rationale", type=str, help="Rationale for kill/pivot/validation")
    parser.add_argument("--session-id", type=str, help="Origin session ID")
    parser.add_argument("--session-file", type=str, help="Origin session context note path")
    parser.add_argument("--sync-session", action="store_true", help="Sync with session context note")
    parser.add_argument("--file", type=str, help="Target hypothesis file")
    parser.add_argument("--root", type=str, help="Workspace root directory")
    parser.add_argument("--json", action="store_true", help="Output list as JSON")

    args = parser.parse_args()
    root_dir = find_workspace_root(args.root)

    if args.create:
        if not args.title:
            print("❌ Error: --title is required to create a hypothesis.", file=sys.stderr)
            sys.exit(1)
        create_hypothesis(args, root_dir)
    elif args.kill:
        args.update = args.kill
        update_hypothesis(args, root_dir)
    elif args.pivot:
        args.update = args.pivot
        update_hypothesis(args, root_dir)
    elif args.validate:
        args.update = args.validate
        update_hypothesis(args, root_dir)
    elif args.update or args.file:
        update_hypothesis(args, root_dir)
    elif args.review:
        print(generate_sync_review(root_dir))
    elif args.list:
        list_hypotheses(args, root_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
