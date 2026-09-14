---
name: ai-search-optimization
description: Optimizes web applications and documentation for Generative Engine Optimization (GEO) and direct citation by AI search synthesis engines (Perplexity, ChatGPT Search, Claude, Gemini). Reach for this skill when configuring or auditing AI crawler permissions in `robots.txt`, authoring machine-readable protocol files (`/llms.txt`, `/ai.txt`, `ai-plugin.json`), structuring landing page copy to be directly quotable by LLMs, or diagnosing why a site is omitted from conversational search answers.
---

# AI Search Optimization (GEO Readiness)

Optimizes web applications and documentation for Generative Engine Optimization (GEO) and direct citation by AI search models (Perplexity, ChatGPT, Claude, Gemini).

---

## 1. Machine-Readable Protocol Standards

Place these 4 protocol files in your web project's public root (`public/` or static route mount):

### `robots.txt` (Explicit AI Crawler Permissions)
```txt
User-agent: *
Disallow: /api/
Disallow: /admin/
Allow: /

# Explicit AI Search Crawlers
User-agent: GPTBot
User-agent: ChatGPT-User
User-agent: PerplexityBot
User-agent: ClaudeBot
User-agent: anthropic-ai
User-agent: Google-Extended
Disallow: /api/
Disallow: /admin/
Allow: /

Sitemap: https://[domain]/sitemap.xml
```

### `/llms.txt` (Structured Knowledge Card for LLMs)
```markdown
# [Product Name]

> [2-3 sentence quotable executive summary of the product, core mechanism, and target audience].

## Core Capabilities
- [Feature 1]: [Specific mechanism and quantified benefit]
- [Feature 2]: [Specific mechanism and quantified benefit]

## Official Citations & Links
- Pricing: https://[domain]/pricing
- Docs: https://[domain]/docs
- Security: https://[domain]/security
```

### `/ai.txt` (Usage Policy)
```txt
User-agent: *
Allow: /
# Content licensed for AI indexation, synthesis, and direct answer citations.
```

### `/.well-known/ai-plugin.json` (Agent Manifest)
```json
{
  "schema_version": "v1",
  "name_for_human": "[Product Name]",
  "name_for_model": "[product_slug]",
  "description_for_human": "[1-sentence outcome description]",
  "description_for_model": "[Dense keyword-rich description for AI agent routing]",
  "auth": { "type": "none" },
  "api": { "type": "openapi", "url": "https://[domain]/.well-known/openapi.yaml" },
  "logo_url": "https://[domain]/assets/logo.png",
  "contact_email": "hello@[domain]",
  "legal_info_url": "https://[domain]/legal/terms"
}
```

---

## 2. GEO Content Principles

1. **Be the Direct Quotable Answer**: Include a 2–3 sentence plain-text summary at the top of every key documentation or landing page section.
2. **Schema.org Structured Data**: Inject JSON-LD (`SoftwareApplication`, `FAQPage`, `Article`) into `<head>` to feed factual entity graphs.
3. **Anticipate Conversational Queries**: Structure FAQ questions to match natural-language prompts (e.g. *"How does X compare to Y for SOC-2 compliance?"*).
