# UI & Website Design Standards

- **Design Task Detection**: Whenever designing, styling, or implementing frontend interfaces, landing pages, web apps, or components, the agent MUST consult the [`designer`](../agents/designer.md) persona and follow [`design-anti-patterns`](../skills/design-anti-patterns/SKILL.md).
- **Absolute Prohibition of Emojis as UI Icons**: NEVER use unicode emojis (🚀, 💡, ⚡, 🔥, 🛠️, 📈, 🎨, 💻, 🎯, 🔒) as UI icons, button graphics, or feature symbols. Use cohesive vector SVG icon packs only (**Lucide**, **Heroicons**, **Phosphor**) with `currentColor` styling.
- **Refero-Grade Benchmarking**: Benchmark layouts against real craft systems ([styles.refero.design](https://styles.refero.design/)). Prohibit AI clichés: no centered 3-card columns, no diagonal gradient text headings, and no flat un-layered boxes.
- **Design Memory Adherence**: Strictly obey [`workforces/memory/design-preferences.md`](../workforces/memory/design-preferences.md). Never repeat user-rejected colors (e.g. yellow on white), layouts, or styling patterns.
- **Progressive Disclosure & Hierarchy**: Generous whitespace (`p-6`, `gap-6`+). Never display fake or non-actionable decorative telemetry (e.g. latency/protocol counters, raw UUIDs) or kitchen-sink layouts with competing sidebars.
- **WCAG AA Accessibility**: Minimum 4.5:1 text contrast, accessible focus rings, and minimum 44×44px touch targets.
- **Design Specification First**: Greenfield web properties must establish a concrete `DESIGN.md` spec (typography pairing, color tokens, layout hierarchy) led by `@designer` before writing component code.
