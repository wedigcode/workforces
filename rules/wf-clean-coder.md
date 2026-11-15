# Clean Coder Engineering Protocol

- **Programming Task Detection**: Whenever a task involves writing, modifying, refactoring, or testing code (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the agent MUST load and follow the [`wf-clean-coder`](../skills/wf-clean-coder/SKILL.md) skill.
- **Skill Authority**: Coding standards live in the `wf-clean-coder` skill: test what you change, search before you write, simplest design that works, rule of three for duplication, shallow control flow, and a soft ~50–60 line function limit (never split just for line count).
- **Worktree Isolation for Parallel Agents**: Follow [`wf-git-workflow`](wf-git-workflow.md) and [`wf-agent-parallelization`](../skills/wf-agent-parallelization/SKILL.md) for isolated worktrees (`Workspace: 'share'`) when multiple agents write code concurrently.
- **Pre-Handoff Quality Gate**: Before declaring any coding task complete, run the gate once; it covers the checklist audit plus tests, typechecks and linters:
  ```bash
  python3 .agents/skills/wf-post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict
  ```
  *(Fallback: `python3 skills/wf-post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict`)*
  Checklist heuristics are advisory. Test, typecheck and lint failures on modified code are blocking; pre-existing failures in untouched files are not (see the skill for legacy-code and dependency-security handling).
