#!/usr/bin/env python3
"""
Work Queue & Maintenance Dispatcher (`/wf-work`)

Coordinates:
- Priority 0: Cross-harness adversarial code review (`codereview` / `auto`)
- Priority 1: Approved execution queue with rolling 1-bite-per-day slice guard (`auto`)
- Priority 2: Token-gated, PM-controllable read-only discovery sweeps
              (`docs`, `security`, `design`, `optimization`, `debt`, `housekeeping`)
- Control commands: `status`, `pause`, `resume`
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


MODE_ALIASES: Dict[str, str] = {
    "auto": "auto",
    "codereview": "codereview",
    "review": "codereview",
    "docs": "docs",
    "security": "security",
    "design": "design",
    "ux": "design",
    "optimization": "optimization",
    "perf": "optimization",
    "debt": "debt",
    "todo": "debt",
    "refactor": "debt",
    "housekeeping": "housekeeping",
    "deps": "housekeeping",
    "status": "status",
    "pause": "pause",
    "resume": "resume",
}

SCAN_IGNORE_DIRS = frozenset({
    ".git", ".worktrees", "node_modules", "vendor", "__pycache__",
    ".venv", "venv", "dist", "build", ".next", "target", "workforces",
})
CODE_EXTS = frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".php", ".rs", ".java", ".rb"})
TODO_RE = re.compile(r"(?:#|//|/\*|\*)\s*\b(TODO|FIXME|HACK|XXX)\b[:\s-]*(.*)", re.IGNORECASE)


def _load_sibling_script(skill_name: str, script_name: str):
    """Load a sibling skill script dynamically (works from source or `.agents`)."""
    here = Path(__file__).resolve().parent
    candidate = here.parent.parent / skill_name / "scripts" / script_name
    if not candidate.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"wf_{skill_name}_{candidate.stem}", str(candidate))
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _list_open_github_prs(repo_root: Path) -> List[Dict[str, Any]]:
    """Best-effort read-only listing of open non-merged PRs via `gh` CLI."""
    try:
        res = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,isDraft,author,url", "--limit", "20"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            parsed = json.loads(res.stdout)
            return parsed if isinstance(parsed, list) else []
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return []


def _scan_debt_hotspots(repo_root: Path, max_files: int = 200) -> Dict[str, Any]:
    """Bounded read-only scan for `TODO`/`FIXME` items and giant files (>600 lines)."""
    todos: List[Dict[str, Any]] = []
    giant_files: List[Dict[str, Any]] = []
    scanned = 0

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in SCAN_IGNORE_DIRS)
        for fname in sorted(files):
            if Path(fname).suffix.lower() not in CODE_EXTS:
                continue
            fpath = Path(root) / fname
            rel = fpath.relative_to(repo_root).as_posix()
            scanned += 1
            try:
                lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            if len(lines) >= 600:
                giant_files.append({"file": rel, "lines": len(lines)})
            for lineno, line in enumerate(lines, 1):
                match = TODO_RE.search(line)
                if match:
                    todos.append({
                        "file": rel,
                        "line": lineno,
                        "tag": match.group(1).upper(),
                        "text": match.group(2).strip()[:120],
                    })
                if len(todos) >= 30:
                    break
            if scanned >= max_files:
                break
        if scanned >= max_files:
            break

    return {
        "files_scanned": scanned,
        "todo_hits": todos[:15],
        "giant_files": sorted(giant_files, key=lambda x: x["lines"], reverse=True)[:10],
    }


def _collect_queue_summary(tasks_dir: Path, task_mod: Any) -> Dict[str, Any]:
    """Summarize task queue counts, awaiting cross-harness reviews, and active claims."""
    summary: Dict[str, Any] = {
        "awaiting_cross_review": 0,
        "approved_queued": 0,
        "in_progress": 0,
        "active_claims": [],
    }
    if not tasks_dir.is_dir():
        return summary

    for fpath in sorted(tasks_dir.glob("*.md")):
        try:
            meta, _ = task_mod.parse_frontmatter(fpath.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        status = str(meta.get("status") or "todo").lower()
        r_state = str(meta.get("review_state") or "none").lower()
        if r_state == "requires_code_review" or (status == "review" and r_state not in ("ready_for_human", "in_review")):
            summary["awaiting_cross_review"] += 1
        if status == "todo" and meta.get("approved_for_execution") is True:
            summary["approved_queued"] += 1
        if status == "in_progress":
            summary["in_progress"] += 1
        if meta.get("claimed_by_harness"):
            summary["active_claims"].append({
                "title": meta.get("title", fpath.name),
                "harness": meta.get("claimed_by_harness"),
                "agent": meta.get("claimed_by_agent"),
                "worktree": meta.get("claimed_worktree"),
                "expires_at": meta.get("claim_expires_at"),
            })
    return summary


def dispatch_work(
    repo_root: Path,
    mode: str = "auto",
    harness: Optional[str] = None,
    agent: Optional[str] = None,
    worktree: Optional[str] = None,
    reason: str = "",
    ignore_idle: bool = False,
    window_remaining_minutes: Optional[int] = None,
    skip_gh: bool = False,
    log_to_inbox: bool = False,
) -> Dict[str, Any]:
    """Run gate checks, claim priority work, or execute bounded discovery sweeps."""
    canonical_mode = MODE_ALIASES.get(mode.strip().lower())
    if not canonical_mode:
        raise ValueError(f"Unsupported /wf-work mode: {mode}")

    budget_mod = _load_sibling_script("wf-usage-tracker", "budget_gate.py")
    task_mod = _load_sibling_script("wf-task-tracker", "report-task.py")
    okf_mod = _load_sibling_script("wf-doc-generator", "scaffold_repo_okf.py")
    issue_mod = _load_sibling_script("wf-issue-tracker", "report-issue.py")
    if not budget_mod or not task_mod:
        raise RuntimeError("Required sibling scripts (budget_gate.py / report-task.py) not found.")

    active_harness = budget_mod.detect_active_harness(explicit=harness, repo_root=repo_root)
    tasks_dir = repo_root / "workforces" / "tasks"

    if canonical_mode == "pause":
        wc = budget_mod.set_discovery_state(repo_root, "paused", reason=reason)
        return {"action": "paused", "harness": active_harness, "work_control": wc}

    if canonical_mode == "resume":
        wc = budget_mod.set_discovery_state(repo_root, "active")
        return {"action": "resumed", "harness": active_harness, "work_control": wc}

    if canonical_mode == "status":
        gate = budget_mod.evaluate_budget_gate(repo_root, mode="docs", harness=active_harness, ignore_idle=True)
        queue = _collect_queue_summary(tasks_dir, task_mod)
        return {"action": "status", "harness": active_harness, "gate": gate, "queue": queue}

    # Priority 0: Cross-Harness Code Review (`codereview` or first phase of `auto`)
    if canonical_mode in ("codereview", "auto"):
        claimed_review = task_mod.claim_next_task(
            tasks_dir=str(tasks_dir),
            current_harness=active_harness,
            mode="codereview",
            agent_name=agent,
            worktree=worktree,
        )
        open_prs = [] if skip_gh else _list_open_github_prs(repo_root)
        if claimed_review:
            return {
                "action": "codereview",
                "harness": active_harness,
                "claimed_task": claimed_review,
                "open_prs": open_prs,
                "instructions": (
                    "Review diff against `<repo>/docs/index.md` + `wf-pr-review` (Option A: NEVER call `gh pr merge` or deploy). "
                    f"Record verdict via `report-task.py --update \"{claimed_review['path']}\" --complete-review approved|changes_requested`."
                ),
            }
        if canonical_mode == "codereview":
            return {
                "action": "idle" if not open_prs else "review_open_prs",
                "harness": active_harness,
                "claimed_task": None,
                "open_prs": open_prs,
                "message": "No cross-harness tasks awaiting review." if not open_prs else f"{len(open_prs)} open GitHub PR(s) available for inspection.",
            }

    # Check token & idle budget before execution/discovery
    gate = budget_mod.evaluate_budget_gate(
        repo_root,
        mode=canonical_mode,
        harness=active_harness,
        ignore_idle=ignore_idle,
        window_remaining_minutes=window_remaining_minutes,
    )

    # Priority 1: Pre-approved execution queue (`auto` only; bypasses discovery pause)
    if canonical_mode == "auto":
        if gate["code"] in ("token_budget_exhausted", "harness_recently_active"):
            return {"action": "halted", "harness": active_harness, "gate": gate}
        claimed_exec = task_mod.claim_next_task(
            tasks_dir=str(tasks_dir),
            current_harness=active_harness,
            mode="auto",
            agent_name=agent,
            worktree=worktree,
        )
        if claimed_exec:
            is_rolling = claimed_exec.get("cadence") == "rolling_slice"
            return {
                "action": "execute_approved_task",
                "harness": active_harness,
                "claimed_task": claimed_exec,
                "rolling_slice": is_rolling,
                "instructions": (
                    "Work in an isolated branch/worktree (`feat/...` or `refactor/...`), extract only 1-3 small helper blocks if rolling_slice, "
                    "run `post_code_reviewer.py --run-checks --strict`, open a Draft PR, and hand off via `--request-review`."
                ),
            }
        # Fall through to discovery (`docs`) only if discovery is allowed
        discovery_gate = budget_mod.evaluate_budget_gate(
            repo_root,
            mode="docs",
            harness=active_harness,
            ignore_idle=ignore_idle,
            window_remaining_minutes=window_remaining_minutes,
        )
        if not discovery_gate["allowed"]:
            return {"action": "halted", "harness": active_harness, "gate": discovery_gate}
        canonical_mode = "docs"
        gate = discovery_gate

    if not gate["allowed"]:
        return {"action": "halted", "harness": active_harness, "gate": gate}

    # Priority 2: Bounded Read-Only Discovery Sweeps
    findings: Dict[str, Any] = {}
    logged_issues: List[str] = []

    if canonical_mode == "docs" and okf_mod:
        findings = okf_mod.audit_hygiene(repo_root)
    elif canonical_mode == "debt":
        findings = _scan_debt_hotspots(repo_root)
    else:
        findings = {
            "sweep_focus": canonical_mode,
            "policy": "Read-only audit; log deduplicated findings to workforces/issues/inbox/ for PM triage. Never open unsolicited PRs.",
        }

    if log_to_inbox and issue_mod:
        inbox_dir = repo_root / "workforces" / "issues" / "inbox"
        triaged_dir = repo_root / "workforces" / "issues" / "triaged"
        completed_dir = repo_root / "workforces" / "issues" / "completed"
        search_dirs = [str(inbox_dir), str(triaged_dir), str(completed_dir)]
        inbox_dir.mkdir(parents=True, exist_ok=True)
        for gf in findings.get("giant_files", [])[:1]:
            title = f"Rolling 1-bite/day refactor: {gf['file']}"
            if not issue_mod.find_similar_issues(title, search_dirs, threshold=0.78):
                slug = issue_mod.slugify(title)
                out_file = inbox_dir / f"rolling-{slug}.md"
                out_file.write_text(
                    issue_mod.build_issue_markdown(
                        title=title,
                        issue_type="refactor",
                        severity="P2",
                        reporter=f"wf-work:{active_harness}",
                        description=f"`{gf['file']}` is {gf['lines']} lines. Propose rolling 1-slice-per-day decomposition (1-3 helpers per Draft PR).",
                        suggested_action="Promote via report-task.py --promote-issue --cadence rolling_slice --approve once approved.",
                        file_path=gf["file"],
                    ),
                    encoding="utf-8",
                )
                logged_issues.append(str(out_file))

    return {
        "action": "discovery",
        "mode": canonical_mode,
        "harness": active_harness,
        "gate": gate,
        "findings": findings,
        "logged_issues": logged_issues,
        "policy": "Never open unsolicited PRs during discovery; log findings to workforces/issues/inbox/ via report-issue.py.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch token-aware `/wf-work` sweeps.")
    parser.add_argument("mode", nargs="?", default="auto", help="auto|codereview|docs|security|design|optimization|debt|housekeeping|status|pause|resume")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--harness", help="Override active harness (`antigravity`, `claude`, `grok`)")
    parser.add_argument("--agent", help="Worker agent label for task claim attribution")
    parser.add_argument("--worktree", help="Worktree/branch label for task claim attribution")
    parser.add_argument("--reason", default="", help="Reason when pausing discovery")
    parser.add_argument("--ignore-idle", action="store_true", help="Ignore harness idle threshold")
    parser.add_argument("--window-remaining-minutes", type=int, default=None, help="Remaining quota window minutes")
    parser.add_argument("--skip-gh", action="store_true", help="Skip GitHub CLI queries")
    parser.add_argument("--log-to-inbox", action="store_true", help="Log top deterministic discovery finding to issues/inbox/")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    result = dispatch_work(
        repo_root=Path(args.root).resolve(),
        mode=args.mode,
        harness=args.harness,
        agent=args.agent,
        worktree=args.worktree,
        reason=args.reason,
        ignore_idle=args.ignore_idle,
        window_remaining_minutes=args.window_remaining_minutes,
        skip_gh=args.skip_gh,
        log_to_inbox=args.log_to_inbox,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"⚙️ /wf-work [{result.get('harness')}] -> {result['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
