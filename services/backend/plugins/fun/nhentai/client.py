import ssl
import httpx
from typing import Dict

# Constants for emulating a modern Firefox browser
HEADERS_FIREFOX_140 = (
    (
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
    ),
    (
        "Accept",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    ),
    ("Accept-Language", "en-US,en;q=0.5"),
    ("Accept-Encoding", "gzip, deflate, br"),
    ("Connection", "keep-alive"),
    ("Sec-Fetch-Dest", "document"),
    ("Sec-Fetch-Mode", "navigate"),
    ("Sec-Fetch-Site", "none"),
    ("Sec-Fetch-User", "?1"),
    ("Upgrade-Insecure-Requests", "1"),
    ("TE", "trailers"),
)

CIPHERS_FIREFOX = (
    "TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
)


def get_nhentai_client() -> httpx.AsyncClient:
    """
    Creates and returns an httpx.AsyncClient configured to mimic a modern
    Firefox browser with specific TLS 1.3 settings to bypass Cloudflare.
    """
    ssl_context = ssl.create_default_context()
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
    ssl_context.set_ciphers(CIPHERS_FIREFOX)

    headers: Dict[str, str] = {k: v for k, v in HEADERS_FIREFOX_140}

    return httpx.AsyncClient(
        headers=headers,
        verify=ssl_context,
        timeout=20.0,
        http2=True,
        follow_redirects=True,
    )
