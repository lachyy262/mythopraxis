# Security policy

## Supported versions

The latest tagged alpha release and the current `main` branch receive security fixes.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting or draft security advisory for vulnerabilities involving code execution, credential handling, provider calls, prompt injection, unsafe evaluation fixtures, or dependency compromise. Do not open a public issue before maintainers have had a reasonable opportunity to investigate.

Include the affected version, reproduction steps, expected impact, and any suggested mitigation. Do not include live credentials or private user data.

Mythopraxis never requires provider credentials for installation, validation, rendering, reporting, or dry-run evaluation. Treat any behavior that sends data to a provider without an explicit live evaluation command as a security defect.

## Input and execution boundaries

- Validation uses the contracts bundled with the installed harness. Repository
  schema files must match those contracts. External JSON Schema references are
  never fetched, including HTTP and local-file references.
- Scenario and exemplar IDs must be lowercase hyphenated slugs. Their resolved
  paths must stay inside both the repository and their expected content folder.
- YAML and contract inputs are limited to 1 MiB per file. YAML aliases are rejected,
  and YAML is limited to 64 nesting levels and 10,000 nodes before construction.
  Each rendered evaluation
  prompt is limited to 32,768 characters, with 2,000,000 characters across a run.
- Evaluations default to at most 1,000 runs. `--max-runs` can choose a limit
  between 1 and 10,000. The full matrix and all prompts are checked before any
  provider call. Both providers limit output to 2,048 tokens per request.
- Only `${OPENAI_MODEL}` and `${ANTHROPIC_MODEL}` are accepted as environment
  placeholders. Live model IDs must use `openai:model-id` or `anthropic:model-id`.
- Results are created exclusively: an existing file or final-component symlink is
  rejected. New result files use mode `0600`, and newly created output directories
  use mode `0700` on POSIX. Existing directory permissions are not changed.

Choose a fresh output filename for each evaluation. If a provider fails after a
run starts, completed rows remain available in the partial results file. Run and
output-token limits bound work; they do not estimate charges or enforce a dollar
budget. Configure provider-side spending limits before using costly models.

These controls do not make third-party instructions trustworthy. Keep normal
agent policies and tool authorization outside the story content. Filesystem
containment assumes the local repository is not being concurrently rewritten by
an attacker; use an isolated, private workspace for untrusted submissions.

## Maintaining the checks

Install `.[dev,providers,audit]` with `-c requirements-dev.txt`, then run `pytest`,
`mythopraxis validate .`, `bandit -r src -q`, and
`pip-audit --disable-pip --no-deps -r requirements-dev.txt`. Provider SDK installation
does not make live calls. CI uses these checks without provider credentials.

`requirements-dev.txt` records the resolved development, provider, and audit
versions, rather than a hash-verified build lock. Refresh it with dependency
updates. When deliberately changing a public schema, update both `schemas/` and
`src/mythopraxis/schemas/`; repository validation detects divergence. Packaged
contracts must remain available in built wheels.
