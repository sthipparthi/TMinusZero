"""Shared configuration for space-news scripts."""

import os
import aiohttp

HF_MODEL = os.getenv("HF_MODEL", "facebook/bart-large-cnn")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"


def request_timeout(total=60, connect=None, sock_read=None):
    """Create an aiohttp ClientTimeout with the given parameters."""
    return aiohttp.ClientTimeout(total=total, connect=connect, sock_read=sock_read)
