# Security Policy

## Research Preview support

ADME Dialog Agent is currently a `0.1.x` Research Preview. Security fixes are
made on the latest development version. Older snapshots and local
modifications may not receive fixes.

The preview is designed for local, single-user use. It does not include
authentication, tenant isolation, or the operational controls required for an
internet-facing multi-user deployment.

## Report privately

Do not open a public issue for a vulnerability. After the GitHub repository is
created, use its private vulnerability reporting or Security Advisory feature.
Until that channel is available, contact the maintainer through a private
method listed on the maintainer's GitHub profile.

Include:

- affected version or commit;
- minimal reproduction steps;
- expected and observed impact;
- whether the issue exposes credentials, molecular data, sessions, or files;
- a proposed fix, if available.

Do not include a real API key, private molecule, complete user conversation,
SQLite database, or unredacted log in the report. Use synthetic fixtures.

The maintainer will aim to acknowledge a complete report within seven days.
Response and release timing will depend on severity and maintainer
availability.

## Issues that belong here

Examples include:

- cross-session or unauthorized access;
- confirmation bypass or replay;
- tool execution outside the allowlist;
- arbitrary code, shell, path, or file access;
- credential or sensitive-context leakage;
- unsafe upload parsing or export behavior;
- audit-log redaction failures;
- dependency vulnerabilities with a credible impact on this project.

Ordinary scientific metadata corrections should use the scientific-validation
issue template unless disclosure would expose private information.

## Secret handling

- Keep real credentials in `.env`, which must remain untracked.
- Never place secrets in `NEXT_PUBLIC_*` variables.
- Never commit local databases, uploads, batch jobs, exports, or logs.
- If a credential is exposed in a commit, screenshot, issue, or chat, revoke
  and replace it. Removing the visible text alone is not sufficient.

## External services

Name and CID resolution may contact PubChem. The optional Agent sends bounded
context to the provider selected by the person running the project. Review a
provider's privacy and retention terms before sending confidential structures
or results.
