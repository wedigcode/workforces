---
name: social-engagement
description: Anti-bot human-safe social engagement and community cultivation engine for X.com, Skool, and LinkedIn. Features cold-post triage culling, persona-based multi-tier comment generation, and interactive HTML action dashboard. Triggers on social, engage, x.com, twitter, skool, linkedin, community, post, comment, reply.
---

# Skill: Social Engagement & Community Growth

The `social-engagement` skill provides a systematic, anti-bot framework for discovering high-potential discussions, discarding stale/dead threads, and drafting valuable, multi-tier replies across X (Twitter), Skool, and LinkedIn.

---

## 1. Safety Guardrails & Human-in-the-Loop Protocol

1. **Zero Unattended Posting**: Under NO circumstances should automated scripts execute HTTP POST or browser clicks to publish comments directly without user review.
2. **Review Dashboard**: All drafted responses must be saved into `workforces/social/` and surfaced via `workforces/social/dashboard.html` for 1-click human copy, verification, and manual posting.
3. **Anti-Bot Quality**: Responses must add authentic value, introduce new angles or framework insights, and avoid low-effort generic compliments (*"Nice post!", "Agreed!"*).

---

## 2. Architecture & Data Flow

```
[Candidate Posts / URLs]
       │
       ▼
[social_crawler.py] ──> Extract DOM / Text & Unfold Threads
       │
       ▼
[is_post_cold()] ─────> Skip if closed/resolved or >48h inactive
       │ (Pass)
       ▼
[engagement_evaluator.py] ─> Score relevance, match persona & draft multi-tier replies
       │
       ▼
[social_indexer.py] ──> Store in SQLite (workforces/social/social_engagement.db)
       │
       ▼
[dashboard_generator.py] ─> Render interactive workforces/social/dashboard.html
```

---

## 3. Scripts & CLI Commands

All scripts are located under `.agents/skills/social-engagement/scripts/` (or `skills/social-engagement/scripts/` in source toolkit):

### A. Index & Triage Manager (`social_indexer.py`)
```bash
# Initialize SQLite schema
python3 .agents/skills/social-engagement/scripts/social_indexer.py --init

# List indexed posts
python3 .agents/skills/social-engagement/scripts/social_indexer.py --list --status drafted

# Show index stats & platform breakdown
python3 .agents/skills/social-engagement/scripts/social_indexer.py --stats

# Export SQLite index to index.json and queue.json
python3 .agents/skills/social-engagement/scripts/social_indexer.py --export-json
```

### B. Evaluator & Multi-Tier Response Generator (`engagement_evaluator.py`)
```bash
# Evaluate discovered posts JSON, score relevance, triage cold posts, and draft replies
python3 .agents/skills/social-engagement/scripts/engagement_evaluator.py --evaluate-json /path/to/discovered_posts.json
```

### C. Progressive Scroll Crawler & Extractor (`social_crawler.py`)
```bash
# Output browser progressive scroll script
python3 .agents/skills/social-engagement/scripts/social_crawler.py --generate-browser-script

# Unfold an introduction or discussion thread into individual member engagement candidates
python3 .agents/skills/social-engagement/scripts/social_crawler.py --unfold-thread thread.json --output /path/to/posts.json

# Parse raw text dump into structured post records
python3 .agents/skills/social-engagement/scripts/social_crawler.py --parse-text-stream dump.txt --output /path/to/posts.json
```

### D. Dashboard Generator (`dashboard_generator.py`)
```bash
# Generate workforces/social/dashboard.html and workforces/social/action_queue.md
python3 .agents/skills/social-engagement/scripts/dashboard_generator.py
```

---

## 4. Multi-Tier High-Engagement Strategy

When evaluating high-traffic threads:
1. **Primary OP Response**:
   - Provide a concrete framework, mental model, or edge-case nuance.
   - End with an open-ended calibration question to invite author engagement.
   - Strictly prohibit empty platitudes (*"Great post!", "100% agree!"*).
2. **Sub-Thread Catalysts**:
   - Identify 2–3 active commenters who asked unanswered questions or raised objections.
   - Craft targeted replies addressing each commenter directly with actionable tips and conversation-starter questions.

---

## 5. Persona Resolution Per Website / Community

Personas are loaded dynamically based on the platform and community configuration in `workforces/social/config.yaml`.
- Platform key matching (`x_com` -> `personas/x-tech-founder.md`, `skool_com` -> `personas/skool-community-mentor.md`, `linkedin_com` -> `personas/linkedin-thought-leader.md`).
- If no custom persona file is found, the engine falls back to standard domain-excellence voice rules.
