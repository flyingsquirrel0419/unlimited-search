# Security Policy

## Supported Versions

Security fixes are currently applied to the `main` branch until tagged releases are established.

## Reporting a Vulnerability

Please do not open a public issue for a vulnerability.

Report security issues by opening a private GitHub security advisory if available, or by contacting the maintainers through the repository owner profile.

Include:

- affected version or commit
- reproduction steps
- target URL class, if relevant
- impact
- whether credentials, private IPs, or local network resources are involved

## Security Boundaries

`unlimited-search` is a public-content reader. It is not designed to bypass authentication, paywalls, access controls, or private network boundaries.

The project should:

- reject private, loopback, link-local, multicast, reserved, and metadata-service targets by default
- validate redirects before following them
- avoid storing credentials
- avoid logging secrets or full private URLs unnecessarily
- stop at authentication and paywall walls
- treat fetched HTML, JSON, RSS, and metadata as untrusted content
- keep fallback providers limited to public, unauthenticated content routes

## Out of Scope

- bypassing logins, paywalls, or CAPTCHA challenges
- scraping private or access-controlled content
- bypassing hard anti-abuse systems, IP bans, or rate limits
- denial-of-service reports based only on intentionally excessive request volume
- issues requiring stolen credentials or compromised local machines
