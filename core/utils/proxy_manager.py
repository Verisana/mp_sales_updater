import random
from typing import Dict

import requests
from bs4 import BeautifulSoup
from core.types import RequestBody
from core.utils.logging_helpers import get_logger

logger = get_logger()


class ProxyManager:
    @staticmethod
    def _send_request(request_info: RequestBody) -> BeautifulSoup:
        bs = BeautifulSoup('', 'lxml')
        try:
            response = requests.request(request_info.method, request_info.url, headers=request_info.headers,
                                        params=request_info.params)
            response.raise_for_status()
            response = response.content
            bs = BeautifulSoup(response, 'lxml')
        except requests.exceptions.RequestException as e:
            logger.warning(f'Requests exception occurred while proxy getting: {e}')
        except Exception as e:
            logger.warning(f'Exception occurred while proxy getting: {e}')
        return bs

    def _get_from_free_proxy_list(self) -> Dict[str, str]:
        url = 'https://free-proxy-list.net/'
        proxies = {'http': '', 'https': ''}

        bs = self._send_request(RequestBody(url, method='get'))
        all_proxies = bs.find('tbody').findAll('tr')

        for proxy in all_proxies:
            all_columns = proxy.findAll('td')
            anonymity_level = all_columns[4].text
            is_https = True if all_columns[6].text == 'yes' else False

            if is_https and anonymity_level == 'elite proxy':
                ip, port = all_columns[0].text, all_columns[1].text
                proxies['http'] = ip + ':' + port
                proxies['https'] = ip + ':' + port
                break
        return proxies

    @staticmethod
    def _get_proxy_from_webshare():
        with open('core/utils/webshare_proxies.txt', 'r') as f:
            proxy_lines = f.readlines()

        proxies = []
        for proxy_line in proxy_lines:
            proxy, port, username, password = proxy_line.strip('\n').split(':')
            proxies.append({'http': f'http://{username}:{password}@{proxy}:{port}',
                            'https': f'https://{username}:{password}@{proxy}:{port}'})
        return random.choice(proxies)

    def get_proxy(self, proxy_source: str = 'webshare') -> Dict[str, str]:
        if proxy_source == 'webshare':
            return self._get_proxy_from_webshare()
