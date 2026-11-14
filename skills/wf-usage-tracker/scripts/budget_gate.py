#!/usr/bin/env python3
"""
Token Budget, Harness Detection & PM Issue-Discovery Kill-Switch Gate

Governs background `/wf-work` sweeps across Antigravity, Claude Code, and Grok:
- Detects active harness (`antigravity`, `claude`, `grok`)
- Enforces `workforces/config.json -> work_control.issue_discovery` (`active` vs `paused`)
- Enforces `max_untriaged_inbox` backpressure check-in cap before discovery sweeps
- Estimates harness token consumption / idle headroom from local session logs
  (`codereview` and pre-approved queue execution bypass discovery pauses/caps)

Exit codes for `--check`:
  0  Allowed to proceed
  2  Gated (discovery paused, inbox cap reached, or token budget exhausted)
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


CHAR_PER_TOKEN = 4.0
DEFAULT_WORK_CONTROL: Dict[str, Any] = {
    "issue_discovery": "active",
    "paused_reason": "",
    "paused_at": None,
    "max_untriaged_inbox": 15,
    "min_idle_minutes": 0,
    "max_daily_tokens": 0,
}

DISCOVERY_MODES = frozenset({
    "docs",
    "security",
    "design",
    "optimization",
    "debt",
    "housekeeping",
    "discovery",
})


def detect_active_harness(explicit: Optional[str] = None, repo_root: Optional[Path] = None) -> str:
    """Detect which AI coding harness is currently executing (`antigravity`, `claude`, or `grok`)."""
    if explicit:
        return explicit.strip().lower()
    if os.environ.get("WORKFORCE_HARNESS"):
        return os.environ["WORKFORCE_HARNESS"].strip().lower()
    if os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or os.environ.get("ANTIGRAVITY_AGENT") or os.environ.get("AGY_ACCOUNT"):
        return "antigravity"
    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_SESSION_ID"):
        return "claude"
    if os.environ.get("GROK_PROJECT_DIR") or os.environ.get("GROK_CLI") or os.environ.get("GROK_SESSION_ID"):
        return "grok"

    if repo_root:
        cfg = load_config(repo_root)
        hosts = cfg.get("hosts") or []
        if isinstance(hosts, list) and hosts:
            return str(hosts[0]).lower()
    return "antigravity"


def load_config(repo_root: Path) -> Dict[str, Any]:
    """Load `workforces/config.json` safely, returning `{}` if missing or malformed."""
    cfg_path = repo_root / "workforces" / "config.json"
    if not cfg_path.is_file():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(repo_root: Path, cfg: Dict[str, Any]) -> Path:
    """Persist updated `workforces/config.json` cleanly."""
    cfg_path = repo_root / "workforces" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return cfg_path


def get_work_control(repo_root: Path) -> Dict[str, Any]:
    """Return merged `work_control` settings with defaults."""
    cfg = load_config(repo_root)
    merged = dict(DEFAULT_WORK_CONTROL)
    raw_wc = cfg.get("work_control")
    if isinstance(raw_wc, dict):
        merged.update(raw_wc)
    return merged


def count_untriaged_inbox(repo_root: Path) -> int:
    """Count pending issue markdown files awaiting PM triage in `workforces/issues/inbox/`."""
    inbox_dir = repo_root / "workforces" / "issues" / "inbox"
    if not inbox_dir.is_dir():
        return 0
    return sum(1 for p in inbox_dir.iterdir() if p.is_file() and p.name.endswith(".md"))


def _scan_recent_jsonl_usage(paths: List[str], now_ts: float) -> Dict[str, Any]:
    """Estimate today's token volume and last-activity age across JSONL session logs."""
    today_prefix = datetime.datetime.now().strftime("%Y-%m-%d")
    today_chars = 0
    latest_mtime = 0.0
    scanned = 0

    for fpath in paths:
        try:
            st = os.stat(fpath)
        except OSError:
            continue
        if st.st_mtime > latest_mtime:
            latest_mtime = st.st_mtime
        # Only parse JSONL files modified today for token count
        mtime_day = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")
        if mtime_day != today_prefix:
            continue
        scanned += 1
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    today_chars += len(line)
        except OSError:
            continue

    idle_minutes = ((now_ts - latest_mtime) / 60.0) if latest_mtime > 0 else None
    return {
        "logs_scanned_today": scanned,
        "estimated_tokens_today": int(round(today_chars / CHAR_PER_TOKEN)),
        "idle_minutes": round(idle_minutes, 1) if idle_minutes is not None else None,
    }


def collect_harness_telemetry(harness: str, repo_root: Path) -> Dict[str, Any]:
    """Collect local token usage and idle telemetry for the specified harness."""
    now_ts = time.time()
    home = os.path.expanduser("~")

    if harness == "antigravity":
        usage_log = repo_root / "workforces" / "tmp" / "usage-log.json"
        if usage_log.is_file():
            try:
                data = json.loads(usage_log.read_text(encoding="utf-8"))
                totals = data.get("aggregate") or {}
                if isinstance(totals, dict) and "estimated_total_tokens" in totals:
                    age_min = round((now_ts - usage_log.stat().st_mtime) / 60.0, 1)
                    return {
                        "source": str(usage_log),
                        "logs_scanned_today": 1,
                        "estimated_tokens_today": int(totals.get("estimated_total_tokens", 0)),
                        "idle_minutes": age_min,
                    }
            except (OSError, ValueError):
                pass
        pattern = os.path.join(home, ".gemini", "antigravity", "brain", "*", ".system_generated", "logs", "transcript.jsonl")
        return {"source": "antigravity_transcripts", **_scan_recent_jsonl_usage(glob.glob(pattern), now_ts)}

    if harness == "claude":
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
        pattern = os.path.join(base, "projects", "**", "*.jsonl")
        return {"source": "claude_projects", **_scan_recent_jsonl_usage(glob.glob(pattern, recursive=True), now_ts)}

    if harness == "grok":
        base = os.environ.get("GROK_HOME") or os.path.join(home, ".grok")
        pattern = os.path.join(base, "**", "*.jsonl")
        return {"source": "grok_logs", **_scan_recent_jsonl_usage(glob.glob(pattern, recursive=True), now_ts)}

    return {"source": "unknown", "logs_scanned_today": 0, "estimated_tokens_today": 0, "idle_minutes": None}


def evaluate_budget_gate(
    repo_root: Path,
    mode: str = "auto",
    harness: Optional[str] = None,
    ignore_idle: bool = False,
    window_remaining_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether a `/wf-work` run in `mode` should proceed.

    `codereview` always bypasses discovery pause and inbox cap.
    `discovery` sweeps (`docs`, `security`, `design`, `optimization`, `debt`, `housekeeping`)
    respect PM `issue_discovery == "paused"` and `max_untriaged_inbox`.
    """
    resolved_harness = detect_active_harness(explicit=harness, repo_root=repo_root)
    wc = get_work_control(repo_root)
    inbox_count = count_untriaged_inbox(repo_root)
    max_inbox = int(wc.get("max_untriaged_inbox", 15))
    discovery_state = str(wc.get("issue_discovery", "active")).lower()
    telemetry = collect_harness_telemetry(resolved_harness, repo_root)

    base: Dict[str, Any] = {
        "allowed": True,
        "code": "ok",
        "reason": "Ready to execute.",
        "mode": mode,
        "harness": resolved_harness,
        "issue_discovery": discovery_state,
        "paused_reason": wc.get("paused_reason", ""),
        "inbox_count": inbox_count,
        "max_untriaged_inbox": max_inbox,
        "telemetry": telemetry,
        "window_remaining_minutes": window_remaining_minutes,
    }

    if mode == "codereview":
        base["reason"] = "Cross-harness code review mode always enabled."
        return base

    max_tokens = int(wc.get("max_daily_tokens", DEFAULT_WORK_CONTROL["max_daily_tokens"]))
    if max_tokens > 0 and telemetry.get("estimated_tokens_today", 0) >= max_tokens:
        base["allowed"] = False
        base["code"] = "token_budget_exhausted"
        base["reason"] = (
            f"Daily token estimate ({telemetry['estimated_tokens_today']}) reached ceiling ({max_tokens}) "
            f"for harness `{resolved_harness}`."
        )
        return base

    min_idle = int(wc.get("min_idle_minutes", 0))
    idle_min = telemetry.get("idle_minutes")
    if not ignore_idle and min_idle > 0 and idle_min is not None and idle_min < min_idle:
        base["allowed"] = False
        base["code"] = "harness_recently_active"
        base["reason"] = (
            f"Harness `{resolved_harness}` was active {idle_min}m ago (threshold: {min_idle}m idle)."
        )
        return base

    if mode in DISCOVERY_MODES:
        if discovery_state == "paused":
            reason = wc.get("paused_reason") or "Paused by project manager check-in."
            base["allowed"] = False
            base["code"] = "discovery_paused"
            base["reason"] = f"Issue discovery is paused: {reason}"
            return base
        if max_inbox > 0 and inbox_count >= max_inbox:
            base["allowed"] = False
            base["code"] = "inbox_cap_reached"
            base["reason"] = (
                f"Inbox has {inbox_count} untriaged issue(s) (cap: {max_inbox}). "
                "Triage with `/wf-sync --daily` or resume via `/wf-work resume` before discovering more."
            )
            return base

    return base


def set_discovery_state(repo_root: Path, state: str, reason: str = "") -> Dict[str, Any]:
    """Toggle `work_control.issue_discovery` (`active` or `paused`) in `workforces/config.json`."""
    cfg = load_config(repo_root)
    wc = dict(DEFAULT_WORK_CONTROL)
    if isinstance(cfg.get("work_control"), dict):
        wc.update(cfg["work_control"])

    wc["issue_discovery"] = state
    if state == "paused":
        wc["paused_reason"] = reason or "Paused by user/PM check-in."
        wc["paused_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        wc["paused_reason"] = ""
        wc["paused_at"] = None

    cfg["work_control"] = wc
    save_config(repo_root, cfg)
    return wc


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness Budget Gate & PM Discovery Kill-Switch")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--harness", help="Override active harness (`antigravity`, `claude`, `grok`)")
    parser.add_argument("--mode", default="auto", help="Execution mode (`auto`, `codereview`, `docs`, `security`, etc.)")
    parser.add_argument("--check", action="store_true", help="Check if mode is allowed (exits 2 if gated)")
    parser.add_argument("--status", action="store_true", help="Show work control and budget status")
    parser.add_argument("--pause-discovery", action="store_true", help="Pause PM/worker issue discovery sweeps")
    parser.add_argument("--resume-discovery", action="store_true", help="Resume PM/worker issue discovery sweeps")
    parser.add_argument("--reason", default="", help="Reason when pausing discovery")
    parser.add_argument("--ignore-idle", action="store_true", help="Ignore `min_idle_minutes` guard")
    parser.add_argument("--window-remaining-minutes", type=int, default=None, help="Available token window minutes")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()

    if args.pause_discovery:
        wc = set_discovery_state(repo_root, "paused", reason=args.reason)
        if args.json:
            print(json.dumps({"work_control": wc}, indent=2))
        else:
            print(f"⏸️ Issue discovery paused: {wc['paused_reason']}")
        return 0

    if args.resume_discovery:
        wc = set_discovery_state(repo_root, "active")
        if args.json:
            print(json.dumps({"work_control": wc}, indent=2))
        else:
            print("▶️ Issue discovery resumed (`active`).")
        return 0

    result = evaluate_budget_gate(
        repo_root,
        mode=args.mode,
        harness=args.harness,
        ignore_idle=args.ignore_idle,
        window_remaining_minutes=args.window_remaining_minutes,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✅" if result["allowed"] else "⏸️"
        print(
            f"{icon} [{result['harness']}] mode={result['mode']} | discovery={result['issue_discovery']} "
            f"| inbox={result['inbox_count']}/{result['max_untriaged_inbox']} | {result['reason']}"
        )

    if args.check and not result["allowed"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
