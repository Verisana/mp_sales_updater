import requests
from bs4 import BeautifulSoup

from core.types import RequestBody


class Connector:
    """Here is we send all url requests in asynchronous way"""
    def __init__(self):
        pass

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

    def send_request(self, request_info: RequestBody) -> (BeautifulSoup, bool):
        bs = BeautifulSoup('', 'lxml')
        try:
            response = requests.request(request_info.method, request_info.url, headers=request_info.headers,
                                        proxies=request_info.proxies, params=request_info.params)
            response.raise_for_status()
            response = response.content
            bs = BeautifulSoup(response, 'lxml')
        except requests.exceptions.BaseHTTPError as e:
            print(f'Requests error: {e}')
        except Exception as e:
            print(f'Exception error occurred: {e}')

        return bs, self.is_captcha_checker(bs)
