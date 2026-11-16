# Changelog

Notable changes are documented using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) categories. Release dates reflect publication of the corresponding version.

## [Unreleased]

## [0.1.0] - 2026-11-16

### Added

- Private vulnerability disclosure policy and contributor verification guide.
- EditorConfig settings for UTF-8, LF line endings, final newlines, and Python indentation.
- Workflow Conduit: event-driven AstrBot image-generation connector for the Official QQ Adapter.
- Explicit `/绘图`, `/画图`, and `/image` commands with generated media returned to the originating group session.
- Single-task concurrency, configurable per-user cooldown, and an in-memory cache of the last 256 accepted requests for deduplication.
- Single-image requests and bounded Base64 PNG, JPEG, and WebP responses, including byte-size and pixel-dimension checks.
- Local keyword filtering and concise failure/timeout notices without automatic retries.
- English and Chinese documentation, synthetic tests, and offline container verification against AstrBot v4.29.1.
- Runtime requirements: Python 3.12, AstrBot >=4.29.1,<4.30, and the `aiohttp`/Pillow dependencies declared in `requirements.txt`.

### Security

- Disabled by default; generation requires an explicit command and an exact allowlisted group session, without wildcard access.
- Upstream API keys read from environment variables rather than plugin configuration.
- Redirects and downloading returned remote image URLs are disallowed; HTTP is limited to explicitly enabled loopback testing.
- Operational logs exclude prompts, API keys, image buffers, and raw upstream error bodies; no external telemetry beacon.
