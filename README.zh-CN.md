# Visual Pipeline Connector (`astrbot_plugin_visual_pipeline`)

**[English](./README.md)**

面向 AstrBot（QQ 官方适配器）的图像生成工作流连接器。通过显式指令触发，将文本提示词转发至自托管或兼容的图像生成 API，并将渲染结果直接回传至群聊会话。

- **版本**：`v0.1.0`
- **开源协议**：MIT License

## 触发方式

支持 `/绘图`、`/画图`、`/image` 指令触发：

```text
/绘图 一只蓝色小猫坐在窗边，水彩插画
```

插件通过 AstrBot 命令分发器挂载：默认支持 `/` 前缀唤醒，亦兼容宿主实例已配置的 `@机器人` 唤醒指令。普通群聊消息不会触发图像生成。

## 核心特性

- **严格的会话白名单控制**：默认关闭，仅对显式配置的群聊会话标识（格式：`适配器实例:GroupMessage:群标识`）生效，不支持通配符 `*` 放行。
- **并发与频次保护**：单任务串行执行；同一用户默认冷却间隔 60 秒，内置最近 256 条请求的进程内去重缓存，避免重复调用。
- **确定性载荷校验**：单次请求固定生成 1 张图片，仅接收标准 Base64 编码图像（`PNG` / `JPEG` / `WebP`）；严格限制响应体积、图像字节数与像素尺寸，不跟随外部重定向或拉取远程 URL。
- **凭据隔离与零日志留存**：API 密钥通过进程环境变量注入，不在配置文件中明文存储；运行日志仅记录状态元数据，不记录提示词内容、密钥、图像数据或上游错误正文。
- **本地拒绝词表拦截**：支持配置附加拒绝词表；请求拒绝、超时或发送失败时直接返回提示，不执行自动重新生成。

## 环境要求与安装

- **运行环境**：`AstrBot >= 4.29.1, < 4.30`，`Python 3.12`，已配置 QQ 官方适配器。

1. **放置插件源码**：将本项目放入 AstrBot 实例的 `data/plugins/astrbot_plugin_visual_pipeline/` 目录下（确保该目录直接包含 `main.py`、`core.py`、`metadata.yaml` 与 `_conf_schema.json`）。
2. **安装依赖**：在 AstrBot 的 Python 环境中安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. **注入环境变量**：在运行 AstrBot 的进程或容器环境中设置 `IMAGE_API_KEY`。请勿将真实密钥写入仓库或插件配置的“变量名”字段。
4. **配置参数**：参照 `config.example.json` 填写上游完整 HTTPS 地址、模型名称、图片尺寸及完整群会话来源白名单，确认无误后将 `enabled` 设为 `true`。

## 上游接口协议

插件向配置的 `/v1/images/generations` HTTPS 地址发送带有 `Authorization: Bearer <IMAGE_API_KEY>` 的 POST 请求：

```json
{
  "model": "your-image-model",
  "prompt": "一只蓝色小猫坐在窗边，水彩插画",
  "n": 1,
  "size": "1024x1024",
  "response_format": "b64_json"
}
```

服务需返回单张 `data[0].b64_json`。仅在本地回环假上游联调时可显式开启 `allow_http_loopback`（限 `127.0.0.1` 等数字回环地址）。

## 容器化验证

安装 Docker 后可在项目目录运行以下离线验证用例（测试容器断网且只读挂载源码）：

```bash
docker run --rm --network none --memory 512m --cpus 1 \
  -v "$PWD:/project:ro" -w /tmp --entrypoint python \
  soulter/astrbot:v4.29.1 -B /project/tests/run.py
```

## 开源许可

MIT License. 由 [VectorDuct](https://vectorduct.com) 维护。
