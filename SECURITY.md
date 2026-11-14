# Security Policy

## Supported Versions

| Version | Security fixes |
| --- | --- |
| 0.1.x | Supported; use the latest available patch |
| Other versions | Not supported |

## Reporting a Vulnerability

Report suspected vulnerabilities privately to [contact@vectorduct.com](mailto:contact@vectorduct.com) or [founders@vectorduct.com](mailto:founders@vectorduct.com). Do not publish vulnerability details or exploit instructions in public GitHub issues before coordinated disclosure.

We aim to acknowledge reports within 48 hours; this is an acknowledgment target, not a guaranteed fix deadline. Include plugin and AstrBot versions, a redacted configuration, expected and observed behavior, and a synthetic reproduction. Never send live bot/API keys, private group identifiers, prompts, or images. Coordinate disclosure with the maintainers after assessment and remediation.

## Security Boundary

- Generation is disabled by default and requires explicit commands from allowlisted group sessions. Wildcard session access is not supported.
- The upstream API key is read from a process environment variable, not stored in plugin configuration. Host environment and bot credentials remain the operator's responsibility.
- The plugin sends requests to the configured image-generation endpoint, rejects redirects, and accepts bounded Base64 image responses rather than downloading returned remote URLs.
- Logs contain operational status codes rather than prompts, API keys, image buffers, or raw upstream error bodies. No external telemetry beacon is included.
- Allowlisting and local keyword filtering are not guarantees of generated-content safety. Operators must trust and secure their AstrBot host, adapter, upstream provider, and delivery destinations.
