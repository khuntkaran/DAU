"""The LLM gateway, rate limiter and provider adapters. No test reaches a real provider."""

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from api.app.config import Settings
from api.app.enums import JobPriority
from api.app.llm.base import Capability, Image, Part, ProviderError, Reply, Text
from api.app.llm.gateway import (
    BREAKER_THRESHOLD,
    AiUnavailable,
    Gateway,
    build_gateway,
)
from api.app.llm.providers.fake import FakeProvider
from api.app.llm.providers.gemini import GeminiProvider
from api.app.llm.providers.groq import GroqProvider
from api.app.llm.ratelimit import HIGH_SHARE, RateLimiter

HIGH, LOW = JobPriority.HIGH, JobPriority.LOW


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fraction: float


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class Scripted:
    """A provider that plays back replies or errors in order."""

    def __init__(self, name: str, replies: list[str | ProviderError], vision: bool = True):
        self.name = name
        self.replies = list(replies)
        self.vision = vision
        self.calls = 0

    def model_for(self, capability: Capability) -> str | None:
        return None if capability == "vision" and not self.vision else f"{self.name}-model"

    def generate(self, **_: Any) -> Reply:
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, ProviderError):
            raise reply
        return Reply(reply, 10, 5)

    def transcribe(self, **_: Any) -> Reply:
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, ProviderError):
            raise reply
        return Reply(reply)


def _gateway(*providers: Any, limiter: RateLimiter | None = None) -> tuple[Gateway, Clock]:
    clock = Clock()
    gateway = Gateway(
        list(providers),
        limiter or RateLimiter({}),
        clock=clock,
        sleep=clock.sleep,
        jitter=lambda: 0.0,
    )
    return gateway, clock


def _ask(gateway: Gateway, vision: bool = False) -> Any:
    return gateway.generate(
        task="t", system="s", parts=[Text("x")], schema=Answer, priority=HIGH, vision=vision
    )


OK = json.dumps({"fraction": 0.7})


# --- Rate limiter ---------------------------------------------------------------------------


def test_the_bucket_allows_the_per_minute_limit_then_waits() -> None:
    clock = Clock()
    limiter = RateLimiter({"gemini": 6}, clock=clock, sleep=clock.sleep)

    assert all(limiter.acquire("gemini", "m", HIGH, timeout=0) for _ in range(6))
    assert not limiter.acquire("gemini", "m", HIGH, timeout=0)
    assert limiter.acquire("gemini", "m", HIGH, timeout=60)
    assert clock.slept == [pytest.approx(10.0)]


def test_background_work_leaves_room_for_people_who_are_waiting() -> None:
    clock = Clock()
    limiter = RateLimiter({"gemini": 10}, clock=clock, sleep=clock.sleep)

    low = sum(limiter.acquire("gemini", "m", LOW, timeout=0) for _ in range(10))
    high = sum(limiter.acquire("gemini", "m", HIGH, timeout=0) for _ in range(10))

    assert low == round(10 * (1 - HIGH_SHARE))
    assert low + high == 10


def test_models_have_separate_buckets() -> None:
    limiter = RateLimiter({"groq": 1}, clock=Clock())
    assert limiter.acquire("groq", "llama", HIGH, timeout=0)
    assert limiter.acquire("groq", "whisper", HIGH, timeout=0)


def test_no_configured_limit_means_no_waiting() -> None:
    limiter = RateLimiter({"gemini": None})
    assert all(limiter.acquire("gemini", "m", LOW, timeout=0) for _ in range(100))


# --- Gateway --------------------------------------------------------------------------------


def test_a_valid_answer_is_parsed_into_the_schema() -> None:
    gateway, _ = _gateway(Scripted("gemini", [OK]))

    result = _ask(gateway)

    assert result.output == Answer(fraction=0.7)
    assert (result.provider, result.model, result.tokens_in) == ("gemini", "gemini-model", 10)


@pytest.mark.parametrize(
    "bad", ["not json", json.dumps({"fraction": 0.7, "rank_first": True}), json.dumps({})]
)
def test_bad_output_is_retried_once(bad: str) -> None:
    provider = Scripted("gemini", [bad, OK])
    gateway, _ = _gateway(provider)

    assert _ask(gateway).output.fraction == 0.7
    assert provider.calls == 2


def test_bad_output_twice_gives_up_on_that_provider() -> None:
    gateway, _ = _gateway(Scripted("gemini", ["nope", "nope", OK]))

    with pytest.raises(AiUnavailable):
        _ask(gateway)


def test_rate_limits_back_off_with_growing_waits() -> None:
    limited = ProviderError("429", rate_limited=True)
    gateway, clock = _gateway(Scripted("gemini", [limited, limited, OK]))

    assert _ask(gateway).provider == "gemini"
    assert clock.slept == [1.0, 2.0]


def test_text_falls_back_to_the_next_provider() -> None:
    down = ProviderError("500")
    gemini = Scripted("gemini", [down, down, down])
    groq = Scripted("groq", [OK], vision=False)
    gateway, _ = _gateway(gemini, groq)

    assert _ask(gateway).provider == "groq"


def test_vision_never_falls_back_to_a_text_only_provider() -> None:
    gemini = Scripted("gemini", [ProviderError("bad request", retryable=False)])
    groq = Scripted("groq", [OK], vision=False)
    gateway, _ = _gateway(gemini, groq)

    with pytest.raises(AiUnavailable):
        _ask(gateway, vision=True)
    assert groq.calls == 0


def test_a_failing_provider_is_rested_after_repeated_failures() -> None:
    down = ProviderError("500")
    gemini = Scripted("gemini", [down] * BREAKER_THRESHOLD)
    groq = Scripted("groq", [OK] * 4, vision=False)
    gateway, clock = _gateway(gemini, groq)

    for _ in range(3):
        _ask(gateway)
    assert gemini.calls == BREAKER_THRESHOLD

    _ask(gateway)
    assert gemini.calls == BREAKER_THRESHOLD

    clock.now += 61
    gemini.replies = [OK]
    assert _ask(gateway).provider == "gemini"


def test_no_configured_provider_is_reported_as_unavailable() -> None:
    gateway, _ = _gateway(Scripted("groq", [], vision=False))
    with pytest.raises(AiUnavailable, match="configured"):
        _ask(gateway, vision=True)


def test_output_schemas_must_forbid_extra_keys() -> None:
    class Loose(BaseModel):
        fraction: float

    gateway, _ = _gateway(Scripted("gemini", [OK]))
    with pytest.raises(TypeError, match="forbid"):
        gateway.generate(task="t", system="s", parts=[], schema=Loose, priority=HIGH)


def test_a_slot_that_never_frees_moves_on_to_the_next_provider() -> None:
    clock = Clock()
    limiter = RateLimiter({"gemini": 1}, clock=clock, sleep=clock.sleep)
    limiter.acquire("gemini", "gemini-model", HIGH, timeout=0)
    gateway = Gateway(
        [Scripted("gemini", [OK]), Scripted("groq", [OK], vision=False)],
        limiter,
        max_wait_s=1,
        clock=clock,
        sleep=clock.sleep,
    )

    assert _ask(gateway).provider == "groq"


def test_transcription_uses_the_speech_provider() -> None:
    whisper = Scripted("groq", [ProviderError("429", rate_limited=True), "namaste"])
    gateway, _ = _gateway(whisper)

    result = gateway.transcribe(audio=b"x", mime_type="audio/webm", language="hi", priority=HIGH)
    assert (result.text, result.provider) == ("namaste", "groq")


def test_transcription_without_a_speech_provider_is_unavailable() -> None:
    class NoSpeech(Scripted):
        def model_for(self, capability: Capability) -> str | None:
            return None if capability == "speech" else "m"

    gateway, _ = _gateway(NoSpeech("gemini", []))
    with pytest.raises(AiUnavailable):
        gateway.transcribe(audio=b"x", mime_type="audio/webm", language=None, priority=HIGH)


# --- Wiring ---------------------------------------------------------------------------------


def test_fake_mode_uses_only_the_fake_provider() -> None:
    gateway = build_gateway(Settings(ai_provider="fake", gemini_api_key="k", groq_api_key="k"))
    assert [p.name for p in gateway.providers] == ["fake"]


def test_providers_without_keys_or_models_are_skipped() -> None:
    settings = Settings(
        ai_provider="gemini",
        gemini_api_key=None,
        gemini_model="g",
        groq_api_key="k",
        groq_text_model=None,
        groq_whisper_model="w",
    )
    gateway = build_gateway(settings)

    assert [p.name for p in gateway.providers] == ["gemini", "gemini_fallback", "groq"]
    assert [p.model_for("text") for p in gateway.providers] == [None, None, None]
    assert gateway.providers[2].model_for("speech") == "w"


def test_the_fake_provider_plays_registered_scripts() -> None:
    fake = FakeProvider({"t": lambda parts: {"fraction": 0.5}})
    gateway, _ = _gateway(fake)

    assert _ask(gateway).output.fraction == 0.5
    assert fake.calls == ["t"]


# --- Provider adapters, with stand-in SDK clients -------------------------------------------


def _ns(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def test_gemini_sends_text_images_and_the_schema() -> None:
    seen: dict[str, Any] = {}

    def generate_content(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _ns(text=OK, usage_metadata=_ns(prompt_token_count=12, candidates_token_count=4))

    client = _ns(models=_ns(generate_content=generate_content))
    gemini = GeminiProvider("key", "gemini-x", client=client)
    parts: list[Part] = [Text("roof"), Image(b"\xff\xd8", "image/jpeg")]

    reply = gemini.generate(task="t", model="gemini-x", system="sys", parts=parts, schema={"a": 1})

    assert reply == Reply(OK, 12, 4)
    assert seen["model"] == "gemini-x"
    assert len(seen["contents"]) == 2
    assert seen["config"].response_mime_type == "application/json"
    assert seen["config"].response_json_schema == {"a": 1}
    assert seen["config"].system_instruction == "sys"
    assert gemini.model_for("speech") is None


def test_gemini_429_is_marked_as_rate_limited() -> None:
    from google.genai import errors

    def generate_content(**_: Any) -> Any:
        raise errors.APIError(429, {"error": {"message": "quota"}})

    gemini = GeminiProvider("key", "g", client=_ns(models=_ns(generate_content=generate_content)))
    with pytest.raises(ProviderError) as caught:
        gemini.generate(task="t", model="g", system="s", parts=[], schema={})
    assert caught.value.rate_limited


def test_groq_puts_the_schema_in_the_prompt_and_asks_for_json() -> None:
    seen: dict[str, Any] = {}

    def create(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _ns(
            choices=[_ns(message=_ns(content=OK))],
            usage=_ns(prompt_tokens=20, completion_tokens=6),
        )

    client = _ns(chat=_ns(completions=_ns(create=create)))
    provider = GroqProvider("key", "llama", "whisper", client=client)

    reply = provider.generate(
        task="t", model="llama", system="sys", parts=[Text("q")], schema={"b": 2}
    )

    assert reply == Reply(OK, 20, 6)
    assert seen["response_format"] == {"type": "json_object"}
    assert '{"b": 2}' in seen["messages"][0]["content"]
    assert seen["messages"][1] == {"role": "user", "content": "q"}


def test_groq_refuses_images() -> None:
    provider = GroqProvider("key", "llama", "whisper", client=_ns())
    with pytest.raises(ProviderError) as caught:
        provider.generate(
            task="t", model="llama", system="s", parts=[Image(b"x", "image/png")], schema={}
        )
    assert not caught.value.retryable


def test_groq_transcribes_with_the_language_hint() -> None:
    seen: dict[str, Any] = {}

    def create(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _ns(text="namaste")

    client = _ns(audio=_ns(transcriptions=_ns(create=create)))
    provider = GroqProvider("key", None, "whisper", client=client)

    reply = provider.transcribe(model="whisper", audio=b"ogg", mime_type="audio/ogg", language="gu")

    assert reply.text == "namaste"
    assert (seen["language"], seen["file"]) == ("gu", ("voice.ogg", b"ogg"))


def test_groq_rate_limits_and_outages_are_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    import groq

    class Limited(groq.RateLimitError):
        def __init__(self) -> None:
            Exception.__init__(self, "429")

    class Down(groq.APIStatusError):
        def __init__(self, status: int) -> None:
            Exception.__init__(self, str(status))
            self.status_code = status

    def raising(exc: Exception) -> Callable[..., Any]:
        def create(**_: Any) -> Any:
            raise exc

        return create

    cases = [(Limited(), True, True), (Down(503), False, True), (Down(400), False, False)]
    for exc, limited, retryable in cases:
        client = _ns(chat=_ns(completions=_ns(create=raising(exc))))
        provider = GroqProvider("key", "llama", None, client=client)
        with pytest.raises(ProviderError) as caught:
            provider.generate(task="t", model="llama", system="s", parts=[], schema={})
        assert (caught.value.rate_limited, caught.value.retryable) == (limited, retryable)


def test_sdk_clients_get_a_timeout_and_no_retries_of_their_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import groq
    from google import genai

    seen: dict[str, Any] = {}
    monkeypatch.setattr(genai, "Client", lambda **kw: seen.setdefault("gemini", kw))
    monkeypatch.setattr(groq, "Groq", lambda **kw: seen.setdefault("groq", kw))

    _ = GeminiProvider("key", "g", timeout_s=12).client
    _ = GroqProvider("key", "t", "w", timeout_s=12).client

    gemini = seen["gemini"]["http_options"]
    assert (gemini.timeout, gemini.retry_options.attempts) == (12000, 1)
    assert (seen["groq"]["timeout"], seen["groq"]["max_retries"]) == (12, 0)


def test_an_overloaded_main_model_falls_back_to_the_lighter_one_for_photos() -> None:
    overloaded = ProviderError("503")
    main = Scripted("gemini", [overloaded] * 3)
    lite = Scripted("gemini_fallback", [OK])
    text_only = Scripted("groq", [OK], vision=False)
    gateway, _ = _gateway(main, lite, text_only)

    result = _ask(gateway, vision=True)

    assert result.provider == "gemini_fallback"
    assert text_only.calls == 0


def test_the_fallback_model_is_configured_from_env() -> None:
    settings = Settings(
        ai_provider="gemini",
        gemini_api_key="k",
        gemini_model="big",
        gemini_fallback_model="lite",
        groq_api_key=None,
    )
    gateway = build_gateway(settings)

    assert [(p.name, p.model_for("vision")) for p in gateway.providers] == [
        ("gemini", "big"),
        ("gemini_fallback", "lite"),
        ("groq", None),
    ]


def test_an_overloaded_model_gets_one_retry_before_moving_on() -> None:
    gemini = Scripted("gemini", [ProviderError("503")] * 3)
    groq = Scripted("groq", [OK], vision=False)
    gateway, clock = _gateway(gemini, groq)

    assert _ask(gateway).provider == "groq"
    assert gemini.calls == 2
    assert clock.slept == [1.0]


def test_a_waiting_person_gets_the_fast_text_provider_first() -> None:
    gemini = Scripted("gemini", [OK])
    groq = Scripted("groq", [OK], vision=False)
    gateway, _ = _gateway(gemini, groq)

    result = gateway.generate(
        task="t", system="s", parts=[Text("x")], schema=Answer, priority=HIGH, prefer_fast=True
    )

    assert result.provider == "groq"
    assert gemini.calls == 0


def test_preferring_fast_never_sends_photos_to_a_text_model() -> None:
    gemini = Scripted("gemini", [OK])
    groq = Scripted("groq", [OK], vision=False)
    gateway, _ = _gateway(gemini, groq)

    result = gateway.generate(
        task="t", system="s", parts=[], schema=Answer, priority=HIGH, vision=True, prefer_fast=True
    )
    assert result.provider == "gemini"
