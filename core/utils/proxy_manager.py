from typing import Dict


class ProxyManager:
    def __init__(self, *args):
        pass

    def get_proxy(self) -> Dict[str, str]:
        return {'http': 'http://', 'https': 'https://'}