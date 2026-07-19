# Security policy

## Reporting a vulnerability

Do not report vulnerabilities in a public issue. Use GitHub private vulnerability reporting when enabled, or contact the maintainers privately.

Include affected version, reproduction steps, impact, and any suggested mitigation. Do not include real resumes, provider keys, or personal data. Maintainers will acknowledge a report, assess severity, coordinate a fix, and publish an advisory when appropriate.

## Deployment boundary

The MVP is intended for single-user local or self-hosted use. It has no user authentication and must not be exposed directly to an untrusted network. Add authentication, TLS, network isolation, rate limits, encrypted backups, and managed secrets before a shared or internet-facing deployment.

Keys entered through Provider settings remain in an expiring API-process memory session. The opaque session identifier is stored in browser `sessionStorage`; it is not an authentication boundary and is cleared when that browser tab session ends. The application does not offer persistent user-key storage. Operators may alternatively inject system keys through environment variables and are responsible for protecting that environment.

Candidate and job text is intentionally persisted for contextual history and exports. Saving a retention period does not schedule cleanup by itself; operators must invoke the retention endpoint or arrange a scheduler. Secure the SQLite file or PostgreSQL deployment and its backups at rest.

See [Data privacy](docs/privacy.md) and [Threat model](docs/threat-model.md) for the current controls and limitations.
