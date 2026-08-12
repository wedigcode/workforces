# Code Graph & Impact Analysis

The **Code Graph** is a zero-dependency symbol indexer and dependency mapper built directly into Workforces. It scans codebases to parse functions, methods, classes, signatures, docstrings, and call relationships, enabling symbol search, code deduplication, pre-hook blast radius analysis, and post-hook code reviews.

---

## 1. Overview & Architecture

Code Graph consists of two core scripts located in [`skills/code-graph/scripts/`](../skills/code-graph/scripts):

1. **[`graph_indexer.py`](../skills/code-graph/scripts/graph_indexer.py)**: Scans the codebase, parses symbols using Python `ast` (with fallback to multi-language regex patterns), and extracts call trees.
2. **[`pre_impact_analyzer.py`](../skills/code-graph/scripts/pre_impact_analyzer.py)**: Evaluates modified files against the index to compute downstream caller blast radius and suggest existing helper utilities.

### Supported Languages
- **Python** (AST parsing with full function call tree extraction)
- **TypeScript / JavaScript** (`.ts`, `.tsx`, `.js`, `.jsx`)
- **Go** (`.go`)
- **Rust** (`.rs`)
- **Java / C#** (`.java`, `.cs`)
- **PHP / Ruby** (`.php`, `.rb`)

---

## 2. Building & Caching the Code Graph

### Incremental `mtime` Caching (Ultra-Fast Pre-Hooks)
To prevent heavy codebase re-scans during interactive editing:
- `graph_indexer.py` compares source file `mtime` timestamps against `workforces/code-graph.json`.
- If no files have changed, scanning completes instantly (**< 5ms cache hit**) without parsing files or writing to disk.
- If files have changed, only modified files are re-parsed and merged into the cached symbol tree.

### Automatic Generation
The incremental index runs automatically via plugin hooks before file modifications (`pre_tool_call` event in [`plugins/workforce-programming-plugin/hooks/hooks.json`](../plugins/workforce-programming-plugin/hooks/hooks.json)).

### Full OKF Catalog Rebuild & Background Cleanliness (`/clean`)
Heavy OKF Markdown catalog file generation is decoupled from pre-hooks. To force a full catalog rebuild and run code cleanliness audits, run:

```bash
# Via CLI
python3 skills/code-graph/scripts/graph_indexer.py --scan ./ --build-okf --force

# Or via slash command / workflow
/clean
```

---

## 3. Generated Artifacts

When built, Code Graph produces two primary outputs:

### 1. JSON Database (`workforces/code-graph.json`)
A machine-readable symbol registry:
```json
{
  "symbol_count": 42,
  "symbols": [
    {
      "name": "calculateTotal",
      "kind": "function",
      "language": "typescript",
      "signature": "calculateTotal(items)",
      "file": "src/services/calculator.ts",
      "line": 42,
      "docstring": "",
      "calls": ["formatCurrency"]
    }
  ]
}
```

### 2. OKF Knowledge Catalog (`workforces/knowledge-catalog/`)
Human and AI-readable Open Knowledge Format catalog:
- **`workforces/knowledge-catalog/index.md`**: Master table listing all indexed symbols, kinds, languages, and line numbers (`src/services/calculator.ts#L42`).
- **`workforces/knowledge-catalog/symbols/<symbol_name>.md`**: Individual concept cards per symbol containing metadata frontmatter, signatures, docstrings, and outbound calls.

---

## 4. Common Workflows & CLI Commands

### 🔍 Symbol Search & Deduplication
Check if a function or helper already exists before writing new code:
```bash
python3 skills/code-graph/scripts/graph_indexer.py --scan ./ --query "format"
```

### 💥 Pre-Hook Impact & Blast Radius Analysis
Analyze downstream dependents and call sites affected by changes in a target file:
```bash
python3 skills/code-graph/scripts/pre_impact_analyzer.py --file src/services/calculator.ts
```

Output example:
```markdown
### 🔍 [Pre-Hook Impact & Context Analysis]
**Target File:** `src/services/calculator.ts`
- **Defined Symbols:** `calculateTotal` (function)

⚠️ **Downstream Blast Radius (Dependent Callers):**
  - `src/controllers/checkout.ts` (line 18): `handleCheckout()` calls `calculateTotal`
```

---

## 5. Hook Integration

Workforces integrates Code Graph into AI agent execution via plugin hooks in [`plugins/workforce-programming-plugin/hooks/hooks.json`](../plugins/workforce-programming-plugin/hooks/hooks.json):

1. **Pre-Hook (`pre_tool_call`)**: Runs `graph_indexer.py` and `pre_impact_analyzer.py` before `write_to_file`, `replace_file_content`, or `multi_replace_file_content` to warn the AI of downstream callers.
2. **Post-Hook (`post_tool_call`)**: Runs [`post_code_reviewer.py`](../skills/post-code-review/scripts/post_code_reviewer.py) after edits to verify cross-system consistency.
