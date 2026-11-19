#!/usr/bin/env python3
"""
Tests for portable Git link resolution, Option A deploy safety hooks,
code review IaC/production-default/OKF checks, repo `<repo>/docs/` OKF
scaffolding & spec dehydration, PM budget/pause gating, multi-harness task
claiming, cross-harness review priority, and rolling 1-bite-per-day slicing.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, rel_path: str):
    """Load a script module dynamically from its repository-relative path."""
    mod_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, str(mod_path))
    if not spec or not spec.loader:
        raise ImportError(f"Could not load {rel_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


git_link_resolver = _load_module("git_link_resolver", "skills/wf-management/scripts/git_link_resolver.py")
deploy_safety_hook = _load_module("deploy_safety_hook", "skills/wf-post-code-review/scripts/deploy_safety_hook.py")
post_code_reviewer = _load_module("post_code_reviewer", "skills/wf-post-code-review/scripts/post_code_reviewer.py")
scaffold_repo_okf = _load_module("scaffold_repo_okf", "skills/wf-doc-generator/scripts/scaffold_repo_okf.py")
budget_gate = _load_module("budget_gate", "skills/wf-usage-tracker/scripts/budget_gate.py")
report_task = _load_module("report_task", "skills/wf-task-tracker/scripts/report-task.py")
work_dispatch = _load_module("work_dispatch", "skills/wf-work/scripts/work_dispatch.py")


def _init_git_repo(repo_dir: Path, remote_url: str | None = None, branch: str = "main") -> None:
    """Create a minimal Git repo for isolated testing."""
    subprocess.run(["git", "init", "-b", branch], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=repo_dir, check=True, capture_output=True)
    if remote_url:
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=repo_dir, check=True, capture_output=True)


class TestGitLinkResolver(unittest.TestCase):
    """Verify multi-provider remote URL formatting and clean relative fallback."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_parse_all_git_hosts(self):
        cases = [
            ("git@github.com:acme/billing-api.git", "github", "github.com", "acme/billing-api"),
            ("https://gitlab.com/team/sub/service.git", "gitlab", "gitlab.com", "team/sub/service"),
            ("git@bitbucket.org:workspace/payments.git", "bitbucket", "bitbucket.org", "workspace/payments"),
            ("git@ssh.dev.azure.com:v3/org/proj/repo", "azure", "dev.azure.com", "org/proj/_git/repo"),
            ("https://codeberg.org/open/tool.git", "gitea", "codeberg.org", "open/tool"),
        ]
        for url, provider, host, owner_repo in cases:
            parsed = git_link_resolver.parse_git_remote_url(url)
            self.assertIsNotNone(parsed, url)
            self.assertEqual(parsed["provider"], provider)
            self.assertEqual(parsed["host"], host)
            self.assertEqual(parsed["owner_repo"], owner_repo)
        self.assertIsNone(git_link_resolver.parse_git_remote_url("file:///Users/dev/repo"))

    def test_build_blob_urls_and_offline_fallback(self):
        gh = {"provider": "github", "host": "github.com", "owner_repo": "acme/app", "scheme": "https"}
        gl = {"provider": "gitlab", "host": "gitlab.com", "owner_repo": "acme/app", "scheme": "https"}
        bb = {"provider": "bitbucket", "host": "bitbucket.org", "owner_repo": "acme/app", "scheme": "https"}
        az = {"provider": "azure", "host": "dev.azure.com", "owner_repo": "org/proj/_git/app", "scheme": "https"}
        gt = {"provider": "gitea", "host": "codeberg.org", "owner_repo": "acme/app", "scheme": "https"}

        self.assertEqual(
            git_link_resolver.build_blob_url(gh, "main", "src/app.py", line=10, end_line=20),
            "https://github.com/acme/app/blob/main/src/app.py#L10-L20",
        )
        self.assertEqual(
            git_link_resolver.build_blob_url(gl, "main", "src/app.py", line=10),
            "https://gitlab.com/acme/app/-/blob/main/src/app.py#L10",
        )
        self.assertEqual(
            git_link_resolver.build_blob_url(bb, "main", "src/app.py", line=5, end_line=9),
            "https://bitbucket.org/acme/app/src/main/src/app.py#lines-5:9",
        )
        self.assertEqual(
            git_link_resolver.build_blob_url(az, "main", "src/app.py", line=4),
            "https://dev.azure.com/org/proj/_git/app?path=/src/app.py&version=GBmain&line=4&lineEnd=4&lineStartColumn=1&lineEndColumn=1",
        )
        self.assertEqual(
            git_link_resolver.build_blob_url(gt, "abcdef12", "src/app.py", line=3),
            "https://codeberg.org/acme/app/src/commit/abcdef12/src/app.py#L3",
        )

        # Offline repo with no remote -> clean repo-relative POSIX path, never file://
        _init_git_repo(self.tmp, remote_url=None)
        f = self.tmp / "src" / "handler.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("pass\n", encoding="utf-8")
        resolved = git_link_resolver.resolve_portable_link(str(f), repo_root=str(self.tmp))
        self.assertEqual(resolved, "src/handler.py")
        self.assertFalse(resolved.startswith("file://"))


class TestDeploySafetyHook(unittest.TestCase):
    """Verify Option A PreToolUse safety gate across feature pushes, protected branches, and deploy CLIs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_allows_safe_commands_and_feature_pushes(self):
        _init_git_repo(self.tmp, branch="feat/order-webhook")
        (self.tmp / "a.txt").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: webhook"], cwd=self.tmp, check=True, capture_output=True)

        safe_cmds = [
            "git status",
            "git commit -m 'docs: explain sam deploy safety'",
            "grep -n 'sam deploy' scripts/*.py",
            "git push -u origin feat/order-webhook",
            "git push",
            "gh pr create --draft --title 'feat: order webhook'",
        ]
        for cmd in safe_cmds:
            self.assertIsNone(deploy_safety_hook.inspect_command(cmd, cwd=str(self.tmp)), cmd)

    def test_gates_deployments_merges_and_protected_pushes(self):
        _init_git_repo(self.tmp, branch="main")
        (self.tmp / "a.txt").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmp, check=True, capture_output=True)

        blocked_cmds = [
            "sam deploy --config-env prod",
            "npx ampx pipeline-deploy --branch main",
            "terraform apply -auto-approve",
            "kubectl apply -f k8s/",
            "gh pr merge 42 --squash",
            "gh workflow run deploy.yml",
            "git push origin feat/x --force",
            "git push origin main",
            "git push origin HEAD:production",
            "git push",
        ]
        for cmd in blocked_cmds:
            reason = deploy_safety_hook.inspect_command(cmd, cwd=str(self.tmp))
            self.assertIsNotNone(reason, f"Expected consent gate on `{cmd}`")

        agy_resp = deploy_safety_hook.format_hook_response("blocked", tool_name="run_command")
        self.assertEqual(agy_resp["decision"], "force_ask")
        claude_resp = deploy_safety_hook.format_hook_response("blocked", tool_name="Bash")
        self.assertEqual(claude_resp["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_blocks_wrapper_options_prefix_stripping_force_with_lease_and_substitutions(self):
        _init_git_repo(self.tmp, branch="feat/origin-cleanup")
        (self.tmp / "a.txt").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: origin cleanup"], cwd=self.tmp, check=True, capture_output=True)

        for cmd in (
            "git push -u origin feat/origin-cleanup",
            "git push origin refs/heads/feat/origin-cleanup",
            "echo 'do not run $(terraform apply)'",
            "git -C . status",
        ):
            self.assertIsNone(deploy_safety_hook.inspect_command(cmd, cwd=str(self.tmp)), cmd)

        for cmd in (
            "npx --yes ampx pipeline-deploy",
            "sudo -n terraform apply -auto-approve",
            "env -i FOO=bar sam deploy --config-env dev",
            "pnpm --filter web exec ampx deploy",
            "git push origin release/v1",
            "git push origin refs/remotes/origin/release/v1",
            "git push --force-with-lease=main origin feat/origin-cleanup",
            "git push -uf origin feat/origin-cleanup",
            "echo $(terraform apply)",
            'printf "%s" "`gh pr merge 42`"',
        ):
            self.assertIsNotNone(deploy_safety_hook.inspect_command(cmd, cwd=str(self.tmp)), f"Bypass not blocked: {cmd}")

    def test_hook_subprocess_fails_closed_and_supports_antigravity_toolcall(self):
        hook_script = str(REPO_ROOT / "skills" / "wf-post-code-review" / "scripts" / "deploy_safety_hook.py")
        clean_env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PROJECT_DIR", "CLAUDE_CODE")}
        for raw_stdin in ("", "{malformed-json", "{}"):
            res = subprocess.run([sys.executable, hook_script], input=raw_stdin, capture_output=True, text=True, check=True, env=clean_env)
            out = json.loads(res.stdout)
            self.assertEqual(out.get("decision"), "force_ask", f"Expected fail-closed force_ask for stdin={raw_stdin!r}")

        safe_agy = json.dumps({"toolCall": {"name": "run_command", "args": {"CommandLine": "git status", "Cwd": str(self.tmp)}}})
        res_safe = subprocess.run([sys.executable, hook_script], input=safe_agy, capture_output=True, text=True, check=True, env=clean_env)
        self.assertEqual(json.loads(res_safe.stdout).get("decision"), "allow")

        bad_agy = json.dumps({"toolCall": {"name": "run_command", "args": {"CommandLine": "sam deploy --no-confirm", "Cwd": str(self.tmp)}}})
        res_bad = subprocess.run([sys.executable, hook_script], input=bad_agy, capture_output=True, text=True, check=True, env=clean_env)
        self.assertEqual(json.loads(res_bad.stdout).get("decision"), "force_ask")

    def test_compiled_execute_hook_fails_closed_when_script_or_python_missing(self):
        ca = _load_module("compile_assets_test", "skills/wf-management/scripts/compile_assets.py")
        profiles = ca.load_host_profiles(str(REPO_ROOT))
        prog_meta = json.loads((REPO_ROOT / "plugins" / "wf-programming-plugin" / "plugin.json").read_text(encoding="utf-8"))

        agy_cmd = ca.compile_plugin_hooks_for_host(prog_meta, profiles["antigravity"])["PreToolUse"][1]["hooks"][0]["command"]
        claude_cmd = ca.compile_plugin_hooks_for_host(prog_meta, profiles["claude"])["PreToolUse"][1]["hooks"][0]["command"]

        res_agy = subprocess.run(["/bin/sh", "-c", agy_cmd], input='{"toolCall":{"args":{"CommandLine":"git status"}}}', cwd=self.tmp, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(res_agy.stdout).get("decision"), "force_ask")

        res_claude = subprocess.run(["/bin/sh", "-c", claude_cmd], input='{"tool_name":"Bash","tool_input":{"command":"git status"}}', cwd=self.tmp, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(res_claude.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")

        # Empty PATH simulates both python3 and python missing -> printf fallback must fail closed
        empty_env = {"PATH": ""}
        res_nopy = subprocess.run(["/bin/sh", "-c", agy_cmd], input="", cwd=self.tmp, env=empty_env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(res_nopy.stdout).get("decision"), "force_ask")


class TestPostCodeReviewerArchitectureChecks(unittest.TestCase):
    """Verify production fallback blocker, SAM/IaC env parity warning, link hygiene, and OKF match notice."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_blocks_production_fallback_and_warns_iac_parity(self):
        (self.tmp / "template.yaml").write_text("Parameters:\n  GatewayUrl:\n    Type: String\n", encoding="utf-8")
        (self.tmp / "samconfig.toml").write_text("[default.deploy.parameters]\nparameter_overrides = \"GatewayUrl=https://sandbox.example.com\"\n", encoding="utf-8")
        docs_arch = self.tmp / "docs" / "architecture"
        docs_arch.mkdir(parents=True, exist_ok=True)
        (docs_arch / "notifications.md").write_text(
            "---\ntype: Architecture\naffected_files:\n  - \"src/services/*.py\"\n---\n# Notifications\n",
            encoding="utf-8",
        )

        diff = (
            "+++ b/src/services/notifier.py\n"
            "+env = os.getenv('APP_ENV', 'production')\n"
            "+secret = os.environ['UNCONFIGURED_WEBHOOK_SECRET']\n"
            "+++ b/README.md\n"
            "+See [notes](file:///Users/alice/notes.md)\n"
        )
        code_sec, _ = post_code_reviewer.audit_code_security_and_bug_patterns(diff, ["src/services/notifier.py"])
        self.assertTrue(any("❌" in i and "Production Default Fallback" in i for i in code_sec), code_sec)

        iac_issues = post_code_reviewer.audit_iac_env_parity(diff, self.tmp)
        self.assertTrue(any("UNCONFIGURED_WEBHOOK_SECRET" in i for i in iac_issues), iac_issues)

        link_issues = post_code_reviewer.audit_portable_links(diff)
        self.assertTrue(any("Non-Portable Local Path" in i for i in link_issues), link_issues)

        okf_notices = post_code_reviewer.audit_okf_affected_files(["src/services/notifier.py"], self.tmp)
        self.assertTrue(any("notifications.md" in i for i in okf_notices), okf_notices)


class TestScaffoldRepoOkf(unittest.TestCase):
    """Verify `<repo>/docs/` OKF scanning, hygiene auditing, and PRD stub dehydration."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _init_git_repo(self.tmp, remote_url="git@github.com:acme/platform.git")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_non_destructive_and_hygiene_and_dehydrate(self):
        (self.tmp / "composer.json").write_text('{"name":"acme/platform"}\n', encoding="utf-8")
        sub = self.tmp / "src" / "EventSubscriber" / "OrderSubscriber.php"
        sub.parent.mkdir(parents=True, exist_ok=True)
        sub.write_text("<?php\n/**\n * Syncs order events.\n */\nclass OrderSubscriber {}\n", encoding="utf-8")
        (self.tmp / "random-notes.txt").write_text("stray root file\n", encoding="utf-8")

        spec = self.tmp / "docs" / "specs" / "order-sync-prd.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        long_lines = "\n".join(f"- Requirement detail {i}" for i in range(1, 90))
        spec.write_text(f"# Order Sync PRD\n\nSend order updates cleanly to external partners.\n\n{long_lines}\n", encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmp, check=True, capture_output=True)

        scan_res = scaffold_repo_okf.scan_and_scaffold(self.tmp)
        self.assertIn("php-backend", scan_res["detected_stacks"])
        index_file = self.tmp / "docs" / "index.md"
        self.assertTrue(index_file.is_file())

        # Preserve custom human content across rescans
        index_file.write_text(
            index_file.read_text(encoding="utf-8") + "\nCUSTOM_ARCHITECT_NOTE_KEEP_ME\n",
            encoding="utf-8",
        )
        scaffold_repo_okf.scan_and_scaffold(self.tmp)
        self.assertIn("CUSTOM_ARCHITECT_NOTE_KEEP_ME", index_file.read_text(encoding="utf-8"))

        hygiene = scaffold_repo_okf.audit_hygiene(self.tmp)
        self.assertIn("random-notes.txt", hygiene["stray_root_files"])
        self.assertEqual(len(hygiene["un_dehydrated_specs"]), 1)

        dehydrated = scaffold_repo_okf.dehydrate_spec(
            spec, repo_root=self.tmp, living_doc="docs/architecture/php-backend.md"
        )
        self.assertLess(dehydrated["stub_lines"], 30)
        stub_text = spec.read_text(encoding="utf-8")
        self.assertIn("dehydrated: true", stub_text)
        self.assertIn(dehydrated["last_full_commit"], stub_text)
        self.assertIn("https://github.com/acme/platform/blob/", stub_text)

    def test_standard_root_docs_dirty_files_and_uncommitted_spec_protection(self):
        _init_git_repo(self.tmp)
        git_repo = self.tmp
        docs_specs = git_repo / "docs" / "specs"
        docs_specs.mkdir(parents=True, exist_ok=True)
        for root_doc in ("readme-deploy.md", "README-local.md", "DEPLOYMENT.md", "llms.txt"):
            (git_repo / root_doc).write_text(f"# {root_doc}\n", encoding="utf-8")
        (git_repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
        (git_repo / "local.log").write_text("ignored log\n", encoding="utf-8")

        dirty_bak = git_repo / "stray-notes.bak"
        dirty_bak.write_text("committed\n", encoding="utf-8")
        committed_spec = docs_specs / "dirty-spec.md"
        committed_spec.write_text("\n".join(f"Line {i}" for i in range(95)) + "\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore", "stray-notes.bak", "docs/specs/dirty-spec.md"], cwd=str(git_repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=str(git_repo), check=True, capture_output=True)

        dirty_bak.write_text("uncommitted local edit\n", encoding="utf-8")
        committed_spec.write_text(committed_spec.read_text(encoding="utf-8") + "UNCOMMITTED_EDIT\n", encoding="utf-8")
        untracked_spec = docs_specs / "untracked-spec.md"
        untracked_spec.write_text("\n".join(f"Draft {i}" for i in range(95)) + "\n", encoding="utf-8")

        hygiene = scaffold_repo_okf.audit_hygiene(git_repo)
        for safe_name in ("readme-deploy.md", "README-local.md", "DEPLOYMENT.md", "llms.txt", "local.log", "stray-notes.bak"):
            self.assertNotIn(safe_name, hygiene["stray_root_files"])
        self.assertIn("stray-notes.bak", hygiene["protected_dirty_files"])
        dehydratable = [item["file"] for item in hygiene["un_dehydrated_specs"]]
        self.assertNotIn("docs/specs/dirty-spec.md", dehydratable)
        self.assertNotIn("docs/specs/untracked-spec.md", dehydratable)

        with self.assertRaises(ValueError):
            scaffold_repo_okf.dehydrate_spec(committed_spec, repo_root=git_repo)
        self.assertIn("UNCOMMITTED_EDIT", committed_spec.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            scaffold_repo_okf.dehydrate_spec(untracked_spec, repo_root=git_repo)
        self.assertIn("Draft 90", untracked_spec.read_text(encoding="utf-8"))

    def test_module_discovery_blast_radius_stale_cards_and_full_index(self):
        billing_dir = self.tmp / "apps" / "billing"
        billing_dir.mkdir(parents=True, exist_ok=True)
        (billing_dir / "invoice.py").write_text(
            "import os\nKEY = os.getenv('BILLING_WEBHOOK_KEY')\n\ndef calculate_tax(amount):\n    return amount * 0.1\n",
            encoding="utf-8",
        )
        (billing_dir / "notifier.py").write_text(
            'class InvoiceNotifier:\n    """Dispatches invoice webhooks."""\n    pass\n',
            encoding="utf-8",
        )
        web_dir = self.tmp / "apps" / "web"
        web_dir.mkdir(parents=True, exist_ok=True)
        (web_dir / "checkout.ts").write_text("export function pay() { return calculate_tax(100); }\n", encoding="utf-8")
        api_dir = self.tmp / "src" / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "routes.py").write_text("def handle():\n    return calculate_tax(50)\n", encoding="utf-8")
        (self.tmp / "tests").mkdir(parents=True, exist_ok=True)
        (self.tmp / "tests" / "test_billing.py").write_text("def test_tax(): pass\n", encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "seed modules"], cwd=self.tmp, check=True, capture_output=True)
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.tmp, check=True, capture_output=True, text=True
        ).stdout.strip()

        for i in range(6):
            (api_dir / "routes.py").write_text(f"def handle():\n    return calculate_tax({51 + i})\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=self.tmp, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"api change {i}"], cwd=self.tmp, check=True, capture_output=True)

        arch_dir = self.tmp / "docs" / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)
        (arch_dir / "api.md").write_text(
            '---\ntype: Architecture Component\ntitle: "API Gateway"\ndescription: "Handles HTTP routes."\n'
            'doc_status: "documented"\naffected_files:\n  - "src/api/**/*"\n  - "src/deleted/**/*"\n---\n# API\n',
            encoding="utf-8",
        )
        (arch_dir / "drifted.md").write_text(
            f'---\ntype: Architecture Component\ntitle: "Drifted API"\ndescription: "Tracks old SHA."\n'
            f'doc_status: "documented"\nlast_verified_commit: "{base_sha}"\naffected_files:\n  - "src/api/**/*"\n---\n# Drifted\n',
            encoding="utf-8",
        )

        scan_res = scaffold_repo_okf.scan_and_scaffold(self.tmp)
        self.assertIn("docs/architecture/api.md", scan_res["indexed_cards"])
        self.assertIn("docs/architecture/drifted.md", scan_res["indexed_cards"])
        index_text = (self.tmp / "docs" / "index.md").read_text(encoding="utf-8")
        self.assertIn("api.md", index_text)
        self.assertIn("drifted.md", index_text)
        self.assertIn("`documented`", index_text)

        hygiene = scaffold_repo_okf.audit_hygiene(self.tmp)
        recs = hygiene["doc_recommendations"]
        self.assertGreaterEqual(len(recs), 2)
        billing_rec = next(r for r in recs if r["module"] == "apps/billing")
        web_rec = next(r for r in recs if r["module"] == "apps/web")
        self.assertGreaterEqual(billing_rec["inbound_callers"], 2)
        self.assertGreater(billing_rec["priority_score"], web_rec["priority_score"])
        self.assertIn("BILLING_WEBHOOK_KEY", billing_rec["env_vars"])
        self.assertIn("tests/test_billing.py", billing_rec["test_files"])
        self.assertIn("calculate_tax", billing_rec["undocumented_symbol_names"])

        stale_files = {s["file"]: s for s in hygiene["stale_cards"]}
        self.assertIn("docs/architecture/api.md", stale_files)
        self.assertIn("src/deleted/**/*", stale_files["docs/architecture/api.md"]["broken_globs"])
        self.assertIn("docs/architecture/drifted.md", stale_files)
        self.assertGreaterEqual(stale_files["docs/architecture/drifted.md"]["commits_behind"], 6)

        cli_res = subprocess.run(
            [sys.executable, str(REPO_ROOT / "skills" / "wf-doc-generator" / "scripts" / "scaffold_repo_okf.py"), "--recommend-docs", str(self.tmp), "--json"],
            capture_output=True, text=True, check=True,
        )
        cli_payload = json.loads(cli_res.stdout)
        self.assertEqual(cli_payload["doc_recommendations"][0]["module"], "apps/billing")


class TestWfWorkMultiHarnessAndBudgetGate(unittest.TestCase):
    """Verify PM pause switch, inbox cap, cross-harness codereview, and rolling 1-bite/day guard."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake_home = self.tmp / "fake_home"
        self.fake_claude_dir = self.fake_home / ".claude"
        self.fake_grok_dir = self.fake_home / ".grok"
        self.fake_claude_dir.mkdir(parents=True, exist_ok=True)
        self.fake_grok_dir.mkdir(parents=True, exist_ok=True)
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "HOME": str(self.fake_home),
                "CLAUDE_CONFIG_DIR": str(self.fake_claude_dir),
                "GROK_HOME": str(self.fake_grok_dir),
            },
        )
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)
        (self.tmp / "workforces" / "tasks").mkdir(parents=True, exist_ok=True)
        (self.tmp / "workforces" / "issues" / "inbox").mkdir(parents=True, exist_ok=True)
        (self.tmp / "workforces" / "config.json").write_text(
            json.dumps({"schema_version": 1, "hosts": ["antigravity"]}, indent=2),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cross_harness_review_priority_and_rolling_slice_guard(self):
        tasks_dir = self.tmp / "workforces" / "tasks"
        # 1. Create an issue and promote with approval + rolling_slice cadence
        issue_file = self.tmp / "workforces" / "issues" / "inbox" / "20261114-big-file.md"
        issue_file.write_text(
            "---\ntitle: \"Refactor BigService\"\ntype: \"refactor\"\nseverity: \"P2\"\nstatus: \"inbox\"\nfile: \"src/BigService.php\"\n---\n\n# Refactor BigService\n\n## Description\n\nLarge class.\n",
            encoding="utf-8",
        )
        promoted = report_task.promote_issue_to_task(
            str(issue_file), str(tasks_dir), approved=True, cadence="rolling_slice"
        )
        self.assertTrue(os.path.isfile(promoted))
        self.assertFalse(issue_file.exists())

        # 2. Create a second rolling slice on the same file that was already sliced today -> must be blocked!
        today = datetime.date.today().isoformat()
        second_task = Path(tasks_dir) / "20261114-second-slice.md"
        second_task.write_text(
            report_task.build_task_markdown(
                title="Second slice same file",
                task_type="refactor",
                priority="P0",
                status="todo",
                file_path="src/BigService.php",
                approved_for_execution=True,
                cadence="rolling_slice",
            ).replace('status: "todo"', f'status: "todo"\nlast_slice_date: "{today}"'),
            encoding="utf-8",
        )

        # 3. Create an item authored by claude awaiting cross-harness code review
        review_task = Path(tasks_dir) / "20261114-claude-pr.md"
        review_task.write_text(
            report_task.build_task_markdown(
                title="Review webhook dispatcher",
                task_type="task",
                priority="P1",
                status="review",
                authored_by_harness="claude",
                review_state="requires_code_review",
            ),
            encoding="utf-8",
        )

        # Same harness (claude) cannot claim its own review item on codereview mode
        self.assertIsNone(report_task.claim_next_task(str(tasks_dir), current_harness="claude", mode="codereview"))

        # Different harness (antigravity) picks up Priority 0 cross-harness review on `auto`
        res_review = work_dispatch.dispatch_work(self.tmp, mode="auto", harness="antigravity", skip_gh=True)
        self.assertEqual(res_review["action"], "codereview")
        self.assertEqual(res_review["claimed_task"]["title"], "Review webhook dispatcher")

        # Next worker (`claude`) gets Priority 1 approved `Refactor BigService` (NOT `second_task` whose last_slice_date == today)
        res_exec = work_dispatch.dispatch_work(self.tmp, mode="auto", harness="claude", skip_gh=True)
        self.assertEqual(res_exec["action"], "execute_approved_task")
        self.assertEqual(res_exec["claimed_task"]["title"], "Refactor BigService")

        # Reclaiming nothing while in progress
        self.assertIsNone(report_task.claim_next_task(str(tasks_dir), current_harness="grok", mode="auto"))

    def test_pm_pause_kill_switch_and_inbox_cap(self):
        inbox = self.tmp / "workforces" / "issues" / "inbox"
        # Pause discovery via `/wf-work pause`
        work_dispatch.dispatch_work(self.tmp, mode="pause", reason="Enough issues", harness="antigravity", skip_gh=True)
        halted = work_dispatch.dispatch_work(self.tmp, mode="docs", harness="antigravity", skip_gh=True)
        self.assertEqual(halted["action"], "halted")
        self.assertEqual(halted["gate"]["code"], "discovery_paused")

        # Codereview remains unblocked even when discovery is paused
        review_gate = budget_gate.evaluate_budget_gate(self.tmp, mode="codereview", harness="claude")
        self.assertTrue(review_gate["allowed"])

        # Resume, then trigger inbox cap
        work_dispatch.dispatch_work(self.tmp, mode="resume", harness="antigravity", skip_gh=True)
        for i in range(15):
            (inbox / f"item-{i}.md").write_text("# Item\n", encoding="utf-8")
        capped = work_dispatch.dispatch_work(self.tmp, mode="debt", harness="grok", skip_gh=True)
        self.assertEqual(capped["action"], "halted")
        self.assertEqual(capped["gate"]["code"], "inbox_cap_reached")

    def test_budget_gate_enforces_configured_daily_token_cap(self):
        cfg_path = self.tmp / "workforces" / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["work_control"] = {"max_daily_tokens": 100}
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        claude_proj = self.fake_claude_dir / "projects" / "demo"
        claude_proj.mkdir(parents=True, exist_ok=True)
        (claude_proj / "session.jsonl").write_text(("x" * 1000) + "\n", encoding="utf-8")

        gated = budget_gate.evaluate_budget_gate(self.tmp, mode="docs", harness="claude")
        self.assertFalse(gated["allowed"])
        self.assertEqual(gated["code"], "token_budget_exhausted")

        # Cross-harness codereview remains unblocked even when daily token budget is exhausted
        review_gate = budget_gate.evaluate_budget_gate(self.tmp, mode="codereview", harness="claude")
        self.assertTrue(review_gate["allowed"])

    def test_rejects_arbitrary_harness_and_enforces_antigravity_est_total_tokens(self):
        tasks_dir = self.tmp / "workforces" / "tasks"
        with self.assertRaises(ValueError):
            budget_gate.detect_active_harness(explicit="arbitrary", repo_root=self.tmp)
        with self.assertRaises(ValueError):
            budget_gate.evaluate_budget_gate(self.tmp, mode="docs", harness="arbitrary")
        with self.assertRaises(ValueError):
            report_task.detect_active_harness(explicit="arbitrary")
        with self.assertRaises(ValueError):
            report_task.claim_next_task(str(tasks_dir), current_harness="arbitrary")

        cfg_path = self.tmp / "workforces" / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["work_control"] = {"max_daily_tokens": 1000}
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        usage_log = self.tmp / "workforces" / "tmp" / "usage-log.json"
        usage_log.parent.mkdir(parents=True, exist_ok=True)
        usage_log.write_text(json.dumps({"aggregate": {"est_total_tokens": 5000}}), encoding="utf-8")

        gated = budget_gate.evaluate_budget_gate(self.tmp, mode="docs", harness="antigravity")
        self.assertFalse(gated["allowed"])
        self.assertEqual(gated["code"], "token_budget_exhausted")
        self.assertEqual(gated["telemetry"]["estimated_tokens_today"], 5000)

    def test_claim_lock_prevents_concurrent_child_entry(self):
        tasks_dir = self.tmp / "workforces" / "tasks"
        child_code = (
            "import importlib.util; "
            f"spec = importlib.util.spec_from_file_location('rt', {str(REPO_ROOT / 'skills' / 'wf-task-tracker' / 'scripts' / 'report-task.py')!r}); "
            "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
            f"ctx = mod._claim_lock({str(tasks_dir)!r}, timeout_sec=0.25); ctx.__enter__()"
        )
        with report_task._claim_lock(str(tasks_dir), timeout_sec=2.0):
            child = subprocess.run([sys.executable, "-c", child_code], capture_output=True, text=True)
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("TimeoutError", child.stderr)

    def test_installed_layout_docs_scaffolding_and_all_discovery_modes(self):
        _init_git_repo(self.tmp, remote_url="https://github.com/acme/sample-app.git")
        for skill_name in ("wf-work", "wf-usage-tracker", "wf-task-tracker", "wf-doc-generator", "wf-issue-tracker", "wf-management"):
            src = REPO_ROOT / "skills" / skill_name / "scripts"
            dst = self.tmp / ".agents" / "skills" / skill_name / "scripts"
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.glob("*.py"):
                shutil.copy2(item, dst / item.name)

        (self.tmp / "random.tmp").write_text("stray note\n", encoding="utf-8")
        (self.tmp / "package.json").write_text(json.dumps({"name": "sample", "dependencies": {"lodash": "*"}}), encoding="utf-8")
        (self.tmp / "src").mkdir(parents=True, exist_ok=True)
        (self.tmp / "src" / "config.py").write_text("import os\nENV = os.getenv('APP_ENV', 'production')\n", encoding="utf-8")
        (self.tmp / "src" / "App.tsx").write_text("export function App() { return <img src='/hero.png' />; }\n", encoding="utf-8")
        (self.tmp / "src" / "worker.py").write_text("import requests\ndef run(urls):\n    for u in urls:\n        requests.get(u)\n", encoding="utf-8")

        installed_dispatch = str(self.tmp / ".agents" / "skills" / "wf-work" / "scripts" / "work_dispatch.py")
        docs_res = subprocess.run(
            [sys.executable, installed_dispatch, "docs", "--root", str(self.tmp), "--harness", "claude", "--skip-gh", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        docs_payload = json.loads(docs_res.stdout)
        self.assertEqual(docs_payload["action"], "discovery")
        self.assertTrue((self.tmp / "docs" / "index.md").is_file())
        self.assertIn("random.tmp", docs_payload["findings"]["stray_root_files"])

        for sweep_mode, expected_kind in (
            ("security", "production_default"),
            ("design", "img_missing_alt"),
            ("optimization", "loop_io_n_plus_1"),
            ("housekeeping", "unpinned_dep"),
        ):
            out = work_dispatch.dispatch_work(self.tmp, mode=sweep_mode, harness="grok", skip_gh=True, log_to_inbox=True)
            self.assertEqual(out["action"], "discovery")
            kinds = [f["kind"] for f in out["findings"]["findings"]]
            self.assertIn(expected_kind, kinds, f"Mode `{sweep_mode}` missed `{expected_kind}` in {out}")
            self.assertGreaterEqual(len(out["logged_issues"]), 1, f"Expected logged inbox issue for `{sweep_mode}`")

    def test_docs_recommendation_promotion_and_dual_deliverable_instructions(self):
        billing_dir = self.tmp / "src" / "billing"
        billing_dir.mkdir(parents=True, exist_ok=True)
        (billing_dir / "ledger.py").write_text("def post_entry(x):\n    return x + 1\n", encoding="utf-8")
        cli_dir = self.tmp / "src" / "cli"
        cli_dir.mkdir(parents=True, exist_ok=True)
        (cli_dir / "main.py").write_text("def run():\n    return post_entry(1)\n", encoding="utf-8")

        res = work_dispatch.dispatch_work(self.tmp, mode="docs", harness="claude", skip_gh=True, log_to_inbox=True)
        self.assertEqual(res["action"], "discovery")
        self.assertGreaterEqual(len(res["logged_issues"]), 2)
        self.assertTrue(any("src-cli" in Path(p).name for p in res["logged_issues"]))

        doc_issue_path = next(
            p for p in res["logged_issues"]
            if "document-module" in Path(p).name and "src-billing" in Path(p).name
        )
        issue_text = Path(doc_issue_path).read_text(encoding="utf-8")
        self.assertIn("docs/architecture/src-billing.md", issue_text)
        self.assertIn("docblocks", issue_text)

        tasks_dir = self.tmp / "workforces" / "tasks"
        promoted_path = report_task.promote_issue_to_task(doc_issue_path, str(tasks_dir), approved=True)
        claimed = work_dispatch.dispatch_work(self.tmp, mode="auto", harness="antigravity", skip_gh=True)
        self.assertEqual(claimed["action"], "execute_approved_task")
        self.assertEqual(Path(claimed["claimed_task"]["path"]).resolve(), Path(promoted_path).resolve())
        self.assertIn("docs/architecture/<module>.md", claimed["instructions"])
        self.assertIn("docblocks", claimed["instructions"])
        self.assertIn("post_code_reviewer.py --run-checks --strict", claimed["instructions"])

    def test_multi_repo_disambiguation_single_target_and_all(self):
        parent = self.tmp / "workspace_parent"
        hub = parent / "hub"
        svc_a = parent / "svc-a"
        svc_b = parent / "svc-b"
        for d in (hub, svc_a, svc_b):
            d.mkdir(parents=True, exist_ok=True)
        _init_git_repo(svc_a, remote_url="git@github.com:acme/svc-a.git")
        _init_git_repo(svc_b, remote_url="git@github.com:acme/svc-b.git")
        (svc_a / "src" / "auth").mkdir(parents=True, exist_ok=True)
        (svc_a / "src" / "auth" / "token.py").write_text("def issue_token():\n    return 'tok'\n", encoding="utf-8")
        (svc_b / "src" / "orders").mkdir(parents=True, exist_ok=True)
        (svc_b / "src" / "orders" / "sync.py").write_text("def sync_order():\n    return True\n", encoding="utf-8")

        (hub / "workforces" / "tasks").mkdir(parents=True, exist_ok=True)
        (hub / "workforces" / "issues" / "inbox").mkdir(parents=True, exist_ok=True)
        (hub / "workforces" / "config.json").write_text(
            json.dumps({"schema_version": 1, "hosts": ["claude"]}, indent=2),
            encoding="utf-8",
        )
        (hub / "workforces" / "workrules.md").write_text(
            "# Work Rules\n\n## Tracked Repositories\n- tracked_repos: [acme/svc-a, acme/svc-b]\n",
            encoding="utf-8",
        )

        # 1. Ambiguous without --repo -> must ask and perform zero writes
        ambiguous = work_dispatch.dispatch_work(hub, mode="docs", harness="claude", skip_gh=True, log_to_inbox=True)
        self.assertEqual(ambiguous["action"], "needs_repo_selection")
        self.assertTrue(ambiguous["ambiguous"])
        self.assertEqual({r["name"] for r in ambiguous["available_repos"]}, {"svc-a", "svc-b"})
        self.assertFalse((svc_a / "docs" / "index.md").exists())
        self.assertFalse((svc_b / "docs" / "index.md").exists())
        self.assertEqual(list((hub / "workforces" / "issues" / "inbox").glob("*.md")), [])

        # 2. Explicit single --repo svc-a -> documents/scans only svc-a and tags issue repo
        one = work_dispatch.dispatch_work(hub, mode="docs", harness="claude", skip_gh=True, log_to_inbox=True, repo="svc-a")
        self.assertEqual(one["action"], "discovery")
        self.assertTrue((svc_a / "docs" / "index.md").is_file())
        self.assertFalse((svc_b / "docs" / "index.md").exists())
        self.assertGreaterEqual(len(one["logged_issues"]), 1)
        a_meta, _ = report_task.parse_frontmatter(Path(one["logged_issues"][0]).read_text(encoding="utf-8"))
        self.assertEqual(a_meta.get("repo"), "svc-a")

        promoted_a = report_task.promote_issue_to_task(one["logged_issues"][0], str(hub / "workforces" / "tasks"), approved=True)
        task_a_meta, _ = report_task.parse_frontmatter(Path(promoted_a).read_text(encoding="utf-8"))
        self.assertEqual(task_a_meta.get("repo"), "svc-a")

        # 3. --repo all -> runs across both svc-a and svc-b
        both = work_dispatch.dispatch_work(hub, mode="docs", harness="grok", skip_gh=True, log_to_inbox=True, repo="all")
        self.assertEqual(both["action"], "discovery")
        self.assertEqual(both["scope"], "all")
        self.assertEqual(set(both["repos"]), {"svc-a", "svc-b"})
        self.assertTrue((svc_b / "docs" / "index.md").is_file())
        self.assertTrue(any("svc-b" in p for p in both["logged_issues"]))


class TestRepositoryCleanHygiene(unittest.TestCase):
    """Ensure zero client-proprietary names or machine-local `/Users/` links were introduced."""

    def test_zero_proprietary_terms_or_local_user_links(self):
        blocked_terms = ("rp" + "ay", "real" + "id", "chck" + "ed")
        scan_roots = ["skills", "rules", "agents", "plugins", "config", "docs"]
        user_link_re = re.compile(r"\]\(\s*(?:file://|/Users/|/home/)")

        for sub in scan_roots:
            base = REPO_ROOT / sub
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in (".py", ".md", ".json", ".sh", ".yml", ".yaml"):
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
                lowered = text.lower()
                for term in blocked_terms:
                    self.assertNotIn(term, lowered, f"Proprietary term `{term}` found in {p.relative_to(REPO_ROOT)}")
                if p.suffix.lower() == ".md":
                    self.assertIsNone(
                        user_link_re.search(text),
                        f"Non-portable local link found in {p.relative_to(REPO_ROOT)}",
                    )


if __name__ == "__main__":
    unittest.main()
