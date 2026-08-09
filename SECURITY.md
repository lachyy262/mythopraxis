# Security policy

## Supported versions

The latest tagged alpha release and the current `main` branch receive security fixes.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting or draft security advisory for vulnerabilities involving code execution, credential handling, provider calls, prompt injection, unsafe evaluation fixtures, or dependency compromise. Do not open a public issue before maintainers have had a reasonable opportunity to investigate.

Include the affected version, reproduction steps, expected impact, and any suggested mitigation. Do not include live credentials or private user data.

Mythopraxis never requires provider credentials for installation, validation, rendering, reporting, or dry-run evaluation. Treat any behavior that sends data to a provider without an explicit live evaluation command as a security defect.
