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
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

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
    ".venv", "venv", "dist", "build", ".next", ".agents", "coverage",
    "var", "cache", ".cache", "tmp", ".tmp", "temp", "storage", "out", "pkg",
    "target", ".turbo", ".nuxt", ".output"
}


class SymbolIndexer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.symbols: List[Dict[str, Any]] = []

    def _filter_gitignored(self, candidate_paths: List[Path]) -> List[Path]:
        """Filter out files ignored by git using git check-ignore --stdin."""
        if not candidate_paths or not (self.root_dir / ".git").exists():
            return candidate_paths
        try:
            rel_strings = [str(p.relative_to(self.root_dir)) for p in candidate_paths]
            res = subprocess.run(
                ["git", "check-ignore", "--stdin"],
                cwd=self.root_dir,
                input="\n".join(rel_strings),
                capture_output=True,
                text=True,
                timeout=30
            )
            ignored_set = set(res.stdout.splitlines())
            if not ignored_set:
                return candidate_paths
            return [p for p in candidate_paths if str(p.relative_to(self.root_dir)) not in ignored_set]
        except Exception:
            return candidate_paths

    def scan(self, json_path: Optional[Path] = None, force: bool = False) -> List[Dict[str, Any]]:
        self.symbols.clear()
        
        # Check cache validity if json_path exists
        cached_symbols_by_file = {}
        json_mtime = 0.0
        if json_path and json_path.exists() and not force:
            try:
                json_mtime = json_path.stat().st_mtime
                data = json.loads(json_path.read_text(encoding="utf-8"))
                for sym in data.get("symbols", []):
                    f_rel = sym.get("file")
                    if f_rel:
                        cached_symbols_by_file.setdefault(f_rel, []).append(sym)
            except Exception:
                cached_symbols_by_file.clear()

        files_to_parse = []
        files_unmodified = []

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in LANG_EXTENSIONS:
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(self.root_dir))
                    try:
                        file_mtime = file_path.stat().st_mtime
                    except Exception:
                        file_mtime = json_mtime + 1.0

                    if cached_symbols_by_file and file_mtime <= json_mtime and rel_path in cached_symbols_by_file:
                        files_unmodified.append(rel_path)
                    else:
                        files_to_parse.append((file_path, LANG_EXTENSIONS[ext]))

        # Filter out gitignored files
        if files_to_parse:
            candidate_paths = [fp for fp, _ in files_to_parse]
            allowed_paths = set(self._filter_gitignored(candidate_paths))
            files_to_parse = [(fp, lang) for fp, lang in files_to_parse if fp in allowed_paths]

        # Fast path: no files modified!
        if cached_symbols_by_file and not files_to_parse:
            for rel_path, syms in cached_symbols_by_file.items():
                self.symbols.extend(syms)
            return self.symbols

        # Retain unmodified cached symbols
        for rel_path in files_unmodified:
            self.symbols.extend(cached_symbols_by_file[rel_path])

        # Parse modified / new files
        for file_path, lang in files_to_parse:
            self._parse_file(file_path, lang)

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
                f.write(f"| `{sym['name']}` | {sym['kind']} | {sym['language']} | [{sym['file']}](../../{sym['file']}#L{sym['line']}) | `{sym['signature']}` |\n")

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
                f.write(f"- **Location:** [{sym['file']}](../../../{sym['file']}#L{sym['line']})\n\n")
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
    parser.add_argument("--build-okf", action="store_true", help="Build full OKF markdown catalog files")
    parser.add_argument("--force", action="store_true", help="Force full rescan ignoring cache")

    args = parser.parse_args()

    root_path = args.scan or "."
    indexer = SymbolIndexer(root_path)
    out_json_path = Path(args.out_json)
    
    symbols = indexer.scan(json_path=out_json_path, force=args.force)
    indexer.export_graph_json(out_json_path)

    if args.build_okf:
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
        print(f"⚡ Code graph up to date: {len(symbols)} symbols indexed in {out_json_path}.")
        if args.build_okf:
            print(f"   OKF Catalog: {args.out_okf}/index.md")


if __name__ == "__main__":
    main()
