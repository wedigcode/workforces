---
name: business-frameworks
description: Applies rigorous MBA-level business frameworks (Harvard, Wharton, Stanford GSB) and quantitative decision models to product strategy. Reach for this skill when evaluating business viability, auditing unit economics (LTV:CAC, CAC payback period), conducting Value Stick analysis (WTP/WTS expansion), architecting compounding growth loops and network effects, or challenging speculative feature proposals with the 4-Step Executive Decision Sequence before writing code.
---

# Business Frameworks & Strategic Decision Mechanics

Contemporary economic frameworks and quantitative decision models for strategic evaluations.

---

## ⚡ The 4-Step Executive Decision Sequence

Apply this 4-step sequence before committing engineering hours or during strategic reviews (`/wf-sync --strategy`):

| Step | Framework | Key Question & Hurdle |
| :---: | :--- | :--- |
| **1** | **JTBD & Customer Validation** | What situational trigger caused the customer to seek progress? Reject solutions lacking causal triggers. |
| **2** | **Value Stick Audit** | Does this expand Customer Delight ($\text{WTP} - \text{Price}$) or Supplier Surplus ($\text{Cost} - \text{WTS}$)? Zero-sum margin extraction is prohibited. |
| **3** | **Growth Loops & Network Effects** | How does user activity feed the next cohort's acquisition (viral, UGC/SEO, paid reinvestment, marketplace liquidity)? |
| **4** | **Unit Economics & Execution** | Are unit economics viable ($\text{LTV:CAC} \ge 3.0\times$, Payback $< 12\text{mo}$)? Use Sense-Seize-Transform to assign execution. |

---

## 📚 Deep Framework References

Detailed mathematical mechanics and case examples are located in `references/`:

| Framework | Core Question Answered | Reference Guide |
| :--- | :--- | :--- |
| **Value Stick** | How does the feature divide economic value across WTP, Price, Cost, and WTS? | [`references/value-stick.md`](references/value-stick.md) |
| **Jobs-to-be-Done (JTBD)** | What functional, emotional, and social job is being hired? | [`references/jobs-to-be-done.md`](references/jobs-to-be-done.md) |
| **Connected Strategy** | Which relationship model (Respond-to-desire, Curated, Coach, Automatic) creates repeat engagement? | [`references/connected-strategy.md`](references/connected-strategy.md) |
| **Growth Loops** | How does usage automatically compound acquisition without pure ad spend? | [`references/growth-loops.md`](references/growth-loops.md) |
| **Multi-Sided Platforms** | How are cross-side network effects, pricing asymmetries, and chicken-and-egg solved? | [`references/platform-strategy.md`](references/platform-strategy.md) |
| **Dynamic Capabilities** | How does the workforce systematically Sense, Seize, and Transform? | [`references/dynamic-capabilities.md`](references/dynamic-capabilities.md) |
| **Unit Economics** | How are LTV, CAC, churn, and payback periods calculated and benchmarked? | [`references/unit-economics.md`](references/unit-economics.md) |
