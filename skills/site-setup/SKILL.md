---
name: site-setup
description: Comprehensive framework for greenfield site setup, multi-team handoffs (PM, Marketing, Design Pilot, Compliance, Dev), tech stack scaffolding with installer safeguards, framework-aware AI protocols, and tool sequencing hierarchy.
---

# 🚀 Site Setup & Product Brief Architecture

The definitive protocol for taking an empty repository or folder from a raw idea to a fully configured, branded, compliant, and scaffolded web property.

---

## 👥 Multi-Team Handoff Architecture

Site setup is not a monolithic step; it is an orchestrated pipeline managed by the `@project-manager` and handed off to specialized team roles:

```mermaid
graph TD
    A["Step 0: @project-manager<br/>Discovery & Team Registration"] --> B["Step 1: Marketing & SEO<br/>Audience, Keywords, Value Prop"]
    B --> C["Step 2: @design-pilot<br/>Visual Concept, Images & Tokens"]
    C --> D["Step 3: Compliance & Sales<br/>FTC Rules & Conversion Model"]
    D --> E["Step 4: @clean-coder (Dev)<br/>Tech Stack & AI Protocols"]
    E --> F["Step 5: PM Finalization<br/>Product Brief & Workstate Roadmap"]
```

### Team Responsibilities & Artifacts
| Stage | Owner / Team | Focus | Output Artifacts |
| :--- | :--- | :--- | :--- |
| **0. Strategy & Scope** | `@project-manager` | Site category, business model, team registration | `workforces/workstate.md`, `workforces/teams/` |
| **1. Marketing & SEO** | `marketing` / `@seo-architect` | Target audience, pain points, keyword strategy, copy hook | `docs/brand-context.md` (Voice, Audience, SEO) |
| **2. Visual Concept** | `design` / `@design-pilot` | Concept ideation (Awwwards/SiteInspire), visual mockups via `generate_image`, layout specs, tokens | `docs/brand-context.md` (Palette, Type), `src/styles/tokens.css`, `workforces/images.json` |
| **3. Compliance & Sales** | `compliance` / `sales` | Affiliate disclosures (Lead Gen) vs Direct SaaS terms, conversion CTAs | Compliance clauses in `docs/product-brief.md` |
| **4. Scaffolding & AI Protocols** | `dev` / `@clean-coder` | Scaffolding tech stack, language-specific AI protocol files (`robots.txt`, `llms.txt`, `ai.txt`, `sitemap`) | Codebase scaffolding, protocol files |
| **5. Brief Finalization** | `@project-manager` | Consolidate 7 mandatory brief sections, unblock P0 build tasks | `docs/product-brief.md`, `workforces/workstate.md` |

---

## 🛑 Framework Scaffolding & Install Safeguard Rule

Whenever executing framework initialization or package installation commands:
- **No Manual Boilerplate Coding**: If an automated command (such as `npx create-next-app`, `npm create vite@latest`, `django-admin startproject`, `poetry new`, `firebase init`, `amplify init`, `docker build`) fails, stalls, requires interactive input, or hits sandbox network isolation:
  1. **DO NOT attempt to manually code framework internals, config boilerplate, or package directories by hand.**
  2. **STOP execution immediately.**
  3. Output the exact command for the user to run in their host terminal.
  4. Wait for the user to confirm completion before proceeding.

---

## 🛠️ Technology Stack & Hosting Matrix

| Technology | Preferred Scaffolding Command | AI Protocol Strategy |
| :--- | :--- | :--- |
| **Next.js (App Router)** | `npx -y create-next-app@latest ./ --typescript --tailwind --eslint --app --src-dir` | `src/app/sitemap.ts` (static export `force-static`), `public/robots.txt`, `public/llms.txt`, `public/ai.txt`, `public/.well-known/ai-plugin.json` |
| **Vite / React / Vue** | `npm create vite@latest ./ -- --template react-ts` | `public/robots.txt`, `public/llms.txt`, `public/ai.txt`, `public/sitemap.xml` |
| **Astro** | `npm create astro@latest ./ -- --template minimal --no-install --no-git` | `@astrojs/sitemap`, `public/robots.txt`, `public/llms.txt`, `public/ai.txt` |
| **Python (FastAPI)** | `poetry new ./` or `pip install fastapi uvicorn` | `/static/robots.txt`, `/static/llms.txt`, `/static/ai.txt`, dynamic `/sitemap.xml` route |
| **Python (Django)** | `django-admin startproject config .` | `django.contrib.sitemaps`, static `robots.txt`, `llms.txt` |
| **Cloudflare Pages** | Integrated with Next.js/Vite/Astro build output (`out` or `dist`) | Native fast-edge static file serving with custom header rules |
| **AWS Amplify** | `npx -y @aws-amplify/cli init` / `amplify.yml` | Custom rewrites in `amplify.yml` for text/markdown MIME types |
| **Google Firebase / Cloud Run** | `firebase init hosting` / `firebase.json` | Hosting rewrites in `firebase.json` for static AI protocol files |
| **Docker** | Containerized multi-stage `Dockerfile` + `docker-compose.yml` | Nginx / Caddy static layer or app server serving protocols |

---

## ⚖️ Page Builder Compliance Variants

Choose the appropriate compliance profile during Step 0:

### 1. Lead Generation / Affiliate Model (`@compliant-page-builder`)
- **Nature**: Connects consumers with independent local service providers (e.g. Angi, HomeAdvisor, Thumbtack, insurance networks). Does not provide services directly.
- **Mandatory Requirements**:
  - Clear, prominent disclaimer in header/footer: *"This website is a free service to help homeowners connect with local service providers. All contractors are independent."*
  - No false guarantees (e.g. avoid *"100% satisfaction guarantee"*, *"Our licensed crew"*).
  - No fake reviews or fabricated testimonials.
  - Transparent advertiser disclosure and privacy policy links on all pages.

### 2. Direct Service / SaaS / E-commerce Model (`@page-builder`)
- **Nature**: The business performs services directly or provides software/products.
- **Allowed Features**:
  - Direct customer reviews, verified case studies, and social proof.
  - Tiered pricing tables, transparent feature breakdowns, and checkout/trial flows.
  - Formal service guarantees, warranties, and SLAs.

---

## ⏱️ Tool Sequencing Hierarchy

Execution MUST follow this strict dependency order:

1. **Step 1: Product Brief & Brand Context** (`docs/product-brief.md`, `docs/brand-context.md`)
2. **Step 2: Design Tokens** (`src/styles/tokens.css` or CSS variables)
3. **Step 3: Concept Images & Image Planning Queue** (`workforces/images.json` + `generate_image`)
4. **Step 4: Framework Scaffolding & Codebase Setup** (scaffold CLI under safeguard rule)
5. **Step 5: Language-Specific AI Protocols & SEO** (`robots.txt`, `llms.txt`, `ai.txt`, `sitemap`)
6. **Step 6: Image Optimization** (`skills/image-workflow/scripts/optimize_images.py`)
7. **Step 7: Component & Page Construction** (building against tokens and compliance rules)
8. **Step 8: SEO & Schema Validation** (LocalBusiness / Organization / FAQ schema)
