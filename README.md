# Visual Pipeline Connector

在 AstrBot 的 QQ 官方适配器中，通过明确指令把文字描述提交到管理员自有的图像 API，并把生成结果回复到原群。

**v0.1.0 · 实验性工作流连接器 · MIT**。已做真实 AstrBot SDK 的离线验证，尚未做公开版真实服务商调用与 QQ 端到端验收。

```text
/绘图 一只蓝色小猫坐在窗边，水彩插画
```

也支持 `/画图`、`/image`。由 AstrBot 的命令分发器触发：默认用 `/` 唤醒，宿主移除前缀后本插件仍识别命令；若实例配置了 @机器人或其他唤醒方式，也支持唤醒后的独立绘图指令。普通讨论不会触发生图。启用前应向使用者说明外部服务处理、群内可见性和可能的费用。

## 功能

- 默认关闭；完整群消息来源白名单，空白名单不开放。
- 一次处理一个任务；同一用户默认间隔 60 秒，缓存最近 256 条已受理请求，避免进程内重复调用。
- 文本直接传给已配置的图像服务；可设置附加拒绝词表。拒绝、超时和发送失败均不自动重新生成。
- 请求固定一张图，仅接收 Base64 PNG/JPEG/WebP；限制响应、图片字节数和像素数，不跟随重定向或下载返回链接。
- 密钥来自环境变量，不随源码提供；插件不记录提示词、密钥、图像或上游错误正文。

首版仅文生图。附图或引用消息会得到明确提示；不读取头像、引用链或本地文件，不运行自动润色、LLM 工具或登录态桥接。模型、尺寸与服务端内容审核由你选择的 API 决定。附加词表不是内容安全保障。

## 安装与配置

需要 AstrBot `>=4.29.1,<4.30`、Python 3.12 和已配置好的 QQ 官方适配器。本版在 AstrBot 4.29.1 / Python 3.12 的隔离容器中验证。

1. 将本项目源码放入 **你自己的 AstrBot 实例** 的 `data/plugins/astrbot_plugin_visual_pipeline/`，确保该目录下直接包含 `main.py`、`core.py`、`metadata.yaml`、`_conf_schema.json`。此目录布局为插件源码安装，不是运行整个 QQBot 部署包。
2. 在 AstrBot 的 Python 环境中安装 `requirements.txt`；已有依赖满足版本范围时无需重复安装。按你自己的实例流程加载插件；已有重要业务请安排维护窗口。
3. 在 AstrBot 配置页填写插件参数，参照 [config.example.json](config.example.json)。示例域名、模型、群来源是占位，不能直接请求。
4. 把 `IMAGE_API_KEY` 注入运行 AstrBot 的进程环境；Docker 用户通过现有部署的环境/secret 注入方式设置。不要把密钥放进仓库、截图或插件的“变量名”字段。
5. 配置服务完整 HTTPS 地址、模型和尺寸。接口需支持下述 JSON 协议。白名单从自己的 AstrBot 会话管理界面取得完整会话来源，格式为 `适配器实例:GroupMessage:群标识`；不能只填写群号，不支持 `*`。
6. 确认 AstrBot 的唤醒前缀包含 `/`（或使用实例已有的 @机器人指令方式），再确认外部处理告知、内容规则和费用控制后，将 `enabled` 设为 `true`。在你自己的测试群手动发送一次指令验证。

卸载或关闭插件不会删除其他插件/业务数据。不要在同一个群同时启用多个相同绘图指令处理器；不同插件、不同进程与服务商计费不在本插件的去重范围内。

### 接口协议

管理员配置完整的 `/v1/images/generations` 地址。服务必须接受 Bearer token 和以下请求，返回单张 `data[0].b64_json`：

```json
{"model":"your-image-model","prompt":"一只蓝色小猫","n":1,"size":"1024x1024","response_format":"b64_json"}
```

返回 `url`、SSE、聊天补全图片消息或自定义多模态协议均不支持。某些服务不支持 `response_format` 或这些尺寸，需使用兼容接口；本插件不自动降级或关闭服务端安全选项。尚未对任何真实服务商作兼容性承诺。

仅为本机假上游测试可显式开启 `allow_http_loopback`，HTTP 地址必须是数字回环 IP（如 `127.0.0.1`）；容器里的回环指向容器自身。HTTPS 地址由管理员信任并控制，普通用户不能改变目标地址。此开关不是面向公网的转发服务。

## 验证

安装 Docker 后在本项目目录运行以下离线用例。首次取得镜像需要网络，测试容器本身断网；源码只读，不挂载真实机器人数据。SDK 初始化数据只存在于临时容器。

```bash
docker run --rm --network none --memory 512m --cpus 1 \
  -v "$PWD:/project:ro" -w /tmp --entrypoint python \
  soulter/astrbot:v4.29.1 -B /project/tests/run.py
```

详情见 [验证范围](docs/verification.md)、[数据与使用边界](docs/privacy-and-usage.md)、[项目展示文案](docs/positioning.md) 和 [来源说明](NOTICE.md)。
