import requests
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

    def get_page(self, request_info: RequestBody) -> (BeautifulSoup, bool):
        for i in range(self.try_count):
            bs, is_captcha = self._send_request(request_info)
            if bs.text:
                return bs, is_captcha
        print("All attempts to connect have been used")
        return BeautifulSoup('', 'lxml'), False

    def _send_request(self, request_info: RequestBody) -> (BeautifulSoup, bool):
        proxies = self.pm.get_proxy() if self.use_proxy else None

        bs = BeautifulSoup('', 'lxml')
        try:
            response = requests.request(request_info.method, request_info.url, headers=request_info.headers,
                                        proxies=proxies, params=request_info.params)
            response.raise_for_status()
            response = response.content
            bs = BeautifulSoup(response, 'lxml')
        except requests.exceptions.BaseHTTPError as e:
            print(f'Requests error: {e}')
        except Exception as e:
            print(f'Exception error occurred: {e}')

        is_captcha = self.is_captcha_checker(bs)
        print(f'Captcha is found in {request_info}') if is_captcha else None
        return bs, is_captcha
