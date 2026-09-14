---
name: social-engagement
description: Drives organic, human-in-the-loop social media engagement and community cultivation across X (Twitter), LinkedIn, and Skool without sounding like an AI bot. Reach for this skill when discovering high-value industry conversations, filtering out low-engagement threads, drafting insightful multi-tier commentary aligned with specific brand personas, or managing queued social interactions in an interactive review dashboard.
---

# Social Engagement & Community Growth

Anti-bot engagement framework for discovering conversations, filtering cold posts, and drafting high-value replies across X.com, LinkedIn, and Skool. Led by `@social`.

---

## 1. Safety Guardrails & Human Review

- **Zero Unattended Posting**: Scripts never post directly to external platforms.
- **Review Dashboard**: All drafted responses save to `workforces/social/dashboard.html` and `action_queue.md` for 1-click human copy and review.
- **Anti-Bot Quality**: Every reply must provide authentic value, introduce a counter-perspective, or cite a practical mental model.

---

## 2. Multi-Tier Engagement Strategy

1. **Primary OP Response**:
   - Provide a concrete framework, mental model, or edge-case nuance.
   - End with an open-ended calibration question to invite author engagement.
   - Strictly prohibit empty platitudes (*"Great post!", "100% agree!"*).
2. **Sub-Thread Catalysts**:
   - Identify 2–3 active commenters who asked unanswered questions or raised objections.
   - Craft targeted replies addressing each commenter directly with actionable tips and conversation-starter questions.

---

## 3. CLI Quick Reference

All scripts run via `.agents/skills/social-engagement/scripts/` (Fallback: `skills/...`):

| Operation | Command Pattern |
| :--- | :--- |
| **Evaluate & Draft** | `python3 .agents/skills/social-engagement/scripts/engagement_evaluator.py --evaluate-json workforces/social/posts.json` |
| **Render Dashboard** | `python3 .agents/skills/social-engagement/scripts/dashboard_generator.py` |
| **Progressive Scroll**| `python3 .agents/skills/social-engagement/scripts/social_crawler.py --generate-browser-script` |
| **Unfold Thread** | `python3 .agents/skills/social-engagement/scripts/social_crawler.py --unfold-thread thread.json --output posts.json` |
| **Index Stats** | `python3 .agents/skills/social-engagement/scripts/social_indexer.py --stats` |
