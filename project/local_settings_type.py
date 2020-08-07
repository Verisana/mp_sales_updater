from dataclasses import dataclass
from typing import List


@dataclass
class LocalSettings:
    secret_key: str
    debug: bool
    allowed_hosts: List[str]
    internal_ips: List[str]
    time_zone: str

    db_name: str
    db_username: str
    db_password: str
    db_host: str
    db_port: str
    sentry_connection_info: str
    json_log_file: str
