#!/usr/bin/env python3
"""
Engagement Evaluator & Multi-Tier Response Generator
Scores discovered posts, resolves the proper persona per website/community,
triages cold/low-engagement posts, and drafts OP and sub-comment responses
driven entirely by configurable persona domain knowledge, frameworks, and questions.
Works with zero external dependencies (standard Python 3 library).

Usage:
    python3 engagement_evaluator.py --evaluate-json <path-to-scraped-posts.json>
"""

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Import indexer from same directory
try:
    from social_indexer import (
        get_db_path,
        init_db,
        is_post_cold,
        resolve_social_dir,
        upsert_draft_reply,
        upsert_post,
        export_to_json
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from social_indexer import (
        get_db_path,
        init_db,
        is_post_cold,
        resolve_social_dir,
        upsert_draft_reply,
        upsert_post,
        export_to_json
    )


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Robust zero-dependency YAML parser for nested dictionaries, lists, and scalars."""
    root: Dict[str, Any] = {}
    # stack entry: (indent, container, key_in_container)
    stack: List[Tuple[int, Any, Optional[str]]] = [(-1, root, None)]

    lines = text.split("\n")
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        # Pop stack items that have >= indentation than current line
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        cur_indent, cur_obj, cur_key = stack[-1]

        # Case 1: List item "- value"
        if stripped.startswith("- "):
            val_str = stripped[2:].strip().strip('"').strip("'")
            # If cur_obj is a dict and we have a cur_key, ensure it's a list
            if isinstance(cur_obj, dict) and cur_key:
                if cur_key not in cur_obj or not isinstance(cur_obj[cur_key], list):
                    cur_obj[cur_key] = []
                cur_obj[cur_key].append(val_str)
            elif isinstance(cur_obj, list):
                cur_obj.append(val_str)
            continue

        # Case 2: Key-value pair "key: value" or "key:"
        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip().strip('"').strip("'")
            val = parts[1].strip()

            if not val or val.startswith("#"):
                # Container key (dict or list depending on upcoming children)
                if isinstance(cur_obj, dict):
                    # We create an empty dict initially, will convert to list if first child is "- "
                    cur_obj[key] = {}
                    stack.append((indent, cur_obj, key))
            else:
                # Scalar value
                clean_val = val.split("#")[0].strip().strip('"').strip("'")
                if clean_val.lower() == "true":
                    typed_val = True
                elif clean_val.lower() == "false":
                    typed_val = False
                elif clean_val.isdigit():
                    typed_val = int(clean_val)
                else:
                    typed_val = clean_val

                if isinstance(cur_obj, dict):
                    if cur_key and isinstance(cur_obj.get(cur_key), dict):
                        cur_obj[cur_key][key] = typed_val
                    else:
                        cur_obj[key] = typed_val

    return root


def load_config(social_dir: str) -> Dict[str, Any]:
    """Loads social config from config.json or config.yaml."""
    json_path = os.path.join(social_dir, "config.json")
    yaml_path = os.path.join(social_dir, "config.yaml")

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = f.read()
                return parse_simple_yaml(content)
        except Exception:
            pass

    return {}


def resolve_persona_for_post(
    social_dir: str,
    platform: str,
    community: str,
    config: Dict[str, Any],
    explicit_persona_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolves the appropriate persona for a specific website/platform and community.
    Priority:
    1. Explicit post target persona (if specified)
    2. Community-specific persona in config (e.g. platforms.skool_com.communities.<name>.persona)
    3. Platform-level persona in config (e.g. platforms.x_com.persona)
    4. Default platform lead persona
    """
    platform_key = platform.replace(".", "_").lower()
    platform_cfg = config.get("platforms", {}).get(platform_key, {})

    persona_id = explicit_persona_id

    # Check community-level persona mapping
    if not persona_id and community and community != "all":
        comm_cfg = platform_cfg.get("communities", {})
        if isinstance(comm_cfg, dict) and community in comm_cfg:
            if isinstance(comm_cfg[community], dict):
                persona_id = comm_cfg[community].get("persona")

    # Fallback to platform-level persona
    if not persona_id:
        persona_id = platform_cfg.get("persona", f"{platform_key}-lead")

    personas_dir = os.path.join(social_dir, "personas")
    persona_file_md = os.path.join(personas_dir, f"{persona_id}.md")
    persona_file_json = os.path.join(personas_dir, f"{persona_id}.json")
    persona_file_yaml = os.path.join(personas_dir, f"{persona_id}.yaml")

    # Default fallback schema
    persona_data: Dict[str, Any] = {
        "id": persona_id,
        "name": persona_id.replace("-", " ").title(),
        "domain": config.get("goals", {}).get("domain", "this industry"),
        "platform": platform,
        "community": community,
        "tone": "direct, value-first, conversational",
        "forbidden_phrases": ["great post", "thanks for sharing", "100% agree"],
        "max_length": 280 if "x" in platform.lower() else 1500,
        "response_frameworks": {
            "value_points": [
                "Focusing on the foundational variables that drive 80% of the outcome",
                "Testing and validating assumptions in production before scaling",
                "Setting clear benchmarks to measure progress objectively"
            ],
            "catalyst_questions": [
                "How are you currently approaching this in your day-to-day workflow?",
                "What has been the biggest bottleneck you've encountered so far?"
            ]
        }
    }

    raw_loaded: Dict[str, Any] = {}
    if os.path.exists(persona_file_json):
        try:
            with open(persona_file_json, "r", encoding="utf-8") as f:
                raw_loaded = json.load(f)
        except Exception:
            pass
    elif os.path.exists(persona_file_yaml):
        try:
            with open(persona_file_yaml, "r", encoding="utf-8") as f:
                raw_loaded = parse_simple_yaml(f.read())
        except Exception:
            pass
    elif os.path.exists(persona_file_md):
        try:
            with open(persona_file_md, "r", encoding="utf-8") as f:
                content = f.read()
                fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if fm_match:
                    parsed = parse_simple_yaml(fm_match.group(1))
                    if isinstance(parsed, dict):
                        raw_loaded = parsed
        except Exception:
            pass

    if raw_loaded:
        persona_data.update(raw_loaded)

    return persona_data


def calculate_relevance_and_virality(
    post: Dict[str, Any],
    config: Dict[str, Any]
) -> Tuple[int, str]:
    """
    Calculates a relevance score (0-100) and triage recommendation.
    Factors: keyword presence, engagement metrics, velocity, and question intent.
    """
    score = 0
    text = (post.get("content_text") or "").lower()
    platform = post.get("platform", "x.com").lower()
    platform_key = platform.replace(".", "_")

    # 1. Keyword Matching (0-40 pts)
    platform_cfg = config.get("platforms", {}).get(platform_key, {})
    keywords = platform_cfg.get("keywords", [])
    if not keywords:
        keywords = config.get("goals", {}).get("target_audiences", ["tips", "advice", "help", "guide"])

    matched_kw = [kw for kw in keywords if kw.lower() in text]
    score += min(len(matched_kw) * 15, 40)

    # 2. Engagement Metrics & Virality (0-35 pts)
    likes = int(post.get("likes", 0))
    replies = int(post.get("replies", 0))
    shares = int(post.get("shares", 0))

    if likes >= 50 or replies >= 10:
        score += 35
    elif likes >= 20 or replies >= 5:
        score += 25
    elif likes >= 5 or replies >= 2:
        score += 15
    elif likes > 0:
        score += 5

    # 3. Conversational / Question Opportunity (0-25 pts)
    if "?" in text or any(q in text for q in ["how do you", "what is", "anyone tried", "recommendations", "thoughts on", "struggling with", "help with"]):
        score += 25
    elif any(d in text for d in ["debate", "versus", "vs", "broken", "fail", "hot take", "unpopular opinion"]):
        score += 15

    # Cold Post Triage Filter
    min_threshold = platform_cfg.get("min_engagement_threshold", {})
    min_likes = min_threshold.get("likes", 0)
    min_replies = min_threshold.get("replies", 0)

    if score < 25 or (min_likes > 0 and likes < min_likes and replies < min_replies and "?" not in text):
        return score, "cold"

    return min(score, 100), "viable"


def extract_topic_from_text(text: str, default_domain: str = "this space") -> str:
    """Extracts a concise conversational topic from post text."""
    cleaned = re.sub(r'https?://\S+', '', text).strip()
    sentences = [s.strip() for s in re.split(r'[.!?\n]', cleaned) if s.strip()]
    if sentences:
        first_s = sentences[0]
        if len(first_s) > 80:
            return first_s[:77] + "..."
        return first_s
    return default_domain


def generate_op_response(
    post: Dict[str, Any],
    persona: Dict[str, Any],
    goal: str
) -> str:
    """
    Drafts a high-impact, value-first response to the original post (OP)
    driven dynamically by the persona's configured domain, frameworks, value points,
    and catalyst questions (applicable to any niche: realtor, roofer, tech, coach, etc.).
    """
    content_text = post.get("content_text", "")
    author = post.get("author", "")
    author_handle = post.get("author_handle", "").lstrip("@")
    platform = post.get("platform", "x.com").lower()

    domain = persona.get("domain") or persona.get("name") or "this space"
    frameworks = persona.get("response_frameworks", {})
    if not isinstance(frameworks, dict):
        frameworks = {}

    # Extract value points & catalyst questions
    value_points = frameworks.get("value_points", [])
    if not value_points and isinstance(persona.get("value_points"), list):
        value_points = persona.get("value_points")

    catalyst_questions = frameworks.get("catalyst_questions", [])
    if not catalyst_questions and isinstance(persona.get("catalyst_questions"), list):
        catalyst_questions = persona.get("catalyst_questions")

    # Select values
    vp1 = value_points[0] if len(value_points) > 0 else f"Focusing on the core variables that impact {domain}"
    vp2 = value_points[1] if len(value_points) > 1 else f"Auditing real-world constraints before scaling"
    vp3 = value_points[2] if len(value_points) > 2 else f"Enforcing clear verification criteria"

    cat_q = catalyst_questions[0] if len(catalyst_questions) > 0 else f"How are you currently approaching this in your workflow?"

    topic = extract_topic_from_text(content_text, domain)

    # Custom template support if configured in persona
    custom_template = frameworks.get("op_template") or persona.get("op_template")
    if custom_template and isinstance(custom_template, str):
        try:
            return custom_template.format(
                author=author,
                author_handle=author_handle,
                domain=domain,
                topic=topic,
                value_point_1=vp1,
                value_point_2=vp2,
                value_point_3=vp3,
                catalyst_question=cat_q
            )
        except Exception:
            pass

    is_x = "x" in platform
    is_skool = "skool" in platform
    is_linkedin = "linkedin" in platform

    if is_skool:
        return (
            f"Solid breakdown on this! When dealing with {domain}, a common challenge is {vp1.lower()}.\n\n"
            f"What has worked consistently well for our setups is {vp2.lower()}.\n\n"
            f"{cat_q}"
        )
    elif is_x:
        if len(value_points) >= 3:
            return (
                f"The key bottleneck with {topic.lower()} comes down to execution friction.\n\n"
                f"What works in {domain}:\n"
                f"1. {vp1}\n"
                f"2. {vp2}\n"
                f"3. {vp3}\n\n"
                f"{cat_q}"
            )
        else:
            return (
                f"Spot on observation. In {domain}, {vp1}.\n\n"
                f"What has made the biggest difference in practice is {vp2}.\n\n"
                f"{cat_q}"
            )
    elif is_linkedin:
        return (
            f"Great perspective on {topic}.\n\n"
            f"In {domain}, one critical factor we frequently see is {vp1.lower()}.\n\n"
            f"Prioritizing {vp2.lower()} creates a noticeable shift in consistency and outcomes.\n\n"
            f"{cat_q}"
        )
    else:
        return (
            f"Appreciate this perspective on {topic}. In {domain}, {vp1}.\n\n"
            f"From our experience, {vp2}.\n\n"
            f"{cat_q}"
        )


def generate_subcomment_catalysts(
    sub_comments: List[Dict[str, Any]],
    persona: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generates targeted replies to active sub-commenters driven by the persona's
    configured domain, sub-comment templates, and catalyst questions.
    """
    catalysts = []
    domain = persona.get("domain") or persona.get("name") or "this space"
    frameworks = persona.get("response_frameworks", {})
    if not isinstance(frameworks, dict):
        frameworks = {}

    value_points = frameworks.get("value_points", [])
    if not value_points and isinstance(persona.get("value_points"), list):
        value_points = persona.get("value_points")

    catalyst_questions = frameworks.get("catalyst_questions", [])
    if not catalyst_questions and isinstance(persona.get("catalyst_questions"), list):
        catalyst_questions = persona.get("catalyst_questions")

    sub_templates = frameworks.get("sub_comment_templates", {})
    if not sub_templates and isinstance(persona.get("sub_comment_templates"), dict):
        sub_templates = persona.get("sub_comment_templates")

    q_template = sub_templates.get("question") if isinstance(sub_templates, dict) else None
    d_template = sub_templates.get("discussion") if isinstance(sub_templates, dict) else None

    for i, comment in enumerate(sub_comments[:3]):
        raw_handle = comment.get("commenter_handle", "")
        handle = raw_handle.lstrip("@")
        c_text = comment.get("comment_text", "")

        if not c_text:
            continue

        vp = value_points[i % len(value_points)] if value_points else f"auditing the specific boundary conditions"
        cat_q = catalyst_questions[(i + 1) % len(catalyst_questions)] if catalyst_questions else f"Are you seeing this consistently or just in specific cases?"

        if "?" in c_text or "how" in c_text.lower():
            if q_template and isinstance(q_template, str):
                try:
                    reply_text = q_template.format(handle=handle, domain=domain, value_point=vp, catalyst_question=cat_q)
                except Exception:
                    reply_text = f"@{handle} We see that frequently in {domain}. In practice, {vp.lower()} resolves the majority of edge cases. {cat_q}"
            else:
                reply_text = (
                    f"@{handle} We see that frequently in {domain}. In practice, {vp.lower()} resolves the majority of edge cases. {cat_q}"
                )
        else:
            if d_template and isinstance(d_template, str):
                try:
                    reply_text = d_template.format(handle=handle, domain=domain, value_point=vp, catalyst_question=cat_q)
                except Exception:
                    reply_text = f"@{handle} That is a key factor. In {domain}, {vp.lower()} often makes or breaks long-term results. {cat_q}"
            else:
                reply_text = (
                    f"@{handle} That is a key factor. In {domain}, {vp.lower()} often makes or breaks long-term results. {cat_q}"
                )

        catalysts.append({
            "target_handle": handle,
            "sub_comment_id": comment.get("id"),
            "content_text": reply_text
        })

    return catalysts


def process_post_item(
    post_data: Dict[str, Any],
    social_dir: str,
    db_path: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Evaluates a single post, indexes it, and generates drafts if viable."""
    platform = post_data.get("platform", "x.com")
    url = post_data.get("url", "")
    community = post_data.get("community", "all")
    content_text = post_data.get("content_text", "")

    # 1. Cold Post Check
    if is_post_cold(db_path, platform, url):
        return {"id": None, "status": "skipped_cold", "url": url}

    # 2. Score & Triage
    score, recommendation = calculate_relevance_and_virality(post_data, config)

    if recommendation == "cold":
        skip_ttl = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)).isoformat()
        post_id = upsert_post(
            db_path=db_path,
            platform=platform,
            url=url,
            content_text=content_text,
            author=post_data.get("author", ""),
            author_handle=post_data.get("author_handle", ""),
            community=community,
            likes=post_data.get("likes", 0),
            replies=post_data.get("replies", 0),
            shares=post_data.get("shares", 0),
            views=post_data.get("views", 0),
            relevance_score=score,
            status="ignored",
            skip_until=skip_ttl,
            metadata=post_data.get("metadata")
        )
        return {"id": post_id, "status": "triaged_cold", "relevance_score": score, "url": url}

    # 3. Resolve Persona (loads domain, frameworks, voice)
    persona = resolve_persona_for_post(
        social_dir, platform, community, config,
        explicit_persona_id=post_data.get("target_persona")
    )
    primary_goal = config.get("goals", {}).get("primary", "community_growth")

    # 4. Upsert Post
    post_id = upsert_post(
        db_path=db_path,
        platform=platform,
        url=url,
        content_text=content_text,
        author=post_data.get("author", ""),
        author_handle=post_data.get("author_handle", ""),
        community=community,
        likes=post_data.get("likes", 0),
        replies=post_data.get("replies", 0),
        shares=post_data.get("shares", 0),
        views=post_data.get("views", 0),
        relevance_score=score,
        target_persona=persona.get("id"),
        status="discovered",
        metadata=post_data.get("metadata")
    )

    # 5. Generate OP Reply (driven by persona domain & value points)
    op_draft = generate_op_response(post_data, persona, primary_goal)
    upsert_draft_reply(
        db_path=db_path,
        post_id=post_id,
        reply_type="op_reply",
        content_text=op_draft,
        persona_id=persona.get("id"),
        target_handle=post_data.get("author_handle", "")
    )

    # 6. Multi-Comment High-Engagement Catalysts
    sub_comments = post_data.get("sub_comments", [])
    if sub_comments and (post_data.get("replies", 0) >= 3 or len(sub_comments) >= 2):
        catalysts = generate_subcomment_catalysts(sub_comments, persona)
        for cat in catalysts:
            upsert_draft_reply(
                db_path=db_path,
                post_id=post_id,
                reply_type="sub_thread_catalyst",
                content_text=cat["content_text"],
                persona_id=persona.get("id"),
                target_handle=cat["target_handle"],
                sub_comment_id=cat.get("sub_comment_id")
            )

    return {
        "id": post_id,
        "status": "drafted",
        "relevance_score": score,
        "persona": persona.get("id"),
        "url": url
    }


def main():
    parser = argparse.ArgumentParser(description="Engagement Evaluator & Response Generator")
    parser.add_argument("--evaluate-json", type=str, help="Path to JSON file containing scraped/discovered posts")
    parser.add_argument("--target-dir", type=str, help="Target workspace directory")

    args = parser.parse_args()

    social_dir = resolve_social_dir(args.target_dir)
    db_path = get_db_path(args.target_dir)
    init_db(db_path)
    config = load_config(social_dir)

    if args.evaluate_json:
        if not os.path.exists(args.evaluate_json):
            print(f"❌ Error: File not found: {args.evaluate_json}")
            sys.exit(1)

        with open(args.evaluate_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        posts = data if isinstance(data, list) else data.get("posts", [])
        print(f"🔍 Evaluating {len(posts)} posts for relevance and persona alignment...")

        results = []
        for p in posts:
            res = process_post_item(p, social_dir, db_path, config)
            results.append(res)

        export_to_json(args.target_dir)

        viable_count = len([r for r in results if r.get("status") == "drafted"])
        cold_count = len([r for r in results if "cold" in r.get("status", "")])

        print(f"✅ Evaluation Complete:")
        print(f"  • Drafted High-Leverage Actions: {viable_count}")
        print(f"  • Triaged / Negative Cached Cold Posts: {cold_count}")


if __name__ == "__main__":
    main()
