# 自动化验证

版本：v0.1.0。运行环境：AstrBot 4.29.1、Python 3.12。

在项目根目录运行：

```bash
docker run --rm --network none --memory 512m --cpus 1 \
  -v "$PWD:/project:ro" -w /tmp --entrypoint python \
  soulter/astrbot:v4.29.1 -B /project/tests/run.py
```

测试使用真实 AstrBot SDK、合成消息事件与本地模拟 Images API，覆盖：

- 默认关闭、群白名单、配置类型和端点地址校验。
- 命令过滤、唤醒前缀、图片消息组件与非指令消息处理。
- 提示词长度、附图/引用、拒绝词表及缺失凭据处理。
- 消息去重、用户冷却、单任务并发与终止取消。
- 请求字段、单张 Base64 图像、响应体积与像素边界。
- 重定向、远程图片链接、无效 JSON、多图、超时及失败不重试。
- 插件入口、模拟 API 与原消息事件图片回复的完整测试链路。

GitHub Actions 使用同一组离线测试；源码以只读方式挂载，容器禁用外部网络。
