import json
import codecs
from typing import Union, Dict, Tuple

import requests
from requests.models import Response
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

    def get_page(self, request_info: RequestBody) -> Union[Tuple[BeautifulSoup, bool, int], Tuple[Dict, bool, int],
                                                           Tuple[None, None, None], Tuple[bytes, None, int]]:
        while True:
            for i in range(self.try_count):
                try:
                    response = self._send_request(request_info)
                    if response.status_code == 500:
                        logger.warning(f'500 response from site. Taking another attempt')
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f'Requests error: {e}')
                    continue

                is_captcha = False
                if request_info.parsing_type == 'bs':
                    bs, is_captcha = self._parse_to_bs(response, request_info)
                    return bs, is_captcha, response.status_code
                elif request_info.parsing_type == 'json':
                    try:
                        json_result = self._parse_to_json(response)
                        return json_result, is_captcha, response.status_code
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f'JSONDecoderError: {e.msg}')
                elif request_info.parsing_type == 'image':
                    return response.content, None, response.status_code
                else:
                    logger.warning('Unrecognized type of parsing')
            logger.error(f"All attempts to connect for {request_info.url[:120]} and {request_info.url[-10:]} "
                         f"have been used. Trying another {self.try_count} attempts")

    def _parse_to_bs(self, response: Response, request_info: RequestBody) -> (BeautifulSoup, bool):
        bs = BeautifulSoup(response.content, 'lxml')

        is_captcha = self.is_captcha_checker(bs)
        logger.error(f'Captcha is found in {request_info}') if is_captcha else None
        return bs, is_captcha

    @staticmethod
    def _parse_to_json(response: Response) -> Dict:
        try:
            return response.json()
        except json.JSONDecodeError as e:
            if e.msg.startswith('Unexpected UTF-8 BOM'):
                return json.loads(response.text.encode().decode('utf-8-sig'))
            else:
                raise e

    def _send_request(self, request_info: RequestBody) -> Response:
        proxies = self.pm.get_proxy() if self.use_proxy else None
        response = requests.request(request_info.method, request_info.url, headers=request_info.headers,
                                    proxies=proxies, params=request_info.params)
        return response
