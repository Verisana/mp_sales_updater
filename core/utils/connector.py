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

    def get_page(self, request_info: RequestBody) -> Union[Tuple[BeautifulSoup, bool], Dict]:
        for i in range(self.try_count):
            response = self._send_request(request_info)
            if request_info.parsing_type == 'bs':
                bs, is_captcha = self._parse_to_bs(response, request_info)
                if bs.text:
                    return bs, is_captcha
            elif request_info.parsing_type == 'json':
                json_result = self._parse_to_json(response, request_info)
                if json_result:
                    return json_result
            else:
                print('Unrecognized type of parsing')
        print("All attempts to connect have been used")

    def _parse_to_bs(self, response: Response, request_info: RequestBody) -> (BeautifulSoup, bool):
        bs = BeautifulSoup('', 'lxml')
        response = response.content
        bs = BeautifulSoup(response, 'lxml')

        is_captcha = self.is_captcha_checker(bs)
        print(f'Captcha is found in {request_info}') if is_captcha else None
        return bs, is_captcha

    def _parse_to_json(self, response: Response, request_info: RequestBody) -> Dict:
        loaded = {}
        try:
            loaded = json.loads(response.text)
        except json.JSONDecodeError as e:
            print(f'JSONDecoderError occurred in request {request_info} result: {response.text}')
        except AttributeError as e:
            pass
        return loaded

    def _send_request(self, request_info: RequestBody) -> Response:
        proxies = self.pm.get_proxy() if self.use_proxy else None
        response = None
        try:
            response = requests.request(request_info.method, request_info.url, headers=request_info.headers,
                                        proxies=proxies, params=request_info.params)
            response.raise_for_status()
        except (requests.exceptions.BaseHTTPError, requests.exceptions.ProxyError) as e:
            print(f'Requests error: {e}')
        return response
