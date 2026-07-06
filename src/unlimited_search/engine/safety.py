from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

DEFAULT_MAX_REDIRECTS = 5


def _is_blocked_ip(raw_host: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw_host.strip("[]"))
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def classify_url(url: str, *, allow_private: bool = False, resolve_dns: bool = True) -> tuple[bool, str]:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        return False, "unsupported_scheme"
    if not parts.hostname:
        return False, "missing_host"
    if parts.username or parts.password:
        return False, "embedded_credentials"
    host = parts.hostname
    if not allow_private and _is_blocked_ip(host):
        return False, "private_ip"
    if resolve_dns and not allow_private and not _is_ip_literal(host):
        try:
            infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
        except socket.gaierror:
            return False, "dns_failed"
        for info in infos:
            sockaddr = info[4]
            if sockaddr and _is_blocked_ip(str(sockaddr[0])):
                return False, "private_dns_target"
    return True, "ok"


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


def resolve_redirect(base_url: str, location: str) -> str:
    return urljoin(base_url, location)

