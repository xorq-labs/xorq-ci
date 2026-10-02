# Changelog

Consumers read this before taking a new `.github/xorq-ci.rev`.

## v0.1.0 (unreleased)

- Pre-commit template with core, shell and infra layers.
  - gitleaks also runs a whole-tree scan in the manual stage: the upstream hook scans staged changes only, so it checks nothing in CI.
  - check-merge-conflict runs with `--assume-in-merge` and check-added-large-files with `--enforce-all`, for the same reason.
- Reusable workflows:
  - `lint.yml` runs the caller's pre-commit config in two passes, commit-time hooks and manual-stage hooks.
  - `workflow-audit.yml` runs the drift check.
- Caller templates: `ci-lint.yml`, `ci-workflow-audit.yml`, `actionlint.yaml`, `renovate.json5`.
- Renovate preset `renovate/default.json`.
- `bin/xorq-ci-drift`: `check`, `update` and `copy` against `.github/xorq-ci.rev`.
