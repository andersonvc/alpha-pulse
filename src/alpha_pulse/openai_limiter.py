# openai_limiter.py

import asyncio
import time
from aiolimiter import AsyncLimiter
import tenacity
import openai  # Or openai.error.RateLimitError if you want specific error classes

# --- Config ---
REQUESTS_PER_MIN = 60
TOKENS_PER_MIN = 200_000

_request_limiter = AsyncLimiter(REQUESTS_PER_MIN, 60)
_current_tokens = 0
_reset_time = time.time() + 60
_token_lock = asyncio.Lock()

def estimate_tokens(text_or_tokens: str | int) -> int:
    if isinstance(text_or_tokens, int):
        return text_or_tokens
    return max(1, len(text_or_tokens) // 4)

async def _wait_for_token_budget(tokens_needed: int):
    global _current_tokens, _reset_time
    async with _token_lock:
        now = time.time()
        if now >= _reset_time:
            _current_tokens = 0
            _reset_time = now + 60

        if _current_tokens + tokens_needed > TOKENS_PER_MIN:
            wait_time = _reset_time - now
            print(f"[Limiter] Sleeping {wait_time:.2f}s to respect token limit...")
            await asyncio.sleep(wait_time)
            _current_tokens = 0
            _reset_time = time.time() + 60
        
        _current_tokens += tokens_needed

class OpenAIAsyncLimiter:
    def __init__(self, tokens_needed: int):
        self.tokens_needed = tokens_needed

    async def __aenter__(self):
        await _request_limiter.acquire()
        await _wait_for_token_budget(self.tokens_needed)

    async def __aexit__(self, exc_type, exc_val, tb):
        pass

def get_openai_limiter(text_or_tokens: str | int) -> OpenAIAsyncLimiter:
    tokens = estimate_tokens(text_or_tokens)
    return OpenAIAsyncLimiter(tokens)

# --- Retry Decorator for OpenAI ---
retry_openai = tenacity.retry(
    retry=tenacity.retry_if_exception_type((openai.RateLimitError, openai.APIError)),
    wait=tenacity.wait_exponential(multiplier=0.5, max=30),
    stop=tenacity.stop_after_attempt(5),
    reraise=True,
)
