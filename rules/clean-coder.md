# Clean Coder Engineering Protocol

- **Programming Task Detection**: Whenever a task involves writing, modifying, refactoring, or testing code (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the agent MUST load and follow the [`clean-coder`](.agents/skills/clean-coder/SKILL.md) skill.
- **Skill Authority**: All software craftsmanship and engineering standards—including AI TDD, method stubs first, symbol deduplication via `code-graph`, function line limits (<= 35 lines), method decomposition, PR review verification form, and the pre-handoff quality gate triad—are governed by the `clean-coder` skill.
- **Worktree Isolation for Parallel Agents**: Follow [`git-workflow`](git-workflow.md) and [`agent-parallelization`](.agents/skills/agent-parallelization/SKILL.md) for isolated worktrees (`Workspace: 'share'`) when multiple agents write code concurrently.
- **Mandatory Pre-Handoff Quality Gate**: Before declaring any coding task complete or handing code over to the user, the agent MUST run the quality gate:
  ```bash
  python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
  ```
  *(Fallback: `python3 skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*
