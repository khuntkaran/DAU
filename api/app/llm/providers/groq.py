"""Groq: Whisper for speech, and Llama as the text fallback. Only the gateway calls this."""

import json
from typing import Any

import groq

from api.app.llm.base import Capability, Part, ProviderError, Reply, Text

_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/mp4": "m4a",
}


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        api_key: str | None,
        text_model: str | None,
        whisper_model: str | None,
        timeout_s: float = 30.0,
        client: Any = None,
    ) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._models: dict[Capability, str | None] = {
            "text": text_model,
            "speech": whisper_model,
            "vision": None,
        }
        self._client = client

    def model_for(self, capability: Capability) -> str | None:
        return self._models[capability] if (self._api_key or self._client) else None

    @property
    def client(self) -> Any:
        if self._client is None:
            # One attempt per call: the gateway owns retries, backoff and fallback.
            self._client = groq.Groq(api_key=self._api_key, timeout=self._timeout_s, max_retries=0)
        return self._client

    def _call(self, fn: Any, **kwargs: Any) -> Any:
        try:
            return fn(**kwargs)
        except groq.RateLimitError:
            raise ProviderError("groq 429", rate_limited=True) from None
        except groq.APIStatusError as exc:
            status = exc.status_code
            raise ProviderError(f"groq {status}", retryable=status >= 500) from None
        except (groq.APIConnectionError, groq.APITimeoutError):
            raise ProviderError("groq unreachable") from None

    def generate(
        self, *, task: str, model: str, system: str, parts: list[Part], schema: dict[str, Any]
    ) -> Reply:
        if any(not isinstance(p, Text) for p in parts):
            raise ProviderError("groq text models do not take images", retryable=False)
        # Groq's JSON mode does not take a schema, so it goes in the system prompt instead.
        instructions = f"{system}\n\nReply with one JSON object matching this schema:\n"
        response = self._call(
            self.client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": instructions + json.dumps(schema)},
                {
                    "role": "user",
                    "content": "\n\n".join(p.text for p in parts if isinstance(p, Text)),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        usage = response.usage
        return Reply(
            text=response.choices[0].message.content or "",
            tokens_in=usage.prompt_tokens if usage else None,
            tokens_out=usage.completion_tokens if usage else None,
        )

    def transcribe(
        self, *, model: str, audio: bytes, mime_type: str, language: str | None
    ) -> Reply:
        extension = _EXTENSIONS.get(mime_type, "webm")
        kwargs: dict[str, Any] = {
            "file": (f"voice.{extension}", audio),
            "model": model,
            "response_format": "json",
            "temperature": 0,
        }
        if language:
            kwargs["language"] = language
        response = self._call(self.client.audio.transcriptions.create, **kwargs)
        return Reply(text=response.text)
