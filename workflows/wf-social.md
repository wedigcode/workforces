---
description: Human-safe social engagement engine — discover, triage cold posts, evaluate relevance, draft multi-tier responses, and generate the interactive action dashboard.
---

# /wf-social — Social Engagement & Community Cultivation

The `/wf-social` workflow discovers high-signal discussions on **X.com**, **Skool**, and **LinkedIn**, filters out dead posts with cold-caching, drafts high-leverage OP and sub-comment responses, and publishes an interactive **HTML Action Dashboard** with one-click copy buttons and live post links.

---

## Usage

```
/wf-social                          → Generate & refresh interactive HTML dashboard and markdown queue
/wf-social evaluate <path/to/posts.json> → Score posts, triage cold items, and generate drafts
/wf-social list                     → List indexed posts with status and relevance score
/wf-social list --status drafted    → List pending draft items
/wf-social stats                    → Display database stats, indexed totals, and platform counts
```

---

## Skills Required

Load these skills before starting:
1. **`social-engagement`** — the core indexer, cold triage, and dashboard generator scripts
2. **`brand-guidelines`** — brand tone, voice rules, and communication consistency
3. **`memory-management`** — OKF knowledge catalog access

```
Read: .agents/skills/social-engagement/SKILL.md
Read: .agents/skills/brand-guidelines/SKILL.md
```

---

## Step 1 — Verify Configuration & Persona Routing

1. Inspect `workforces/social/config.yaml` to confirm:
   - Primary user goal (`community_growth`, `brand_authority`, `lead_generation`, `support`).
   - Platform keywords and minimum engagement thresholds.
   - Persona assignment for the target website or community.

---

## Step 2 — Progressive Ingestion & Negative Cold-Post Triage

1. **Progressive Feed & Thread Ingestion**:
   - When inspecting dynamic feeds (Skool, X.com, LinkedIn), execute progressive scrolling (`window.scrollTo` in 5–10 stepped increments with 1.0–1.5s pauses) to trigger lazy-loading and ingest 15–20+ recent member posts.
   - For introduction threads (e.g. "Intro yourself") or Q&A discussions, unfold full comment streams into individually addressable posts:
     ```bash
     python3 .agents/skills/social-engagement/scripts/social_crawler.py --unfold-thread /path/to/thread.json --output /path/to/posts.json
     ```
2. **Negative Cold-Post Triage**:
   - Check if post was previously marked `ignored` or `cold` via `social_indexer.py`.
   - Skip cold posts immediately to conserve compute and avoid redundant reading.


---

## Step 3 — Relevance Scoring & Multi-Tier Response Generation

1. Execute the evaluator:
   ```bash
   python3 .agents/skills/social-engagement/scripts/engagement_evaluator.py --evaluate-json <path-to-posts.json>
   ```
2. The evaluator:
   - Scores relevance (0–100) based on keywords, velocity, and question opportunities.
   - Automatically loads the proper persona for the platform/community from `workforces/social/personas/`.
   - Drafts a value-first **Primary OP Response** using proven mental models and open-ended calibration questions.
   - On high-traffic viral posts, drafts **Sub-Thread Catalysts** targeting 2–3 active commenters to spark multi-turn conversation.

---

## Step 4 — Generate Action Dashboard & Review Queue

1. Run the dashboard generator:
   ```bash
   python3 .agents/skills/social-engagement/scripts/dashboard_generator.py
   ```
2. Outputs:
   - **`workforces/social/dashboard.html`**: Sleek, standalone dark-mode dashboard with one-click copy buttons and direct post links.
   - **`workforces/social/action_queue.md`**: Clean markdown queue for terminal/editor viewing.

---

## Step 5 — Human Review & Publishing

1. Review pending items in `workforces/social/dashboard.html` or `workforces/social/action_queue.md`.
2. Click **Open Post in Browser ↗** to navigate to the live discussion.
3. Click **Copy Reply** to grab the generated response and paste it with zero anti-bot risk.
