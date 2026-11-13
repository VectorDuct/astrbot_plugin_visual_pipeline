import asyncio
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from astrbot.api.message_components import Image, Plain, Reply
from plugin.main import VisualPipelinePlugin
from test_core import png

ORIGIN = 'demo-bot:GroupMessage:demo-group'


class Event:
    unified_msg_origin = ORIGIN
    message_str = '/绘图 a blue cat'
    is_at_or_wake_command = True
    def __init__(self, message_id='test-1', sender='demo-user', parts=None):
        self.message_obj = SimpleNamespace(message_id=message_id)
        self.sender = sender
        self.parts = parts or [Plain(self.message_str)]
        self.sent = []
        self.stopped = False
        self.platform = 'qq_official'
    def get_platform_name(self):
        return self.platform
    def get_sender_id(self):
        return self.sender
    def get_messages(self):
        return self.parts
    def stop_event(self):
        self.stopped = True
    async def send(self, chain):
        self.sent.append(chain)


class PluginTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        config = {'enabled': True, 'allowed_origins': [ORIGIN],
                  'endpoint': 'https://images.example.com/v1/images/generations', 'model': 'test-model'}
        self.plugin = VisualPipelinePlugin(None, config)
        self.env = patch.dict(os.environ, {'IMAGE_API_KEY': 'test-token'})
        self.env.start()
        self.generate = AsyncMock(return_value=png())
        self.mock = patch('plugin.main.ImageClient.generate', self.generate)
        self.mock.start()

    async def asyncTearDown(self):
        await self.plugin.terminate()
        self.mock.stop()
        self.env.stop()

    async def finish(self):
        if self.plugin.task:
            await self.plugin.task

    async def test_explicit_command_real_sdk_image_and_original_event(self):
        event = Event()
        await self.plugin.draw(event)
        await self.finish()
        self.generate.assert_awaited_once_with('a blue cat')
        self.assertTrue(event.stopped)
        self.assertEqual(len(event.sent), 2)
        self.assertIsInstance(event.sent[-1].chain[-1], Image)

    async def test_fail_closed_for_unauthorized_events(self):
        events = [Event() for _ in range(6)]
        events[0].unified_msg_origin = 'demo-bot:GroupMessage:other-group'
        events[1].platform = 'aiocqhttp'
        events[2].unified_msg_origin = 'demo-bot:FriendMessage:demo-user'
        events[3].message_str = '请问如何画图'
        events[4].message_str = '/imagecat'
        events[5].message_str = '绘图 a cat'
        events[5].is_at_or_wake_command = False
        for event in events:
            await self.plugin.draw(event)
            self.assertFalse(event.stopped)
            self.assertFalse(event.sent)
        self.generate.assert_not_awaited()

    async def test_default_disabled_empty_allowlist(self):
        for change in [{'enabled': False}, {'allowed_origins': []}, {'enabled': 'true'}]:
            config = dict(self.plugin.config, **change)
            other = VisualPipelinePlugin(None, config)
            await other.draw(Event())
            await other.terminate()
        self.generate.assert_not_awaited()

    async def test_prompt_and_metadata_validation(self):
        events = [Event() for _ in range(4)]
        events[0].message_str = '/绘图 '
        events[1].message_str = '/绘图 ' + 'x' * 3001
        events[2].message_obj.message_id = ''
        events[3].sender = ''
        for event in events:
            await self.plugin.draw(event)
            self.assertTrue(event.stopped)
            self.assertEqual(len(event.sent), 1)
        self.generate.assert_not_awaited()

    async def test_reject_attachments_and_quotes(self):
        for part in [Image.fromBase64(png()), Reply(id='synthetic-message')]:
            event = Event(parts=[part])
            await self.plugin.draw(event)
            self.assertEqual(len(event.sent), 1)
        self.generate.assert_not_awaited()

    async def test_local_rule_and_missing_key(self):
        self.plugin.config['deny_terms'] = ['blocked']
        event = Event()
        event.message_str = '/绘图 ＢＬＯＣＫＥＤ'
        await self.plugin.draw(event)
        self.assertNotIn('ＢＬＯＣＫＥＤ', event.sent[0].chain[0].text)
        with patch.dict(os.environ, {'IMAGE_API_KEY': ''}):
            await self.plugin.draw(Event())
        self.generate.assert_not_awaited()

    async def test_duplicate_and_cooldown(self):
        await self.plugin.draw(Event())
        await self.finish()
        await self.plugin.draw(Event())
        await self.plugin.draw(Event(message_id='test-2'))
        self.generate.assert_awaited_once()
        await self.plugin.draw(Event(message_id='test-3', sender='other-user'))
        await self.finish()
        self.assertEqual(self.generate.await_count, 2)

    async def test_concurrent_admission_single_job(self):
        gate = asyncio.Event()
        async def wait(*args):
            await gate.wait()
            return png()
        self.generate.side_effect = wait
        await asyncio.gather(self.plugin.draw(Event()), self.plugin.draw(Event(message_id='test-2', sender='other')))
        await asyncio.sleep(0)
        self.generate.assert_awaited_once()
        gate.set()
        await self.finish()

    async def test_upstream_failure_sanitized_no_retry(self):
        self.generate.side_effect = RuntimeError('test-token private prompt upstream-url')
        event = Event()
        await self.plugin.draw(event)
        await self.finish()
        self.generate.assert_awaited_once()
        for word in ['test-token', 'private prompt', 'upstream-url']:
            self.assertNotIn(word, str(event.sent))

    async def test_acceptance_send_failure_no_generation(self):
        event = Event()
        event.send = AsyncMock(side_effect=RuntimeError('send failed'))
        await self.plugin.draw(event)
        self.generate.assert_not_awaited()

    async def test_delivery_failure_no_regeneration(self):
        event = Event()
        event.send = AsyncMock(side_effect=[None, RuntimeError('send failed'), None])
        await self.plugin.draw(event)
        await self.finish()
        self.generate.assert_awaited_once()
        self.assertEqual(event.send.await_count, 3)

    async def test_terminate_cancels_job_and_blocks_new_work(self):
        self.generate.side_effect = lambda *args: None
        async def wait(*args):
            await asyncio.Event().wait()
        self.generate.side_effect = wait
        event = Event()
        await self.plugin.draw(event)
        await asyncio.sleep(0)
        await self.plugin.terminate()
        self.assertTrue(self.plugin.task.cancelled())
        await self.plugin.draw(Event(message_id='new'))
        self.generate.assert_awaited_once()
        self.assertEqual(len(event.sent), 1)

    async def test_termination_during_acceptance_prevents_job(self):
        event = Event()
        async def close_during_send(chain):
            await self.plugin.terminate()
        event.send = close_during_send
        await self.plugin.draw(event)
        await self.finish()
        self.generate.assert_not_awaited()

    async def test_sdk_normalized_command(self):
        from astrbot.core.star.filter.command import CommandFilter
        event = Event()
        event.message_str = '绘图 a blue cat'
        event.get_message_str = lambda: event.message_str
        event.set_extra = lambda *args: None
        sdk_filter = CommandFilter('绘图')
        sdk_filter.handler_params = {}
        self.assertTrue(sdk_filter.filter(event, {}))
        await self.plugin.draw(event)
        await self.finish()
        self.generate.assert_awaited_once_with('a blue cat')
