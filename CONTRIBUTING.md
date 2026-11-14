# Contributing

Keep pull requests focused, explain the expected behavior, and include verification results. Use synthetic prompts, images, credentials, and group identifiers. Report vulnerabilities privately through [SECURITY.md](./SECURITY.md).

## Local Verification

The supported host is AstrBot `>=4.29.1,<4.30` with Python 3.12 and the Official QQ Adapter. The plugin uses `aiohttp` and Pillow as declared in `requirements.txt`; it is not a standard-library-only plugin.

Run the same isolated test command used by GitHub CI from the repository root in a POSIX shell:

```bash
docker run --rm --network none --memory 512m --cpus 1 \
  -v "$PWD:/project:ro" -w /tmp --entrypoint python \
  soulter/astrbot:v4.29.1 -B /project/tests/run.py
```

Docker must be running. The AstrBot image must be available locally or downloadable before the container starts. Tests run with the repository mounted read-only, networking disabled, and no live bot data or provider credentials. Use the pinned SDK image rather than substituting a different AstrBot version when reproducing CI.

## Code Style and Boundaries

- Follow existing Python formatting, type annotations, asynchronous conventions, and valid UTF-8 encoding. Preserve Chinese command aliases and both README languages.
- Reuse existing dependencies and explain any proposed runtime dependency.
- Preserve disabled-by-default behavior, exact session allowlisting, per-user cooldowns, bounded concurrency, deduplication, and explicit command dispatch.
- Keep API keys in environment variables and operational logs free of prompts, media buffers, credentials, and upstream error bodies. Do not add external telemetry.
- Add synthetic regression coverage for changes to command authorization, request validation, timeouts, redirects, or image limits. Avoid tests that require real QQ accounts or external image generation.
