from __future__ import annotations

import logging
import ssl
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from modules._platform import get_cwd, get_platform_full, is_frozen
from modules.settings import (
    get_github_token,
    get_proxy_host,
    get_proxy_password,
    get_proxy_port,
    get_proxy_type,
    get_proxy_user,
    get_use_custom_tls_certificates,
    get_user_id,
)
from PySide6.QtCore import QObject, Signal
from urllib3 import PoolManager, ProxyManager, make_headers
from urllib3.contrib.socks import SOCKSProxyManager

if TYPE_CHECKING:
    from semver import Version

logger = logging.getLogger()

proxy_types_chemes = {
    1: "http://",
    2: "https://",
    3: "socks4a://",
    4: "socks5h://",
}

REQUEST_MANAGER = PoolManager | ProxyManager | SOCKSProxyManager


# TODO
# It is impossible to kill existing instance of PoolManager
# and create a new one without restarting application


class ConnectionManager(QObject):
    error = Signal()

    def __init__(self, version: Version, proxy_type=None) -> None:
        super().__init__()
        self.version = version
        if proxy_type is None:
            proxy_type = get_proxy_type()
        self.proxy_type = proxy_type
        self.manager: REQUEST_MANAGER | None = None

        # Basic Headers
        agent = f"Blender-Launcher-v2/v.{self.version!s}/{get_platform_full()}/UserID-{get_user_id()}"
        self._headers = {"user-agent": agent}
        logger.info(f"Connection Manager Header: {agent}")
        # Get custom certificates file path
        if is_frozen() is True:
            self.cacert = (Path(getattr(sys, "_MEIPASS", "")) / "files" / "custom.pem").as_posix()
        else:
            self.cacert = (get_cwd() / "source/resources/certificates/custom.pem").as_posix()

        self.request_counter = 0

    def setup(self):
        if self.proxy_type == 0:  # Use generic requests
            if get_use_custom_tls_certificates():
                # Generic requests with CERT_REQUIRED
                self.manager = PoolManager(
                    num_pools=50,
                    maxsize=10,
                    headers=self._headers,
                    cert_reqs=ssl.CERT_REQUIRED,
                    ca_certs=self.cacert,
                )
            else:
                # Generic requests w/o CERT_REQUIRED
                self.manager = PoolManager(num_pools=50, maxsize=10, headers=self._headers)
        else:  # Use Proxy
            ip = get_proxy_host()
            port = get_proxy_port()
            scheme = proxy_types_chemes[self.proxy_type]

            if self.proxy_type > 2:  # Use SOCKS Proxy
                if get_use_custom_tls_certificates():
                    # SOCKS Proxy with CERT_REQUIRED
                    self.manager = SOCKSProxyManager(
                        proxy_url=f"{scheme}{ip}:{port}",
                        num_pools=50,
                        maxsize=10,
                        headers=self._headers,
                        username=get_proxy_user(),
                        password=get_proxy_password(),
                        cert_reqs=ssl.CERT_REQUIRED,
                        ca_certs=self.cacert,
                    )
                else:
                    # SOCKS Proxy w/o CERT_REQUIRED
                    self.manager = SOCKSProxyManager(
                        proxy_url=f"{scheme}{ip}:{port}",
                        num_pools=50,
                        maxsize=10,
                        headers=self._headers,
                        username=get_proxy_user(),
                        password=get_proxy_password(),
                    )
            else:  # Use HTTP Proxy
                # HTTP Proxy autherification headers
                auth_headers = make_headers(proxy_basic_auth=f"{get_proxy_user()}:{get_proxy_password()}")

                if get_use_custom_tls_certificates():
                    # HTTP Proxy with CERT_REQUIRED
                    self.manager = ProxyManager(
                        proxy_url=f"{scheme}{ip}:{port}",
                        num_pools=50,
                        maxsize=10,
                        headers=self._headers,
                        proxy_headers=auth_headers,
                        cert_reqs=ssl.CERT_REQUIRED,
                        ca_certs=self.cacert,
                    )
                else:
                    # HTTP Proxy w/o CERT_REQUIRED
                    self.manager = ProxyManager(
                        proxy_url=f"{scheme}{ip}:{port}",
                        num_pools=50,
                        maxsize=10,
                        headers=self._headers,
                        proxy_headers=auth_headers,
                    )

    def request(self, _method, _url, fields=None, headers=None, **urlopen_kw):
        try:
            assert self.manager is not None

            """
            Counter for request. Not supposed to exceed 7 requests
            4 requests for Blender Builder
            1 requests for Blender Download
            3 requests for GitHub
            """
            self.request_counter += 1
            logger.debug(f"Request Counter: {self.request_counter}")

            merged_headers = headers.copy() if headers else {}

            # Add GitHub token to headers if the request is to GitHub API and token is set
            if "api.github.com" in _url:
                github_token = get_github_token()
                if github_token:
                    merged_headers["Authorization"] = f"token {github_token}"
                    logger.debug(f"GitHub API request to: {_url} (with authentication)")
                else:
                    logger.debug(f"GitHub API request to: {_url} (no token configured)")

            return self.manager.request(
                _method, _url, fields=fields, headers=merged_headers if merged_headers else None, **urlopen_kw
            )
        except Exception:
            self.error.emit()
            return None
