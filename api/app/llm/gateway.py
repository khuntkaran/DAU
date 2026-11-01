"""The only code that talks to Gemini or Groq.

It picks a provider, waits for a rate-limit slot, asks for JSON, validates it against a strict
schema, retries once on bad output, backs off on 429, falls back from Gemini to Groq for text,
and stops calling a provider for a minute after five failures in a row. When nothing works it
raises `AiUnavailable`; callers show calculated numbers without the AI part.
"""

import logging
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from api.app.config import Settings, get_settings
from api.app.enums import JobPriority
from api.app.llm.base import Capability, Part, Provider, ProviderError
from api.app.llm.providers.fake import FakeProvider
from api.app.llm.providers.gemini import GeminiProvider
from api.app.llm.providers.groq import GroqProvider
from api.app.llm.ratelimit import RateLimiter

logger = logging.getLogger("suryasetu.llm")

T = TypeVar("T", bound=BaseModel)

ATTEMPTS_PER_PROVIDER = 3
# A 429 clears in seconds, so it is retried. A 5xx or timeout means the model is struggling:
# one more try, then the next provider, so a household is not left waiting on an overload.
SERVER_ERROR_TRIES = 2
BREAKER_THRESHOLD = 5
BREAKER_COOLDOWN_S = 60.0
BACKOFF_BASE_S = 1.0
BACKOFF_CAP_S = 8.0
# Providers that answer short text tasks in well under a second. When a person is waiting on
# a text-only task, these are tried first.
FAST_TEXT_PROVIDERS = ("groq",)


class AiUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Result(Generic[T]):
    output: T
    provider: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int


@dataclass(frozen=True)
class Transcription:
    text: str
    provider: str
    model: str
    latency_ms: int


class Gateway:
    def __init__(
        self,
        providers: list[Provider],
        limiter: RateLimiter,
        *,
        max_wait_s: float = 20.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self.providers = providers
        self._limiter = limiter
        self._max_wait_s = max_wait_s
        self._clock = clock
        self._sleep = sleep
        self._jitter = jitter
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}
        self._lock = threading.Lock()

    # --- Circuit breaker --------------------------------------------------------------------

    def _usable(self, provider: Provider) -> bool:
        with self._lock:
            return self._open_until.get(provider.name, 0.0) <= self._clock()

    def _failed(self, provider: Provider) -> None:
        with self._lock:
            count = self._failures.get(provider.name, 0) + 1
            self._failures[provider.name] = count
            if count >= BREAKER_THRESHOLD:
                self._open_until[provider.name] = self._clock() + BREAKER_COOLDOWN_S
                self._failures[provider.name] = 0
                logger.warning("llm breaker open provider=%s", provider.name)

    def _succeeded(self, provider: Provider) -> None:
        with self._lock:
            self._failures[provider.name] = 0

    def _backoff(self, attempt: int) -> None:
        self._sleep(min(BACKOFF_BASE_S * 2**attempt, BACKOFF_CAP_S) + self._jitter() / 2)

    def _candidates(self, capability: Capability) -> list[tuple[Provider, str]]:
        found = []
        for provider in self.providers:
            model = provider.model_for(capability)
            if model:
                found.append((provider, model))
        return found

    # --- Calls ------------------------------------------------------------------------------

    def generate(
        self,
        *,
        task: str,
        system: str,
        parts: list[Part],
        schema: type[T],
        priority: JobPriority,
        vision: bool = False,
        prefer_fast: bool = False,
    ) -> Result[T]:
        """Structured output from the first provider that gives valid JSON for `schema`."""
        if schema.model_config.get("extra") != "forbid":
            raise TypeError(f"{schema.__name__} must forbid extra keys")
        json_schema = schema.model_json_schema()
        candidates = self._candidates("vision" if vision else "text")
        if prefer_fast and not vision:
            candidates.sort(key=lambda c: c[0].name not in FAST_TEXT_PROVIDERS)
        if not candidates:
            raise AiUnavailable("no AI provider is configured for this task")

        for provider, model in candidates:
            if not self._usable(provider):
                continue
            invalid = server_errors = 0
            for attempt in range(ATTEMPTS_PER_PROVIDER):
                if not self._limiter.acquire(provider.name, model, priority, self._max_wait_s):
                    break
                started = self._clock()
                try:
                    reply = provider.generate(
                        task=task, model=model, system=system, parts=parts, schema=json_schema
                    )
                except ProviderError as exc:
                    self._failed(provider)
                    logger.warning("llm error provider=%s task=%s %s", provider.name, task, exc)
                    # A breaker that just opened means this provider is resting: move on.
                    server_errors += 0 if exc.rate_limited else 1
                    if not exc.retryable or not self._usable(provider):
                        break
                    if server_errors >= SERVER_ERROR_TRIES:
                        break
                    self._backoff(attempt)
                    continue
                latency_ms = int((self._clock() - started) * 1000)
                try:
                    output = schema.model_validate_json(reply.text)
                except ValidationError:
                    invalid += 1
                    logger.warning("llm invalid output provider=%s task=%s", provider.name, task)
                    if invalid > 1:
                        self._failed(provider)
                        break
                    continue
                self._succeeded(provider)
                logger.info(
                    "llm ok provider=%s model=%s task=%s ms=%s in=%s out=%s",
                    provider.name,
                    model,
                    task,
                    latency_ms,
                    reply.tokens_in,
                    reply.tokens_out,
                )
                return Result(
                    output, provider.name, model, reply.tokens_in, reply.tokens_out, latency_ms
                )
        raise AiUnavailable(f"no provider gave a valid answer for {task}")

    def transcribe(
        self, *, audio: bytes, mime_type: str, language: str | None, priority: JobPriority
    ) -> Transcription:
        for provider, model in self._candidates("speech"):
            if not self._usable(provider):
                continue
            server_errors = 0
            for attempt in range(ATTEMPTS_PER_PROVIDER):
                if not self._limiter.acquire(provider.name, model, priority, self._max_wait_s):
                    break
                started = self._clock()
                try:
                    reply = provider.transcribe(
                        model=model, audio=audio, mime_type=mime_type, language=language
                    )
                except ProviderError as exc:
                    self._failed(provider)
                    server_errors += 0 if exc.rate_limited else 1
                    if not exc.retryable or not self._usable(provider):
                        break
                    if server_errors >= SERVER_ERROR_TRIES:
                        break
                    self._backoff(attempt)
                    continue
                self._succeeded(provider)
                latency_ms = int((self._clock() - started) * 1000)
                logger.info(
                    "llm ok provider=%s model=%s task=transcribe ms=%s",
                    provider.name,
                    model,
                    latency_ms,
                )
                return Transcription(reply.text, provider.name, model, latency_ms)
        raise AiUnavailable("speech recognition is unavailable")


def build_gateway(settings: Settings) -> Gateway:
    limiter = RateLimiter(
        {
            "gemini": settings.gemini_rpm_limit,
            "gemini_fallback": settings.gemini_rpm_limit,
            "groq": settings.groq_rpm_limit,
        }
    )
    providers: list[Provider]
    if settings.ai_provider == "fake":
        providers = [FakeProvider()]
    else:
        timeout = settings.llm_timeout_s
        gemini = GeminiProvider(settings.gemini_api_key, settings.gemini_model, timeout)
        # Its own name, so its breaker stays closed while the main model is overloaded.
        lite = GeminiProvider(
            settings.gemini_api_key,
            settings.gemini_fallback_model,
            timeout,
            name="gemini_fallback",
        )
        groq = GroqProvider(
            settings.groq_api_key,
            settings.groq_text_model,
            settings.groq_whisper_model,
            timeout,
        )
        # The preferred provider goes first. The lighter Gemini covers overload spikes, and
        # Groq covers text when Gemini is down altogether.
        providers = (
            [gemini, lite, groq] if settings.ai_provider == "gemini" else [groq, gemini, lite]
        )
    return Gateway(providers, limiter, max_wait_s=settings.llm_max_wait_s)


@lru_cache
def get_gateway() -> Gateway:
    # One per process, so the rate limits and the breaker are shared by every request.
    return build_gateway(get_settings())
