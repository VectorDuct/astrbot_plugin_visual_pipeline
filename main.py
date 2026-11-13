"""Explicit text-to-image commands for AstrBot's official QQ adapters."""
import asyncio
from collections import OrderedDict
import os
import re
import time

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.message_components import Image, Plain, Reply
from astrbot.api.star import Context, Star, register

from .core import Settings, ImageClient, accepts_prompt

COMMAND = re.compile(r'^/?(?:绘图|画图|image)(?:\s+|$)', re.IGNORECASE)
PLATFORMS = {'qq_official', 'qq_official_webhook'}


@register('astrbot_plugin_visual_pipeline', 'Visual Pipeline Connector contributors',
          '通过自有图像 API，在授权 QQ 群中按明确指令生成图片。', '0.1.0')
class VisualPipelinePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.task = None
        self.closed = False
        self.lock = asyncio.Lock()
        self.seen = OrderedDict()
        self.cooldowns = {}

    async def terminate(self):
        self.closed = True
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def notify(self, event, text, image=None):
        chain = [Plain(text)]
        if image:
            chain.append(Image.fromBase64(image))
        await event.send(MessageChain(chain=chain).use_markdown(False))

    @filter.command('绘图', alias={'画图', 'image'})
    async def draw(self, event: AstrMessageEvent):
        # Do not handle private messages or other adapters, even with a mistaken allowlist.
        if event.get_platform_name() not in PLATFORMS:
            return
        origin = str(event.unified_msg_origin)
        if ':GroupMessage:' not in origin:
            return
        try:
            settings = Settings.from_mapping(self.config)
        except ValueError:
            logger.warning('[VisualPipeline] invalid configuration')
            return
        if self.closed or not settings.enabled or origin not in settings.allowed_origins:
            return
        if not getattr(event, 'is_at_or_wake_command', False):
            return
        # AstrBot strips the configured wake prefix before command dispatch.
        match = COMMAND.match(event.message_str)
        if not match:
            return
        event.stop_event()
        prompt = event.message_str[match.end():].strip()
        if not 1 <= len(prompt) <= 3000:
            await self.notify(event, '请用 /绘图 加画面描述，最多 3000 字。')
            return
        # Never silently ignore an attachment, quote or avatar instruction by fetching private data.
        if any(isinstance(part, (Image, Reply)) for part in event.get_messages()):
            await self.notify(event, '当前版本仅支持文字描述，请另发一条纯文字绘图指令。')
            return
        if not accepts_prompt(prompt, settings.deny_terms):
            await self.notify(event, '这条请求不符合当前机器人的使用规则。')
            return
        key = os.environ.get(settings.api_key_env, '').strip()
        if (not settings.endpoint or not settings.model or not key or len(key) > 8192
                or any(ord(char) < 32 or ord(char) > 126 for char in key)):
            await self.notify(event, '绘图服务尚未配置完成，请联系管理员。')
            return
        sender = str(event.get_sender_id() or '')
        message_id = str(getattr(event.message_obj, 'message_id', '') or '')
        if not sender or not message_id:
            await self.notify(event, '无法识别这条请求，请重新发送绘图指令。')
            return
        request_key = (origin, sender, message_id)
        cooldown_key = (origin, sender)
        async with self.lock:
            now = time.monotonic()
            self.cooldowns = {k: until for k, until in self.cooldowns.items() if until > now}
            if self.closed:
                return
            if request_key in self.seen:
                await self.notify(event, '这条请求已受理，不会重复生成。')
                return
            if self.task and not self.task.done():
                await self.notify(event, '正在处理一张图片，请稍后再发指令。')
                return
            if cooldown_key in self.cooldowns:
                await self.notify(event, '请求较频繁，请稍后再试。')
                return
            # A failed acceptance reply must not trigger a billed request.
            try:
                await self.notify(event, '已受理，完成后将在这里回复图片。')
            except Exception:
                logger.warning('[VisualPipeline] acceptance delivery failed; no generation')
                return
            if self.closed:
                return
            self.seen[request_key] = True
            while len(self.seen) > 256:
                self.seen.popitem(last=False)
            self.cooldowns[cooldown_key] = now + settings.cooldown_seconds
            self.task = asyncio.create_task(self.render(event, prompt, settings, key))

    async def render(self, event, prompt, settings, key):
        stage = 'generation'
        try:
            image = await ImageClient(settings, key).generate(prompt)
            stage = 'delivery'
            await self.notify(event, '图片已生成。', image)
        except asyncio.CancelledError:
            # Cancelling a client request cannot guarantee that the provider stops billing.
            raise
        except Exception:
            # Upstream exceptions can contain secrets and user input: never interpolate them.
            logger.warning('[VisualPipeline] %s failed; no retry', stage)
            try:
                text = ('图片发送失败；可能已产生生成费用，请勿重复提交同一请求。'
                        if stage == 'delivery' else
                        '本次未取得可发送的图片，可能被拒绝或服务暂不可用；不会自动重试。')
                await self.notify(event, text)
            except Exception:
                logger.warning('[VisualPipeline] notice delivery failed')
