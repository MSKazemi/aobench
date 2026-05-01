# Security Policy

## Scope

ExaBench is a benchmark framework that runs against **mock HPC environments** — it does not connect to real clusters, schedulers, or infrastructure. There are no network services, no authentication systems, and no persistent user data.

Security reports are most relevant for:
- Vulnerabilities in dependency parsing or task loading that could execute arbitrary code
- Prompt injection through benchmark task content
- Credential leakage in example configurations

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email the maintainers directly at the address in `pyproject.toml` or open a [GitHub Security Advisory](https://github.com/mohsen-seyedkazemi-ardebili/ExaBench/security/advisories/new).

Include:
- A description of the vulnerability and its impact
- Steps to reproduce
- Any relevant logs or output

You will receive an acknowledgement within 72 hours and a resolution timeline within 7 days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1   | No        |
