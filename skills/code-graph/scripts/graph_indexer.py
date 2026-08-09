#!/usr/bin/env python3
"""
Graph Indexer & Method Finder for Workforces
Zero external dependencies (uses standard Python 3: ast, re, json, pathlib, argparse).

Scans codebases to discover classes, functions, methods, docstrings, signatures,
and call references. Generates workforces/code-graph.json and OKF concept files
in workforces/knowledge-catalog/symbols/.
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Supported file extensions & comment rules
LANG_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby"
}

IGNORE_DIRS = {
    ".git", ".node_modules", "node_modules", "vendor", "__pycache__",
    ".venv", "venv", "dist", "build", ".next", ".agents", "coverage"
}


class SymbolIndexer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.symbols: List[Dict[str, Any]] = []

    def scan(self) -> List[Dict[str, Any]]:
        self.symbols.clear()
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in LANG_EXTENSIONS:
                    file_path = Path(root) / file
                    self._parse_file(file_path, LANG_EXTENSIONS[ext])
        return self.symbols

    def _parse_file(self, file_path: Path, language: str):
        rel_path = str(file_path.relative_to(self.root_dir))
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        if language == "python":
            self._parse_python(content, rel_path)
        else:
            self._parse_regex(content, rel_path, language)

    def _parse_python(self, content: str, rel_path: str):
        try:
            tree = ast.parse(content)
        except Exception:
            self._parse_regex(content, rel_path, "python")
            return

        lines = content.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]
                sig = f"{node.name}({', '.join(args)})"
                self.symbols.append({
                    "name": node.name,
                    "kind": "function",
                    "language": "python",
                    "signature": sig,
                    "file": rel_path,
                    "line": node.lineno,
                    "docstring": doc.strip(),
                    "calls": self._extract_python_calls(node)
                })
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                self.symbols.append({
                    "name": node.name,
                    "kind": "class",
                    "language": "python",
                    "signature": f"class {node.name}",
                    "file": rel_path,
                    "line": node.lineno,
                    "docstring": doc.strip(),
                    "calls": []
                })

    def _extract_python_calls(self, fn_node: ast.AST) -> List[str]:
        calls = set()
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return sorted(list(calls))

    def _parse_regex(self, content: str, rel_path: str, language: str):
        lines = content.splitlines()

        # Regex patterns for functions/methods across languages
        patterns = [
            # JS/TS: function foo(), const foo = () =>, async function foo()
            (r'^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)', "function"),
            (r'^\s*(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>', "function"),
            (r'^\s*(?:public|private|protected|async|static|\s)*\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)\s*(?::|{)', "method"),
            # Go: func Foo(...) or func (r *Receiver) Foo(...)
            (r'^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(([^)]*)\)', "function"),
            # Rust: fn foo(...)
            (r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)', "function"),
            # Java / C#: public void foo(...)
            (r'^\s*(?:public|private|protected|static|async|override|\s)+\s+[\w<>]+\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)', "method"),
            # Class definition across languages
            (r'^\s*(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z0-9_]+)', "class")
        ]

        for idx, line in enumerate(lines, 1):
            for pat, kind in patterns:
                match = re.search(pat, line)
                if match:
                    name = match.group(1)
                    if name in ("if", "for", "while", "switch", "catch", "constructor"):
                        continue
                    args = match.group(2) if match.lastindex >= 2 else ""
                    sig = f"{name}({args.strip()})" if kind != "class" else f"class {name}"
                    
                    self.symbols.append({
                        "name": name,
                        "kind": kind,
                        "language": language,
                        "signature": sig,
                        "file": rel_path,
                        "line": idx,
                        "docstring": "",
                        "calls": []
                    })
                    break

    def export_graph_json(self, output_file: Path):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "symbol_count": len(self.symbols),
                "symbols": self.symbols
            }, f, indent=2)

    def export_okf_catalog(self, catalog_dir: Path):
        catalog_dir.mkdir(parents=True, exist_ok=True)
        
        # Write symbols index file
        index_file = catalog_dir / "index.md"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write("type: Code Symbol Index\n")
            f.write("title: Codebase Symbol & Method Index\n")
            f.write(f"description: Extracted catalog of {len(self.symbols)} functions, methods, and classes.\n")
            f.write("---\n\n")
            f.write("# Codebase Symbol Index\n\n")
            f.write("| Symbol | Kind | Language | File | Signature |\n")
            f.write("|--------|------|----------|------|-----------|\n")
            for sym in self.symbols:
                f.write(f"| `{sym['name']}` | {sym['kind']} | {sym['language']} | [{sym['file']}](file:///{self.root_dir}/{sym['file']}#L{sym['line']}) | `{sym['signature']}` |\n")

        # Write individual symbol OKF files for key functions
        symbols_dir = catalog_dir / "symbols"
        symbols_dir.mkdir(exist_ok=True)

        for sym in self.symbols:
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', sym['name'])
            sym_file = symbols_dir / f"{safe_name}.md"
            with open(sym_file, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(f"type: Code Symbol\n")
                f.write(f"title: {sym['name']}\n")
                f.write(f"description: {sym['kind'].capitalize()} in {sym['file']}\n")
                f.write(f"language: {sym['language']}\n")
                f.write(f"file: {sym['file']}\n")
                f.write(f"line: {sym['line']}\n")
                f.write("---\n\n")
                f.write(f"# `{sym['name']}`\n\n")
                f.write(f"- **Kind:** {sym['kind']}\n")
                f.write(f"- **Signature:** `{sym['signature']}`\n")
                f.write(f"- **Location:** [{sym['file']}](file:///{self.root_dir}/{sym['file']}#L{sym['line']})\n\n")
                if sym['docstring']:
                    f.write(f"## Documentation\n```\n{sym['docstring']}\n```\n\n")
                if sym['calls']:
                    f.write("## Dependencies / Calls\n")
                    for call in sym['calls']:
                        f.write(f"- `{call}`\n")


def query_symbols(symbols: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    query_lower = query.lower()
    matches = []
    for sym in symbols:
        if (query_lower in sym['name'].lower() or
            query_lower in sym['signature'].lower() or
            query_lower in sym['docstring'].lower()):
            matches.append(sym)
    return matches


def main():
    parser = argparse.ArgumentParser(description="Code Graph Indexer & Method Finder (Workforces)")
    parser.add_argument("--scan", type=str, help="Scan codebase path")
    parser.add_argument("--query", type=str, help="Search query for existing methods")
    parser.add_argument("--out-json", type=str, default="workforces/code-graph.json", help="Path to output JSON")
    parser.add_argument("--out-okf", type=str, default="workforces/knowledge-catalog", help="Path to OKF catalog")

    args = parser.parse_args()

    root_path = args.scan or "."
    indexer = SymbolIndexer(root_path)
    symbols = indexer.scan()

    out_json_path = Path(args.out_json)
    indexer.export_graph_json(out_json_path)

    out_okf_path = Path(args.out_okf)
    indexer.export_okf_catalog(out_okf_path)

    if args.query:
        matches = query_symbols(symbols, args.query)
        print(f"\n🔍 Query: '{args.query}' — Found {len(matches)} matching symbol(s):\n")
        for m in matches:
            print(f"  • [{m['kind']}] {m['name']} ({m['language']}) -> {m['file']}:{m['line']}")
            print(f"    Signature: {m['signature']}")
            if m['docstring']:
                print(f"    Doc: {m['docstring'][:80]}...")
            print()
    else:
        print(f"✅ Code graph indexed successfully: {len(symbols)} symbols extracted.")
        print(f"   JSON: {out_json_path}")
        print(f"   OKF Catalog: {out_okf_path}/index.md")


if __name__ == "__main__":
    main()
