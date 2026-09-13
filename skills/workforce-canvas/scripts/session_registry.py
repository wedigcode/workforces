#!/usr/bin/env python3
"""
Workforce Canvas Chat Session Registry
Manages active Antigravity chat sessions, port mappings, heartbeats, and targeted event routing.
"""

import datetime
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import fcntl
except ImportError:
    fcntl = None  # Windows compatibility fallback


def detect_current_chat_session(fallback: Optional[str] = None) -> str:
    """Detect current chat session ID from environment or metadata."""
    # 1. Antigravity Conversation ID
    conv_id = os.environ.get("ANTIGRAVITY_CONVERSATION_ID", "").strip()
    if conv_id:
        return conv_id

    # 2. Antigravity Source Metadata JSON
    source_meta = os.environ.get("ANTIGRAVITY_SOURCE_METADATA", "").strip()
    if source_meta:
        try:
            parsed = json.loads(source_meta)
            tool_meta = parsed.get("tool", {})
            if tool_meta.get("conversationId"):
                return str(tool_meta["conversationId"]).strip()
        except Exception:
            pass

    # 3. Trajectory ID fallback
    traj_id = os.environ.get("ANTIGRAVITY_TRAJECTORY_ID", "").strip()
    if traj_id:
        return traj_id

    if fallback:
        return fallback

    # Fallback to generated unique ID
    return f"session-{uuid.uuid4().hex[:8]}"


def get_chat_sessions_file(root_dir: Path) -> Path:
    """Return path to workforces/.chat-sessions.json."""
    return Path(root_dir).resolve() / "workforces" / ".chat-sessions.json"


def _read_registry(sessions_file: Path) -> Dict[str, Any]:
    """Read registry json safely."""
    if not sessions_file.exists():
        return {"sessions": {}, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        content = sessions_file.read_text(encoding="utf-8")
        if not content.strip():
            return {"sessions": {}, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        data = json.loads(content)
        if "sessions" not in data or not isinstance(data["sessions"], dict):
            data = {"sessions": {}, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        return data
    except Exception:
        return {"sessions": {}, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def _write_registry(sessions_file: Path, data: Dict[str, Any]):
    """Write registry atomically with locking."""
    sessions_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file = sessions_file.with_suffix(".lock")

    lf = None
    if fcntl is not None:
        try:
            lf = open(lock_file, "w")
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        except Exception:
            lf = None

    try:
        data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tmp_file = sessions_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_file.replace(sessions_file)
    finally:
        if lf is not None and fcntl is not None:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                lf.close()
            except Exception:
                pass


def get_chat_sessions(root_dir: Path, prune_stale_seconds: int = 120) -> Dict[str, Any]:
    """Retrieve all registered chat sessions and prune stale ones."""
    sessions_file = get_chat_sessions_file(root_dir)
    data = _read_registry(sessions_file)
    sessions = data.get("sessions", {})
    now = time.time()
    modified = False

    for sid, sinfo in list(sessions.items()):
        status = sinfo.get("status", "active")
        last_hb = sinfo.get("last_heartbeat") or sinfo.get("registered_at")
        if status == "active" and last_hb:
            try:
                # Handle ISO format timestamp
                clean_hb = last_hb.replace("Z", "+00:00")
                dt = datetime.datetime.fromisoformat(clean_hb)
                hb_epoch = dt.timestamp()
                if (now - hb_epoch) > prune_stale_seconds:
                    sinfo["status"] = "idle"
                    modified = True
            except Exception:
                pass

    if modified:
        _write_registry(sessions_file, data)

    return sessions


def register_chat_session(
    root_dir: Path,
    session_id: str,
    alias: Optional[str] = None,
    role: str = "watcher",
    port: Optional[int] = None,
    pid: Optional[int] = None,
    current_task: Optional[str] = None,
    status: str = "active",
) -> Dict[str, Any]:
    """Register or update an active chat session."""
    root_dir = Path(root_dir).resolve()
    sessions_file = get_chat_sessions_file(root_dir)
    data = _read_registry(sessions_file)
    sessions = data.setdefault("sessions", {})

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_id = session_id.strip()
    short_id = clean_id[:8] if len(clean_id) >= 8 else clean_id
    session_alias = alias.strip() if alias and alias.strip() else f"Chat {short_id}"

    existing = sessions.get(clean_id, {})
    entry = {
        "session_id": clean_id,
        "short_id": short_id,
        "alias": session_alias,
        "role": role,
        "port": port if port is not None else existing.get("port"),
        "pid": pid if pid is not None else existing.get("pid", os.getpid()),
        "status": status,
        "has_watcher": bool(role == "watcher" or existing.get("has_watcher") or role == "both"),
        "has_server": bool(role == "webserver" or existing.get("has_server") or role == "both"),
        "current_task": current_task or existing.get("current_task", ""),
        "registered_at": existing.get("registered_at", now_iso),
        "last_heartbeat": now_iso,
    }

    sessions[clean_id] = entry
    _write_registry(sessions_file, data)
    return entry


def heartbeat_chat_session(
    root_dir: Path,
    session_id: str,
    current_task: Optional[str] = None,
) -> bool:
    """Send heartbeat for an active chat session."""
    root_dir = Path(root_dir).resolve()
    sessions_file = get_chat_sessions_file(root_dir)
    data = _read_registry(sessions_file)
    sessions = data.get("sessions", {})

    clean_id = session_id.strip()
    if clean_id in sessions:
        sessions[clean_id]["last_heartbeat"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sessions[clean_id]["status"] = "active"
        if current_task is not None:
            sessions[clean_id]["current_task"] = current_task
        _write_registry(sessions_file, data)
        return True
    else:
        # Register on first heartbeat if missing
        register_chat_session(root_dir, clean_id, current_task=current_task)
        return True


def unregister_chat_session(
    root_dir: Path,
    session_id: str,
    status: str = "stopped",
) -> bool:
    """Mark a chat session as stopped or offline."""
    root_dir = Path(root_dir).resolve()
    sessions_file = get_chat_sessions_file(root_dir)
    data = _read_registry(sessions_file)
    sessions = data.get("sessions", {})

    clean_id = session_id.strip()
    if clean_id in sessions:
        sessions[clean_id]["status"] = status
        sessions[clean_id]["stopped_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _write_registry(sessions_file, data)
        return True
    return False


def emit_session_directive(
    root_dir: Path,
    target_session_id: str,
    message: str,
    sender: str = "@human",
    priority: str = "P1",
    action: Optional[str] = None,
) -> Dict[str, Any]:
    """Emit a targeted directive event to workforces/.events/pending/ for a specific chat session."""
    root_dir = Path(root_dir).resolve()
    events_dir = root_dir / "workforces" / ".events"
    pending_dir = events_dir / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    seq_file = events_dir / ".seq"
    lock_file = events_dir / ".seq.lock"

    lf = None
    if fcntl is not None:
        try:
            lf = open(lock_file, "w")
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        except Exception:
            lf = None

    try:
        current_seq = 0
        if seq_file.exists():
            try:
                current_seq = int(seq_file.read_text(encoding="utf-8").strip())
            except Exception:
                current_seq = 0
        current_seq += 1
        seq_file.write_text(str(current_seq), encoding="utf-8")
    finally:
        if lf is not None and fcntl is not None:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                lf.close()
            except Exception:
                pass

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    ts_iso = now_utc.isoformat()
    ts_compact = now_utc.strftime("%Y%m%dT%H%M%SZ")
    seq_str = f"{current_seq:04d}"
    event_id = f"{ts_compact}_{seq_str}_session_directive"
    filename = f"{event_id}.json"

    event_data = {
        "event_id": event_id,
        "event_type": "session_directive",
        "target_chat_session_id": target_session_id.strip(),
        "timestamp": ts_iso,
        "sequence": current_seq,
        "payload": {
            "session_id": target_session_id.strip(),
            "sender": sender,
            "message": message.strip(),
            "priority": priority,
            "action": action or "Direct communication from dashboard",
            "timestamp": ts_iso,
        }
    }

    event_file = pending_dir / filename
    tmp_file = event_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(event_data, indent=2), encoding="utf-8")
    tmp_file.replace(event_file)
    return event_data
