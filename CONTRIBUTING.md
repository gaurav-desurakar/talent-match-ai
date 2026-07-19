# Contributing

Thank you for helping build safer, more explainable recruiting software.

## Before making changes

1. Open an issue for substantial product, schema, provider, or scoring changes.
2. Install the supported toolchain with `make install`, then run `make db-upgrade`.
3. Use fictional fixtures only. Never commit real candidate data, credentials, or confidential job information.

## Engineering expectations

- Prefer clear, strictly typed code over clever abstractions.
- Keep provider-specific behaviour behind the provider interface.
- Keep scoring, mandatory handling, and triage deterministic.
- Treat uploaded content and provider output as untrusted data.
- Schema-validate model output and fail visibly when it cannot be validated.
- Never fabricate candidate evidence or expose private model reasoning.
- Never use protected or inferred demographic characteristics in scoring.
- Keep frontend components modular and avoid global mutable state.
- Add meaningful errors and never suppress failures silently.
- Update relevant documentation when product behaviour, setup, APIs, privacy, or limitations change.

## Validation

Run the same primary checks as CI before opening a pull request:

```bash
make test
make lint
```

Backend coverage must remain at or above 90%. If dependencies change, update the relevant lockfile and keep the Makefile, CI, Docker, and README instructions consistent.

By participating, you agree to follow the Code of Conduct. Contributions are accepted under Apache License 2.0.
