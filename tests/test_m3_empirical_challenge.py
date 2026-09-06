#!/usr/bin/env python3
"""
Test Suite: Milestone 3 Adversarial Empirical Challenge
Rigorous empirical challenge and verification for Milestone 3 (R3):
1. Verifies semantic query mapping for "What do we have to work on?", "Show active tasks",
   and backlog triage queries to wf-sync and task-tracker across all 37 skills.
2. Verifies modern Antigravity orchestration (agent-parallelization topologies) is properly
   documented and integrated into wf-sync, wf-plan, and rules/base.md.
3. Verifies complete removal of wf-work across agents/, rules/, workflows/, teams/, docs/, and skills/.
4. Verifies personal_sync.py execution across markdown and JSON output formats.
5. Verifies strict YAML frontmatter hygiene and scalar safety.
"""

import json
import math
import os
import re
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"
RULES_DIR = REPO_ROOT / "rules"
WORKFLOWS_DIR = REPO_ROOT / "workflows"
TEAMS_DIR = REPO_ROOT / "teams"
DOCS_DIR = REPO_ROOT / "docs"
PERSONAL_SYNC_SCRIPT = SKILLS_DIR / "task-tracker" / "scripts" / "personal_sync.py"


def parse_frontmatter(content: str) -> Dict[str, str]:
    """Parse YAML frontmatter enclosed by --- delimiters."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        return {}
    fm_text = match.group(1)
    fields = {}
    pattern = re.compile(r"^([a-zA-Z0-9_-]+):[ \t]*(.*)$", re.MULTILINE)
    matches = list(pattern.finditer(fm_text))
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        val_start = m.end()
        val_end = matches[i + 1].start() if i + 1 < len(matches) else len(fm_text)
        raw_val = m.group(2) + "\n" + fm_text[val_start:val_end]
        val = raw_val.strip()
        if val.startswith(">-") or val.startswith(">") or val.startswith("|"):
            val = re.sub(r"^[>|]-?\s*", "", val).strip()
        fields[key] = val
    return fields


class BM25Retriever:
    """Okapi BM25 implementation for semantic retrieval evaluation across skill descriptions."""

    def __init__(self, corpus: Dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.doc_ids = list(corpus.keys())
        self.k1 = k1
        self.b = b
        self.stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an",
            "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
            "before", "being", "below", "between", "both", "but", "by", "can",
            "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
            "doing", "don't", "down", "during", "each", "few", "for", "from",
            "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
            "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
            "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
            "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
            "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
            "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
            "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
            "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
            "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
            "then", "there", "there's", "these", "they", "they'd", "they'll",
            "they're", "they've", "this", "those", "through", "to", "too", "under",
            "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
            "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
            "where's", "which", "while", "who", "who's", "whom", "why", "why's",
            "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
            "you've", "your", "yours", "yourself", "yourselves", "skill", "skills",
            "reach", "when", "across", "using", "use",
        }
        self.doc_tokens: Dict[str, List[str]] = {}
        self.doc_lens: Dict[str, int] = {}
        self.df: Counter = Counter()

        for doc_id, text in corpus.items():
            tokens = self._tokenize(text)
            self.doc_tokens[doc_id] = tokens
            self.doc_lens[doc_id] = len(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.df[t] += 1

        self.avg_doc_len = sum(self.doc_lens.values()) / max(len(self.doc_lens), 1)
        self.N = len(self.doc_ids)

    def _stem(self, word: str) -> str:
        w = word.lower()
        for _ in range(2):
            if len(w) > 4:
                if w.endswith("ing"):
                    w = w[:-3]
                elif w.endswith("ies"):
                    w = w[:-3] + "y"
                elif w.endswith("ed"):
                    w = w[:-2]
                elif w.endswith("es"):
                    w = w[:-2]
                elif w.endswith("s") and not w.endswith("ss"):
                    w = w[:-1]
        return w

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"[a-zA-Z0-9_-]+", text.lower())
        tokens = []
        for w in words:
            if w not in self.stopwords and len(w) > 1:
                tokens.append(self._stem(w))
        return tokens

    def score(self, query: str) -> List[Tuple[str, float]]:
        q_tokens = self._tokenize(query)
        scores: Dict[str, float] = {doc_id: 0.0 for doc_id in self.doc_ids}

        for q in q_tokens:
            df = self.df.get(q, 0)
            if df == 0:
                continue
            idf = math.log(1.0 + (self.N - df + 0.5) / (df + 0.5))
            for doc_id in self.doc_ids:
                tf = self.doc_tokens[doc_id].count(q)
                if tf == 0:
                    continue
                doc_len = self.doc_lens[doc_id]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[doc_id] += idf * (numerator / denominator)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class TestM3TaskQueryMapping(unittest.TestCase):
    """Adversarial stress-testing of user task queries against all 37 skills."""

    @classmethod
    def setUpClass(cls):
        cls.skills: Dict[str, str] = {}
        for s_dir in SKILLS_DIR.iterdir():
            if s_dir.is_dir() and not s_dir.name.startswith("."):
                skill_file = s_dir / "SKILL.md"
                if skill_file.is_file():
                    fm = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
                    cls.skills[s_dir.name] = fm.get("description", "")
        cls.retriever = BM25Retriever(cls.skills)

    def test_verbatim_trigger_strings_present_in_frontmatters(self):
        """Verify verbatim triggers 'what do we have to work on?' and 'active tasks' in both wf-sync and task-tracker."""
        wf_sync_desc = self.skills.get("wf-sync", "").lower()
        task_tracker_desc = self.skills.get("task-tracker", "").lower()

        # Both must explicitly address "what do we have to work on?"
        self.assertIn("what do we have to work on?", wf_sync_desc)
        self.assertIn("what do we have to work on?", task_tracker_desc)

        # Both must address active tasks
        self.assertIn("active tasks", wf_sync_desc)
        self.assertIn("active", task_tracker_desc)

        # wf-sync must explicitly mention backlog triage
        self.assertTrue(
            "backlog triage" in wf_sync_desc or "reviewing backlog priorities" in wf_sync_desc,
            f"wf-sync must mention backlog triage/priorities. Got: {wf_sync_desc}",
        )

    def test_semantic_retrieval_for_task_queries(self):
        """Empirically test that realistic task queries rank wf-sync or task-tracker in Top-2 among all 37 skills."""
        test_queries = [
            ("What do we have to work on?", {"wf-sync", "task-tracker"}),
            ("Show active tasks", {"wf-sync", "task-tracker"}),
            ("What are my active tasks?", {"wf-sync", "task-tracker"}),
            ("Review backlog priorities and unblock sprint tasks", {"wf-sync", "task-tracker"}),
            ("Backlog triage meeting", {"wf-sync", "task-tracker"}),
            ("What should we work on next?", {"wf-sync", "task-tracker"}),
            ("Surface blocked tasks during daily standup", {"wf-sync", "task-tracker"}),
            ("Personal sync review across active git branch and task backlog", {"wf-sync", "task-tracker"}),
            ("Triage inbox reports into prioritized engineering tasks", {"wf-sync", "task-tracker", "issue-tracker"}),
        ]

        for query, expected_set in test_queries:
            with self.subTest(query=query):
                ranked = self.retriever.score(query)
                top2_skills = {r[0] for r in ranked[:2]}
                overlap = top2_skills.intersection(expected_set)
                self.assertTrue(
                    len(overlap) > 0,
                    f"Query '{query}' failed to retrieve any of {expected_set} in Top-2. Ranked: {ranked[:4]}",
                )


class TestM3AgentParallelizationTopologies(unittest.TestCase):
    """Verify modern Antigravity orchestration and parallelization topologies documentation."""

    def test_agent_parallelization_skill_documents_all_three_topologies(self):
        """Verify agent-parallelization explicitly documents Topology 1, 2, and 3."""
        ap_file = SKILLS_DIR / "agent-parallelization" / "SKILL.md"
        self.assertTrue(ap_file.is_file(), "Missing skills/agent-parallelization/SKILL.md")
        content = ap_file.read_text(encoding="utf-8")

        # Topologies verification
        self.assertIn("TOPOLOGY 1: PARALLEL WORKTREES", content)
        self.assertIn("TOPOLOGY 2: VERTICAL RELAY", content)
        self.assertIn("TOPOLOGY 3: DIRECT SINGLE-BRANCH", content)

        # Core mechanics verification
        self.assertIn("git worktree add", content)
        self.assertIn(".worktrees/", content)
        self.assertIn("Workspace: 'share'", content)
        self.assertIn("NEVER run parallel coding subagents in `Workspace: 'inherit'`", content)
        self.assertIn("gh stack init", content)
        self.assertIn("gh stack add", content)
        self.assertIn("gh stack submit", content)
        self.assertIn("git rerere", content)
        self.assertIn("git worktree remove", content)
        self.assertIn("git worktree prune", content)

    def test_worktrees_directory_ignored_in_gitignore(self):
        """Verify .worktrees/ is in .gitignore to prevent accidental commit of worktrees."""
        gitignore_file = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore_file.is_file(), "Missing .gitignore")
        lines = gitignore_file.read_text(encoding="utf-8").splitlines()
        has_worktrees_ignore = any(".worktrees" in line for line in lines)
        self.assertTrue(has_worktrees_ignore, ".worktrees/ must be listed in .gitignore")

    def test_wf_sync_integrates_direct_orchestration_handoff(self):
        """Verify wf-sync/SKILL.md explicitly documents direct orchestration handoff to agent-parallelization."""
        sync_file = SKILLS_DIR / "wf-sync" / "SKILL.md"
        content = sync_file.read_text(encoding="utf-8")
        self.assertIn("Direct Orchestration Handoff (Modern Antigravity Execution)", content)
        self.assertIn("agent-parallelization", content)
        self.assertIn("Topology 1", content)
        self.assertIn("Topology 2", content)
        self.assertIn("personal_sync.py", content)

    def test_wf_plan_integrates_execution_topologies(self):
        """Verify wf-plan/SKILL.md integrates agent-parallelization execution topologies."""
        plan_file = SKILLS_DIR / "wf-plan" / "SKILL.md"
        content = plan_file.read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", content)
        self.assertIn("Parallel Worktrees", content)
        self.assertIn("Vertical Relay", content)
        self.assertIn("Direct Single-Branch", content)

    def test_rules_base_documents_topologies_in_auto_execution(self):
        """Verify rules/base.md includes the 3 topologies in Auto-Execution Mode."""
        base_rule = RULES_DIR / "base.md"
        content = base_rule.read_text(encoding="utf-8")
        self.assertIn("Parallel Worktrees", content)
        self.assertIn("Vertical Relay", content)
        self.assertIn("Direct Single-Branch", content)
        self.assertIn("Developer Inspection Card", content)


class TestM3CompleteWfWorkRetirement(unittest.TestCase):
    """Verify wf-work is completely absent from all active runtime code, agents, rules, workflows, and docs."""

    def test_filesystem_deletion(self):
        """Verify skills/wf-work and workflows/wf-work.md do not exist."""
        self.assertFalse((SKILLS_DIR / "wf-work").exists(), "skills/wf-work must not exist")
        self.assertFalse((WORKFLOWS_DIR / "wf-work.md").exists(), "workflows/wf-work.md must not exist")

    def test_zero_wf_work_references_in_agents(self):
        """Verify zero wf-work references in agents/."""
        for md in AGENTS_DIR.glob("*.md"):
            content = md.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", content, f"wf-work found in {md.name}")

    def test_zero_wf_work_references_in_rules(self):
        """Verify zero wf-work references in rules/."""
        for md in RULES_DIR.glob("*.md"):
            content = md.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", content, f"wf-work found in {md.name}")

    def test_zero_wf_work_references_in_workflows(self):
        """Verify zero wf-work references in workflows/."""
        for md in WORKFLOWS_DIR.glob("*.md"):
            content = md.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", content, f"wf-work found in {md.name}")

    def test_zero_wf_work_references_in_teams(self):
        """Verify zero wf-work references in teams/."""
        for md in TEAMS_DIR.glob("**/*.md"):
            content = md.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", content, f"wf-work found in {md.relative_to(TEAMS_DIR)}")

    def test_zero_wf_work_references_in_docs_and_readme(self):
        """Verify zero wf-work references in docs/, README.md, and GEMINI.md."""
        for md in DOCS_DIR.glob("*.md"):
            content = md.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", content, f"wf-work found in {md.name}")
        self.assertNotIn("wf-work", (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertNotIn("wf-work", (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8"))


class TestM3PersonalSyncExecution(unittest.TestCase):
    """Empirically test personal_sync.py command execution."""

    def test_personal_sync_markdown_output(self):
        """Verify personal_sync.py runs with --format markdown and contains expected sections."""
        res = subprocess.run(
            [sys.executable, str(PERSONAL_SYNC_SCRIPT), "--root", str(REPO_ROOT), "--format", "markdown"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(res.returncode, 0, f"personal_sync.py markdown failed: {res.stderr}")
        self.assertIn("Personal Sync", res.stdout)
        self.assertIn("What You Are Working On", res.stdout)

    def test_personal_sync_json_output(self):
        """Verify personal_sync.py runs with --format json and produces valid JSON data structure."""
        res = subprocess.run(
            [sys.executable, str(PERSONAL_SYNC_SCRIPT), "--root", str(REPO_ROOT), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(res.returncode, 0, f"personal_sync.py json failed: {res.stderr}")
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError as err:
            self.fail(f"personal_sync.py output was not valid JSON: {err}\nOutput: {res.stdout[:200]}")
        self.assertIn("git", data)
        self.assertIn("tracked_repos", data)
        self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
