import json
from typing import Union, Any, Dict, Tuple

import requests
from requests.models import Response
from bs4 import BeautifulSoup

from core.types import RequestBody
from core.utils.proxy_manager import ProxyManager


class Connector:
    """Here is we send all url requests in asynchronous way"""
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
                                                           Tuple[None, None, None]]:
        for i in range(self.try_count):
            try:
                response = self._send_request(request_info)
            except requests.exceptions.RequestException as e:
                print(f'Requests error: {e}')
                continue

            is_captcha = False
            if request_info.parsing_type == 'bs':
                bs, is_captcha = self._parse_to_bs(response, request_info)
                return bs, is_captcha, response.status_code
            elif request_info.parsing_type == 'json':
                try:
                    json_result = self._parse_to_json(response, request_info)
                    return json_result, is_captcha, response.status_code
                except json.JSONDecodeError as e:
                    print(f'JSONDecoderError: {e.msg} occurred in request {request_info} result: {response.text}')
            else:
                print('Unrecognized type of parsing')
        print("All attempts to connect have been used")
        return None, None, None

    def _parse_to_bs(self, response: Response, request_info: RequestBody) -> (BeautifulSoup, bool):
        bs = BeautifulSoup(response.content, 'lxml')

        is_captcha = self.is_captcha_checker(bs)
        print(f'Captcha is found in {request_info}') if is_captcha else None
        return bs, is_captcha

    @staticmethod
    def _parse_to_json(response: Response, request_info: RequestBody) -> Dict:
        return response.json()

    def _send_request(self, request_info: RequestBody) -> Response:
        proxies = self.pm.get_proxy() if self.use_proxy else None
        response = requests.request(request_info.method, request_info.url, headers=request_info.headers,
                                    proxies=proxies, params=request_info.params)
        return response
