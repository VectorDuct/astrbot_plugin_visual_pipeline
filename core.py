"""Bounded client for an operator-authorized Images API; no account/session bridge."""
from dataclasses import dataclass
import base64
import binascii
import io
import ipaddress
import json
import re
import unicodedata
from urllib.parse import urlsplit
import warnings

import aiohttp
from PIL import Image

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_RESPONSE_BYTES = 17 * 1024 * 1024
MAX_PIXELS = 20_000_000


class ProviderError(Exception):
    """Deliberately contains no upstream body, URL, prompt or credentials."""


def accepts_prompt(prompt, deny_terms):
    normalized = unicodedata.normalize('NFKC', prompt).casefold()
    return not any(unicodedata.normalize('NFKC', term).casefold() in normalized
                   for term in deny_terms if term.strip())


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    allowed_origins: tuple = ()
    endpoint: str = ''
    api_key_env: str = 'IMAGE_API_KEY'
    model: str = ''
    size: str = '1024x1024'
    cooldown_seconds: int = 60
    timeout_seconds: int = 180
    allow_http_loopback: bool = False
    deny_terms: tuple = ()

    @classmethod
    def from_mapping(cls, config):
        defaults = cls()
        data = {name: config.get(name, getattr(defaults, name)) for name in cls.__dataclass_fields__}
        for name in ('enabled', 'allow_http_loopback'):
            if type(data[name]) is not bool:
                raise ValueError('invalid configuration')
        for name in ('allowed_origins', 'deny_terms'):
            if not isinstance(data[name], (list, tuple)) or len(data[name]) > 256:
                raise ValueError('invalid configuration')
            if any(not isinstance(item, str) or not item.strip() or len(item) > 512 for item in data[name]):
                raise ValueError('invalid configuration')
            data[name] = tuple(item.strip() for item in data[name])
        for name, low, high in [('cooldown_seconds', 1, 86400), ('timeout_seconds', 10, 600)]:
            if type(data[name]) is not int or not low <= data[name] <= high:
                raise ValueError('invalid configuration')
        for name in ('endpoint', 'api_key_env', 'model', 'size'):
            if not isinstance(data[name], str) or len(data[name]) > 2048:
                raise ValueError('invalid configuration')
            data[name] = data[name].strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', data['api_key_env']):
            raise ValueError('invalid configuration')
        if data['size'] not in ('1024x1024', '1024x1536', '1536x1024', '1024x1792', '1792x1024'):
            raise ValueError('invalid configuration')
        if data['endpoint']:
            url = urlsplit(data['endpoint'])
            try:
                loopback = ipaddress.ip_address(url.hostname or '').is_loopback
            except ValueError:
                loopback = False
            try:
                port = url.port
            except ValueError:
                raise ValueError('invalid configuration') from None
            if (not url.hostname or url.username is not None or url.password is not None
                    or url.query or url.fragment or '\\' in data['endpoint']
                    or any(ord(char) < 33 for char in data['endpoint'])
                    or not url.path or port == 0
                    or not (url.scheme == 'https' or (url.scheme == 'http' and loopback and data['allow_http_loopback']))):
                raise ValueError('invalid configuration')
        return cls(**data)


def validate_image(encoded):
    if not isinstance(encoded, str) or not encoded or len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
        raise ProviderError('invalid_image')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if (image.format not in ('PNG', 'JPEG', 'WEBP') or image.width * image.height > MAX_PIXELS
                        or getattr(image, 'is_animated', False)):
                    raise ValueError()
                image.verify()
    except (ValueError, TypeError, binascii.Error, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning, SyntaxError):
        raise ProviderError('invalid_image') from None
    return encoded


class ImageClient:
    def __init__(self, settings, api_key):
        self.settings = settings
        self.api_key = api_key

    async def generate(self, prompt):
        payload = {'model': self.settings.model, 'prompt': prompt, 'n': 1,
                   'size': self.settings.size, 'response_format': 'b64_json'}
        # Disabling environment proxy/netrc and redirects keeps credentials on the configured request.
        try:
            async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(
                    total=self.settings.timeout_seconds, connect=15), auto_decompress=False) as session:
                async with session.post(self.settings.endpoint, json=payload,
                        headers={'Authorization': f'Bearer {self.api_key}', 'Accept-Encoding': 'identity'},
                        allow_redirects=False) as response:
                    if response.status != 200 or response.headers.get('Content-Encoding', 'identity') != 'identity':
                        raise ProviderError('request_failed')
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        data.extend(chunk)
                        if len(data) > MAX_RESPONSE_BYTES:
                            raise ProviderError('response_too_large')
            result = json.loads(data)
            if not isinstance(result, dict) or result.get('error'):
                raise ProviderError('request_failed')
            images = result.get('data')
            if not isinstance(images, list) or len(images) != 1 or not isinstance(images[0], dict):
                raise ProviderError('invalid_response')
            return validate_image(images[0].get('b64_json'))
        except ProviderError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError, TypeError, RecursionError, OverflowError):
            raise ProviderError('request_failed') from None
