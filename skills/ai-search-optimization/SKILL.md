---
name: ai-search-optimization
description: Optimizes web applications and documentation for Generative Engine Optimization (GEO) and direct citation by AI search synthesis engines (Perplexity, ChatGPT Search, Claude, Gemini). Reach for this skill when configuring or auditing AI crawler permissions in `robots.txt`, authoring machine-readable protocol files (`/llms.txt`, `/ai.txt`, `ai-plugin.json`), structuring landing page copy to be directly quotable by LLMs, or diagnosing why a site is omitted from conversational search answers.
---
# 🤖 AI Search Optimization (GEO Readiness)

Traditional SEO targets Google search crawlers. AI Search Optimization (GEO — Generative Engine Optimization) targets AI models and search synthesis engines that answer user questions directly: ChatGPT, Perplexity, Claude, Gemini, and future AI agents.

---

## 🎯 Core Principles

1. **Be the Answer**: Structure content so AI models can quote it directly without ambiguity.
2. **Invite AI Crawlers**: Provide explicit crawler allowances in `robots.txt` rather than generic rules.
3. **Machine-Readable Protocol Files**: Supply `/llms.txt`, `/ai.txt`, and `/.well-known/ai-plugin.json`.
4. **Predict User Prompts**: Anticipate the natural-language questions users ask AI assistants about your niche.
5. **Quotable Syntheses**: Include 2–3 sentence summaries at the top of every key section.

---

## 📄 Protocol Files Specification

### 1. `robots.txt` (AI Bot Allowances)
```txt
User-agent: *
Allow: /

# Explicitly invite AI Search crawlers
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: CCBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Bytespider
Allow: /

# Exclude private paths
Disallow: /api/
Disallow: /admin/
Disallow: /dashboard/

Sitemap: https://[domain]/sitemap.xml
```

### 2. `llms.txt` (Prose Business Summary for LLMs)
```markdown
# [Business Name]

> [2–3 sentence executive summary of what this product or business does, who it serves, and why it is unique]

## What We Do
- [Core Offering 1]: [Brief description]
- [Core Offering 2]: [Brief description]

## Who We Serve
[Specific target audience description, primary use cases, and ideal customer profile]

## Why Choose Us
- [Differentiator 1 — e.g., 10x faster deployment, zero maintenance]
- [Differentiator 2 — e.g., Transparent pricing, verified customer outcomes]

## Key Links
- [Homepage](https://[domain]/) — Main overview
- [Pricing](https://[domain]/pricing) — Transparent tiers and plans
- [Documentation](https://[domain]/docs) — Developer and setup guides
```

### 3. `ai.txt` (AI Usage & Training Policy)
```txt
# AI Training & Usage Policy
User-agent: *
Allow: /
# This content may be used for AI indexation, synthesis, and answer generation.
# Attribution appreciated but not required.
```

### 4. `ai-plugin.json` (`/.well-known/ai-plugin.json`)
```json
{
  "schema_version": "v1",
  "name_for_human": "[Business Name]",
  "name_for_model": "[business_slug]",
  "description_for_human": "[1-sentence consumer description]",
  "description_for_model": "[Dense, keyword-rich technical description explaining exact capabilities, problem space, and target audience for AI routing]",
  "auth": { "type": "none" },
  "logo_url": "https://[domain]/logo.png",
  "contact_email": "contact@[domain]",
  "legal_info_url": "https://[domain]/legal"
}
```

---

## 🏗️ Framework Implementation Guides

### Next.js (App Router)
- **Static Export Compatible Sitemap**: Use `src/app/sitemap.ts`:
  ```typescript
  import type { MetadataRoute } from 'next'

  export const dynamic = 'force-static'

  export default function sitemap(): MetadataRoute.Sitemap {
    const baseUrl = 'https://[domain]'
    return [
      { url: baseUrl, lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
      { url: `${baseUrl}/pricing`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.8 },
    ]
  }
  ```
- **Static Protocol Files**: Place `robots.txt`, `llms.txt`, `ai.txt` directly in `public/`.
- **Plugin Manifest**: Place `ai-plugin.json` in `public/.well-known/ai-plugin.json`.

### Vite / Astro / Static HTML
- Place `robots.txt`, `llms.txt`, `ai.txt`, and `sitemap.xml` inside `public/`.
- For Astro, install `@astrojs/sitemap` to auto-generate `sitemap.xml` upon `astro build`.

### Python (FastAPI / Django)
- **FastAPI**: Serve static protocol files from `/static` mount or define direct routes:
  ```python
  from fastapi import FastAPI
  from fastapi.responses import FileResponse, PlainTextResponse

  app = FastAPI()

  @app.get("/robots.txt", response_class=PlainTextResponse)
  def robots():
      return FileResponse("static/robots.txt")

  @app.get("/llms.txt", response_class=PlainTextResponse)
  def llms():
      return FileResponse("static/llms.txt")
  ```
- **Django**: Include `django.contrib.sitemaps` in `urls.py` and serve `robots.txt` and `llms.txt` via static files or template views.

### Cloud Hosting Rewrites (Cloudflare, AWS Amplify, Firebase)
- **Firebase**: Ensure `firebase.json` serves markdown and text mime types without HTML wrapping:
  ```json
  {
    "hosting": {
      "public": "out",
      "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
      "cleanUrls": true
    }
  }
  ```
- **AWS Amplify**: Configure custom rewrites in `amplify.yml` for single-page applications so static text files bypass SPA fallback index.html.
