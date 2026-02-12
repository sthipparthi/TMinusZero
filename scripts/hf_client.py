"""Hugging Face API summarization client."""

import asyncio
from config import HF_API_URL, HF_TOKEN


def extract_summary_from_response(response_data):
    """Extract summary text from HF API response.

    Handles list[dict], dict, and str response formats.
    """
    if isinstance(response_data, list) and response_data and isinstance(response_data[0], dict):
        return response_data[0].get("summary_text") or response_data[0].get("generated_text") or ""
    if isinstance(response_data, dict):
        return response_data.get("summary_text") or response_data.get("generated_text") or ""
    if isinstance(response_data, str):
        return response_data
    return ""


async def call_hf_api(session, text, max_new_tokens=512, min_length=None, retries=1):
    """POST to HF inference API with optional retries and exponential backoff.

    Args:
        session: aiohttp ClientSession
        text: Input text to summarize
        max_new_tokens: Maximum tokens to generate
        min_length: Minimum summary length (optional)
        retries: Number of attempts (default=1 for single attempt)

    Returns:
        str: Summary text, or "" on failure
    """
    payload = {"inputs": text, "parameters": {"max_new_tokens": max_new_tokens}}
    if min_length is not None:
        payload["parameters"]["min_length"] = min_length

    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Accept": "application/json"}
    backoff = 2

    for attempt in range(1, retries + 1):
        try:
            async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return extract_summary_from_response(result)
                else:
                    text_resp = await resp.text()
                    print(f"HF API returned status {resp.status}, body: {text_resp}")
                    print(f"Using HF model endpoint: {HF_API_URL}")
                    if resp.status in (429, 503, 502, 500) and attempt < retries:
                        raise Exception(f"Retryable HF status: {resp.status}")
                    return ""
        except Exception as e:
            if attempt < retries:
                wait = backoff ** attempt
                print(f"HF call failed (attempt {attempt}) -> {e}. Backing off {wait}s")
                await asyncio.sleep(wait)
                continue
            else:
                if retries > 1:
                    print(f"HF call failed after {retries} attempts: {e}")
                else:
                    print(f"HF call failed: {e}")
                return ""
