# Team Pack Building Block: Product & Engineering

## Domain Purpose
Builds, tests, debugs, and maintains high-quality software, APIs, database schemas, and user interfaces.

---

## Principles of Domain Excellence

1. **Clean Code & Architecture:**
   - Keep functions small, single-responsibility, and well-typed.
   - Prefer simplicity over premature over-engineering; preserve standard framework conventions.

2. **Defensive Design & Quality:**
   - Write clear automated unit/integration tests for critical business paths.
   - Inspect empirical logs and tracebacks before diagnosing runtime issues.

3. **Engineering Focus by Business Model:**
   - **SaaS:** Prioritize API performance, multi-tenant database isolation, automated auth, and CI/CD pipelines.
   - **Local Service:** Prioritize fast mobile load times, instant form submission handling, and lightweight static/SSR pages.
   - **Enterprise:** Prioritize strict role-based access control (RBAC), audit logging, SOC2 compliance, and zero-downtime deployments.

---

## Reusable Heuristics & Building Blocks

- **Frontend Specialist:** Responsive UI layout, accessible HTML, state management.
- **Backend Specialist:** REST/GraphQL API design, database migrations, authentication.
- **Security Auditor:** OWASP top 10 auditing, dependency vulnerability scanning.

---

## SOP / Workflow Patterns
When generating an engineering team for a project, consider whether the project needs:
- `product-launch` (Release checklist, build validation, deployment orchestration)
- `debug` (Log extraction, root cause analysis, targeted bug fixes)
- `investigate` (Performance profiling and error classification)
