#!/usr/bin/env python3
"""
Social Indexer & Data Store Manager
High-performance SQLite engine with cold-post triage caching and JSON export
for the Workforces Social Engagement Engine.

Usage:
    python3 social_indexer.py --init
    python3 social_indexer.py --list [--status STATUS] [--platform PLATFORM]
    python3 social_indexer.py --stats
    python3 social_indexer.py --export-json
"""

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional


def resolve_social_dir(target_dir: Optional[str] = None) -> str:
    """Resolves the workforces/social directory path."""
    if target_dir:
        base = os.path.abspath(target_dir)
    else:
        # Fallback to current working directory
        cwd = os.getcwd()
        base = cwd

    # Check if inside a workforces repo
    if os.path.exists(os.path.join(base, "workforces")):
        social_dir = os.path.join(base, "workforces", "social")
    else:
        social_dir = os.path.join(base, "social")

    os.makedirs(social_dir, exist_ok=True)
    return social_dir


def get_db_path(target_dir: Optional[str] = None) -> str:
    social_dir = resolve_social_dir(target_dir)
    return os.path.join(social_dir, "social_index.db")


def init_db(db_path: str) -> None:
    """Initializes SQLite database schema."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        platform TEXT NOT NULL,
        community TEXT DEFAULT 'all',
        author TEXT,
        author_handle TEXT,
        url TEXT NOT NULL,
        content_text TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        replies INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        views INTEGER DEFAULT 0,
        relevance_score INTEGER DEFAULT 0,
        target_persona TEXT,
        status TEXT DEFAULT 'discovered', -- discovered, drafted, approved, posted, ignored
        discovered_at TEXT NOT NULL,
        last_checked_at TEXT NOT NULL,
        skip_until TEXT,                  -- for cold-post negative caching
        metadata JSON
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sub_comments (
        id TEXT PRIMARY KEY,
        post_id TEXT NOT NULL,
        commenter_handle TEXT,
        comment_text TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        is_question INTEGER DEFAULT 0,
        status TEXT DEFAULT 'discovered',
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS draft_replies (
        id TEXT PRIMARY KEY,
        post_id TEXT NOT NULL,
        sub_comment_id TEXT,
        reply_type TEXT NOT NULL, -- 'op_reply' or 'sub_thread_catalyst'
        target_handle TEXT,
        content_text TEXT NOT NULL,
        persona_id TEXT,
        status TEXT DEFAULT 'pending', -- pending, approved, posted, rejected
        created_at TEXT NOT NULL,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_score ON posts(relevance_score);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status ON draft_replies(status);")

    conn.commit()
    conn.close()


def generate_post_id(platform: str, url_or_id: str) -> str:
    """Generates a unique deterministic ID for a post."""
    raw = f"{platform.lower().strip()}:{url_or_id.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def upsert_post(
    db_path: str,
    platform: str,
    url: str,
    content_text: str,
    author: str = "",
    author_handle: str = "",
    community: str = "all",
    likes: int = 0,
    replies: int = 0,
    shares: int = 0,
    views: int = 0,
    relevance_score: int = 0,
    target_persona: str = "",
    status: str = "discovered",
    skip_until: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Inserts or updates a post in the index."""
    init_db(db_path)
    post_id = generate_post_id(platform, url)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO posts (
        id, platform, community, author, author_handle, url, content_text,
        likes, replies, shares, views, relevance_score, target_persona,
        status, discovered_at, last_checked_at, skip_until, metadata
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        likes=excluded.likes,
        replies=excluded.replies,
        shares=excluded.shares,
        views=excluded.views,
        relevance_score=CASE WHEN excluded.relevance_score > 0 THEN excluded.relevance_score ELSE posts.relevance_score END,
        target_persona=CASE WHEN excluded.target_persona != '' THEN excluded.target_persona ELSE posts.target_persona END,
        last_checked_at=excluded.last_checked_at,
        skip_until=COALESCE(excluded.skip_until, posts.skip_until),
        metadata=COALESCE(excluded.metadata, posts.metadata);
    """, (
        post_id, platform, community, author, author_handle, url, content_text,
        likes, replies, shares, views, relevance_score, target_persona,
        status, now, now, skip_until, json.dumps(metadata or {})
    ))

    conn.commit()
    conn.close()
    return post_id


def is_post_cold(db_path: str, platform: str, url: str) -> bool:
    """Checks if a post is marked as cold/ignored and should be skipped."""
    init_db(db_path)
    post_id = generate_post_id(platform, url)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, skip_until FROM posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    status, skip_until = row
    if status == "ignored":
        if not skip_until:
            return True
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if now < skip_until:
            return True
    return False


def upsert_draft_reply(
    db_path: str,
    post_id: str,
    reply_type: str,
    content_text: str,
    persona_id: str = "",
    target_handle: str = "",
    sub_comment_id: Optional[str] = None,
) -> str:
    """Upserts a generated draft reply for a post or sub-comment."""
    init_db(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    draft_id = hashlib.sha256(f"{post_id}:{reply_type}:{target_handle}:{content_text[:30]}".encode("utf-8")).hexdigest()[:16]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO draft_replies (
        id, post_id, sub_comment_id, reply_type, target_handle, content_text, persona_id, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    ON CONFLICT(id) DO UPDATE SET
        content_text=excluded.content_text,
        persona_id=excluded.persona_id;
    """, (draft_id, post_id, sub_comment_id, reply_type, target_handle, content_text, persona_id, now))

    # Also update post status to drafted if discovered
    cur.execute("UPDATE posts SET status = 'drafted' WHERE id = ? AND status = 'discovered'", (post_id,))

    conn.commit()
    conn.close()
    return draft_id


def export_to_json(target_dir: Optional[str] = None) -> Dict[str, Any]:
    """Exports SQLite index to index.json and queue.json for agent and user inspection."""
    social_dir = resolve_social_dir(target_dir)
    db_path = get_db_path(target_dir)
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT p.*, 
           json_group_array(
               json_object(
                   'id', d.id,
                   'reply_type', d.reply_type,
                   'target_handle', d.target_handle,
                   'content_text', d.content_text,
                   'persona_id', d.persona_id,
                   'status', d.status,
                   'created_at', d.created_at
               )
           ) as drafts_json
    FROM posts p
    LEFT JOIN draft_replies d ON p.id = d.post_id
    GROUP BY p.id
    ORDER BY p.relevance_score DESC, p.last_checked_at DESC;
    """)

    rows = cur.fetchall()
    posts_list = []
    queue_list = []

    for row in rows:
        item = dict(row)
        if item.get("drafts_json"):
            drafts = json.loads(item["drafts_json"])
            # filter out null draft objects when left join has no match
            item["drafts"] = [d for d in drafts if d.get("id") is not None]
        else:
            item["drafts"] = []
        del item["drafts_json"]

        if item.get("metadata"):
            try:
                item["metadata"] = json.loads(item["metadata"])
            except Exception:
                pass

        posts_list.append(item)

        if item["status"] in ("drafted", "approved") and len(item["drafts"]) > 0:
            queue_list.append(item)

    conn.close()

    # Write index.json
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    index_file = os.path.join(social_dir, "index.json")
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump({"updated_at": now_iso, "posts": posts_list}, f, indent=2)

    # Write queue.json
    queue_file = os.path.join(social_dir, "queue.json")
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump({"updated_at": now_iso, "pending_actions": queue_list}, f, indent=2)

    return {"total_indexed": len(posts_list), "queue_count": len(queue_list)}


def get_stats(db_path: str) -> Dict[str, Any]:
    """Returns index statistics."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM posts")
    total_posts = cur.fetchone()[0]

    cur.execute("SELECT status, COUNT(*) FROM posts GROUP BY status")
    status_counts = dict(cur.fetchall())

    cur.execute("SELECT platform, COUNT(*) FROM posts GROUP BY platform")
    platform_counts = dict(cur.fetchall())

    cur.execute("SELECT COUNT(*) FROM draft_replies WHERE status = 'pending'")
    pending_drafts = cur.fetchone()[0]

    conn.close()

    return {
        "total_posts": total_posts,
        "by_status": status_counts,
        "by_platform": platform_counts,
        "pending_drafts": pending_drafts
    }


def main():
    parser = argparse.ArgumentParser(description="Social Indexer & Data Store Manager")
    parser.add_argument("--init", action="store_true", help="Initialize SQLite schema")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--list", action="store_true", help="List indexed posts")
    parser.add_argument("--status", type=str, help="Filter by status (discovered, drafted, approved, ignored)")
    parser.add_argument("--platform", type=str, help="Filter by platform (x.com, skool.com, linkedin.com)")
    parser.add_argument("--export-json", action="store_true", help="Export database to index.json and queue.json")
    parser.add_argument("--target-dir", type=str, help="Target workspace directory")

    args = parser.parse_args()
    db_path = get_db_path(args.target_dir)

    if args.init:
        init_db(db_path)
        print(f"✅ Initialized Social Index database at: {db_path}")
        return

    if args.stats:
        stats = get_stats(db_path)
        print("\n📊 Social Engagement Index Statistics:")
        print(f"  • Total Posts Indexed: {stats['total_posts']}")
        print(f"  • Pending Draft Replies: {stats['pending_drafts']}")
        print(f"  • Status Breakdown: {json.dumps(stats['by_status'], indent=4)}")
        print(f"  • Platform Breakdown: {json.dumps(stats['by_platform'], indent=4)}\n")
        return

    if args.export_json or not any([args.init, args.stats, args.list]):
        result = export_to_json(args.target_dir)
        print(f"✅ Exported {result['total_indexed']} posts and {result['queue_count']} queue items to JSON.")
        return

    if args.list:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = "SELECT id, platform, community, author_handle, relevance_score, status, url, content_text FROM posts WHERE 1=1"
        params = []
        if args.status:
            query += " AND status = ?"
            params.append(args.status)
        if args.platform:
            query += " AND platform = ?"
            params.append(args.platform)
        query += " ORDER BY relevance_score DESC LIMIT 50"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        print(f"\n📋 Indexed Posts ({len(rows)} results):")
        for r in rows:
            print(f"  [{r['platform']}] {r['author_handle']} | Score: {r['relevance_score']} | Status: {r['status']}")
            print(f"    URL: {r['url']}")
            print(f"    Text: {r['content_text'][:100]}...\n")


if __name__ == "__main__":
    main()
