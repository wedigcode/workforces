# Social Engagement & Community Interaction Rules

These rules govern all automated and assisted social discovery, content scoring, and comment drafting across X.com, Skool, LinkedIn, and community platforms.

---

## 1. Anti-Bot Safety & The "Slow is Safe" Protocol
- **Account Protection Priority**: Platforms (X.com, Skool, LinkedIn) actively monitor and penalize bot-like behavior, rapid API polling, and headless automation.
- **Human-in-the-Loop by Default**: Draft all suggested responses to the **Action Dashboard** (`workforces/social/dashboard.html`) and markdown queue (`workforces/social/action_queue.md`) with direct post links and copy buttons so a human operator can review and post safely.
- **Zero Headless Scraping Abuse**: Never make high-frequency programmatic scraping calls that trigger Cloudflare, Akamai, or anti-bot defenses. Use browser-driven inspection with realistic human pacing.

---

## 2. Value-First Principle & Absolute Prohibition of AI Sycophancy
- **No Empty AI Platitudes**: NEVER generate generic, hollow comments such as:
  - *"Great post! Thanks for sharing!"*
  - *"100% agree with this! Very insightful."*
  - *"Spot on! Couldn't have said it better."*
  - *"Love this perspective, saving for later!"*
- **The Value-First Standard**: Every single response generated MUST provide at least ONE of:
  1. **A Concrete Framework / Mental Model**: A structured way to apply or think about the topic.
  2. **A Constructive, Data-Backed Nuance or Counter-Perspective**: A respectful addition or edge-case consideration that deepens the discussion.
  3. **A Conversational Catalyst**: An open-ended, high-context question that invites the author or community to reply.
  4. **A Practical Implementation Tip**: Actionable steps or lessons learned from real-world execution.

---

## 3. Multi-Tier High-Engagement Threading
- **Beyond Single Comments**: When a post has high engagement (significant reply velocity or debate), the agent MUST NOT stop at responding only to the original post (OP).
- **Sub-Thread Identification**: Identify 2–3 active commenters who asked unanswered questions, raised thoughtful objections, or shared interesting experiences.
- **Targeted Catalyst Replies**: Generate personalized sub-replies that:
  - Address the specific commenter by context.
  - Bridge their point back to practical solutions or insights.
  - Pose a targeted follow-up question to spark multi-turn conversation.

---

## 4. Per-Website & Per-Community Persona Fidelity
- **Context Awareness**: The tone, formatting, and depth must adapt strictly to the target website and community guidelines:
  - **X.com (Twitter)**: Punchy, concise (<280 chars unless longform), hook-first, clear line breaks, insight-dense.
  - **Skool.com**: Warm, community-minded, structured markdown, step-by-step guidance, supportive peer tone.
  - **LinkedIn**: Professional storytelling, clear spacing, business/ROI outcomes, strategic takeaways.
- **Persona Routing**: Always load the persona associated with the specific website or community from `workforces/social/personas/` via `workforces/social/config.yaml`.

---

## 5. Strategic Goal Alignment
Every comment drafted must align with the active strategic goal configured in `workforces/social/config.yaml`:
- **`brand_authority`**: Highlight deep engineering/architectural expertise, benchmarks, and production-tested patterns.
- **`community_growth`**: Spark thoughtful debate, connect like-minded builders, and naturally invite high-intent peers into the community.
- **`lead_generation`**: Share relevant open-source tools, templates, or teardowns where organically helpful.
- **`support_and_reputation`**: Solve specific user pain points and debug community technical issues.

---

## 6. Cold-Post Negative Caching (Triage Efficiency)
- To avoid wasting tokens and review cycles on low-value content, the engine must tag non-viable posts (below engagement threshold, off-topic, or spam) as `cold`/`ignored` in the SQLite index.
- Never re-evaluate or re-read cold posts unless their engagement velocity undergoes a major verified surge.
