#!/usr/bin/env python3
"""
Test Suite: Agents Subagent Schema Validation
Validates all 13 agents in agents/*.md for compliance with the official
Antigravity subagent specification without PyYAML.
"""

import os
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"
SKILLS_DIR = REPO_ROOT / "skills"

# Standard toolset required across all workforce agents
REQUIRED_TOOLS = [
    "view_file",
    "grep_search",
    "list_dir",
    "find_by_name",
    "run_command",
    "write_to_file",
    "replace_file_content",
    "send_message",
]

# The 8 mandatory Antigravity subagent schema fields
MANDATORY_FIELDS = [
    "name",
    "description",
    "tools",
    "mainAgent",
    "subagent",
    "model",
    "skills",
    "commandExecutionPolicy",
]

EXPECTED_AGENT_COUNT = 13


def parse_agent_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse YAML frontmatter enclosed by --- delimiters without PyYAML.
    Parses strings, booleans, and list items (- item).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)
    fields: Dict[str, Any] = {}

    pattern = re.compile(r"^([a-zA-Z0-9_-]+):[ \t]*(.*)$", re.MULTILINE)
    matches = list(pattern.finditer(fm_text))
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        val_start = m.end()
        val_end = matches[i + 1].start() if i + 1 < len(matches) else len(fm_text)
        raw_val = (m.group(2) + "\n" + fm_text[val_start:val_end]).strip()

        # Check if it's a list (lines starting with -)
        if raw_val.startswith("- ") or "\n  - " in "\n" + raw_val or "\n- " in "\n" + raw_val:
            items: List[str] = []
            for line in raw_val.splitlines():
                sline = line.strip()
                if sline.startswith("-"):
                    items.append(sline.lstrip("- ").strip())
            fields[key] = items
        elif raw_val.lower() in ("true", "false"):
            fields[key] = (raw_val.lower() == "true")
        else:
            # Strip block scalar indicators if present
            if raw_val.startswith(">-") or raw_val.startswith(">") or raw_val.startswith("|"):
                raw_val = re.sub(r"^[>|]-?\s*", "", raw_val).strip()
            fields[key] = raw_val

    return fields


class TestAgentsSubagentSchema(unittest.TestCase):
    """Verifies all agent definitions comply with the Antigravity subagent specification."""

    def setUp(self):
        self.assertTrue(AGENTS_DIR.is_dir(), f"Agents directory does not exist at {AGENTS_DIR}")
        self.agent_files = sorted(AGENTS_DIR.glob("*.md"))
        self.skill_names = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}

    def test_agents_count(self):
        """Assert exactly 13 agents are defined in agents/*.md."""
        self.assertEqual(
            len(self.agent_files),
            EXPECTED_AGENT_COUNT,
            f"Expected {EXPECTED_AGENT_COUNT} agent files, found {len(self.agent_files)}: "
            f"{[f.name for f in self.agent_files]}",
        )

    def test_mandatory_fields_presence(self):
        """Assert presence of all 8 Antigravity subagent fields in every agent file."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(
                    fm,
                    f"Failed to parse frontmatter in {agent_file.name}",
                )
                for field in MANDATORY_FIELDS:
                    self.assertIn(
                        field,
                        fm,
                        f"Missing mandatory field '{field}' in {agent_file.name}",
                    )

    def test_name_matches_filename_stem(self):
        """Assert agent 'name' is non-empty and matches the filename stem."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(fm)
                name = fm.get("name")
                self.assertIsInstance(name, str)
                self.assertEqual(
                    name,
                    agent_file.stem,
                    f"Agent name '{name}' does not match file stem '{agent_file.stem}'",
                )

    def test_description_validity(self):
        """Assert agent 'description' is a non-empty string with meaningful length."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(fm)
                desc = fm.get("description")
                self.assertIsInstance(desc, str)
                self.assertGreater(
                    len(desc.strip()),
                    30,
                    f"Description in {agent_file.name} is too short (<30 chars): '{desc}'",
                )

    def test_tools_include_standard_workforce_tools(self):
        """Assert tools list includes all 8 standard tools for workforce agents."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(fm)
                tools = fm.get("tools")
                self.assertIsInstance(tools, list, f"'tools' in {agent_file.name} must be a list")
                tools_set = set(tools)
                for req_tool in REQUIRED_TOOLS:
                    self.assertIn(
                        req_tool,
                        tools_set,
                        f"Agent {agent_file.name} missing required tool '{req_tool}'",
                    )

    def test_skills_exist_under_skills_dir(self):
        """Assert all skills declared by the agent exist as directories under skills/."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(fm)
                skills = fm.get("skills")
                self.assertIsInstance(skills, list, f"'skills' in {agent_file.name} must be a list")
                self.assertTrue(len(skills) > 0, f"Agent {agent_file.name} declares empty skills")
                for skill in skills:
                    self.assertIn(
                        skill,
                        self.skill_names,
                        f"Agent {agent_file.name} references non-existent skill '{skill}'",
                    )

    def test_main_agent_policy(self):
        """Assert mainAgent is False for scribe.md and True for all other agents."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(fm)
                main_agent = fm.get("mainAgent")
                self.assertIsInstance(main_agent, bool)
                if agent_file.name == "scribe.md":
                    self.assertFalse(
                        main_agent,
                        "scribe.md must have mainAgent: false (background precision note-taker only)",
                    )
                else:
                    self.assertTrue(
                        main_agent,
                        f"{agent_file.name} must have mainAgent: true for interactive selection",
                    )

    def test_subagent_and_model_and_execution_policy(self):
        """Assert subagent is True, model is 'inherit', and commandExecutionPolicy is 'sandbox'."""
        for agent_file in self.agent_files:
            with self.subTest(agent=agent_file.name):
                content = agent_file.read_text(encoding="utf-8")
                fm = parse_agent_frontmatter(content)
                self.assertIsNotNone(fm)
                self.assertIs(
                    fm.get("subagent"),
                    True,
                    f"Agent {agent_file.name} subagent must be True",
                )
                self.assertEqual(
                    fm.get("model"),
                    "inherit",
                    f"Agent {agent_file.name} model must be 'inherit'",
                )
                self.assertEqual(
                    fm.get("commandExecutionPolicy"),
                    "sandbox",
                    f"Agent {agent_file.name} commandExecutionPolicy must be 'sandbox'",
                )

    def test_parser_edge_cases(self):
        """Verify frontmatter parser handles booleans, lists, and invalid input cleanly."""
        self.assertIsNone(parse_agent_frontmatter(""))
        self.assertIsNone(parse_agent_frontmatter("No frontmatter"))

        sample = (
            "---\n"
            "name: test-agent\n"
            "description: Test description\n"
            "tools:\n"
            "  - tool1\n"
            "  - tool2\n"
            "mainAgent: true\n"
            "subagent: false\n"
            "model: inherit\n"
            "skills:\n"
            "  - skill1\n"
            "commandExecutionPolicy: sandbox\n"
            "---\n"
            "# Prompt body"
        )
        parsed = parse_agent_frontmatter(sample)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["name"], "test-agent")
        self.assertEqual(parsed["tools"], ["tool1", "tool2"])
        self.assertIs(parsed["mainAgent"], True)
        self.assertIs(parsed["subagent"], False)
        self.assertEqual(parsed["skills"], ["skill1"])


if __name__ == "__main__":
    unittest.main()
