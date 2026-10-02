# xorq-ci

Shared CI/CD pieces for xorq-labs repositories. Each piece is consumed the one
way that works for it:

| Piece | How a repo consumes it |
|---|---|
| `renovate/default.json` (Renovate preset) | referenced: `.github/renovate.json5` extends it |
| `.github/workflows/lint.yml`, `workflow-audit.yml` (reusable workflows) | referenced: `uses: xorq-labs/xorq-ci/...@<sha>` |
| `templates/` (pre-commit config, caller workflows, actionlint config) | copied, then checked by `bin/xorq-ci-drift` |

## Adopting it

1. Record the version in `.github/xorq-ci.rev`, as one line:

   ```
   v0.1.0 <the tag's 40-character commit sha>
   ```

   This is the only place the version is written. Renovate bumps it in the
   same PR as every `uses:` ref to xorq-ci.

2. Copy what you need. With a clone of xorq-ci at that tag:

   ```bash
   drift=path/to/xorq-ci/bin/xorq-ci-drift
   $drift copy templates/pre-commit-config.yaml .pre-commit-config.yaml
   $drift copy templates/workflows/ci-lint.yml .github/workflows/ci-lint.yml
   $drift copy templates/workflows/ci-workflow-audit.yml .github/workflows/ci-workflow-audit.yml
   $drift copy templates/actionlint.yaml .github/actionlint.yaml
   $drift copy templates/renovate.json5 .github/renovate.json5
   ```

   `copy` fills in the version from `.github/xorq-ci.rev`.

3. Fit the pre-commit config to the repo. Delete the layers it doesn't use,
   and change its first line from `managed` to `forked`. If the repo uses the
   infra layer, add an `.opentofu-version` file; `lint.yml` installs that
   version.

4. Run both `pre-commit run --all-files` and
   `pre-commit run --all-files --hook-stage manual`, and fix what they find.

## Managed and forked copies

Every copied file names its source in its first lines:

```
# xorq-ci: managed templates/workflows/ci-lint.yml
```

- `managed`: identical to upstream at the recorded version. Any difference
  fails `xorq-ci-drift check`.
- `forked`: started from upstream and changed on purpose. The check reports
  the diff without failing.

`xorq-ci-drift check` also fails when a `uses: xorq-labs/xorq-ci/...@<sha>`
names a different sha than `.github/xorq-ci.rev`. After a version bump,
`xorq-ci-drift update` re-copies the managed files and leaves forked ones
alone. In CI, `ci-workflow-audit` runs the check.

## Two passes in CI

`lint.yml` runs the repo's pre-commit config twice:

1. `pre-commit run --all-files` runs the commit-time hooks.
2. `--hook-stage manual` runs hooks meant for CI.

The template's manual stage holds a whole-tree gitleaks scan. The upstream
gitleaks hook scans only staged changes, so in CI, where nothing is staged, it
would check nothing.

## Developing xorq-ci

```bash
python3 -m unittest discover -s tests   # bin/xorq-ci-drift
python3 dev/fixture-test                # the template against fixtures/ (needs tofu)
pre-commit run --all-files              # this repo's own hooks
```

`dev/fixture-test` proves that the template passes a clean fixture repo and
that each hook fails a known-bad change. A new hook needs a new case there.
