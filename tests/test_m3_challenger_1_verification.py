#!/usr/bin/env python3
"""
Adversarial Verification Suite: Milestone 3 Challenger 1
Empirically stress-tests the retirement of wf-work and task query consolidation:
1. Validates that skills/wf-work/ and workflows/wf-work.md are completely deleted.
2. Asserts exactly 37 skills exist in skills/, all with valid SKILL.md and YAML frontmatter.
3. Performs exhaustive grep across all active skill, agent, rule, workflow, and doc files for wf-work.
4. Stress-tests BM25 semantic query routing for task triage and standup queries to wf-sync/task-tracker.
5. Verifies integration of Antigravity modern orchestration (agent-parallelization) in place of wf-work loops.
"""

import math
import os
import re
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"
RULES_DIR = REPO_ROOT / "rules"
WORKFLOWS_DIR = REPO_ROOT / "workflows"
DOCS_DIR = REPO_ROOT / "docs"
TEAMS_DIR = REPO_ROOT / "teams"


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
    """Okapi BM25 implementation for semantic retrieval evaluation."""

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
            "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've",
            "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
            "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of",
            "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
            "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd",
            "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
            "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
            "there", "there's", "these", "they", "they'd", "they'll", "they're",
            "they've", "this", "those", "through", "to", "too", "under", "until", "up",
            "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
            "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
            "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
            "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
            "yourself", "yourselves",
        }
        self.doc_tokens = {
            doc_id: self._tokenize(text) for doc_id, text in corpus.items()
        }
        self.doc_lens = {doc_id: len(toks) for doc_id, toks in self.doc_tokens.items()}
        self.avg_doc_len = sum(self.doc_lens.values()) / max(len(self.doc_lens), 1)
        self.df = Counter()
        for toks in self.doc_tokens.values():
            for t in set(toks):
                self.df[t] += 1
        self.N = len(self.doc_ids)
        self.idf = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log((self.N - freq + 0.5) / (freq + 0.5) + 1.0)

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"[A-Za-z0-9_-]+", text.lower())
        tokens = []
        for w in words:
            if w in self.stopwords:
                continue
            tokens.append(w)
            parts = [p for p in re.split(r"[-_]", w) if p and p not in self.stopwords]
            if len(parts) > 1:
                tokens.extend(parts)
        return tokens

    def query(self, query_str: str) -> List[Tuple[str, float]]:
        q_tokens = self._tokenize(query_str)
        scores = {}
        for doc_id, toks in self.doc_tokens.items():
            doc_len = self.doc_lens[doc_id]
            tf = Counter(toks)
            score = 0.0
            for qt in q_tokens:
                if qt not in tf:
                    continue
                term_tf = tf[qt]
                term_idf = self.idf.get(qt, 0.0)
                num = term_tf * (self.k1 + 1.0)
                denom = term_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += term_idf * (num / denom)
            scores[doc_id] = score
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class TestMilestone3EmpiricalChallenger(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill_dirs = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
        cls.skills_corpus = {}
        for s_dir in cls.skill_dirs:
            content = (s_dir / "SKILL.md").read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            desc = fm.get("description", "")
            cls.skills_corpus[s_dir.name] = desc
        cls.retriever = BM25Retriever(cls.skills_corpus)

    def test_wf_work_skill_and_workflow_complete_absence(self):
        """Verify skills/wf-work/ and workflows/wf-work.md are completely deleted."""
        self.assertFalse((SKILLS_DIR / "wf-work").exists(), "skills/wf-work must not exist")
        self.assertFalse((WORKFLOWS_DIR / "wf-work.md").exists(), "workflows/wf-work.md must not exist")

    def test_exactly_37_skills_in_skills_dir(self):
        """Verify exactly 37 skills exist in skills/ directory."""
        self.assertEqual(
            len(self.skill_dirs),
            37,
            f"Expected exactly 37 skills in skills/, but found {len(self.skill_dirs)}: {[d.name for d in self.skill_dirs]}"
        )
        self.assertNotIn("wf-work", [d.name for d in self.skill_dirs])

    def test_exhaustive_grep_no_active_wf_work_in_skills(self):
        """Verify no skill files (excluding workforce-management scripts and usage-tracker) contain /wf-work."""
        for s_dir in self.skill_dirs:
            if s_dir.name in ("workforce-management", "usage-tracker"):
                continue
            for file_path in s_dir.glob("**/*"):
                if not file_path.is_file():
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                # Search for active slash-command invocation /wf-work
                self.assertNotIn(
                    "/wf-work",
                    text,
                    f"Found active '/wf-work' invocation in skill file: {file_path.relative_to(REPO_ROOT)}"
                )

    def test_exhaustive_grep_no_wf_work_in_agents(self):
        """Verify no files in agents/ reference wf-work or /wf-work."""
        for agent_file in AGENTS_DIR.glob("*.md"):
            text = agent_file.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", text, f"Found 'wf-work' in agent: {agent_file.relative_to(REPO_ROOT)}")

    def test_exhaustive_grep_no_wf_work_in_rules(self):
        """Verify no files in rules/ reference wf-work or /wf-work."""
        for rule_file in RULES_DIR.glob("*.md"):
            text = rule_file.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", text, f"Found 'wf-work' in rule: {rule_file.relative_to(REPO_ROOT)}")

    def test_exhaustive_grep_no_wf_work_in_workflows(self):
        """Verify no files in workflows/ reference wf-work or /wf-work."""
        for wf_file in WORKFLOWS_DIR.glob("*.md"):
            text = wf_file.read_text(encoding="utf-8")
            self.assertNotIn("wf-work", text, f"Found 'wf-work' in workflow: {wf_file.relative_to(REPO_ROOT)}")

    def test_exhaustive_grep_no_wf_work_in_teams(self):
        """Verify no pack.json or pack.md in teams/ reference wf-work or /wf-work."""
        for team_file in TEAMS_DIR.glob("**/*"):
            if team_file.suffix in (".json", ".md"):
                text = team_file.read_text(encoding="utf-8")
                self.assertNotIn("wf-work", text, f"Found 'wf-work' in team file: {team_file.relative_to(REPO_ROOT)}")

    def test_exhaustive_grep_no_wf_work_in_docs_and_readme(self):
        """Verify README.md and docs/ do not reference wf-work as active tool."""
        readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/wf-work", readme_text, "Found '/wf-work' in README.md")
        for doc_file in DOCS_DIR.glob("*.md"):
            text = doc_file.read_text(encoding="utf-8")
            self.assertNotIn("/wf-work", text, f"Found '/wf-work' in doc: {doc_file.relative_to(REPO_ROOT)}")

    def test_semantic_task_queries_map_to_sync_and_tracker(self):
        """Adversarially stress-test BM25 retrieval for task triage and standup queries."""
        test_queries = [
            ("What do we have to work on?", ["wf-sync", "task-tracker"]),
            ("Show active tasks", ["wf-sync", "task-tracker", "issue-tracker"]),
            ("What are my active tasks today?", ["wf-sync", "task-tracker"]),
            ("Daily standup sync and task unblocking", ["wf-sync", "task-tracker"]),
            ("Review backlog priorities and triage tasks", ["wf-sync", "task-tracker", "github-project-planning"]),
            ("Check sprint backlog and current task status", ["wf-sync", "task-tracker", "github-project-planning"]),
        ]

        for query_str, expected_matches in test_queries:
            results = self.retriever.query(query_str)
            top_3 = [doc_id for doc_id, score in results[:3]]
            matched = any(exp in top_3 for exp in expected_matches)
            self.assertTrue(
                matched,
                f"Query '{query_str}' did not match any of {expected_matches} in Top-3: {top_3}"
            )

    def test_antigravity_orchestration_connected_in_wf_sync_and_plan(self):
        """Verify modern Antigravity orchestration and agent-parallelization are documented."""
        sync_text = (SKILLS_DIR / "wf-sync" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Direct Orchestration Handoff", sync_text)
        self.assertIn("agent-parallelization", sync_text)

        plan_text = (SKILLS_DIR / "wf-plan" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", plan_text)
        self.assertNotIn("/wf-work", plan_text)

        base_rules = (RULES_DIR / "base.md").read_text(encoding="utf-8")
        self.assertIn("agent-parallelization", base_rules)
        self.assertNotIn("/wf-work", base_rules)


if __name__ == "__main__":
    unittest.main()
