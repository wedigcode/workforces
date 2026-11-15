#!/usr/bin/env python3
"""
Verifies that Antigravity tool names and invocation options in skill, rule, agent and
team bodies are translated to Claude Code equivalents when compiling the .claude copy,
while the Antigravity (.agents) copy stays byte-for-byte untranslated.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "wf-management" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import compile_assets as ca  # noqa: E402

ANTIGRAVITY_TERMS = re.compile(
    r"\b(view_file|grep_search|list_dir|find_by_name|run_command|write_to_file|"
    r"replace_file_content|multi_replace_file_content|read_url_content)\b|`Workspace: '"
)


class TestClaudeToolNameTranslation(unittest.TestCase):
    def setUp(self):
        self.profiles = ca.load_host_profiles(str(REPO_ROOT))

    def test_translates_tool_names_and_worktree_option(self):
        body = (
            "Use `view_file`, `grep_search`, `list_dir` and `run_command` with `IsDaemon=True`. "
            "Edit via `write_to_file`, `replace_file_content`, `multi_replace_file_content`. "
            "Spawn subagents with `Workspace: 'share'`, never `Workspace: 'inherit'`. "
            "Leave os.listdir, my_view_file_helper and generate_image alone."
        )
        out = ca.translate_tool_names_for_host(body, self.profiles["claude"])
        for expected in ("`Read`", "`Grep`", "`Glob`", "`Bash`", "`Write`", "`Edit`", "`MultiEdit`",
                         "`run_in_background: true`", "`isolation: \"worktree\"`", "Agent tool without `isolation`"):
            self.assertIn(expected, out)
        self.assertIsNone(ANTIGRAVITY_TERMS.search(out))
        self.assertIn("my_view_file_helper", out)
        self.assertIn("generate_image", out)

    def test_antigravity_profile_is_untouched(self):
        body = "Use `run_command` and `Workspace: 'share'`."
        self.assertEqual(ca.translate_tool_names_for_host(body, self.profiles["antigravity"]), body)

    def test_full_claude_install_has_no_antigravity_tool_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = {
                "agents": sorted(p.stem for p in (REPO_ROOT / "agents").glob("*.md")),
                "rules": sorted(p.stem for p in (REPO_ROOT / "rules").glob("*.md")),
                "skills": sorted(p.name for p in (REPO_ROOT / "skills").iterdir() if p.is_dir()),
                "teams": sorted(p.name for p in (REPO_ROOT / "teams").iterdir() if p.is_dir()),
                "workflows": [],
                "plugins": [],
            }
            ca.install_compiled_hosts(str(REPO_ROOT), tmp, ["claude"], manifest)
            offenders = []
            for md in Path(tmp, ".claude").rglob("*.md"):
                text = ca.strip_markdown_frontmatter(md.read_text(encoding="utf-8"))
                if ANTIGRAVITY_TERMS.search(text):
                    offenders.append(str(md.relative_to(tmp)))
            self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
