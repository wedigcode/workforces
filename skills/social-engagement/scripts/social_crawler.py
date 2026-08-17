#!/usr/bin/env python3
"""
Social Crawler & Progressive Scroll Extractor
Handles progressive downward scrolling, DOM extraction, and comment stream unfolding
for dynamic community feeds (Skool, X.com, LinkedIn) and discussion threads.

Usage:
    python3 social_crawler.py --extract-feed <input_html_or_json> --output <output_posts.json>
    python3 social_crawler.py --generate-browser-script [skool|x|linkedin]
    python3 social_crawler.py --parse-skool-dom <dom_dump.txt> --output <extracted.json>
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Import indexer helpers if available
try:
    from social_indexer import generate_post_id, resolve_social_dir
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from social_indexer import generate_post_id, resolve_social_dir
    except ImportError:
        def generate_post_id(platform: str, url_or_id: str) -> str:
            raw = f"{platform.lower().strip()}:{url_or_id.strip()}"
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

        def resolve_social_dir(target_dir: Optional[str] = None) -> str:
            base = os.path.abspath(target_dir) if target_dir else os.getcwd()
            if os.path.exists(os.path.join(base, "workforces")):
                social_dir = os.path.join(base, "workforces", "social")
            else:
                social_dir = os.path.join(base, "social")
            os.makedirs(social_dir, exist_ok=True)
            return social_dir


# Client-side JavaScript snippet that can be executed in browser / subagent
# to perform progressive scrolling and structured post extraction
BROWSER_PROGRESSIVE_SCROLL_JS = """
async function progressiveScrollAndExtract(options = {}) {
    const maxScrolls = options.maxScrolls || 8;
    const scrollDelay = options.scrollDelay || 1200;
    const targetMinPosts = options.targetMinPosts || 15;
    const isThread = options.isThread || false;

    console.log(`Starting progressive scrolling (max: ${maxScrolls}, min posts: ${targetMinPosts})...`);

    // Helper to sleep
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // Progressive scroll loop
    let lastHeight = document.body.scrollHeight;
    let scrollCount = 0;

    while (scrollCount < maxScrolls) {
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
        await sleep(scrollDelay);

        // Click any "Load more", "View more replies", or "Show more" buttons if present
        const expandButtons = Array.from(document.querySelectorAll('button, a')).filter(el => {
            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
            return txt.includes('view more') || txt.includes('load more') || txt.includes('more comments') || txt.includes('show more');
        });

        for (const btn of expandButtons) {
            try {
                btn.click();
                await sleep(300);
            } catch (e) {}
        }

        const newHeight = document.body.scrollHeight;
        scrollCount++;

        // Check if we have enough items
        const postElements = document.querySelectorAll('[data-post-id], .styled__PostCardWrapper, article, .post-item, .comment-item');
        if (postElements.length >= targetMinPosts && newHeight === lastHeight) {
            break;
        }
        lastHeight = newHeight;
    }

    console.log(`Progressive scrolling complete after ${scrollCount} increments.`);

    // Extract structured data from DOM
    const currentUrl = window.location.href;
    const isSkool = currentUrl.includes('skool.com');
    const isX = currentUrl.includes('x.com') || currentUrl.includes('twitter.com');
    const isLinkedIn = currentUrl.includes('linkedin.com');

    const results = [];

    if (isSkool) {
        // Skool extraction logic
        // 1. Thread comments extraction (if inside a thread)
        const commentWrappers = document.querySelectorAll('.styled__CommentWrapper, .comment-item, [class*="CommentWrapper"]');
        if (commentWrappers.length > 0) {
            // We are inside a thread
            const threadTitle = document.querySelector('h1, [class*="PostTitle"]')?.innerText?.trim() || document.title;
            const opBody = document.querySelector('[class*="PostContent"], [class*="BodyText"]')?.innerText?.trim() || "";
            const opAuthor = document.querySelector('[class*="AuthorName"], [class*="UserName"]')?.innerText?.trim() || "Community Member";

            const threadPost = {
                platform: "skool.com",
                community: currentUrl.split('/')[3] || "all",
                url: currentUrl,
                title: threadTitle,
                author: opAuthor,
                author_handle: `@${opAuthor.replace(/\\s+/g, '').toLowerCase()}`,
                content_text: `${threadTitle}\\n\\n${opBody}`.trim(),
                is_thread_op: true,
                likes: 0,
                replies: commentWrappers.length,
                sub_comments: []
            };

            commentWrappers.forEach((el, idx) => {
                const authorEl = el.querySelector('[class*="Author"], [class*="Name"], strong, a');
                const authorName = authorEl?.innerText?.trim() || `Member ${idx + 1}`;
                const textEl = el.querySelector('[class*="CommentContent"], [class*="Body"], p');
                const commentText = textEl?.innerText?.trim() || el.innerText?.trim() || "";

                if (commentText && commentText.length > 5) {
                    threadPost.sub_comments.push({
                        id: `c_${idx}`,
                        commenter_handle: `@${authorName.replace(/\\s+/g, '').toLowerCase()}`,
                        author_name: authorName,
                        comment_text: commentText,
                        likes: 0
                    });
                }
            });

            results.push(threadPost);
        } else {
            // 2. Feed cards extraction
            const cardWrappers = document.querySelectorAll('[class*="PostCardWrapper"], [class*="PostItem"], a[href*="/"]');
            const seenUrls = new Set();

            cardWrappers.forEach(card => {
                const titleEl = card.querySelector('h2, h3, [class*="Title"]');
                const bodyEl = card.querySelector('[class*="Content"], [class*="Preview"], p');
                const authorEl = card.querySelector('[class*="Author"], [class*="User"]');
                const linkEl = card.querySelector('a') || (card.tagName === 'A' ? card : null);

                const postUrl = linkEl?.href || currentUrl;
                if (seenUrls.has(postUrl) || !titleEl) return;
                seenUrls.add(postUrl);

                const title = titleEl?.innerText?.trim() || "";
                const body = bodyEl?.innerText?.trim() || "";
                const author = authorEl?.innerText?.trim() || "Member";

                if (title || body) {
                    results.push({
                        platform: "skool.com",
                        community: currentUrl.split('/')[3] || "all",
                        url: postUrl,
                        title: title,
                        author: author,
                        author_handle: `@${author.replace(/\\s+/g, '').toLowerCase()}`,
                        content_text: `${title}\\n\\n${body}`.trim(),
                        likes: 0,
                        replies: 0,
                        sub_comments: []
                    });
                }
            });
        }
    }

    return {
        extracted_at: new Date().toISOString(),
        url: currentUrl,
        total_items: results.length,
        items: results
    };
}
"""


def detect_post_intent(text: str, title: str = "") -> Dict[str, bool]:
    """
    Detects if a post represents a newcomer introduction, a technical bottleneck,
    or a high-signal open question.
    """
    full_text = f"{title}\n{text}".lower()

    # 1. Newcomer Introduction Intent
    intro_keywords = [
        "intro yourself", "introduce yourself", "just joined", "new here", "new member",
        "excited to be here", "hello everyone", "hey everyone", "glad to join", "my background is",
        "starting my journey", "looking forward to learning", "first post", "new to the group"
    ]
    is_introduction = any(k in full_text for k in intro_keywords)

    # 2. Technical / Architecture Bottleneck Intent
    tech_keywords = [
        "aws", "amplify", "lambda", "cloud", "architecture", "database", "dynamodb", "postgres",
        "supabase", "firebase", "deployment", "backend", "auth", "cognito", "api", "rest", "graphql",
        "error", "bug", "stuck on", "troubleshooting", "scaling", "latency", "docker", "infra",
        "pipeline", "orchestration", "cost", "timeout", "permission", "iam"
    ]
    is_tech_bottleneck = any(re.search(rf"\b{re.escape(k)}\b", full_text) for k in tech_keywords)

    # 3. Question / Assistance Request Intent
    question_keywords = [
        "how do i", "how do you", "what is the best", "anyone know", "any recommendations",
        "can someone explain", "stuck on", "struggling with", "need advice", "feedback on",
        "thoughts on", "which one should", "why does"
    ]
    is_question = ("?" in full_text) or any(k in full_text for k in question_keywords)

    return {
        "is_introduction": is_introduction,
        "is_tech_bottleneck": is_tech_bottleneck,
        "is_question": is_question
    }


def parse_raw_text_stream(raw_text: str, default_platform: str = "skool.com", community: str = "all") -> List[Dict[str, Any]]:
    """
    Robust text parser that converts unstructured feed copies, thread comment dumps,
    or browser logs into structured post records.
    """
    posts = []
    blocks = re.split(r'\n{2,}(?=[A-Z0-9@#]|---|\*{3,})', raw_text.strip())

    for idx, block in enumerate(blocks):
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        if not lines:
            continue

        first_line = lines[0]
        # Match author patterns like "John Doe @johndoe", "Sarah Smith", "@dev_lead"
        author_match = re.match(r'^([A-Za-z0-9\s_\-\.]+)(?:\s+@([A-Za-z0-9_]+))?', first_line)
        if author_match and len(lines) > 1:
            author = author_match.group(1).strip()
            handle = f"@{author_match.group(2)}" if author_match.group(2) else f"@{author.replace(' ', '').lower()}"
            content_lines = lines[1:]
        else:
            author = "Community Member"
            handle = f"@member_{idx + 1}"
            content_lines = lines

        content_text = "\n".join(content_lines)
        title = lines[0] if len(lines) > 1 else ""

        # Detect intent
        intent = detect_post_intent(content_text, title)

        # Generate unique URL / ID
        post_url = f"https://www.skool.com/{community}/post-{idx + 1}"

        posts.append({
            "platform": default_platform,
            "community": community,
            "url": post_url,
            "author": author,
            "author_handle": handle,
            "title": title,
            "content_text": content_text,
            "likes": 1 if intent["is_introduction"] else 0,
            "replies": 0,
            "shares": 0,
            "views": 0,
            "is_introduction": intent["is_introduction"],
            "is_tech_bottleneck": intent["is_tech_bottleneck"],
            "is_question": intent["is_question"],
            "sub_comments": []
        })

    return posts


def extract_thread_comments_as_individual_posts(
    thread_data: Dict[str, Any],
    parent_title: str = "Community Discussion"
) -> List[Dict[str, Any]]:
    """
    Transforms individual replies inside large introduction threads (e.g. "Intro yourself")
    into individually addressable engagement candidates so each member receives a bespoke welcome/advice.
    """
    extracted_posts = []
    community = thread_data.get("community", "all")
    platform = thread_data.get("platform", "skool.com")
    base_url = thread_data.get("url", f"https://www.skool.com/{community}/welcome")

    sub_comments = thread_data.get("sub_comments", [])
    for idx, c in enumerate(sub_comments):
        c_text = c.get("comment_text", "").strip()
        if not c_text or len(c_text) < 10:
            continue

        author = c.get("author_name") or c.get("commenter_handle", "").lstrip("@") or f"Member {idx + 1}"
        handle = c.get("commenter_handle") or f"@{author.replace(' ', '').lower()}"
        intent = detect_post_intent(c_text, parent_title)

        post_url = f"{base_url}#comment-{idx + 1}"

        extracted_posts.append({
            "platform": platform,
            "community": community,
            "url": post_url,
            "author": author,
            "author_handle": handle,
            "title": f"Reply in '{parent_title}' by {author}",
            "content_text": c_text,
            "likes": c.get("likes", 0),
            "replies": 0,
            "shares": 0,
            "views": 0,
            "is_introduction": intent["is_introduction"] or ("intro" in parent_title.lower() or "welcome" in parent_title.lower()),
            "is_tech_bottleneck": intent["is_tech_bottleneck"],
            "is_question": intent["is_question"],
            "sub_comments": []
        })

    return extracted_posts


def main():
    parser = argparse.ArgumentParser(description="Social Crawler & Progressive Scroll Extractor")
    parser.add_argument("--generate-browser-script", action="store_true", help="Print browser progressive scroll JS")
    parser.add_argument("--parse-text-stream", type=str, help="Path to text dump file to parse")
    parser.add_argument("--unfold-thread", type=str, help="Path to JSON file with thread sub_comments to unfold into post queue")
    parser.add_argument("--community", type=str, default="all", help="Target community slug (e.g. ai-automation-vault)")
    parser.add_argument("--platform", type=str, default="skool.com", help="Target platform (skool.com, x.com, linkedin.com)")
    parser.add_argument("--output", type=str, help="Path to write structured JSON output")

    args = parser.parse_args()

    if args.generate_browser_script:
        print(BROWSER_PROGRESSIVE_SCROLL_JS)
        return

    if args.parse_text_stream:
        if not os.path.exists(args.parse_text_stream):
            print(f"❌ Error: File not found: {args.parse_text_stream}")
            sys.exit(1)

        with open(args.parse_text_stream, "r", encoding="utf-8") as f:
            raw_text = f.read()

        posts = parse_raw_text_stream(raw_text, default_platform=args.platform, community=args.community)
        print(f"✅ Extracted {len(posts)} posts from raw text stream.")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump({"posts": posts}, f, indent=2)
            print(f"💾 Saved extracted posts to: {args.output}")
        return

    if args.unfold_thread:
        if not os.path.exists(args.unfold_thread):
            print(f"❌ Error: File not found: {args.unfold_thread}")
            sys.exit(1)

        with open(args.unfold_thread, "r", encoding="utf-8") as f:
            thread_data = json.load(f)

        parent_title = thread_data.get("title", "Community Discussion")
        unfolded = extract_thread_comments_as_individual_posts(thread_data, parent_title=parent_title)
        print(f"✅ Unfolded {len(unfolded)} comments into standalone engagement candidates.")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump({"posts": unfolded}, f, indent=2)
            print(f"💾 Saved unfolded posts to: {args.output}")
        return


if __name__ == "__main__":
    main()
