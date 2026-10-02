"""Tests for bin/xorq-ci-drift against throwaway upstream and consumer repos."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "xorq-ci-drift"
_loader = importlib.machinery.SourceFileLoader("xorq_ci_drift", str(SCRIPT))
_spec = importlib.util.spec_from_loader("xorq_ci_drift", _loader)
drift = importlib.util.module_from_spec(_spec)
_loader.exec_module(drift)

CALLER = """\
# xorq-ci: managed templates/workflows/ci-lint.yml
name: ci-lint
on: pull_request
jobs:
  lint:
    uses: xorq-labs/xorq-ci/.github/workflows/lint.yml@XORQ_CI_SHA # XORQ_CI_TAG
"""
CONFIG = """\
# xorq-ci: managed templates/pre-commit-config.yaml
repos: []
"""


def sh(*args: str, cwd: Path) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    sh("git", "init", "-q", "-b", "main", cwd=path)
    sh("git", "config", "user.email", "test@example.invalid", cwd=path)
    sh("git", "config", "user.name", "test", cwd=path)


def commit_all(path: Path) -> str:
    sh("git", "add", "-A", cwd=path)
    sh("git", "commit", "-q", "-m", "x", cwd=path)
    return sh("git", "rev-parse", "HEAD", cwd=path).strip()


class DriftTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.upstream = self.tmp / "upstream"
        init_repo(self.upstream)
        (self.upstream / "templates" / "workflows").mkdir(parents=True)
        (self.upstream / "templates" / "workflows" / "ci-lint.yml").write_text(CALLER)
        (self.upstream / "templates" / "pre-commit-config.yaml").write_text(CONFIG)
        self.sha = commit_all(self.upstream)
        self.consumer = self.tmp / "consumer"
        init_repo(self.consumer)
        (self.consumer / ".github").mkdir()
        (self.consumer / ".github" / "xorq-ci.rev").write_text(f"v0.1.0 {self.sha}\n")
        self.run_drift(
            "copy", "templates/workflows/ci-lint.yml", ".github/workflows/ci-lint.yml"
        )
        self.run_drift(
            "copy", "templates/pre-commit-config.yaml", ".pre-commit-config.yaml"
        )
        commit_all(self.consumer)

    def run_drift(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            rc = drift.main(
                [*args, "--root", str(self.consumer), "--upstream", str(self.upstream)]
            )
        return rc, out.getvalue()

    def edit(self, rel: str, old: str, new: str) -> None:
        path = self.consumer / rel
        path.write_text(path.read_text().replace(old, new))
        commit_all(self.consumer)

    def test_fresh_copies_are_clean(self) -> None:
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 0, out)
        caller = (self.consumer / ".github/workflows/ci-lint.yml").read_text()
        self.assertIn(f"lint.yml@{self.sha} # v0.1.0", caller)

    def test_edited_managed_file_fails(self) -> None:
        self.edit(".github/workflows/ci-lint.yml", "on: pull_request", "on: push")
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 1, out)
        self.assertIn("managed copy differs", out)

    def test_forked_file_reports_without_failing(self) -> None:
        self.edit(".pre-commit-config.yaml", "managed", "forked")
        self.edit(".pre-commit-config.yaml", "repos: []", "repos: [x]")
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 0, out)
        self.assertIn(
            "forked from templates/pre-commit-config.yaml): 2 changed lines", out
        )

    def test_uses_ref_must_match_rev(self) -> None:
        self.edit(".github/workflows/ci-lint.yml", "managed", "forked")
        self.edit(".github/workflows/ci-lint.yml", self.sha, "f" * 40)
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 1, out)
        self.assertIn("but .github/xorq-ci.rev records", out)

    def test_update_restores_managed_file(self) -> None:
        self.edit(".github/workflows/ci-lint.yml", "on: pull_request", "on: push")
        rc, out = self.run_drift("update")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.run_drift("check")[0], 0)

    def test_missing_upstream_path_fails(self) -> None:
        self.edit(
            ".pre-commit-config.yaml",
            "templates/pre-commit-config.yaml",
            "templates/gone.yaml",
        )
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 1, out)
        self.assertIn("does not exist upstream", out)

    def test_malformed_rev_file_cannot_run(self) -> None:
        (self.consumer / ".github" / "xorq-ci.rev").write_text("main\n")
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 2, out)

    def test_unknown_sha_cannot_run(self) -> None:
        (self.consumer / ".github" / "xorq-ci.rev").write_text(f"v0.1.0 {'0' * 40}\n")
        rc, out = self.run_drift("check")
        self.assertEqual(rc, 2, out)
        self.assertIn("upstream has no commit", out)


if __name__ == "__main__":
    unittest.main()
