import asyncio
import base64
import io
from dataclasses import replace
from unittest.mock import patch
import unittest

from aiohttp import web
from PIL import Image

from plugin.core import Settings, ImageClient, ProviderError, validate_image, accepts_prompt


def png():
    output = io.BytesIO()
    Image.new('RGB', (8, 8), 'blue').save(output, 'PNG')
    return base64.b64encode(output.getvalue()).decode()


class SettingsTests(unittest.TestCase):
    def test_defaults_closed(self):
        settings = Settings.from_mapping({})
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.allowed_origins, ())

    def test_bad_urls(self):
        for url in ['http://remote.test/v1/images/generations', 'https://u:p@host.test/x',
                    'https://host.test/x?key=secret', 'file:///tmp/image', 'https://host.test/x#x',
                    'http://localhost.evil.test/x']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                Settings.from_mapping({'endpoint': url})

    def test_invalid_types_and_bounds(self):
        for config in [{'enabled': 'false'}, {'allowed_origins': '*'}, {'cooldown_seconds': -1},
                       {'timeout_seconds': 601}, {'api_key_env': 'bad-name'}, {'deny_terms': [1]},
                       {'size': '99999x99999'}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                Settings.from_mapping(config)

    def test_prompt_rules(self):
        self.assertTrue(accepts_prompt('a cat', ('blocked',)))
        self.assertFalse(accepts_prompt('ＢＬＯＣＫＥＤ content', ('blocked',)))

    def test_images(self):
        self.assertEqual(validate_image(png()), png())
        for value in ['', '!!!', base64.b64encode(b'not image').decode(), 'x' * 20000000, None]:
            with self.subTest(value_type=type(value)), self.assertRaises(ProviderError):
                validate_image(value)


class HTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        self.redirect_visits = 0
        self.mode = 'ok'
        async def generate(request):
            self.calls.append((dict(request.headers), await request.json()))
            if self.mode == 'redirect':
                raise web.HTTPFound('/leak')
            if self.mode == 'refused':
                return web.json_response({'error': {'message': 'private detail'}}, status=400)
            if self.mode == 'url':
                return web.json_response({'data': [{'url': 'http://127.0.0.1/private'}]})
            if self.mode == 'large':
                return web.Response(body=b'x' * (17 * 1024 * 1024))
            if self.mode == 'bad_json':
                return web.Response(body=b'not json')
            if self.mode == 'many':
                return web.json_response({'data': [{'b64_json': png()}] * 2})
            if self.mode == 'compressed':
                return web.Response(body=b'invalid', headers={'Content-Encoding': 'gzip'})
            if self.mode == 'slow':
                await asyncio.sleep(2)
            return web.json_response({'data': [{'b64_json': png()}]})
        app = web.Application()
        app.router.add_post('/v1/images/generations', generate)
        async def redirected(request):
            self.redirect_visits += 1
            return web.Response(text='should not run')
        app.router.add_get('/leak', redirected)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.settings = Settings.from_mapping({'endpoint': f'http://127.0.0.1:{port}/v1/images/generations',
                                              'allow_http_loopback': True, 'model': 'test-model'})

    async def asyncTearDown(self):
        await self.runner.cleanup()

    async def test_success_one_request(self):
        result = await ImageClient(self.settings, 'test-token').generate('test prompt')
        self.assertEqual(result, png())
        self.assertEqual(len(self.calls), 1)
        headers, body = self.calls[0]
        self.assertEqual(headers['Authorization'], 'Bearer test-token')
        self.assertEqual(body, {'model': 'test-model', 'prompt': 'test prompt', 'n': 1,
                                'size': '1024x1024', 'response_format': 'b64_json'})

    async def test_redirect_refusal_url_and_size_fail_without_retry(self):
        for mode in ['redirect', 'refused', 'url', 'large', 'bad_json', 'many', 'compressed']:
            self.mode = mode
            with self.subTest(mode=mode), self.assertRaises(ProviderError) as error:
                await ImageClient(self.settings, 'test-token').generate('private prompt')
            self.assertNotIn('private', str(error.exception))
        self.assertEqual(len(self.calls), 7)
        self.assertEqual(self.redirect_visits, 0)

    async def test_cancellation(self):
        self.mode = 'slow'
        task = asyncio.create_task(ImageClient(self.settings, 'test-token').generate('test'))
        while not self.calls:
            await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(len(self.calls), 1)

    async def test_timeout_no_retry(self):
        self.mode = 'slow'
        with self.assertRaises(ProviderError):
            await ImageClient(replace(self.settings, timeout_seconds=0.05), 'test-token').generate('test')
        self.assertEqual(len(self.calls), 1)

    async def test_real_sdk_plugin_to_http_to_reply(self):
        from plugin.main import VisualPipelinePlugin
        from test_plugin import Event, ORIGIN
        config = dict(self.settings.__dict__, enabled=True, allowed_origins=[ORIGIN])
        plugin = VisualPipelinePlugin(None, config)
        event = Event()
        event.message_str = '绘图 a blue cat'  # SDK has removed the wake prefix.
        with patch.dict('os.environ', {'IMAGE_API_KEY': 'test-token'}):
            try:
                await plugin.draw(event)
                await plugin.task
            finally:
                await plugin.terminate()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1]['prompt'], 'a blue cat')
        self.assertEqual(set(self.calls[0][1]), {'model', 'prompt', 'n', 'size', 'response_format'})
        self.assertEqual(len(event.sent), 2)
        self.assertEqual(event.sent[-1].chain[-1].file, 'base64://' + png())
