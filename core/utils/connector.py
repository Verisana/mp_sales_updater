import asyncio
import json
from typing import Union, Dict, Tuple

import aiohttp
from bs4 import BeautifulSoup

from core.types import RequestBody
from core.utils.proxy_manager import ProxyManager
from core.utils.logging_helpers import get_logger

logger = get_logger()


class Connector:
    """Here is we send all url requests"""

    def __init__(self, use_proxy=True, try_count=10):
        self.pm = ProxyManager()
        self.use_proxy = use_proxy
        self.try_count = try_count

    @staticmethod
    def is_captcha_checker(bs: BeautifulSoup) -> bool:
        for frame in bs.findAll('iframe'):
            try:
                frame['src']
            except KeyError:
                continue
            if 'captcha' in frame['src'] and 'fallback' not in frame['src']:
                return True
        return False

    async def get_page(self, request_info: RequestBody) -> Union[Tuple[BeautifulSoup, bool, int],
                                                                 Tuple[Dict, bool, int],
                                                                 Tuple[None, None, None], Tuple[bytes, None, int]]:
        async with aiohttp.ClientSession() as session:
            while True:
                for i in range(self.try_count):
                    try:
                        try:
                            response = await self._send_request(request_info, session)
                        except aiohttp.ClientError as e:
                            logger.warning(f'aiohttp error: {e}')
                            continue

                        is_captcha = False
                        if request_info.parsing_type == 'bs':
                            try:
                                content = await response.content.read()
                            except aiohttp.ClientPayloadError as e:
                                logger.warning(f'ClientPayloadError: {e} for bs parsing. Try another attempt')
                                continue
                            bs, is_captcha = self._parse_to_bs(content, request_info)
                            return bs, is_captcha, response.status
                        elif request_info.parsing_type == 'json':
                            try:
                                json_result = await self._parse_to_json(response)
                                return json_result, is_captcha, response.status
                            except json.JSONDecodeError as e:
                                logger.warning(
                                    f'JSONDecoderError: {e.msg}')
                        elif request_info.parsing_type == 'image':
                            content = await response.content.read()
                            return content, None, response.status
                        else:
                            logger.warning('Unrecognized type of parsing')
                    except asyncio.TimeoutError as e:
                        logger.warning(f'Asyncio timeout error occurred {e}. Try another attempt')
                logger.error(f"All attempts to connect for {request_info.url[:120]} and {request_info.url[-10:]} "
                             f"have been used. Trying another {self.try_count} attempts")

    def _parse_to_bs(self, content: bytes, request_info: RequestBody) -> (BeautifulSoup, bool):
        bs = BeautifulSoup(content, 'lxml')

        is_captcha = self.is_captcha_checker(bs)
        logger.error(f'Captcha is found in {request_info}') if is_captcha else None
        return bs, is_captcha

    @staticmethod
    async def _parse_to_json(response: aiohttp.ClientResponse) -> Dict:
        try:
            parsed_json = await response.json()
            return parsed_json
        except json.JSONDecodeError as e:
            if e.msg.startswith('Unexpected UTF-8 BOM'):
                text = await response.text()
                return json.loads(text.encode().decode('utf-8-sig'))
            else:
                raise e

    async def _send_request(self, request_info: RequestBody, session: aiohttp.ClientSession) -> aiohttp.ClientResponse:
        proxies = self.pm.get_proxy() if self.use_proxy else None
        response = await session.request(method=request_info.method, url=request_info.url, headers=request_info.headers,
                                         proxy=proxies['http'], params=request_info.params)
        return response
