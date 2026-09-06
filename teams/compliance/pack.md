# Team Pack Building Block: Compliance & Governance

## Domain Purpose
Ensures regulatory compliance, data privacy, ad platform adherence, and governance across software and communications.

---

## Principles of Domain Excellence

1. **Proactive Auditing & Continuous Compliance:**
   - Integrate compliance checks early in content generation, ad creative design, and software architecture, not as an afterthought.
   - Maintain continuous monitoring of regulatory shifts, consent mechanisms, and security telemetry.

2. **Regulatory Data Privacy & Framework Adherence:**
   - **GDPR & CCPA:** Enforce strict consent management, cookie policies, data minimization, right-to-be-forgotten workflows, and data subject access requests (DSAR).
   - **HIPAA:** Maintain strict protected health information (PHI) encryption in transit and at rest, Business Associate Agreements (BAAs), and audit logging.
   - **SOC2 Type II:** Enforce continuous security controls, access controls, change management, infrastructure monitoring, and evidence collection.

3. **Terms of Service & Ad Platform Adherence:**
   - **Terms & Policies:** Draft transparent terms of service, acceptable use policies, refund/cancellation disclosures, and clear end-user agreements.
   - **Ad Platform Compliance:** Review advertising campaigns, landing page claims, claims substantiation, and prohibited content rules for Google Ads, Meta Ads, TikTok, and major ad networks to prevent account suspensions.

4. **Compliance Focus by Business Model:**
   - **Lead Generation / Affiliate:** Transparent contractor referral disclaimers, no false satisfaction/licensing guarantees, FTC advertising disclosure, privacy policies on all pages.
   - **SaaS:** Data privacy (GDPR/CCPA), terms of service, cookie consent, subscription cancellation disclosure, auto-renewal compliance.
   - **Local Service:** Local licensing disclosures, transparent pricing quotes, anti-spam (TCPA/CAN-SPAM) opt-out options, SMS consent logging.
   - **Enterprise:** Formal SOC2 Type II controls, HIPAA BAA agreements, ISO 27001 auditing, vendor risk assessments, enterprise SLA compliance.


---

## Team Roles & Governance

- **Data Privacy Officer / Auditor:** Audits data ingestion/storage, handles GDPR/CCPA/HIPAA consent workflows, manages DSAR requests, and enforces data minimization.
- **Platform & Terms Compliance Specialist:** Ensures ad creative and landing page claims satisfy ad network policies (Google, Meta, etc.), drafts Terms of Service, and reviews consumer disclosure rules.
- **Security & SOC2 Governance Specialist:** Defines infrastructure security controls, manages SOC2 Type II readiness, performs vendor risk assessments, and enforces RBAC/IAM auditing.

> ℹ️ *Automated reference lineage, link integrity, and subtask tracking are executed via the `integrity-validator` skill and automated lifecycle hooks (`workforce-integrity-plugin`), rather than an autonomous agent persona.*


---

## SOP / Workflow Patterns
When generating a compliance team for a project, consider whether the project needs:
- `privacy-audit` (Auditing data collection, consent flows, cookie banners, GDPR/CCPA compliance, and DSAR handling)
- `terms-compliance` (Drafting and reviewing Terms of Service, Privacy Policies, ad copy claims, and ad network policy adherence)
- `soc2-readiness` (Evaluating SOC2 controls, infrastructure security headers, access logging, and evidence gathering)
