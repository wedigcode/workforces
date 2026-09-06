#!/usr/bin/env python3
"""
Adversarial Test Suite: Empirical Semantic Discovery & Strict YAML Validation
Tests all 38 skills under skills/ for:
1. Strict YAML validity and scalar safety across all files.
2. Absence of tautological slash-command listings.
3. Presence of rich situational context, symptoms, and architectural dilemmas.
4. BM25 Information Retrieval accuracy across 37 realistic user problem statements.
5. High-precision disambiguation between closely related skills.
"""

import math
import re
import subprocess
import unittest
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


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
    """Okapi BM25 implementation for zero-dependency semantic retrieval evaluation."""

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
                elif w.endswith("ers") or w.endswith("er"):
                    w = re.sub(r"er?s?$", "", w)
                elif w.endswith("s") and not w.endswith("ss"):
                    w = w[:-1]
        return w

    def _tokenize(self, text: str) -> List[str]:
        # Split on non-alphanumeric to separate hyphenated compounds (ast-based -> ast, based)
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        tokens = []
        for w in words:
            if len(w) > 1 and w not in self.stopwords:
                stemmed = self._stem(w)
                if stemmed not in self.stopwords:
                    tokens.append(stemmed)
        return tokens

    def score(self, query: str) -> List[Tuple[str, float]]:
        query_tokens = self._tokenize(query)
        scores: Dict[str, float] = {doc_id: 0.0 for doc_id in self.doc_ids}

        for token in query_tokens:
            if token not in self.df:
                continue
            df_val = self.df[token]
            idf = math.log((self.N - df_val + 0.5) / (df_val + 0.5) + 1.0)

            for doc_id, tokens in self.doc_tokens.items():
                tf = tokens.count(token)
                if tf == 0:
                    continue
                doc_len = self.doc_lens[doc_id]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[doc_id] += idf * (numerator / denominator)

        # Sort descending by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked


class TestEmpiricalSemanticDiscovery(unittest.TestCase):
    """Adversarial validation of YAML validity and semantic discovery across all skills."""

    @classmethod
    def setUpClass(cls):
        cls.skills: Dict[str, str] = {}
        cls.raw_frontmatters: Dict[str, str] = {}
        for p in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            text = p.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            name = fm.get("name", p.parent.name)
            desc = fm.get("description", "")
            cls.skills[name] = desc
            match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
            cls.raw_frontmatters[name] = match.group(1) if match else ""

        cls.retriever = BM25Retriever(cls.skills)

    def test_all_37_skills_present(self):
        """Assert exactly 37 skills are indexed."""
        self.assertEqual(len(self.skills), 37, f"Expected 37 skills, found {len(self.skills)}")

    def test_strict_yaml_validity_via_ruby_psych(self):
        """Empirically test every SKILL.md with Ruby's libyaml engine (Psych) in strict mode."""
        ruby_script = """
        require "yaml"
        failed = []
        Dir.glob("skills/*/SKILL.md").sort.each do |f|
          content = File.read(f)
          if content =~ /\\A---\\s*\\n(.*?)\\n---\\s*(?:\\n|\\z)/m
            begin
              parsed = YAML.safe_load($1, permitted_classes: [], aliases: false)
              raise "Not a hash" unless parsed.is_a?(Hash)
              raise "Missing name" unless parsed["name"] && !parsed["name"].to_s.strip.empty?
              raise "Missing description" unless parsed["description"] && !parsed["description"].to_s.strip.empty?
            rescue => e
              failed << "#{f}: #{e.message.lines.first.strip}"
            end
          else
            failed << "#{f}: missing frontmatter delimiters"
          end
        end
        if failed.empty?
          puts "SUCCESS"
        else
          puts "FAILED:\\n" + failed.join("\\n")
          exit 1
        end
        """
        proc = subprocess.run(["ruby", "-e", ruby_script], capture_output=True, text=True)
        self.assertEqual(
            proc.returncode,
            0,
            f"Ruby Psych strict YAML parser failed on skills:\n{proc.stdout}\n{proc.stderr}",
        )
        self.assertIn("SUCCESS", proc.stdout)

    def test_remediated_skills_block_scalar_hygiene(self):
        """Verify codebase-improvement specifically uses block scalars cleanly."""
        target_skills = ["codebase-improvement"]
        for name in target_skills:
            raw_fm = self.raw_frontmatters.get(name, "")
            self.assertRegex(
                raw_fm,
                r"description:\s*>-",
                f"Skill '{name}' does not use folded block scalar indicator '>-'",
            )
            desc = self.skills.get(name, "")
            self.assertGreater(len(desc), 300, f"Skill '{name}' description too short")
            self.assertNotIn(">-", desc, f"Scalar indicator leaked into parsed description of '{name}'")

    def test_zero_tautological_slash_commands(self):
        """Assert zero descriptions contain tautological slash-command triggers like 'Triggers on /wf-'."""
        tautology_patterns = [
            re.compile(r"triggers\s+on\s+/", re.IGNORECASE),
            re.compile(r"trigger:\s*/", re.IGNORECASE),
            re.compile(r"command:\s*/", re.IGNORECASE),
            re.compile(r"slash-command\s+triggers", re.IGNORECASE),
        ]
        for name, desc in self.skills.items():
            for pat in tautology_patterns:
                m = pat.search(desc)
                self.assertIsNone(
                    m,
                    f"Skill '{name}' contains tautological slash command trigger: '{m.group(0) if m else ''}' in '{desc}'",
                )

    def test_all_descriptions_answer_symptoms_and_dilemmas(self):
        """Assert every description states the problem it solves and symptom-based triggers."""
        for name, desc in self.skills.items():
            has_trigger_cue = (
                "reach for this skill" in desc.lower()
                or "trigger it when" in desc.lower()
                or "slated for complete deletion" in desc.lower()
            )
            self.assertTrue(
                has_trigger_cue,
                f"Skill '{name}' lacks standardized trigger clause ('Reach for this skill...'): '{desc}'",
            )
            self.assertGreaterEqual(
                len(desc),
                300,
                f"Skill '{name}' description is not sufficiently rich (<300 chars): {len(desc)} chars",
            )

    def test_bm25_semantic_discovery_oracle(self):
        """
        Adversarial test: evaluate BM25 retrieval against 37 real-world problem statements.
        Every test scenario represents an actual symptom, architectural dilemma, or workflow.
        Asserts that the target skill ranks in Top-2 for every query.
        """
        test_scenarios = [
            {
                "query": "Multiple subagents are editing the repository concurrently causing git index lock collisions and branch conflicts",
                "expected": "agent-parallelization",
            },
            {
                "query": "Configure robots.txt and llms.txt protocol files so Perplexity and ChatGPT Search index and cite our docs",
                "expected": "ai-search-optimization",
            },
            {
                "query": "Define official brand voice typography scales hex color palettes and audit marketing copy for voice drift",
                "expected": "brand-guidelines",
            },
            {
                "query": "Calculate customer acquisition cost LTV to CAC payback period and analyze Value Stick willingness to pay",
                "expected": "business-frameworks",
            },
            {
                "query": "Follow Test-Driven Development red-green-refactor enforce SOLID architecture and ensure zero error swallowing",
                "expected": "clean-coder",
            },
            {
                "query": "Construct an AST call graph to map function dependencies and evaluate blast radius before refactoring",
                "expected": "code-graph",
            },
            {
                "query": "Conduct proactive codebase cleanup across the 5 pillars removing dead code unused dependencies and query bottlenecks",
                "expected": "codebase-improvement",
            },
            {
                "query": "Landing page has generic purple gradients floating glow cards and fake metrics that look like amateur AI templates",
                "expected": "design-anti-patterns",
            },
            {
                "query": "Generate API reference documentation for TypeScript and Python packages into an Open Knowledge Format catalog",
                "expected": "doc-generator",
            },
            {
                "query": "Conduct competitive gap analysis and write a Product Requirement Document with phased P0 P1 milestones",
                "expected": "feature-research",
            },
            {
                "query": "Link tasks to GitHub Issues and manage project board backlog items scored by RICE priority using gh CLI",
                "expected": "github-project-planning",
            },
            {
                "query": "Formulate a falsifiable experiment hypothesis with leading indicators lagging KPIs and explicit kill thresholds",
                "expected": "hypothesis-tracker",
            },
            {
                "query": "Generate visual assets using Antigravity AI convert reference images into JSON prompts and compress WebP",
                "expected": "image-workflow",
            },
            {
                "query": "Audit documentation for broken markdown relative links dangling file paths and ghost references to missing files",
                "expected": "integrity-validator",
            },
            {
                "query": "Log an emergent bug and technical debt discovered during active coding to backlog inbox without interrupting flow",
                "expected": "issue-tracker",
            },
            {
                "query": "Sync with Google Jules asynchronous coding agent audit remote changes and review proposed PR diffs",
                "expected": "jules-integration",
            },
            {
                "query": "Pre-revenue product launch optimizing Time to First Dollar with 7-day Stripe pre-sale offers and concierge MVP",
                "expected": "launch-playbook",
            },
            {
                "query": "Validate customer willingness to pay before coding using smoke tests fake door pretotyping and Mom Test interviews",
                "expected": "market-validation",
            },
            {
                "query": "Maintain persistent skill memory state timestamps and navigate modular markdown knowledge catalog",
                "expected": "memory-management",
            },
            {
                "query": "Switch between Author Voice persona and Target Audience customer profile to adapt email tone of voice",
                "expected": "persona-management",
            },
            {
                "query": "Analyze git diff after editing code to detect broken function contract signatures duplicate utilities and missing tests",
                "expected": "post-code-review",
            },
            {
                "query": "Review open GitHub pull request inspect diff for security vulnerabilities and post line comments with gh CLI",
                "expected": "pr-review",
            },
            {
                "query": "Save conversation milestones architectural rationale and decisions before context truncation so we can resume later",
                "expected": "session-context",
            },
            {
                "query": "Bootstrap greenfield web application repository create Product Brief set up tech stack and CI/CD pipeline",
                "expected": "site-setup",
            },
            {
                "query": "Engage organically in technical Twitter and LinkedIn discussions with brand persona commentary without sounding like a bot",
                "expected": "social-engagement",
            },
            {
                "query": "Update task lifecycle status in workforces/tasks/ answer what do we have to work on and manage priority P0 queues",
                "expected": "task-tracker",
            },
            {
                "query": "Design responsive interaction wireframes map user onboarding journey and fix WCAG accessibility contrast drop-off",
                "expected": "ui-ux-design",
            },
            {
                "query": "Monitor token consumption audit LLM prompt bloat and log thinking step tool overhead across agent sessions",
                "expected": "usage-tracker",
            },
            {
                "query": "Apply 8pt grid system harmonic typography scale and visual hierarchy rules before styling UI components",
                "expected": "visual-design-fundamentals",
            },
            {
                "query": "Unpack root business bottlenecks evaluate build-vs-buy decisions and validate Jobs-to-be-Done before building",
                "expected": "wf-advisor",
            },
            {
                "query": "Unbundle bloated SaaS incumbents identify under-served niche markets and evaluate product ideas with viability scorecards",
                "expected": "wf-ideate",
            },
            {
                "query": "Triage production cloud outage App Runner 504 timeouts elevated error rates and extract telemetry logs without modifying infra",
                "expected": "wf-investigate",
            },
            {
                "query": "Transform PRD goals into phased engineering plan with concurrency topologies and worktree task breakdown",
                "expected": "wf-plan",
            },
            {
                "query": "Structure critical architectural dilemma into XML question schema to interview user rather than guessing preferences",
                "expected": "wf-question-formulation",
            },
            {
                "query": "Run daily morning standup review recent commits surface blocked tasks and align weekly strategic OKR roadmap",
                "expected": "wf-sync",
            },
            {
                "query": "Render browser interactive visual command canvas showing task status dependencies and AST call graphs",
                "expected": "workforce-canvas",
            },
            {
                "query": "Install dev or marketing team packs update core toolkit scripts and prune unused configurations safely",
                "expected": "workforce-management",
            },
        ]

        top1_count = 0
        top2_count = 0
        failures = []

        for scenario in test_scenarios:
            query = scenario["query"]
            expected = scenario["expected"]
            ranked = self.retriever.score(query)
            top_candidates = [r[0] for r in ranked[:3]]
            top_scores = [round(r[1], 3) for r in ranked[:3]]

            if expected == top_candidates[0]:
                top1_count += 1
                top2_count += 1
            elif len(top_candidates) > 1 and expected == top_candidates[1]:
                top2_count += 1
            else:
                failures.append(
                    f"Query: '{query}'\n  Expected: '{expected}', Got: {top_candidates} (scores: {top_scores})"
                )

        total = len(test_scenarios)
        pass_rate_top1 = (top1_count / total) * 100
        pass_rate_top2 = (top2_count / total) * 100

        print(
            f"\\n[BM25 Semantic Discovery Benchmark] Total: {total} | Top-1: {top1_count}/{total} ({pass_rate_top1:.1f}%) | Top-2: {top2_count}/{total} ({pass_rate_top2:.1f}%)"
        )

        self.assertFalse(
            failures,
            f"{len(failures)} queries failed to retrieve expected skill in Top-2:\\n" + "\\n".join(failures),
        )
        self.assertGreaterEqual(
            pass_rate_top1,
            90.0,
            f"Top-1 accuracy {pass_rate_top1:.1f}% below 90% threshold",
        )

    def test_pairwise_dilemma_disambiguation(self):
        """
        Adversarial test: test subtle distinctions between high-risk overlapping skill pairs.
        Each query must strictly favor the specialized skill over its conceptual neighbor.
        """
        disambiguation_pairs = [
            (
                "Find duplicate utility functions and broken signatures in git diff right after editing code",
                "post-code-review",
                "pr-review",
            ),
            (
                "Submit GitHub PR review comments and approve pull request diffs via gh CLI",
                "pr-review",
                "post-code-review",
            ),
            (
                "Find all callers and reference paths of function auth_token in the AST before modifying it",
                "code-graph",
                "clean-coder",
            ),
            (
                "Refactor class to adhere to Single Responsibility Principle and write failing test first",
                "clean-coder",
                "code-graph",
            ),
            (
                "Log deferred bug discovered while coding to inbox without interrupting current task",
                "issue-tracker",
                "task-tracker",
            ),
            (
                "Surface active and blocked tasks during daily standup and update task priority to P0",
                "task-tracker",
                "issue-tracker",
            ),
            (
                "Audit markdown links and check for dangling file references and missing image files",
                "integrity-validator",
                "codebase-improvement",
            ),
            (
                "Sweep codebase for dead functions unused packages and SQL query performance bottlenecks",
                "codebase-improvement",
                "integrity-validator",
            ),
            (
                "Eliminate purple glow cards and generic gradient buttons from dashboard styling",
                "design-anti-patterns",
                "visual-design-fundamentals",
            ),
            (
                "Establish 8pt grid baseline typography scale and WCAG color contrast tokens",
                "visual-design-fundamentals",
                "design-anti-patterns",
            ),
        ]

        for query, target, foil in disambiguation_pairs:
            with self.subTest(target=target, foil=foil):
                ranked = dict(self.retriever.score(query))
                target_score = ranked.get(target, 0.0)
                foil_score = ranked.get(foil, 0.0)
                self.assertGreater(
                    target_score,
                    foil_score,
                    f"Disambiguation failure for query '{query}': {target} ({target_score:.3f}) was not higher than {foil} ({foil_score:.3f})",
                )


if __name__ == "__main__":
    unittest.main()
