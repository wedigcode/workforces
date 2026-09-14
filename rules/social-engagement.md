# Social Engagement & Community Interaction Rules

- **Social Task Detection**: Whenever discovering discussions, evaluating feeds, or drafting social commentary (X.com, LinkedIn, Skool), the agent MUST consult [`@social`](../agents/social.md) and follow [`social-engagement`](../skills/social-engagement/SKILL.md).
- **Prohibition of AI Sycophancy**: NEVER draft hollow platitudes (*"Great post!", "100% agree!"*). Every response MUST provide a concrete framework, data-backed nuance, conversational catalyst, or practical execution tip.
- **Human-in-the-Loop Default**: Under NO circumstances execute unattended automated posting. All drafted responses MUST route to `workforces/social/dashboard.html` or `action_queue.md` for human review before publishing.
- **Progressive Scroll Ingestion**: When inspecting feeds via browser agents, execute 5–10 stepped scrolls (`window.scrollTo`) with 1.0–1.5s pauses and expand comment streams. Static `y = 0` scraping is prohibited.
- **Platform & Persona Fidelity**: Format strictly for the target platform (X.com punchy hook-first, Skool peer-supportive, LinkedIn strategic/ROI) matching the active persona in `workforces/social/config.yaml`.
