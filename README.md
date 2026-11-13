# Visual Pipeline Connector (`astrbot_plugin_visual_pipeline`)

**[简体中文](./README.zh-CN.md)**

An event-driven image generation workflow plugin for AstrBot (Official QQ Adapter). Routes explicit user drawing commands to a self-hosted or compatible image generation API and returns rendered media directly to the originating group chat.

- **Version**: `v0.1.0`
- **License**: MIT

## Usage

Triggered via explicit `/绘图`, `/画图`, or `/image` commands:

```text
/绘图 一只蓝色小猫坐在窗边，水彩插画
```

The plugin hooks into AstrBot's command dispatcher (supporting the default `/` prefix as well as `@bot` mention triggers when configured on the host instance). Regular group conversation never triggers generation.

## Key Features

- **Strict Session Allowlist**: Disabled by default. Only processes commands from explicitly allowlisted group session identifiers (`<adapter_id>:GroupMessage:<group_id>`). Wildcards (`*`) are not permitted.
- **Concurrency & Rate Limiting**: Serializes generation tasks one at a time, enforces a configurable per-user cooldown (default `60s`), and maintains an in-memory LRU cache of the last 256 accepted requests to prevent duplicate submissions.
- **Deterministic Payload Validation**: Requests a single image (`n: 1`) and accepts strictly Base64-encoded image payloads (`PNG`, `JPEG`, `WebP`). Enforces strict ceilings on response size, image byte length, and pixel dimensions without following external redirects or fetching remote URLs.
- **Credential Isolation & Zero Content Logging**: Reads upstream API keys exclusively from process environment variables. Logs contain operational status codes only—never prompts, API keys, image buffers, or upstream error bodies.
- **Local Deny-List Filtering**: Supports configurable local keyword blocklists prior to upstream dispatch. Failed or timed-out requests return a concise status notice without automatic retries.

## Requirements & Installation

- **Runtime**: `AstrBot >= 4.29.1, < 4.30`, `Python 3.12`, and a configured Official QQ Adapter.

1. **Install Plugin Source**: Place this repository inside your AstrBot instance at `data/plugins/astrbot_plugin_visual_pipeline/` (ensuring `main.py`, `core.py`, `metadata.yaml`, and `_conf_schema.json` sit at the plugin root).
2. **Install Dependencies**: Run inside your AstrBot Python environment:
   ```bash
   pip install -r requirements.txt
   ```
3. **Inject Credentials**: Set the `IMAGE_API_KEY` environment variable in your host or container runtime. Never place raw secret values inside configuration files or repository commits.
4. **Configure Parameters**: Using `config.example.json` as a reference, configure the upstream HTTPS endpoint, model identifier, image dimensions, and allowed group session IDs in the AstrBot console, then set `enabled` to `true`.

## Upstream API Contract

The plugin sends an HTTP `POST` request with `Authorization: Bearer <IMAGE_API_KEY>` to your configured `/v1/images/generations` HTTPS endpoint:

```json
{
  "model": "your-image-model",
  "prompt": "一只蓝色小猫坐在窗边，水彩插画",
  "n": 1,
  "size": "1024x1024",
  "response_format": "b64_json"
}
```

The upstream service must return a JSON payload containing `data[0].b64_json`. For local loopback testing against a mock server (e.g., `127.0.0.1`), `allow_http_loopback` can be explicitly enabled in configuration.

## Containerized Verification

Run the offline unit test suite inside an isolated, network-disabled AstrBot container:

```bash
docker run --rm --network none --memory 512m --cpus 1 \
  -v "$PWD:/project:ro" -w /tmp --entrypoint python \
  soulter/astrbot:v4.29.1 -B /project/tests/run.py
```

## License

MIT License. Maintained by [VectorDuct](https://vectorduct.com).
