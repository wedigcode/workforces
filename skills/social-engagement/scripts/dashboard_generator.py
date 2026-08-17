#!/usr/bin/env python3
"""
Social Dashboard & Action Queue Generator
Generates an interactive, dark-mode HTML Action Dashboard (workforces/social/dashboard.html)
and a markdown action queue (workforces/social/action_queue.md) with direct post links,
one-click copy buttons, and multi-comment sub-thread cards.

Usage:
    python3 dashboard_generator.py
    python3 dashboard_generator.py --target-dir /path/to/project
"""

import argparse
import datetime
import html
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional

# Import indexer helpers
try:
    from social_indexer import get_db_path, init_db, resolve_social_dir
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from social_indexer import get_db_path, init_db, resolve_social_dir


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workforces Social Engagement Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #090d16;
      --bg-surface: #0f172a;
      --bg-card: #18181b;
      --bg-card-hover: #1f2228;
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(99, 102, 241, 0.4);
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-indigo: #6366f1;
      --accent-indigo-hover: #4f46e5;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-sky: #0ea5e9;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      line-height: 1.5;
      min-height: 100vh;
      padding: 2.5rem 1.5rem;
    }

    .container {
      max-width: 1080px;
      margin: 0 auto;
    }

    /* Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--border-subtle);
      margin-bottom: 2rem;
    }

    .brand-title {
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-subtitle {
      color: var(--text-muted);
      font-size: 0.875rem;
      margin-top: 0.25rem;
    }

    .stats-bar {
      display: flex;
      gap: 1.5rem;
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }

    .stat-val {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Filter Tabs */
    .filter-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .tabs {
      display: flex;
      gap: 0.5rem;
      background: var(--bg-surface);
      padding: 0.25rem;
      border-radius: var(--radius-md);
      border: 1px solid var(--border-subtle);
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      padding: 0.4rem 0.85rem;
      font-size: 0.8125rem;
      font-weight: 500;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .tab-btn:hover {
      color: var(--text-primary);
    }

    .tab-btn.active {
      background: var(--bg-card);
      color: var(--text-primary);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    }

    /* Cards */
    .feed {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .post-card {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 1.5rem;
      transition: border-color 0.2s ease, transform 0.1s ease;
      position: relative;
    }

    .post-card:hover {
      border-color: rgba(255, 255, 255, 0.15);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .meta-group {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .platform-badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .badge-x { background: rgba(14, 165, 233, 0.15); color: var(--accent-sky); }
    .badge-skool { background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); }
    .badge-linkedin { background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); }

    .author-name {
      font-weight: 600;
      font-size: 0.9375rem;
    }

    .author-handle {
      color: var(--text-muted);
      font-size: 0.8125rem;
    }

    .score-badge {
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-emerald);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
    }

    .btn-external {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--text-secondary);
      text-decoration: none;
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-subtle);
      background: var(--bg-card);
      transition: all 0.15s ease;
    }

    .btn-external:hover {
      color: var(--text-primary);
      border-color: rgba(255, 255, 255, 0.25);
    }

    .post-content {
      color: var(--text-secondary);
      font-size: 0.9375rem;
      margin-bottom: 1.25rem;
      white-space: pre-wrap;
      background: rgba(0, 0, 0, 0.2);
      padding: 0.85rem;
      border-radius: var(--radius-sm);
      border-left: 3px solid var(--border-subtle);
    }

    .metrics-row {
      display: flex;
      gap: 1.25rem;
      font-size: 0.8125rem;
      color: var(--text-muted);
      margin-bottom: 1.25rem;
    }

    .metric-val {
      color: var(--text-secondary);
      font-weight: 600;
    }

    /* Response Blocks */
    .response-section {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }

    .response-box {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1rem;
    }

    .response-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.6rem;
    }

    .response-label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .response-text {
      font-size: 0.9375rem;
      color: var(--text-primary);
      white-space: pre-wrap;
      line-height: 1.6;
      margin-bottom: 0.75rem;
    }

    .btn-copy {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: var(--accent-indigo);
      color: white;
      border: none;
      padding: 0.45rem 0.85rem;
      font-size: 0.8125rem;
      font-weight: 600;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: background 0.15s ease;
    }

    .btn-copy:hover {
      background: var(--accent-indigo-hover);
    }

    .btn-copy.copied {
      background: var(--accent-emerald);
    }

    .sub-thread-box {
      border-left: 2px solid var(--accent-amber);
      background: rgba(24, 24, 27, 0.6);
      margin-top: 0.5rem;
    }

    .icon {
      width: 14px;
      height: 14px;
      stroke-width: 2;
      stroke: currentColor;
      fill: none;
    }
  </style>
</head>
<body>

  <div class="container">
    <header>
      <div>
        <h1 class="brand-title">
          <svg class="icon" style="width:24px;height:24px;" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          Social Engagement Engine
        </h1>
        <div class="brand-subtitle">Anti-Bot Human-Safe Action Dashboard & Reply Queue</div>
      </div>
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-val">__PENDING_COUNT__</span>
          <span class="stat-label">Pending Drafts</span>
        </div>
        <div class="stat-item">
          <span class="stat-val">__TOTAL_INDEXED__</span>
          <span class="stat-label">Total Indexed</span>
        </div>
      </div>
    </header>

    <div class="filter-bar">
      <div class="tabs">
        <button class="tab-btn active" onclick="filterPlatform('all', this)">All Platforms</button>
        <button class="tab-btn" onclick="filterPlatform('x.com', this)">X.com</button>
        <button class="tab-btn" onclick="filterPlatform('skool.com', this)">Skool</button>
        <button class="tab-btn" onclick="filterPlatform('linkedin.com', this)">LinkedIn</button>
      </div>
      <div style="font-size: 0.8125rem; color: var(--text-muted);">
        Generated: <strong>__TIMESTAMP__</strong>
      </div>
    </div>

    <div class="feed" id="postFeed">
      __POST_CARDS__
    </div>
  </div>

  <script>
    function copyText(btn, text) {
      navigator.clipboard.writeText(text).then(() => {
        const orig = btn.innerHTML;
        btn.innerHTML = `<svg class="icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
        btn.classList.add('copied');
        setTimeout(() => {
          btn.innerHTML = orig;
          btn.classList.remove('copied');
        }, 2000);
      });
    }

    function filterPlatform(platform, btn) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const cards = document.querySelectorAll('.post-card');
      cards.forEach(card => {
        if (platform === 'all' || card.getAttribute('data-platform') === platform) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    }
  </script>
</body>
</html>
"""


def render_post_card(post: Dict[str, Any]) -> str:
    """Renders a single post card with OP and sub-thread drafts."""
    platform = html.escape(post.get("platform", "x.com"))
    author = html.escape(post.get("author", "Author"))
    author_handle = html.escape(post.get("author_handle", "@author"))
    url = post.get("url", "#")
    content_text = html.escape(post.get("content_text", ""))
    score = post.get("relevance_score", 0)
    persona = html.escape(post.get("target_persona", "general-lead"))

    badge_class = "badge-x"
    if "skool" in platform.lower():
        badge_class = "badge-skool"
    elif "linkedin" in platform.lower():
        badge_class = "badge-linkedin"

    likes = post.get("likes", 0)
    replies = post.get("replies", 0)
    shares = post.get("shares", 0)

    drafts = post.get("drafts", [])
    response_html = ""

    for d in drafts:
        reply_type = d.get("reply_type", "op_reply")
        d_text = d.get("content_text", "")
        escaped_d_text = html.escape(d_text)
        json_escaped_text = json.dumps(d_text)
        target = html.escape(d.get("target_handle", ""))

        if reply_type == "op_reply":
            response_html += f"""
            <div class="response-box">
              <div class="response-header">
                <span class="response-label">
                  <svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>
                  Primary OP Response ({persona})
                </span>
                <button class="btn-copy" onclick='copyText(this, {json_escaped_text})'>
                  <svg class="icon" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  Copy Reply
                </button>
              </div>
              <div class="response-text">{escaped_d_text}</div>
            </div>
            """
        else:
            response_html += f"""
            <div class="response-box sub-thread-box">
              <div class="response-header">
                <span class="response-label" style="color: var(--accent-amber);">
                  <svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z"/></svg>
                  Sub-Comment Catalyst for {target}
                </span>
                <button class="btn-copy" style="background:#4b5563;" onclick='copyText(this, {json_escaped_text})'>
                  <svg class="icon" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  Copy Sub-Reply
                </button>
              </div>
              <div class="response-text">{escaped_d_text}</div>
            </div>
            """

    return f"""
    <div class="post-card" data-platform="{platform}">
      <div class="card-header">
        <div class="meta-group">
          <span class="platform-badge {badge_class}">{platform}</span>
          <span class="author-name">{author}</span>
          <span class="author-handle">{author_handle}</span>
          <span class="score-badge">Match Score: {score}/100</span>
        </div>
        <a href="{url}" target="_blank" rel="noopener noreferrer" class="btn-external">
          Open Post in Browser
          <svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
        </a>
      </div>

      <div class="post-content">{content_text}</div>

      <div class="metrics-row">
        <span>Likes: <span class="metric-val">{likes}</span></span>
        <span>Replies: <span class="metric-val">{replies}</span></span>
        <span>Shares: <span class="metric-val">{shares}</span></span>
      </div>

      <div class="response-section">
        {response_html}
      </div>
    </div>
    """


def generate_dashboard(target_dir: Optional[str] = None) -> str:
    """Generates dashboard.html and action_queue.md."""
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
                   'status', d.status
               )
           ) as drafts_json
    FROM posts p
    LEFT JOIN draft_replies d ON p.id = d.post_id
    WHERE p.status IN ('drafted', 'approved', 'discovered')
    GROUP BY p.id
    ORDER BY p.relevance_score DESC, p.last_checked_at DESC;
    """)

    rows = cur.fetchall()
    cards_html = []
    markdown_queue = ["# Social Action Queue\n\nDirect post links and copyable draft responses for review.\n"]

    total_indexed = 0
    pending_count = 0

    for row in rows:
        item = dict(row)
        if item.get("drafts_json"):
            drafts = json.loads(item["drafts_json"])
            item["drafts"] = [d for d in drafts if d.get("id") is not None]
        else:
            item["drafts"] = []
        del item["drafts_json"]

        total_indexed += 1
        if len(item["drafts"]) > 0:
            pending_count += len(item["drafts"])
            cards_html.append(render_post_card(item))

            # Markdown Queue block
            markdown_queue.append(f"## [{item['platform'].upper()}] {item['author_handle']} — Score: {item['relevance_score']}/100")
            markdown_queue.append(f"- **Link**: [Open Post]({item['url']})")
            markdown_queue.append(f"- **Context**: {item['content_text'][:150]}...")
            for d in item["drafts"]:
                markdown_queue.append(f"\n### Draft ({d['reply_type']}) targeting {d['target_handle']}:")
                markdown_queue.append(f"```text\n{d['content_text']}\n```\n")
            markdown_queue.append("---\n")

    conn.close()

    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html_output = HTML_TEMPLATE.replace("__PENDING_COUNT__", str(pending_count))
    html_output = html_output.replace("__TOTAL_INDEXED__", str(total_indexed))
    html_output = html_output.replace("__TIMESTAMP__", now_str)
    html_output = html_output.replace(
        "__POST_CARDS__",
        "\n".join(cards_html) if cards_html else "<div style='color:var(--text-muted);padding:2rem;text-align:center;'>No pending actions found in queue.</div>"
    )

    # Write dashboard.html
    dashboard_path = os.path.join(social_dir, "dashboard.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    # Write action_queue.md
    action_queue_path = os.path.join(social_dir, "action_queue.md")
    with open(action_queue_path, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_queue))

    return dashboard_path


def main():
    parser = argparse.ArgumentParser(description="Social Action Dashboard Generator")
    parser.add_argument("--target-dir", type=str, help="Target workspace directory")

    args = parser.parse_args()
    out = generate_dashboard(args.target_dir)
    print(f"✅ Generated Social Engagement Dashboard at: {out}")
    print(f"✅ Updated Action Queue at: {os.path.join(os.path.dirname(out), 'action_queue.md')}")


if __name__ == "__main__":
    main()
