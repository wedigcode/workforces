#!/usr/bin/env python3
"""
Test Suite: Skills Schema & Frontmatter Validation
Validates all modular skills under skills/ for structural compliance,
SKILL.md presence, and YAML frontmatter schema without PyYAML.
"""

import os
import re
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# 6 discrete slash-command workflow skills (wf-work retired per R3)
DISCRETE_WF_SKILLS = {
    "wf-advisor",
    "wf-ideate",
    "wf-investigate",
    "wf-plan",
    "wf-question-formulation",
    "wf-sync",
}

# Total expected skills: 31 domain skills + 6 discrete wf-* skills = 37
EXPECTED_TOTAL_SKILLS = 37


def parse_yaml_frontmatter(content: str) -> Optional[Dict[str, str]]:
    """
    Parse YAML frontmatter enclosed by --- delimiters without PyYAML.
    Returns a dictionary of key-value pairs or None if no valid frontmatter.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)
    fields: Dict[str, str] = {}

    pattern = re.compile(r"^([a-zA-Z0-9_-]+):[ \t]*(.*)$", re.MULTILINE)
    matches = list(pattern.finditer(fm_text))
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        val_start = m.end()
        val_end = matches[i + 1].start() if i + 1 < len(matches) else len(fm_text)
        raw_val = m.group(2) + "\n" + fm_text[val_start:val_end]
        # Clean up whitespace and folded scalar indicators (>-, |, etc.)
        val = raw_val.strip()
        if val.startswith(">-") or val.startswith(">") or val.startswith("|"):
            val = re.sub(r"^[>|]-?\s*", "", val).strip()
        fields[key] = val

    return fields


class TestSkillsSchema(unittest.TestCase):
    """Verifies all skills comply with the Agent Skills specification."""

    def setUp(self):
        self.assertTrue(
            SKILLS_DIR.is_dir(),
            f"Skills directory does not exist at {SKILLS_DIR}",
        )
        self.skill_dirs = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])

    def test_skills_count_and_categories(self):
        """Assert exactly 37 skills exist: 31 domain skills + 6 discrete wf-* skills."""
        self.assertEqual(
            len(self.skill_dirs),
            EXPECTED_TOTAL_SKILLS,
            f"Expected {EXPECTED_TOTAL_SKILLS} skills, found {len(self.skill_dirs)}: "
            f"{[d.name for d in self.skill_dirs]}",
        )
        skill_names = {d.name for d in self.skill_dirs}

        # Check all discrete wf-* skills are present
        for wf_skill in DISCRETE_WF_SKILLS:
            self.assertIn(
                wf_skill,
                skill_names,
                f"Missing discrete workflow skill: {wf_skill}",
            )

        # Check domain skills count
        domain_skills = skill_names - DISCRETE_WF_SKILLS
        self.assertEqual(
            len(domain_skills),
            31,
            f"Expected 31 domain skills, got {len(domain_skills)}: {domain_skills}",
        )

    def test_all_skills_contain_skill_md(self):
        """Assert every skill directory contains a non-empty SKILL.md file."""
        for skill_dir in self.skill_dirs:
            with self.subTest(skill=skill_dir.name):
                skill_md = skill_dir / "SKILL.md"
                self.assertTrue(
                    skill_md.is_file(),
                    f"Missing SKILL.md in {skill_dir.name}",
                )
                self.assertGreater(
                    skill_md.stat().st_size,
                    0,
                    f"SKILL.md in {skill_dir.name} is empty",
                )

    def test_skill_frontmatter_name(self):
        """Assert 'name' is present, non-empty, lowercase hyphenated, and matches directory name."""
        name_regex = re.compile(r"^[a-z0-9-]+$")
        for skill_dir in self.skill_dirs:
            with self.subTest(skill=skill_dir.name):
                skill_md = skill_dir / "SKILL.md"
                content = skill_md.read_text(encoding="utf-8")
                fm = parse_yaml_frontmatter(content)
                self.assertIsNotNone(
                    fm,
                    f"Failed to parse frontmatter in {skill_dir.name}/SKILL.md",
                )
                self.assertIn(
                    "name",
                    fm,
                    f"Missing 'name' field in {skill_dir.name}/SKILL.md frontmatter",
                )
                name = fm["name"].strip()
                self.assertTrue(name, f"Empty 'name' in {skill_dir.name}/SKILL.md")
                self.assertEqual(
                    name,
                    skill_dir.name,
                    f"Skill name '{name}' does not match directory '{skill_dir.name}'",
                )
                self.assertRegex(
                    name,
                    name_regex,
                    f"Skill name '{name}' does not match lowercase hyphenated pattern",
                )

    def test_skill_frontmatter_description_and_triggers(self):
        """Assert 'description' is present, non-empty, and provides clear purpose & triggers."""
        for skill_dir in self.skill_dirs:
            with self.subTest(skill=skill_dir.name):
                skill_md = skill_dir / "SKILL.md"
                content = skill_md.read_text(encoding="utf-8")
                fm = parse_yaml_frontmatter(content)
                self.assertIsNotNone(
                    fm,
                    f"Failed to parse frontmatter in {skill_dir.name}/SKILL.md",
                )
                self.assertIn(
                    "description",
                    fm,
                    f"Missing 'description' in {skill_dir.name}/SKILL.md frontmatter",
                )
                description = fm["description"].strip()
                self.assertGreater(
                    len(description),
                    30,
                    f"Description in {skill_dir.name}/SKILL.md is too short (<30 chars): '{description}'",
                )

                # For discrete slash-command skills (wf-*), trigger conditions must be explicit
                if skill_dir.name in DISCRETE_WF_SKILLS:
                    has_trigger = (
                        "trigger" in description.lower()
                        or f"/{skill_dir.name}" in description
                        or skill_dir.name in description
                    )
                    self.assertTrue(
                        has_trigger,
                        f"Discrete skill {skill_dir.name} description lacks explicit trigger keywords: '{description}'",
                    )

    def test_frontmatter_parser_edge_cases(self):
        """Verify zero-dependency YAML frontmatter parser handles edge cases gracefully."""
        # Empty input
        self.assertIsNone(parse_yaml_frontmatter(""))
        self.assertIsNone(parse_yaml_frontmatter("No frontmatter at all"))
        self.assertIsNone(parse_yaml_frontmatter("---\nunterminated frontmatter"))

        # Valid minimal frontmatter
        sample = "---\nname: my-skill\ndescription: A test skill\n---\n# Body"
        parsed = parse_yaml_frontmatter(sample)
        self.assertEqual(parsed, {"name": "my-skill", "description": "A test skill"})

        # Folded scalar block indicator
        sample_folded = "---\nname: my-skill\ndescription: >-\n  A multiline\n  description\n---\n"
        parsed_folded = parse_yaml_frontmatter(sample_folded)
        self.assertEqual(parsed_folded["name"], "my-skill")
        self.assertIn("A multiline", parsed_folded["description"])


if __name__ == "__main__":
    unittest.main()
