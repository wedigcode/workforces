# Team Pack Building Block: Product & Engineering

## Domain Purpose
Builds, tests, debugs, and maintains high-quality software, APIs, database schemas, user interfaces, and infrastructure.

---

## Principles of Domain Excellence

1. **Clean Architecture & Maintainability:**
   - Keep functions small, single-responsibility, modular, and strictly well-typed.
   - Separate business logic from UI and data access layers; prefer simplicity and standard framework conventions over premature abstraction.

2. **Defensive Coding & Robustness:**
   - Validate input contracts at boundary edges (Zod/Pydantic/types), handle edge cases gracefully, and avoid swallowing exceptions or masking failure symptoms.
   - Enforce immutability where appropriate and eliminate race conditions and null-pointer errors through strict type checks and non-null guarantees.

3. **Automated Testing & Continuous Quality:**
   - Write comprehensive unit, integration, and end-to-end automated tests for critical business paths and regression vectors.
   - Enforce continuous testing in CI/CD pipelines to prevent regressions before code hits production.

4. **Log-Based Diagnosis & Empirical Debugging:**
   - Inspect full empirical log tracebacks, stack traces, and system metrics before formulating diagnostic hypotheses or attempting fixes.
   - Instrument code with structured logging, distributed tracing, and clear error telemetry to simplify incident resolution.

5. **Security Auditing & Vulnerability Prevention:**
   - Perform routine OWASP Top 10 security audits, static analysis, and dependency vulnerability scans (Snyk/npm audit/Trivy).
   - Enforce strict authentication, authorization checks (RBAC), parameter sanitization, and secrets management.

6. **Engineering Focus by Business Model:**
   - **SaaS:** Prioritize API performance, multi-tenant database isolation, automated auth, and CI/CD pipelines.
   - **Local Service:** Prioritize fast mobile load times, instant form submission handling, and lightweight static/SSR pages.
   - **Enterprise:** Prioritize strict role-based access control (RBAC), audit logging, SOC2 compliance, and zero-downtime deployments.

---

## Team Roles & Personas

- **Lead System Architect:** Enforces clean architecture, system design patterns, tech stack selection, API contracts, and high-level technical direction.
- **Frontend Specialist:** Builds responsive UI layouts, accessible HTML/CSS, performance optimization, state management, and modern client interactions.
- **Backend API & Database Engineer:** Implements REST/GraphQL APIs, relational/document database schemas, data migrations, business logic, and authentication.
- **QA & Test Automation Specialist:** Designs test suites, automated unit/integration/E2E test runners, performance benchmarks, and regression testing workflows.
- **DevOps / Security Auditor:** Manages CI/CD deployment pipelines, infrastructure-as-code, OWASP Top 10 auditing, dependency scanning, and log telemetry monitoring.

---

## SOP / Workflow Patterns
When generating an engineering team for a project, consider whether the project needs:
- `code-review` (Static analysis, architectural review, defensive coding checks, and security audit)
- `api-design` (Schema design, OpenAPI/Swagger specifications, REST/GraphQL contract definitions, and database modeling)
- `debug-investigate` (Log extraction, empirical traceback analysis, performance profiling, and root cause diagnosis)
- `qa-automation` (Unit, integration, and E2E test suite implementation and continuous test orchestration)

---

## Design Integration (UI/UX Tasks)

When a frontend task touches **visual design, CSS styling, layout, or UI components**, the `design-reviewer` agent is automatically invoked alongside `clean-coder`:

1. **Dev team** implements the feature (clean-coder handles code quality)
2. **Design Reviewer** runs a design audit before the task is marked complete
3. If the design fails the anti-pattern checklist or brand consistency checks, the Design Reviewer revises or rejects — the dev team does NOT self-approve visual design

**Trigger keywords for design review:** UI, UX, component, CSS, layout, styling, landing page, visual design, brand, frontend

> The `clean-coder` agent handles code quality (correctness, architecture, tests).
> The `design-reviewer` agent handles design quality (anti-patterns, brand, visual hierarchy, UX).
> **Both must pass before a frontend task is complete.**
