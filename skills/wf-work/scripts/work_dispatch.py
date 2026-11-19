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
import inspect
import json
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

_HOST_SKILL_BASES = (".agents", ".claude", ".grok", ".github", ".github/copilot", ".cursor", "")


def _load_sibling_script(skill_name: str, script_name: str, repo_root: Optional[Path] = None):
    """Locate and load a skill script across source `skills/` and installed host directories."""
    script_file = Path(__file__).resolve()
    candidates: List[Path] = []
    if skill_name == "wf-work":
        candidates.append(script_file.parent / script_name)
    if len(script_file.parents) > 2:
        candidates.append(script_file.parents[2] / skill_name / "scripts" / script_name)
    if repo_root is not None:
        for base in _HOST_SKILL_BASES:
            root_base = (repo_root / base) if base else repo_root
            candidates.append(root_base / "skills" / skill_name / "scripts" / script_name)

    target = next((p for p in candidates if p.is_file()), None)
    if target is None:
        return None
    spec = importlib.util.spec_from_file_location(f"wf_{skill_name}_{target.stem}", str(target))
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
        return []
    return []


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


def _try_claim_review(
    repo_root: Path,
    tasks_dir: Path,
    task_mod: Any,
    active_harness: str,
    agent: Optional[str],
    worktree: Optional[str],
    skip_gh: bool,
    only_review: bool,
) -> Optional[Dict[str, Any]]:
    """Attempt Priority 0 cross-harness code review claim."""
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
    if only_review:
        return {
            "action": "idle" if not open_prs else "review_open_prs",
            "harness": active_harness,
            "claimed_task": None,
            "open_prs": open_prs,
            "message": "No cross-harness tasks awaiting review." if not open_prs else f"{len(open_prs)} open GitHub PR(s) available for inspection.",
        }
    return None


def _try_claim_approved_exec(
    tasks_dir: Path,
    task_mod: Any,
    active_harness: str,
    agent: Optional[str],
    worktree: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Attempt Priority 1 pre-approved task claim with rolling slice protection."""
    claimed_exec = task_mod.claim_next_task(
        tasks_dir=str(tasks_dir),
        current_harness=active_harness,
        mode="auto",
        agent_name=agent,
        worktree=worktree,
    )
    if not claimed_exec:
        return None
    is_rolling = claimed_exec.get("cadence") == "rolling_slice"
    task_type = str(claimed_exec.get("type") or "").lower()
    target_repo = str(claimed_exec.get("repo") or "").strip()
    repo_note = f" (target repo: `{target_repo}`)" if target_repo else ""
    if task_type == "docs":
        instructions = (
            f"Work in an isolated `docs/...` branch/worktree{repo_note}. Follow `wf-doc-generator`: "
            "(1) author/enrich `<repo>/docs/architecture/<module>.md` (`doc_status: documented`, refactor-ready OKF schema) "
            "and refresh `docs/index.md` via `scaffold_repo_okf.py --scan`, "
            "(2) add concise 2-4 line module/class boundary docblocks, public docstrings, and inline 'why' comments in the module's source files, "
            "(3) run `post_code_reviewer.py --run-checks --strict`, open a Draft PR, and hand off via `--request-review`."
        )
    else:
        instructions = (
            f"Work in an isolated branch/worktree (`feat/...`, `fix/...`, or `refactor/...`){repo_note}. "
            "First inspect matching `<repo>/docs/architecture/*.md` cards and run `pre_impact_analyzer.py --file <target>`; "
            "if rolling_slice, extract only 1-3 small helper blocks; keep `docs/architecture/*.md` (`affected_files`, `Constraints & Why`, `last_verified_commit`) synced; "
            "run `post_code_reviewer.py --run-checks --strict`, open a Draft PR, and hand off via `--request-review`."
        )
    return {
        "action": "execute_approved_task",
        "harness": active_harness,
        "claimed_task": claimed_exec,
        "rolling_slice": is_rolling,
        "instructions": instructions,
    }


def _tag_candidates_repo(findings: Dict[str, Any], repo_label: str) -> None:
    """Annotate discovery issue candidates with `[repo_label]` prefix and `repo` metadata."""
    if not repo_label:
        return
    prefix = f"[{repo_label}] "
    for cand in findings.get("issue_candidates") or []:
        if not cand.get("repo"):
            cand["repo"] = repo_label
        title = str(cand.get("title") or "")
        if title and not title.startswith(prefix):
            cand["title"] = f"{prefix}{title}"


def _run_discovery_sweep(
    canonical_mode: str,
    repo_root: Path,
    scanners_mod: Any,
    okf_mod: Any,
    repo_label: str = "",
) -> Dict[str, Any]:
    """Execute concrete read-only discovery sweep for the selected mode."""
    if scanners_mod is None:
        return {"sweep_focus": canonical_mode, "issue_candidates": []}
    if canonical_mode == "docs":
        findings = scanners_mod.run_docs_sweep(repo_root, okf_mod, repo_label=repo_label)
    elif canonical_mode == "debt":
        findings = scanners_mod.run_debt_sweep(repo_root)
    elif canonical_mode == "security":
        findings = scanners_mod.run_security_sweep(repo_root)
    elif canonical_mode == "design":
        findings = scanners_mod.run_design_sweep(repo_root)
    elif canonical_mode == "optimization":
        findings = scanners_mod.run_optimization_sweep(repo_root)
    elif canonical_mode == "housekeeping":
        findings = scanners_mod.run_housekeeping_sweep(repo_root)
    else:
        findings = {"sweep_focus": canonical_mode, "issue_candidates": []}
    _tag_candidates_repo(findings, repo_label)
    return findings


def _is_duplicate_candidate(cand: Dict[str, Any], title: str, search_dirs: List[str], issue_mod: Any) -> bool:
    """Return True if an existing issue matches `title` within the same `(repo, file)` scope."""
    matches = issue_mod.find_similar_issues(title, search_dirs, threshold=0.78)
    if not matches:
        return False
    cand_repo = str(cand.get("repo") or "").strip().lower()
    cand_file = str(cand.get("file") or "").strip().lower()
    for _, _, meta in matches:
        match_repo = str(meta.get("repo") or "").strip().lower()
        match_file = str(meta.get("file") or "").strip().lower()
        if cand_repo != match_repo:
            continue
        if cand_file and match_file and cand_file != match_file:
            continue
        return True
    return False


def _log_discovery_candidates(
    repo_root: Path,
    active_harness: str,
    gate: Dict[str, Any],
    findings: Dict[str, Any],
    issue_mod: Any,
    inbox_offset: int = 0,
) -> List[str]:
    """Log bounded, deduplicated discovery findings into `workforces/issues/inbox/`."""
    if issue_mod is None:
        return []
    candidates = findings.get("issue_candidates") or []
    if not candidates:
        return []

    inbox_dir = repo_root / "workforces" / "issues" / "inbox"
    search_dirs = [
        str(inbox_dir),
        str(repo_root / "workforces" / "issues" / "triaged"),
        str(repo_root / "workforces" / "issues" / "completed"),
    ]
    current_inbox = int(gate.get("inbox_count", 0)) + inbox_offset
    max_inbox = int(gate.get("max_untriaged_inbox", 15))
    allowance = min(3, max(0, max_inbox - current_inbox)) if max_inbox > 0 else 3
    if allowance <= 0:
        return []

    supports_repo = "repo" in inspect.signature(issue_mod.build_issue_markdown).parameters
    inbox_dir.mkdir(parents=True, exist_ok=True)
    logged: List[str] = []
    for cand in candidates:
        if len(logged) >= allowance:
            break
        title = str(cand.get("title") or "").strip()
        if not title or _is_duplicate_candidate(cand, title, search_dirs, issue_mod):
            continue
        out_file = inbox_dir / f"auto-{issue_mod.slugify(title.replace('/', '-'))}.md"
        if out_file.exists():
            continue
        kwargs: Dict[str, Any] = {
            "title": title,
            "issue_type": str(cand.get("type") or "chore"),
            "severity": str(cand.get("severity") or "P2"),
            "reporter": f"wf-work:{active_harness}",
            "description": str(cand.get("description") or title),
            "suggested_action": str(cand.get("suggested_action") or "Review and promote via `/wf-sync --daily`."),
            "file_path": str(cand.get("file") or ""),
        }
        if supports_repo and cand.get("repo"):
            kwargs["repo"] = str(cand["repo"])
        out_file.write_text(issue_mod.build_issue_markdown(**kwargs), encoding="utf-8")
        logged.append(str(out_file))
    return logged


def _build_needs_repo_response(canonical_mode: str, active_harness: str, resolved: Dict[str, Any]) -> Dict[str, Any]:
    """Build non-mutating disambiguation response when target repository is ambiguous."""
    return {
        "action": "needs_repo_selection",
        "mode": canonical_mode,
        "harness": active_harness,
        "ambiguous": True,
        "reason": resolved.get("reason"),
        "available_repos": resolved.get("available_repos", []),
        "question": (
            f"Multiple configured repositories were found. Which repository should `/wf-work {canonical_mode}` run on? "
            "Specify a repo name/slug, or pass `--repo all` to run across all configured repositories."
        ),
    }


def _execute_discovery_phase(
    repo_root: Path,
    canonical_mode: str,
    active_harness: str,
    gate: Dict[str, Any],
    repo: Optional[str],
    log_to_inbox: bool,
    scanners_mod: Any,
    okf_mod: Any,
    issue_mod: Any,
    repo_scope_mod: Any,
) -> Dict[str, Any]:
    """Resolve single vs. multi-repo target(s) and execute bounded discovery sweeps."""
    fallback = [{"name": repo_root.name, "slug": repo_root.name, "path": str(repo_root), "is_workspace_root": True}]
    if repo_scope_mod is not None:
        resolved = repo_scope_mod.resolve_repo_targets(repo_root, repo_arg=repo)
        if resolved.get("status") == "ambiguous":
            return _build_needs_repo_response(canonical_mode, active_harness, resolved)
        targets = resolved.get("targets") or fallback
        scope = resolved.get("scope", "single")
    else:
        targets = fallback
        scope = "single"

    policy_note = "Never open unsolicited PRs during discovery; log findings to workforces/issues/inbox/ via report-issue.py."
    if len(targets) == 1 and scope != "all":
        t = targets[0]
        repo_label = "" if t.get("is_workspace_root") else str(t.get("name") or "")
        findings = _run_discovery_sweep(canonical_mode, Path(t["path"]), scanners_mod, okf_mod, repo_label=repo_label)
        logged_issues = _log_discovery_candidates(repo_root, active_harness, gate, findings, issue_mod) if log_to_inbox else []
        return {
            "action": "discovery",
            "mode": canonical_mode,
            "harness": active_harness,
            "gate": gate,
            "target_repo": t,
            "findings": findings,
            "logged_issues": logged_issues,
            "policy": policy_note,
        }

    results_by_repo: Dict[str, Any] = {}
    merged_candidates: List[Dict[str, Any]] = []
    all_logged: List[str] = []
    for t in targets:
        r_name = str(t.get("name") or Path(t["path"]).name)
        r_findings = _run_discovery_sweep(canonical_mode, Path(t["path"]), scanners_mod, okf_mod, repo_label=r_name)
        results_by_repo[r_name] = r_findings
        merged_candidates.extend(r_findings.get("issue_candidates") or [])
        if log_to_inbox:
            all_logged.extend(_log_discovery_candidates(repo_root, active_harness, gate, r_findings, issue_mod, inbox_offset=len(all_logged)))

    return {
        "action": "discovery",
        "mode": canonical_mode,
        "scope": "all",
        "harness": active_harness,
        "gate": gate,
        "repos": [str(t.get("name") or "") for t in targets],
        "results_by_repo": results_by_repo,
        "findings": {"issue_candidates": merged_candidates, "repo_count": len(targets)},
        "logged_issues": all_logged,
        "policy": policy_note,
    }


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
    log_to_inbox: bool = True,
    repo: Optional[str] = None,
) -> Dict[str, Any]:
    """Run gate checks, claim priority work, or execute bounded discovery sweeps."""
    canonical_mode = MODE_ALIASES.get(mode.strip().lower())
    if not canonical_mode:
        raise ValueError(f"Unsupported /wf-work mode: {mode}")

    budget_mod = _load_sibling_script("wf-usage-tracker", "budget_gate.py", repo_root=repo_root)
    task_mod = _load_sibling_script("wf-task-tracker", "report-task.py", repo_root=repo_root)
    okf_mod = _load_sibling_script("wf-doc-generator", "scaffold_repo_okf.py", repo_root=repo_root)
    issue_mod = _load_sibling_script("wf-issue-tracker", "report-issue.py", repo_root=repo_root)
    scanners_mod = _load_sibling_script("wf-work", "discovery_scanners.py", repo_root=repo_root)
    repo_scope_mod = _load_sibling_script("wf-work", "repo_scope.py", repo_root=repo_root)
    if not budget_mod or not task_mod:
        raise RuntimeError("Required sibling scripts (budget_gate.py / report-task.py) not found.")

    active_harness = budget_mod.detect_active_harness(explicit=harness, repo_root=repo_root)
    tasks_dir = repo_root / "workforces" / "tasks"

    if canonical_mode == "pause":
        return {"action": "paused", "harness": active_harness, "work_control": budget_mod.set_discovery_state(repo_root, "paused", reason=reason)}
    if canonical_mode == "resume":
        return {"action": "resumed", "harness": active_harness, "work_control": budget_mod.set_discovery_state(repo_root, "active")}
    if canonical_mode == "status":
        gate = budget_mod.evaluate_budget_gate(repo_root, mode="docs", harness=active_harness, ignore_idle=True)
        return {"action": "status", "harness": active_harness, "gate": gate, "queue": _collect_queue_summary(tasks_dir, task_mod)}

    if canonical_mode in ("codereview", "auto"):
        rev = _try_claim_review(repo_root, tasks_dir, task_mod, active_harness, agent, worktree, skip_gh, canonical_mode == "codereview")
        if rev is not None:
            return rev

    gate = budget_mod.evaluate_budget_gate(
        repo_root, mode=canonical_mode, harness=active_harness, ignore_idle=ignore_idle, window_remaining_minutes=window_remaining_minutes
    )
    if canonical_mode == "auto":
        if gate["code"] in ("token_budget_exhausted", "harness_recently_active"):
            return {"action": "halted", "harness": active_harness, "gate": gate}
        claimed = _try_claim_approved_exec(tasks_dir, task_mod, active_harness, agent, worktree)
        if claimed is not None:
            return claimed
        gate = budget_mod.evaluate_budget_gate(
            repo_root, mode="docs", harness=active_harness, ignore_idle=ignore_idle, window_remaining_minutes=window_remaining_minutes
        )
        canonical_mode = "docs"

    if not gate["allowed"]:
        return {"action": "halted", "harness": active_harness, "gate": gate}

    return _execute_discovery_phase(
        repo_root, canonical_mode, active_harness, gate, repo, log_to_inbox, scanners_mod, okf_mod, issue_mod, repo_scope_mod
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch token-aware `/wf-work` sweeps.")
    parser.add_argument("mode", nargs="?", default="auto", help="auto|codereview|docs|security|design|optimization|debt|housekeeping|status|pause|resume")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--repo", default=None, help="Target configured/sibling repository name, slug, path, or 'all'")
    parser.add_argument("--harness", help="Override active harness (`antigravity`, `claude`, `grok`)")
    parser.add_argument("--agent", help="Worker agent label for task claim attribution")
    parser.add_argument("--worktree", help="Worktree/branch label for task claim attribution")
    parser.add_argument("--reason", default="", help="Reason when pausing discovery")
    parser.add_argument("--ignore-idle", action="store_true", help="Ignore harness idle threshold")
    parser.add_argument("--window-remaining-minutes", type=int, default=None, help="Remaining quota window minutes")
    parser.add_argument("--skip-gh", action="store_true", help="Skip GitHub CLI queries")
    parser.add_argument("--log-to-inbox", dest="log_to_inbox", action="store_true", default=True, help="Log deduplicated discovery findings to issues/inbox/ (default)")
    parser.add_argument("--no-log-to-inbox", dest="log_to_inbox", action="store_false", help="Run discovery without writing to issues/inbox/")
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
        repo=args.repo,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    elif result.get("action") == "needs_repo_selection":
        print(f"❓ {result.get('question')}")
        for r in result.get("available_repos", []):
            print(f"  - {r.get('name')} ({r.get('slug')}) -> {r.get('path')}")
    else:
        print(f"⚙️ /wf-work [{result.get('harness')}] -> {result['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
