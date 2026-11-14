#!/usr/bin/env python3
"""
report-task — Task & Action Item capture, evolution, and lifecycle management script.

Usage:
    # 1. Report a new task linked to a session:
    python3 .agents/skills/wf-task-tracker/scripts/report-task.py \
        --title "Follow up with pilot team lead" \
        --type follow-up \
        --priority P1 \
        --assignee "@user" \
        --reporter wf-scribe \
        --session-id "026" \
        --session-file "workforces/session-context/026_2026-08-23_claude_scribe_product_brief.md" \
        --description "Send updated SOC2 summary and schedule 15m review." \
        --suggested-action "Draft email and attach SOC2 bridge letter." \
        --evolution-note "Initial discussion: user agreed to follow up by Tuesday." \
        --sync-session

    # 2. Update status in-place (e.g. start working on it):
    python3 .agents/skills/wf-task-tracker/scripts/report-task.py \
        --update "workforces/tasks/20260823-120000-follow-up-with-pilot-team-lead.md" \
        --start \
        --evolution-note "Started drafting email response." \
        --sync-session

    # 3. Mark task as blocked or done:
    python3 .agents/skills/wf-task-tracker/scripts/report-task.py \
        --update "follow-up-with-pilot-team-lead" \
        --done \
        --evolution-note "Sent email and scheduled call for Thursday." \
        --sync-session

    # 4. Drop a task with deciding factors / reason:
    python3 .agents/skills/wf-task-tracker/scripts/report-task.py \
        --update "follow-up-with-pilot-team-lead" \
        --drop "Lead reached out directly; separate follow-up no longer required." \
        --sync-session

    # 5. Check for similar tasks before creating:
    python3 .agents/skills/wf-task-tracker/scripts/report-task.py \
        --find-similar "pilot team lead"

    *(Fallback for toolkit development: substitute skills/wf-task-tracker/scripts/report-task.py)*
"""

import argparse
import datetime
import difflib
import errno
import json
import os
import re
import shutil
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore[assignment]

try:
    from personal_sync import sync_workstate_from_tasks, reconcile_github_tasks, resolve_portable_md_link as _resolve_portable_md_link
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    try:
        from personal_sync import sync_workstate_from_tasks, reconcile_github_tasks, resolve_portable_md_link as _resolve_portable_md_link
    except ImportError:
        def sync_workstate_from_tasks(root_dir: str) -> bool:
            return False
        def reconcile_github_tasks(root_dir: str, **kwargs) -> list:
            return []
        def _resolve_portable_md_link(target_path: str, relative_from: Optional[str] = None) -> str:
            return os.path.basename(target_path) if os.path.isabs(target_path) else target_path.replace("\\", "/")

VALID_STATUSES = ["todo", "in_progress", "review", "blocked", "done", "dropped"]
VALID_PRIORITIES = ["P0", "P1", "P2", "P3"]
VALID_CADENCES = ["one_shot", "rolling_slice"]
VALID_REVIEW_STATES = ["none", "requires_code_review", "in_review", "ready_for_human", "changes_requested"]
VALID_HARNESSES = frozenset({"antigravity", "claude", "grok"})
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def detect_active_harness(explicit: Optional[str] = None, root_dir: Optional[str] = None) -> str:
    """Resolve current AI harness (`antigravity`, `claude`, or `grok`) from flag, env, or config."""
    if explicit is not None and str(explicit).strip():
        val = str(explicit).strip().lower()
        if val not in VALID_HARNESSES:
            raise ValueError(f"Unsupported harness '{explicit}'. Must be one of: {sorted(VALID_HARNESSES)}")
        return val
    env_harness = os.environ.get("WORKFORCE_HARNESS")
    if env_harness and env_harness.strip():
        val = env_harness.strip().lower()
        if val not in VALID_HARNESSES:
            raise ValueError(f"Unsupported WORKFORCE_HARNESS '{env_harness}'. Must be one of: {sorted(VALID_HARNESSES)}")
        return val
    if os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or os.environ.get("ANTIGRAVITY_AGENT") or os.environ.get("AGY_ACCOUNT"):
        return "antigravity"
    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_SESSION_ID"):
        return "claude"
    if os.environ.get("GROK_PROJECT_DIR") or os.environ.get("GROK_CLI") or os.environ.get("GROK_SESSION_ID"):
        return "grok"
    cfg_root = root_dir or os.getcwd()
    cfg_path = os.path.join(cfg_root, "workforces", "config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                hosts = json.load(fh).get("hosts") or []
                if isinstance(hosts, list):
                    for host in hosts:
                        cand = str(host).strip().lower()
                        if cand in VALID_HARNESSES:
                            return cand
        except (OSError, ValueError):
            pass
    return "antigravity"


def _clear_claim_fields(meta: Dict[str, Any]) -> None:
    """Clear worker claim ownership and expiration timestamps on a task metadata dict."""
    for key in (
        "claimed_by_harness",
        "claimed_by_agent",
        "claimed_at",
        "claimed_session_id",
        "claimed_worktree",
        "claim_expires_at",
    ):
        meta[key] = None


def _prepend_evolution_note(body: str, note: str, now: Optional[datetime.datetime] = None) -> str:
    """Prepend a timestamped lineage bullet under `## 🧠 Session Lineage & Deciding Factors`."""
    stamp = (now or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")
    entry = f"- **{stamp}:** {note}"
    header = "## 🧠 Session Lineage & Deciding Factors"
    if header in body:
        before, after = body.split(header, 1)
        return before + header + "\n\n" + entry + "\n" + after.lstrip("\r\n")
    return body.rstrip() + f"\n\n{header}\n\n{entry}\n"


def _is_pid_dead(lock_path: str) -> bool:
    """Return True only when the PID recorded in `lock_path` is demonstrably no longer alive."""
    try:
        with open(lock_path, "r", encoding="utf-8") as fh:
            raw_pid = fh.read().strip()
        pid = int(raw_pid) if raw_pid else 0
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        return True
    except (OSError, ValueError):
        return False


def _write_lock_pid(fd: int) -> None:
    """Record current process PID inside an already-locked file descriptor."""
    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, f"{os.getpid()}\n".encode("utf-8"))
    except OSError:
        pass


@contextmanager
def _claim_lock(tasks_dir: str, timeout_sec: float = 5.0) -> Iterator[None]:
    """Acquire a kernel advisory lock (`fcntl.flock` / `msvcrt.locking`) protecting task claiming."""
    os.makedirs(tasks_dir, exist_ok=True)
    lock_path = os.path.join(tasks_dir, ".claim.lock")
    deadline = time.monotonic() + timeout_sec

    if fcntl is not None or msvcrt is not None:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        locked = False
        try:
            while time.monotonic() < deadline:
                try:
                    if fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    elif msvcrt is not None:
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    locked = True
                    _write_lock_pid(fd)
                    break
                except (BlockingIOError, OSError) as exc:
                    if fcntl is not None and exc.errno not in (errno.EACCES, errno.EAGAIN, getattr(errno, "EWOULDBLOCK", errno.EAGAIN)):
                        raise
                    time.sleep(0.05)
            if not locked:
                raise TimeoutError(f"Timed out acquiring task claim lock: {lock_path}")
            yield
        finally:
            if locked:
                try:
                    if fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    elif msvcrt is not None:
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            os.close(fd)
        return

    acquired = False
    while time.monotonic() < deadline:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, f"{os.getpid()}\n".encode("utf-8"))
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            if _is_pid_dead(lock_path):
                try:
                    os.unlink(lock_path)
                    continue
                except OSError:
                    pass
            time.sleep(0.05)
    if not acquired:
        raise TimeoutError(f"Timed out acquiring task claim lock: {lock_path}")
    try:
        yield
    finally:
        try:
            os.unlink(lock_path)
        except OSError:
            pass


def _is_claim_expired(meta: Dict[str, Any], now_utc: datetime.datetime) -> bool:
    """Return True if a task has an active claim whose TTL has expired."""
    expires_raw = meta.get("claim_expires_at")
    if not expires_raw or expires_raw in ("~", "None"):
        return False
    try:
        expires_dt = datetime.datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=datetime.timezone.utc)
        return now_utc >= expires_dt
    except ValueError:
        return False


def _reclaim_expired_in_locked_dir(tasks_dir: str, now_utc: datetime.datetime) -> List[Dict[str, Any]]:
    """Release expired leases inside `tasks_dir` (caller MUST hold `_claim_lock`)."""
    reclaimed: List[Dict[str, Any]] = []
    if not os.path.isdir(tasks_dir):
        return reclaimed
    now_local = datetime.datetime.now()
    for fname in sorted(os.listdir(tasks_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.abspath(os.path.join(tasks_dir, fname))
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                meta, body = parse_frontmatter(f.read())
        except OSError:
            continue
        if not meta.get("claimed_by_harness"):
            continue
        if not _is_claim_expired(meta, now_utc):
            continue

        prev_harness = meta.get("claimed_by_harness")
        if meta.get("review_state") == "in_review":
            meta["review_state"] = "requires_code_review"
            meta["status"] = "review"
        elif meta.get("status") == "in_progress":
            meta["status"] = "todo"
        _clear_claim_fields(meta)
        meta["updated_at"] = now_local.isoformat()
        body = _prepend_evolution_note(body, f"⏱️ Lease expired (previous harness: {prev_harness}); returned to queue.", now_local)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(dump_frontmatter(meta, body))
        reclaimed.append({"path": fpath, "title": meta.get("title", fname), "previous_harness": prev_harness})
    return reclaimed


def claim_next_task(
    tasks_dir: str,
    current_harness: str,
    mode: str = "auto",
    agent_name: Optional[str] = None,
    worktree: Optional[str] = None,
    ttl_minutes: int = 90,
) -> Optional[Dict[str, Any]]:
    """
    Atomically claim the highest-priority eligible work item for `current_harness`.

    Priority 0 (`codereview` or `auto`): cross-harness PR/task reviews
      (`review_state == 'requires_code_review'` and `authored_by_harness != current_harness`).
    Priority 1 (`auto` only): `approved_for_execution == true` and `status == 'todo'`,
      enforcing the stateless rolling 1-bite-per-day guard for `cadence == 'rolling_slice'`.
    """
    normalized_harness = str(current_harness or "").strip().lower()
    if normalized_harness not in VALID_HARNESSES:
        raise ValueError(
            f"Unsupported harness '{current_harness}'. Must be one of: {sorted(VALID_HARNESSES)}"
        )
    current_harness = normalized_harness
    today_str = datetime.date.today().isoformat()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_local = datetime.datetime.now()
    expires_utc = now_utc + datetime.timedelta(minutes=ttl_minutes)
    session_id = os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or os.environ.get("CLAUDE_SESSION_ID") or ""

    with _claim_lock(tasks_dir):
        _reclaim_expired_in_locked_dir(tasks_dir, now_utc)
        records: List[Tuple[str, Dict[str, Any], str]] = []
        active_rolling_files = set()

        if not os.path.isdir(tasks_dir):
            return None

        for fname in sorted(os.listdir(tasks_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.abspath(os.path.join(tasks_dir, fname))
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    meta, body = parse_frontmatter(f.read())
                records.append((fpath, meta, body))
                if meta.get("status") in ("in_progress", "review") and meta.get("file"):
                    active_rolling_files.add(str(meta.get("file")).strip())
            except OSError:
                continue

        # Priority 0: Cross-Harness Code Review
        review_candidates: List[Tuple[int, str, str, Dict[str, Any], str]] = []
        for fpath, meta, body in records:
            if meta.get("claimed_by_harness"):
                continue
            r_state = str(meta.get("review_state") or "none").lower()
            st = str(meta.get("status") or "todo").lower()
            needs_review = r_state == "requires_code_review" or (st == "review" and r_state not in ("ready_for_human", "in_review"))
            if not needs_review:
                continue
            author_h = str(meta.get("authored_by_harness") or "").lower()
            if author_h and author_h == current_harness.lower():
                continue
            prio = PRIORITY_ORDER.get(str(meta.get("priority", "P2")), 9)
            stamp = str(meta.get("updated_at") or meta.get("reported_at") or "")
            review_candidates.append((prio, stamp, fpath, meta, body))

        if review_candidates:
            review_candidates.sort(key=lambda x: (x[0], x[1]))
            fpath, meta, body = review_candidates[0][2:]
            meta["status"] = "review"
            meta["review_state"] = "in_review"
            meta["claimed_by_harness"] = current_harness
            meta["claimed_by_agent"] = agent_name or f"@{current_harness}-reviewer"
            meta["claimed_at"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            meta["claim_expires_at"] = expires_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            if session_id:
                meta["claimed_session_id"] = session_id
            if worktree:
                meta["claimed_worktree"] = worktree
            meta["updated_at"] = now_local.isoformat()
            body = _prepend_evolution_note(
                body,
                f"🔎 Claimed for cross-harness review by `{current_harness}` ({meta['claimed_by_agent']}).",
                now_local,
            )
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(dump_frontmatter(meta, body))
            return {"claim_kind": "codereview", "path": fpath, **meta}

        if mode == "codereview":
            return None

        # Priority 1: Approved Execution Back-Queue
        exec_candidates: List[Tuple[int, str, str, Dict[str, Any], str]] = []
        for fpath, meta, body in records:
            if meta.get("status") != "todo" or meta.get("claimed_by_harness"):
                continue
            if meta.get("approved_for_execution") is not True:
                continue
            cadence = str(meta.get("cadence") or "one_shot")
            target_file = str(meta.get("file") or "").strip()
            if cadence == "rolling_slice":
                if str(meta.get("last_slice_date") or "") == today_str:
                    continue
                if target_file and target_file in active_rolling_files:
                    continue
            prio = PRIORITY_ORDER.get(str(meta.get("priority", "P2")), 9)
            stamp = str(meta.get("reported_at") or meta.get("updated_at") or "")
            exec_candidates.append((prio, stamp, fpath, meta, body))

        if not exec_candidates:
            return None

        exec_candidates.sort(key=lambda x: (x[0], x[1]))
        fpath, meta, body = exec_candidates[0][2:]
        meta["status"] = "in_progress"
        meta["claimed_by_harness"] = current_harness
        meta["claimed_by_agent"] = agent_name or f"@{current_harness}"
        meta["claimed_at"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        meta["claim_expires_at"] = expires_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        if session_id:
            meta["claimed_session_id"] = session_id
        if worktree:
            meta["claimed_worktree"] = worktree
        meta["updated_at"] = now_local.isoformat()
        body = _prepend_evolution_note(
            body,
            f"⏳ Claimed from approved queue by `{current_harness}` ({meta['claimed_by_agent']}).",
            now_local,
        )
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(dump_frontmatter(meta, body))
        return {"claim_kind": "execution", "path": fpath, **meta}


def promote_issue_to_task(
    issue_path: str,
    tasks_dir: str,
    approved: bool = False,
    cadence: str = "one_shot",
    priority_override: Optional[str] = None,
    assignee: Optional[str] = None,
) -> str:
    """Promote a backlog issue file (`workforces/issues/inbox/`) into an actionable task."""
    with open(issue_path, "r", encoding="utf-8") as f:
        imeta, ibody = parse_frontmatter(f.read())

    now = datetime.datetime.now()
    title = str(imeta.get("title") or os.path.splitext(os.path.basename(issue_path))[0])
    prio = priority_override or str(imeta.get("severity") or imeta.get("priority") or "P2")
    if prio not in VALID_PRIORITIES:
        prio = "P2"

    desc_match = re.search(r"## Description\s*\n\n(.*?)(?=\n\n##|\Z)", ibody, re.DOTALL)
    act_match = re.search(r"## Suggested Action\s*\n\n(.*?)(?=\n\n##|\Z)", ibody, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""
    suggested_action = act_match.group(1).strip() if act_match else ""

    os.makedirs(tasks_dir, exist_ok=True)
    filename = f"{now.strftime('%Y%m%d-%H%M%S')}-{slugify(title)}.md"
    task_path = os.path.join(tasks_dir, filename)

    triaged_dest = issue_path
    inbox_parent = os.path.dirname(os.path.dirname(os.path.abspath(issue_path)))
    if os.path.basename(os.path.dirname(os.path.abspath(issue_path))) == "inbox":
        triaged_dir = os.path.join(inbox_parent, "triaged")
        os.makedirs(triaged_dir, exist_ok=True)
        triaged_dest = os.path.join(triaged_dir, os.path.basename(issue_path))
        imeta["status"] = "triaged"
        imeta["triage_status"] = "triaged"
        imeta["updated_at"] = now.isoformat()
        with open(issue_path, "w", encoding="utf-8") as f:
            f.write(dump_frontmatter(imeta, ibody))
        shutil.move(issue_path, triaged_dest)

    rel_source = _resolve_portable_md_link(triaged_dest)
    content = build_task_markdown(
        title=title,
        task_type=str(imeta.get("type") or "task"),
        priority=prio,
        status="todo",
        reporter=str(imeta.get("reporter") or "wf-project-manager"),
        assignee=assignee,
        description=description,
        suggested_action=suggested_action,
        file_path=str(imeta.get("file") or ""),
        session_id=str(imeta.get("session_id") or ""),
        session_file=str(imeta.get("session_file") or ""),
        github_issue=imeta.get("github_issue"),
        evolution_notes=[f"**{now.strftime('%Y-%m-%d %H:%M')}:** Promoted from `{rel_source}` (approved={approved}, cadence={cadence})."],
        created_at=now,
        updated_at=now,
        approved_for_execution=approved,
        cadence=cadence,
        source_issue=rel_source,
    )
    with open(task_path, "w", encoding="utf-8") as f:
        f.write(content)
    return task_path


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
                metadata[key] = val

    return metadata, body


def dump_frontmatter(metadata: Dict[str, Any], body: str) -> str:
    """Convert metadata dictionary and body into markdown with YAML frontmatter."""
    lines = ["---"]
    for k, v in metadata.items():
        if v is None:
            lines.append(f"{k}: ~")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            elif isinstance(v[0], dict):
                lines.append(f"{k}:")
                for item in v:
                    first = True
                    for sub_k, sub_v in item.items():
                        if first:
                            lines.append(f'  - {sub_k}: "{sub_v}"')
                            first = False
                        else:
                            lines.append(f'    {sub_k}: "{sub_v}"')
            else:
                formatted_items = [f'"{item}"' for item in v]
                lines.append(f"{k}: [{', '.join(formatted_items)}]")
        else:
            clean_v = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{clean_v}"')
    lines.append("---")
    lines.append("")
    lines.append(body.strip("\r\n"))
    lines.append("")
    return "\n".join(lines)


def extract_title(filepath: str) -> str:
    """Pull the `title:` value from a YAML frontmatter block in a task file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            metadata, _ = parse_frontmatter(f.read())
            return str(metadata.get("title", ""))
    except OSError:
        pass
    return ""


def find_task_by_identifier(identifier: str, search_dirs: List[str]) -> Optional[str]:
    """Find task/issue file by exact path, relative path, filename, or partial slug match."""
    if os.path.isfile(identifier):
        return os.path.abspath(identifier)

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

        for fname in os.listdir(d):
            if not fname.endswith(".md"):
                continue
            if identifier.lower() in fname.lower():
                return os.path.abspath(os.path.join(d, fname))
    return None


def find_similar_tasks(
    query_title: str, search_dirs: List[str], threshold: float = 0.70
) -> List[Tuple[str, float, Dict[str, Any]]]:
    """
    Return existing task files whose title or content is similar to query_title.
    Returns list of (filepath, ratio, metadata).
    """
    matches = []
    seen_paths = set()
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.abspath(os.path.join(directory, fname))
            if fpath in seen_paths:
                continue
            seen_paths.add(fpath)
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


def build_task_markdown(
    title: str,
    task_type: str = "task",
    priority: str = "P2",
    status: str = "todo",
    reporter: str = "wf-scribe",
    assignee: Optional[str] = None,
    description: str = "",
    suggested_action: str = "",
    file_path: str = "",
    session_id: str = "",
    chat_session_id: str = "",
    session_file: str = "",
    recommended_tools: Optional[List[str]] = None,
    delegated_to: Optional[str] = None,
    github_labels: Optional[List[str]] = None,
    github_issue: Optional[str] = None,
    github_pr: Optional[str] = None,
    evolution_notes: Optional[List[str]] = None,
    created_at: Optional[datetime.datetime] = None,
    updated_at: Optional[datetime.datetime] = None,
    approved_for_execution: Optional[bool] = None,
    cadence: Optional[str] = None,
    authored_by_harness: Optional[str] = None,
    review_state: Optional[str] = None,
    source_issue: Optional[str] = None,
) -> str:
    """Construct complete task file markdown with frontmatter and lineage."""
    now = created_at or datetime.datetime.now()
    up_now = updated_at or now

    metadata: Dict[str, Any] = {
        "title": title,
        "type": task_type or "task",
        "priority": priority,
        "status": status,
        "reporter": reporter,
        "assignee": assignee or None,
        "reported_at": now.isoformat(),
        "updated_at": up_now.isoformat(),
        "file": file_path or "",
        "session_id": session_id or None,
        "chat_session_id": chat_session_id or os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or None,
        "session_file": session_file or None,
        "recommended_tools": recommended_tools or [],
        "delegated_to": delegated_to or None,
        "github_labels": github_labels or [],
        "github_issue": github_issue or None,
        "github_pr": github_pr or None,
    }
    if approved_for_execution is not None:
        metadata["approved_for_execution"] = approved_for_execution
    if cadence:
        metadata["cadence"] = cadence
    if authored_by_harness:
        metadata["authored_by_harness"] = authored_by_harness
    if review_state:
        metadata["review_state"] = review_state
    if source_issue:
        metadata["source_issue"] = source_issue

    session_origin_link = ""
    if session_file:
        session_href = _resolve_portable_md_link(session_file)
        session_origin_link = f"**Origin Session:** [{os.path.basename(session_file)}]({session_href})\n"

    header_parts = [
        f"**Type:** `{task_type}`",
        f"**Priority:** `{priority}`",
        f"**Status:** `{status}`",
        f"**Reporter:** `{reporter}`",
    ]
    if assignee:
        header_parts.append(f"**Assignee:** `{assignee}`")
    header_line = " | ".join(header_parts)

    tool_delegation_line = ""
    parts_line = []
    if recommended_tools:
        parts_line.append(f"**Recommended Tools:** `{', '.join(recommended_tools)}`")
    if delegated_to:
        parts_line.append(f"**Delegated To:** `{delegated_to}`")
    if github_labels:
        parts_line.append(f"**GitHub Labels:** `{'`, `'.join(github_labels)}`")
    if parts_line:
        tool_delegation_line = " | ".join(parts_line) + "\n"

    evolution_lines = []
    if evolution_notes:
        for note in evolution_notes:
            evolution_lines.append(f"- {note}")
    else:
        evolution_lines.append(f"- **{now.strftime('%Y-%m-%d %H:%M')}:** Initial creation: {description[:120] if description else title}")

    body = f"""# {title}

{header_line}  
**Reported:** {now.strftime("%Y-%m-%d %H:%M")} | **Updated:** {up_now.strftime("%Y-%m-%d %H:%M")}  
{session_origin_link}{f"**Affected file:** `{file_path}`\n" if file_path else ""}{tool_delegation_line}
## Description

{description if description else "_No description provided._"}

## Suggested Action

{suggested_action if suggested_action else "_No suggested action provided._"}

## 🧠 Session Lineage & Deciding Factors

{chr(10).join(evolution_lines)}
"""

    return dump_frontmatter(metadata, body)


def sync_task_to_session_file(
    session_file_path: str,
    task_file_path: str,
    task_meta: Dict[str, Any],
    evolution_summary: str = "",
) -> bool:
    """
    Ensure the session context markdown file lists the task in frontmatter (tracked_tasks) and body.
    Maintains backward compatibility with tracked_issues.
    """
    if not os.path.isfile(session_file_path):
        return False

    try:
        with open(session_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        task_id = os.path.splitext(os.path.basename(task_file_path))[0]
        title = task_meta.get("title", task_id)
        task_type = task_meta.get("type", "task")
        priority = task_meta.get("priority", task_meta.get("severity", "P2"))
        status = task_meta.get("status", "todo")
        is_dropped = status in ("dropped", "rejected", "wont-fix")

        # Update or append in frontmatter tracked_tasks (or tracked_issues if present)
        uses_tracked_tasks = "tracked_tasks" in meta or "tracked_issues" not in meta
        list_key = "tracked_tasks" if uses_tracked_tasks else "tracked_issues"
        tracked = meta.get(list_key)
        if not isinstance(tracked, list):
            tracked = []

        found = False
        new_tracked = []
        for item in tracked:
            if isinstance(item, dict) and (
                item.get("id") == task_id or item.get("file") == task_file_path or (item.get("title") and item.get("title") == title)
            ):
                found = True
                new_item = {
                    "id": task_id,
                    "file": task_file_path,
                    "title": title,
                    "type": task_type,
                    "priority" if list_key == "tracked_tasks" else "severity": priority,
                    "status": status,
                }
                new_tracked.append(new_item)
            else:
                new_tracked.append(item)

        if not found:
            new_item = {
                "id": task_id,
                "file": task_file_path,
                "title": title,
                "type": task_type,
                "priority" if list_key == "tracked_tasks" else "severity": priority,
                "status": status,
            }
            new_tracked.append(new_item)

        meta[list_key] = new_tracked
        meta["updated_at"] = datetime.datetime.now().isoformat()

        # Determine task line formatting in Markdown body
        summary_text = evolution_summary or task_meta.get("description", "")[:100]
        for prefix in ["❌ Dropped:", "❌ Rejected:", "❌ Dropped by user:", "❌ Rejected by user:"]:
            if summary_text.startswith(prefix):
                summary_text = summary_text[len(prefix):].strip()

        task_link = _resolve_portable_md_link(task_file_path, relative_from=session_file_path)
        if is_dropped:
            task_entry = f"- [~~{title}~~]({task_link}) (~~`{task_type}`~~ | ~~{priority}~~) — ❌ **Dropped:** {summary_text}"
        elif status == "done":
            task_entry = f"- [{title}]({task_link}) (`{task_type}` | {priority}) — ✅ **Done:** {summary_text}"
        elif status == "in_progress":
            task_entry = f"- [{title}]({task_link}) (`{task_type}` | {priority}) — ⏳ **In Progress:** {summary_text}"
        elif status == "blocked":
            task_entry = f"- [{title}]({task_link}) (`{task_type}` | {priority}) — ⚠️ **Blocked:** {summary_text}"
        else:
            task_entry = f"- [{title}]({task_link}) (`{task_type}` | {priority}) — {summary_text}"

        # Match section header (either tasks or legacy issues)
        section_headers = [
            "## 📋 Tracked Tasks & Action Items",
            "## 📋 Tracked Tasks",
            "## 📋 Tracked Issues & Feature Ideas",
            "## 📋 Tracked Issues",
        ]
        target_header = None
        for h in section_headers:
            if h in body:
                target_header = h
                break

        if target_header:
            parts = body.split(target_header, 1)
            before_sec = parts[0] + target_header + "\n"
            after_sec = parts[1]

            next_header = re.search(r"\n##\s+", after_sec)
            if next_header:
                sec_content = after_sec[:next_header.start()]
                rest = after_sec[next_header.start():]
            else:
                sec_content = after_sec
                rest = ""

            lines = [l for l in sec_content.splitlines() if l.strip()]
            new_lines = []
            replaced = False
            for l in lines:
                if task_id in l or title in l or os.path.basename(task_file_path) in l:
                    new_lines.append(task_entry)
                    replaced = True
                else:
                    new_lines.append(l)
            if not replaced:
                new_lines.append(task_entry)

            updated_sec = "\n" + "\n".join(new_lines) + "\n"
            body = before_sec + updated_sec + rest
        else:
            new_header = "## 📋 Tracked Tasks & Action Items"
            insert_marker = "## 📁 Key Files & Code Symbols"
            if insert_marker in body:
                body = body.replace(
                    insert_marker,
                    f"{new_header}\n{task_entry}\n\n{insert_marker}"
                )
            else:
                body = body.rstrip() + f"\n\n{new_header}\n{task_entry}\n"

        new_content = dump_frontmatter(meta, body)
        with open(session_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"⚠️ Failed to sync task to session file {session_file_path}: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report, update, evolve, and manage tasks and action items."
    )
    parser.add_argument("--title", help="Short task/action title")
    parser.add_argument(
        "--type", default="task",
        help="Task type/tag (e.g. 'follow-up', 'bug', 'idea', 'debt', 'design', 'ops', 'business', 'marketing')",
    )
    parser.add_argument(
        "--priority", default="P2",
        choices=VALID_PRIORITIES,
        help="Priority level (P0=urgent, P1=high, P2=medium, P3=low)",
    )
    parser.add_argument(
        "--severity", dest="priority_alias",
        choices=VALID_PRIORITIES,
        help="Backward-compatible alias for --priority",
    )
    parser.add_argument(
        "--status",
        choices=VALID_STATUSES,
        help="Task status: todo | in_progress | review | blocked | done | dropped",
    )
    parser.add_argument(
        "--start", "--in-progress", dest="start_task", action="store_true",
        help="Set task status to 'in_progress'",
    )
    parser.add_argument(
        "--review", "--awaiting-review", dest="review_task", action="store_true",
        help="Set task status to 'review' (awaiting review/approval)",
    )
    parser.add_argument(
        "--reviewer", default="",
        help="Tagged reviewer for task review (e.g. '@human' or agent like '@wf-programmer')",
    )
    parser.add_argument(
        "--block", nargs="?", const="Blocked on external dependency",
        help="Set task status to 'blocked' with optional reason",
    )
    parser.add_argument(
        "--done", "--complete", dest="done_task", action="store_true",
        help="Set task status to 'done'",
    )
    parser.add_argument(
        "--drop", "--reject", dest="drop_reason", nargs="?",
        const="Dropped by user during consultation",
        help="Mark task as dropped with optional deciding factors / reason",
    )
    parser.add_argument("--reporter", default=None, help="Agent or human that logged the task (default: wf-scribe)")
    parser.add_argument("--assignee", help="Person or agent assigned (e.g. '@user', '@me', '@aaron', '@wf-scribe')")
    parser.add_argument("--file", default="", help="Affected file path (optional)")
    parser.add_argument("--description", default="", help="Full description of the task or action")
    parser.add_argument("--suggested-action", default="", help="Recommended next step or implementation plan")
    parser.add_argument("--session-id", default="", help="Associated session sequence ID (e.g. '026')")
    parser.add_argument(
        "--chat-session-id", default="",
        help="Antigravity chat session ID (auto-detected from ANTIGRAVITY_CONVERSATION_ID if omitted)",
    )
    parser.add_argument("--session-file", default="", help="Path to session context markdown note")
    parser.add_argument(
        "--tools", "--recommended-tools", dest="recommended_tools",
        help="Comma-separated list of recommended enabling tools or MCP servers",
    )
    parser.add_argument(
        "--delegated-to",
        help="Subagent or worker delegated to execute this task",
    )
    parser.add_argument(
        "--github-labels",
        help="Comma-separated list of GitHub labels to attach",
    )
    parser.add_argument(
        "--github-issue",
        help="Linked GitHub issue number/url if synced",
    )
    parser.add_argument(
        "--pr", "--github-pr", dest="github_pr",
        help="Linked GitHub PR number/url (e.g. '1495' or 'https://github.com/org/repo/pull/1495')",
    )
    parser.add_argument(
        "--reconcile-github", action="store_true",
        help="Reconcile active tasks against remote GitHub PR/issue states",
    )
    parser.add_argument(
        "--no-sync-workstate", action="store_true",
        help="Skip automatically synchronizing workforces/workstate.md",
    )
    parser.add_argument(
        "--evolution-note",
        help="Decision note explaining requirement evolution, trade-offs, or updates mid-session",
    )
    parser.add_argument(
        "--update",
        help="File path or ID/slug of an existing task to update",
    )
    parser.add_argument(
        "--find-similar",
        help="Search for existing tasks similar to the given title string",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List tasks across task directories",
    )
    parser.add_argument(
        "--sync-session", action="store_true",
        help="Sync task metadata back into the active session context file",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--out-dir", default="",
        help="Output directory for task files (defaults to workforces/tasks/ or .scribe/tasks/)",
    )
    parser.add_argument(
        "--output", default="",
        help="AI execution output or resolution report to attach to the task body",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip duplicate check and write regardless",
    )
    parser.add_argument("--approve", action="store_true", help="Mark task approved_for_execution: true for worker queue")
    parser.add_argument("--unapprove", action="store_true", help="Mark task approved_for_execution: false")
    parser.add_argument("--cadence", choices=VALID_CADENCES, help="Execution cadence: one_shot | rolling_slice")
    parser.add_argument("--last-slice-date", default="", help="Override YYYY-MM-DD last rolling slice date")
    parser.add_argument("--promote-issue", help="Promote an issue file from issues/inbox/ into tasks/")
    parser.add_argument("--request-review", action="store_true", help="Mark task ready for cross-harness code review")
    parser.add_argument(
        "--complete-review",
        choices=["approved", "changes_requested"],
        help="Submit cross-harness review verdict",
    )
    parser.add_argument("--review-notes", default="", help="Review commentary appended when completing review")
    parser.add_argument("--allow-same-harness", action="store_true", help="Allow review verdict from same harness")
    parser.add_argument("--complete-slice", action="store_true", help="Complete one rolling slice while keeping task active for future days")
    parser.add_argument("--claim-next", action="store_true", help="Atomically claim next highest-priority review or approved task")
    parser.add_argument("--reclaim-stale", action="store_true", help="Release expired worker claims back to the queue")
    parser.add_argument("--mode", default="auto", help="Claim mode: auto | codereview")
    parser.add_argument("--harness", default="", help="Override active harness (`antigravity`, `claude`, `grok`)")
    parser.add_argument("--agent", default="", help="Worker agent label when claiming (e.g. @wf-programmer)")
    parser.add_argument("--worktree", default="", help="Worktree/branch label when claiming")
    parser.add_argument("--ttl-minutes", type=int, default=90, help="Claim lease TTL in minutes (default: 90)")

    args = parser.parse_args()

    # Determine default tasks directory
    if args.out_dir:
        tasks_dir = args.out_dir
    elif os.path.isdir("workforces/tasks"):
        tasks_dir = "workforces/tasks"
    elif os.path.isdir(".scribe/tasks"):
        tasks_dir = ".scribe/tasks"
    elif os.path.isdir("workforces/issues/inbox"):
        tasks_dir = "workforces/tasks"
    else:
        tasks_dir = "workforces/tasks"

    # Search directories include standard task dirs and legacy issue dirs
    search_dirs = [
        tasks_dir,
        "workforces/tasks",
        ".scribe/tasks",
        "workforces/issues/inbox",
        "workforces/issues/triaged",
        "workforces/issues/completed",
    ]

    # Resolve priority
    effective_priority = args.priority_alias or args.priority
    active_harness = detect_active_harness(explicit=args.harness or None)

    # MODE -3: Reclaim Stale Claims
    if args.reclaim_stale:
        with _claim_lock(tasks_dir):
            reclaimed = _reclaim_expired_in_locked_dir(tasks_dir, datetime.datetime.now(datetime.timezone.utc))
        if reclaimed and not args.no_sync_workstate:
            root_dir = os.path.abspath(os.path.join(tasks_dir, "..", "..")) if ("workforces" in tasks_dir or ".scribe" in tasks_dir) else os.getcwd()
            sync_workstate_from_tasks(root_dir)
        if args.json:
            print(json.dumps({"reclaimed": reclaimed}, indent=2))
        else:
            print(f"♻️ Reclaimed {len(reclaimed)} stale task claim(s).")
        return

    # MODE -2: Atomic Claim Next (Priority 0 cross-harness review -> Priority 1 approved queue)
    if args.claim_next:
        claimed = claim_next_task(
            tasks_dir=tasks_dir,
            current_harness=active_harness,
            mode=args.mode,
            agent_name=args.agent or None,
            worktree=args.worktree or None,
            ttl_minutes=args.ttl_minutes,
        )
        if claimed and not args.no_sync_workstate:
            root_dir = os.path.abspath(os.path.join(tasks_dir, "..", "..")) if ("workforces" in tasks_dir or ".scribe" in tasks_dir) else os.getcwd()
            sync_workstate_from_tasks(root_dir)
        if args.json:
            print(json.dumps({"claimed": claimed}, indent=2))
        elif claimed:
            print(f"🔒 Claimed [{claimed['claim_kind']}] for `{active_harness}`: {claimed['title']} -> {claimed['path']}")
        else:
            print(f"No eligible tasks to claim for `{active_harness}` (mode={args.mode}).")
        return

    # MODE -1: Promote Issue to Task
    if args.promote_issue:
        issue_target = find_task_by_identifier(args.promote_issue, search_dirs)
        if not issue_target:
            print(f"❌ Error: Could not locate issue matching '{args.promote_issue}'", file=sys.stderr)
            sys.exit(1)
        new_task_path = promote_issue_to_task(
            issue_path=issue_target,
            tasks_dir=tasks_dir,
            approved=args.approve,
            cadence=args.cadence or "one_shot",
            priority_override=args.priority_alias or (args.priority if args.priority != "P2" else None),
            assignee=args.assignee,
        )
        if not args.no_sync_workstate:
            root_dir = os.path.abspath(os.path.join(tasks_dir, "..", "..")) if ("workforces" in tasks_dir or ".scribe" in tasks_dir) else os.getcwd()
            sync_workstate_from_tasks(root_dir)
        if args.json:
            print(json.dumps({"task_path": new_task_path, "approved_for_execution": bool(args.approve)}, indent=2))
        else:
            print(f"✅ Promoted issue to task: {new_task_path}")
        return

    # MODE 0: Reconcile GitHub Tasks
    if args.reconcile_github:
        root_dir = os.path.abspath(os.path.join(tasks_dir, "..", "..")) if ("workforces" in tasks_dir or ".scribe" in tasks_dir) else os.getcwd()
        reconciled = reconcile_github_tasks(root_dir)
        if not args.no_sync_workstate:
            sync_workstate_from_tasks(root_dir)
        if args.json:
            print(json.dumps(reconciled, indent=2))
        else:
            if not reconciled:
                print("Zero tasks needed reconciliation against GitHub.")
            else:
                print(f"🔄 Reconciled {len(reconciled)} task(s) against GitHub:")
                for r in reconciled:
                    print(f"  - [{r['status']}] {r['title']} ({r['reason']})")
        return

    # MODE 1: Find Similar Tasks
    if args.find_similar:
        results = find_similar_tasks(args.find_similar, search_dirs)
        if args.json:
            output = [
                {
                    "path": fpath,
                    "similarity": round(ratio, 2),
                    "title": meta.get("title", ""),
                    "type": meta.get("type", ""),
                    "priority": meta.get("priority", meta.get("severity", "")),
                    "status": meta.get("status", ""),
                    "session_id": meta.get("session_id"),
                }
                for fpath, ratio, meta in results
            ]
            print(json.dumps(output, indent=2))
        else:
            if not results:
                print(f"No similar tasks found for '{args.find_similar}'.")
            else:
                print(f"🔍 Found {len(results)} matching task(s):")
                for fpath, ratio, meta in results:
                    status_str = meta.get("status", "todo")
                    print(f"  - [{ratio:.0%}] ({status_str}) {meta.get('title', '')}")
                    print(f"    Path: {fpath}")
                    if meta.get("session_id"):
                        print(f"    Session: #{meta.get('session_id')}")
        return

    # MODE 2: List Tasks
    if args.list:
        tasks = []
        seen_paths = set()
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.abspath(os.path.join(d, fname))
                if fpath in seen_paths:
                    continue
                seen_paths.add(fpath)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        meta, _ = parse_frontmatter(f.read())
                        status_val = meta.get("status", "todo")
                        if args.status and status_val != args.status:
                            continue
                        tasks.append((fpath, meta))
                except OSError:
                    continue

        if args.json:
            print(json.dumps([{"path": p, **m} for p, m in tasks], indent=2))
        else:
            if not tasks:
                print("No tasks found.")
            else:
                print(f"📋 Found {len(tasks)} task(s):")
                for fpath, meta in tasks:
                    prio = meta.get("priority", meta.get("severity", "P2"))
                    st = meta.get("status", "todo")
                    ttype = meta.get("type", "task")
                    print(f"  - [{st}] [{prio}] ({ttype}) {meta.get('title', '')} -> {fpath}")
        return

    # MODE 3: Update Existing Task
    update_target = args.update or (args.drop_reason if (args.drop_reason and not args.title and os.path.exists(str(args.drop_reason))) else None)
    if update_target:
        target_file = find_task_by_identifier(update_target, search_dirs)
        if not target_file:
            print(f"❌ Error: Could not locate task matching '{update_target}'", file=sys.stderr)
            sys.exit(1)

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        now = datetime.datetime.now()

        # Update metadata fields if explicitly provided
        if args.title:
            meta["title"] = args.title
        if args.type and args.type != "task":
            meta["type"] = args.type
        if effective_priority and effective_priority != "P2":
            meta["priority"] = effective_priority
            if "severity" in meta:
                del meta["severity"]
        elif "severity" in meta and "priority" not in meta:
            meta["priority"] = meta.pop("severity")

        if args.reporter:
            meta["reporter"] = args.reporter
        if args.assignee:
            meta["assignee"] = args.assignee
        if args.file:
            meta["file"] = args.file
        if args.session_id:
            meta["session_id"] = args.session_id
        if args.chat_session_id:
            meta["chat_session_id"] = args.chat_session_id
        if args.session_file:
            meta["session_file"] = args.session_file
        if args.recommended_tools:
            tools_list = [t.strip() for t in args.recommended_tools.replace(",", " ").split() if t.strip()]
            meta["recommended_tools"] = tools_list
        if args.delegated_to:
            meta["delegated_to"] = args.delegated_to
        if args.github_labels:
            labels_list = [l.strip() for l in args.github_labels.replace(",", " ").split() if l.strip()]
            meta["github_labels"] = labels_list
        if args.github_issue:
            meta["github_issue"] = args.github_issue
        if args.github_pr:
            meta["github_pr"] = args.github_pr
        elif not meta.get("github_pr"):
            # Auto-detect PR from description or evolution note
            search_text = f"{args.description or ''} {args.suggested_action or ''} {args.evolution_note or ''}"
            url_match = re.search(r"https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/pull/\d+", search_text)
            if url_match:
                meta["github_pr"] = url_match.group(0)
            else:
                pr_match = re.search(r"(?:PR\s*#?|pull/)(\d{2,6})", search_text, re.IGNORECASE)
                if pr_match:
                    meta["github_pr"] = pr_match.group(1)

        # Handle status transitions & multi-harness review lifecycle
        if args.approve:
            meta["approved_for_execution"] = True
        elif args.unapprove:
            meta["approved_for_execution"] = False
        if args.cadence:
            meta["cadence"] = args.cadence
        if args.last_slice_date:
            meta["last_slice_date"] = args.last_slice_date

        if args.request_review:
            meta["status"] = "review"
            meta["review_state"] = "requires_code_review"
            meta["authored_by_harness"] = active_harness
            if meta.get("cadence") == "rolling_slice":
                meta["last_slice_date"] = datetime.date.today().isoformat()
            _clear_claim_fields(meta)
        elif args.complete_review:
            author_h = str(meta.get("authored_by_harness") or "").lower()
            if author_h and author_h == active_harness.lower() and not args.allow_same_harness:
                print(
                    f"❌ Error: Cross-harness review required (authored on `{author_h}`, cannot review on `{active_harness}` without --allow-same-harness).",
                    file=sys.stderr,
                )
                sys.exit(1)
            meta["reviewed_by_harness"] = active_harness
            _clear_claim_fields(meta)
            if args.complete_review == "approved":
                meta["review_state"] = "ready_for_human"
                meta["status"] = "done" if args.done_task else "review"
            else:
                meta["review_state"] = "changes_requested"
                meta["status"] = "todo"
                meta["approved_for_execution"] = True
        elif args.complete_slice:
            meta["status"] = "todo"
            meta["review_state"] = "none"
            meta["github_pr"] = None
            meta["last_slice_date"] = datetime.date.today().isoformat()
            _clear_claim_fields(meta)
        elif args.status:
            meta["status"] = args.status
        elif args.start_task:
            meta["status"] = "in_progress"
        elif args.review_task:
            meta["status"] = "review"
        elif args.block:
            meta["status"] = "blocked"
        elif args.done_task:
            meta["status"] = "done"
            _clear_claim_fields(meta)
        elif args.drop_reason:
            meta["status"] = "dropped"
            _clear_claim_fields(meta)

        if args.reviewer:
            meta["reviewer"] = args.reviewer
        elif meta.get("status") == "review" and not meta.get("reviewer"):
            meta["reviewer"] = "@human"

        # Remove legacy triage fields if present
        if "triage_status" in meta:
            del meta["triage_status"]

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

        # Handle deciding factor / evolution note
        evo_header = "## 🧠 Session Lineage & Deciding Factors"
        evo_entry = None
        drop_note = None

        if args.drop_reason:
            drop_note = args.drop_reason if (isinstance(args.drop_reason, str) and args.drop_reason.strip() and args.drop_reason != "true") else "Dropped by user during consultation."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ❌ Dropped: {drop_note}"
        elif args.request_review:
            note_text = args.evolution_note or f"Authored on `{active_harness}`; awaiting cross-harness review."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** 🔍 Requesting Cross-Harness Code Review: {note_text}"
        elif args.complete_review:
            r_notes = args.review_notes or args.evolution_note or args.complete_review
            badge = "✅ Review Approved (ready for human merge)" if args.complete_review == "approved" else "🔄 Review Changes Requested"
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** {badge} by `{active_harness}`: {r_notes}"
        elif args.complete_slice:
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** 🧩 Rolling slice completed for {meta.get('last_slice_date')}; next slice deferred to future day."
        elif args.block and isinstance(args.block, str) and args.block.strip() and args.block != "true":
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ⚠️ Blocked: {args.block}"
        elif args.done_task:
            note_text = args.evolution_note or "Task completed."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ✅ Completed: {note_text}"
        elif args.review_task or meta.get("status") == "review":
            note_text = args.evolution_note or f"Ready for review by {meta.get('reviewer', '@human')}."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** 🔍 Awaiting Review: {note_text}"
        elif args.start_task:
            note_text = args.evolution_note or "Started task execution."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ⏳ In Progress: {note_text}"
        elif args.evolution_note:
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** {args.evolution_note}"

        if evo_entry:
            if evo_header in body:
                parts = body.split(evo_header, 1)
                before = parts[0] + evo_header + "\n\n"
                after = parts[1].lstrip("\r\n")
                body = before + evo_entry + "\n" + after
            else:
                body = body.rstrip() + f"\n\n{evo_header}\n\n{evo_entry}\n"

        # Attach or update AI execution output if provided
        if getattr(args, "output", None) and args.output.strip():
            out_header = "## 🤖 AI Execution & Resolution Output"
            out_block = f"{out_header}\n\n{args.output.strip()}"
            if out_header in body:
                body = re.sub(r"## 🤖 AI Execution & Resolution Output\s*\n\n.*?(?=\n\n##|\Z)", out_block, body, flags=re.DOTALL)
            elif evo_header in body:
                body = body.replace(evo_header, f"{out_block}\n\n{evo_header}", 1)
            else:
                body = body.rstrip() + f"\n\n{out_block}\n"

        # Synchronize metadata badges in markdown body if present
        if meta.get("status"):
            body = re.sub(
                r"(\*\*Status:\*\*\s*`)[^`]+(`)",
                r"\g<1>" + meta["status"] + r"\g<2>",
                body
            )
            body = re.sub(
                r"(\|\s*Status:\s*)(?:todo|in_progress|blocked|done|dropped)",
                r"\g<1>" + meta["status"],
                body,
                flags=re.IGNORECASE
            )
        if meta.get("priority"):
            body = re.sub(
                r"(\*\*Priority:\*\*\s*`)[^`]+(`)",
                r"\g<1>" + meta["priority"] + r"\g<2>",
                body
            )
        if meta.get("team"):
            body = re.sub(
                r"(\*\*Team:\*\*\s*`)[^`]+(`)",
                r"\g<1>" + meta["team"] + r"\g<2>",
                body
            )
        body = re.sub(
            r"(\*\*Updated:\*\*\s*)[0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2})?",
            r"\g<1>" + now.strftime("%Y-%m-%d %H:%M"),
            body
        )

        # Update frontmatter & write in-place
        new_content = dump_frontmatter(meta, body)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Task updated: {target_file} (Status: {meta.get('status', 'todo')})")

        # Sync back to session file if requested
        session_file = args.session_file or meta.get("session_file")
        if (args.sync_session or session_file) and session_file:
            evo_summary = args.evolution_note or drop_note or (f"Status changed to {meta.get('status')}")
            sync_task_to_session_file(
                session_file,
                target_file,
                meta,
                evolution_summary=evo_summary
            )
            print(f"🔗 Synced to session context: {session_file}")

        # Synchronize workforces/workstate.md
        if not args.no_sync_workstate:
            root_dir = os.path.abspath(os.path.join(tasks_dir, "..", "..")) if ("workforces" in tasks_dir or ".scribe" in tasks_dir) else os.getcwd()
            sync_workstate_from_tasks(root_dir)

        return

    # MODE 4: Create New Task
    if not args.title:
        print("❌ Error: --title is required to create a new task.", file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        sys.exit(1)

    # Check for duplicates unless --force
    if not args.force:
        similar = find_similar_tasks(args.title, search_dirs, threshold=0.75)
        if similar:
            print("⚠️  Similar task(s) already exist — skipping to avoid duplicates:\n")
            for fpath, ratio, meta in similar:
                st = meta.get("status", "todo")
                print(f"   [{ratio:.0%} match] ({st}) {meta.get('title', extract_title(fpath))}")
                print(f"   → {fpath}\n")
            print("💡 Options:")
            print(f"   - Update existing: python3 {sys.argv[0]} --update \"{similar[0][0]}\" --evolution-note \"...\"")
            print(f"   - Drop existing:   python3 {sys.argv[0]} --update \"{similar[0][0]}\" --drop \"...\"")
            print("   - Force create anyway: re-run with --force")
            sys.exit(1)

    os.makedirs(tasks_dir, exist_ok=True)
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)
    filename = f"{timestamp}-{slug}.md"
    filepath = os.path.join(tasks_dir, filename)

    evolution_notes = []
    if args.evolution_note:
        evolution_notes.append(f"**{now.strftime('%Y-%m-%d %H:%M')}:** {args.evolution_note}")

    tools_list = [t.strip() for t in args.recommended_tools.replace(",", " ").split() if t.strip()] if args.recommended_tools else []
    labels_list = [l.strip() for l in args.github_labels.replace(",", " ").split() if l.strip()] if args.github_labels else []

    init_status = args.status or ("in_progress" if args.start_task else "todo")

    # Auto-detect PR if not passed explicitly
    detected_pr = args.github_pr
    if not detected_pr:
        search_text = f"{args.description or ''} {args.suggested_action or ''} {args.evolution_note or ''}"
        url_match = re.search(r"https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/pull/\d+", search_text)
        if url_match:
            detected_pr = url_match.group(0)
        else:
            pr_match = re.search(r"(?:PR\s*#?|pull/)(\d{2,6})", search_text, re.IGNORECASE)
            if pr_match:
                detected_pr = pr_match.group(1)

    content = build_task_markdown(
        title=args.title,
        task_type=args.type,
        priority=effective_priority,
        status=init_status,
        reporter=args.reporter or "wf-scribe",
        assignee=args.assignee,
        description=args.description,
        suggested_action=args.suggested_action,
        file_path=args.file,
        session_id=args.session_id,
        chat_session_id=args.chat_session_id,
        session_file=args.session_file,
        recommended_tools=tools_list,
        delegated_to=args.delegated_to,
        github_labels=labels_list,
        github_issue=args.github_issue,
        github_pr=detected_pr,
        evolution_notes=evolution_notes,
        created_at=now,
        updated_at=now,
        approved_for_execution=True if args.approve else None,
        cadence=args.cadence,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Task created: {filepath}")

    if args.sync_session and args.session_file:
        meta_dict = {
            "title": args.title,
            "type": args.type,
            "priority": effective_priority,
            "status": init_status,
            "assignee": args.assignee,
            "description": args.description,
            "recommended_tools": tools_list,
            "delegated_to": args.delegated_to,
            "github_labels": labels_list,
            "github_pr": detected_pr,
        }
        sync_task_to_session_file(
            args.session_file,
            filepath,
            meta_dict,
            evolution_summary=args.evolution_note or args.description[:100]
        )
        print(f"🔗 Synced to session context: {args.session_file}")

    # Synchronize workforces/workstate.md
    if not args.no_sync_workstate:
        root_dir = os.path.abspath(os.path.join(tasks_dir, "..", "..")) if ("workforces" in tasks_dir or ".scribe" in tasks_dir) else os.getcwd()
        sync_workstate_from_tasks(root_dir)


if __name__ == "__main__":
    main()
