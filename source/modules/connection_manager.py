from __future__ import annotations

import logging
import os
import re
import ssl
from typing import TYPE_CHECKING

import certifi
import truststore
from modules.platform_utils import get_platform, get_platform_full
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

# On Linux, truststore verifies with OpenSSL and looks for system CAs only at
# handshake time; it does not fail if none exist. Mirror its lookup so we can
# fall back to certifi up front. Keep in sync with truststore._openssl.
_SYSTEM_CA_FILE_CANDIDATES = (
    "/etc/ssl/cert.pem",
    "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",
    "/etc/pki/tls/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/ssl/ca-bundle.pem",
)
_HASHED_CERT_FILENAME_RE = re.compile(r"^[0-9a-fA-F]{8}\.[0-9]$")


def _has_system_ca_certs() -> bool:
    defaults = ssl.get_default_verify_paths()
    if defaults.cafile:
        return True
    if (
        defaults.capath
        and os.path.isdir(defaults.capath)
        and any(_HASHED_CERT_FILENAME_RE.match(name) for name in os.listdir(defaults.capath))
    ):
        return True
    return any(os.path.isfile(path) for path in _SYSTEM_CA_FILE_CANDIDATES)


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
        self._headers = {"user-agent": agent, "Accept-Encoding": "gzip, deflate"}
        logger.info(f"Connection Manager Header: {agent}")
        # Verify TLS with the OS trust store via truststore, so distrust and
        # revocation pushed by the OS (e.g. Windows' disallowed list) applies
        # without shipping a new release. Fall back to certifi's CA bundle on
        # Linux systems without CA certificates. certifi replaced the stale
        # bundled custom.pem that lacked ISRG Root X2. See #414.
        self.ssl_context = self._create_ssl_context()

        self.request_counter = 0

    @staticmethod
    def _create_ssl_context() -> ssl.SSLContext:
        if get_platform() == "Linux" and not _has_system_ca_certs():
            logger.warning("No system CA certificates found; falling back to certifi")
            return ssl.create_default_context(cafile=certifi.where())

        logger.info("TLS verification: OS trust store (truststore)")
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # type: ignore[return-value]

    def setup(self):
        if self.proxy_type == 0:  # Use generic requests
            if get_use_custom_tls_certificates():
                # Generic requests with CERT_REQUIRED
                self.manager = PoolManager(
                    num_pools=50,
                    maxsize=10,
                    headers=self._headers,
                    ssl_context=self.ssl_context,
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
                        ssl_context=self.ssl_context,
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
                        ssl_context=self.ssl_context,
                        proxy_ssl_context=self.ssl_context,
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

            response = self.manager.request(
                _method, _url, fields=fields, headers=merged_headers if merged_headers else None, **urlopen_kw
            )
            if response is not None and response.status == 401:
                logger.warning("Request returned a 401 response; your credentials are possibly expired!")

            return response

        except Exception:
            self.error.emit()
            return None
