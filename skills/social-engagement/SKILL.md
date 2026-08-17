---
name: social-engagement
description: Anti-bot human-safe social engagement and community cultivation engine for X.com, Skool, and LinkedIn. Features cold-post triage culling, persona-based multi-tier comment generation, and interactive HTML action dashboard. Triggers on social, engage, x.com, twitter, skool, linkedin, community, post, comment, reply.
tools:
  - view_file
  - run_command
  - write_to_file
  - replace_file_content
---

# Social Engagement Skill

The **Social Engagement Skill** provides an anti-bot resilient, high-leverage engagement system designed to discover trending conversations across **X.com**, **Skool.com**, **LinkedIn**, and community forums, index them with cold-post triage caching, and generate high-impact single and multi-comment responses aligned with configurable user goals and platform personas.

---

## 1. Anti-Bot Safety & The "Slow is Safe" Architecture

Social platforms aggressively detect and penalize automated bot scrapers and high-frequency API hammering. To keep user accounts safe:
1. **Zero Bot Scraper Fingerprints**: Do not make high-frequency automated HTTP requests. Use browser-driven DOM inspection and human-paced navigation.
2. **Action Dashboard & Review Queue**: All generated responses are written to an interactive **HTML Action Dashboard** (`workforces/social/dashboard.html`) and markdown action queue (`workforces/social/action_queue.md`) with direct post links and one-click copy buttons.
3. **Safe Human Execution**: A human operator can quickly review, click *"Open Post in Browser"*, and paste the response safely.

---

## 2. Core Components & Directory Structure

```
workforces/social/
├── config.yaml          # Multi-platform settings, goals, keywords, thresholds
├── personas/            # Persona profiles for specific platforms or communities
├── social_index.db      # High-performance SQLite database (WAL mode)
├── index.json           # JSON export of indexed posts & threads
├── queue.json           # Active pending drafts and review queue
├── action_queue.md      # Markdown queue with direct post links
└── dashboard.html       # Self-contained dark-mode interactive HTML review dashboard
```

---

## 3. Scripts & CLI Commands

All scripts are located under `skills/social-engagement/scripts/`:

### A. Index & Triage Manager (`social_indexer.py`)
```bash
# Initialize SQLite schema
python3 skills/social-engagement/scripts/social_indexer.py --init

# List indexed posts
python3 skills/social-engagement/scripts/social_indexer.py --list --status drafted

# Show index stats & platform breakdown
python3 skills/social-engagement/scripts/social_indexer.py --stats

# Export SQLite index to index.json and queue.json
python3 skills/social-engagement/scripts/social_indexer.py --export-json
```

### B. Evaluator & Multi-Tier Response Generator (`engagement_evaluator.py`)
```bash
# Evaluate discovered posts JSON, score relevance, triage cold posts, and draft replies
python3 skills/social-engagement/scripts/engagement_evaluator.py --evaluate-json /path/to/discovered_posts.json
```

### C. Dashboard Generator (`dashboard_generator.py`)
```bash
# Generate workforces/social/dashboard.html and workforces/social/action_queue.md
python3 skills/social-engagement/scripts/dashboard_generator.py
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
