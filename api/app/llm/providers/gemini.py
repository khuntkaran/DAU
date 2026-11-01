"""Gemini, for vision and reasoning. Only the gateway calls this."""

from typing import Any

from google import genai
from google.genai import errors, types

from api.app.llm.base import Capability, Image, Part, ProviderError, Reply, Text


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        timeout_s: float = 30.0,
        client: Any = None,
        name: str = "gemini",
    ) -> None:
        self.name = name
        self._model = model
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._client = client

    def model_for(self, capability: Capability) -> str | None:
        if capability == "speech" or not self._model:
            return None
        return self._model if (self._api_key or self._client) else None

    @property
    def client(self) -> Any:
        if self._client is None:
            # One attempt per call: the gateway owns retries, backoff and fallback.
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(
                    timeout=int(self._timeout_s * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        return self._client

    def generate(
        self, *, task: str, model: str, system: str, parts: list[Part], schema: dict[str, Any]
    ) -> Reply:
        contents = [
            types.Part.from_text(text=p.text)
            if isinstance(p, Text)
            else types.Part.from_bytes(data=p.data, mime_type=p.mime_type)
            for p in parts
            if isinstance(p, Text | Image)
        ]
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_json_schema=schema,
                    temperature=0.2,
                ),
            )
        except errors.APIError as exc:
            code = exc.code or 0
            raise ProviderError(
                f"gemini {code}", rate_limited=code == 429, retryable=code == 429 or code >= 500
            ) from None
        except Exception as exc:
            raise ProviderError(f"gemini unreachable: {type(exc).__name__}") from None

        usage = response.usage_metadata
        return Reply(
            text=response.text or "",
            tokens_in=usage.prompt_token_count if usage else None,
            tokens_out=usage.candidates_token_count if usage else None,
        )

    def transcribe(
        self, *, model: str, audio: bytes, mime_type: str, language: str | None
    ) -> Reply:
        raise ProviderError("gemini is not used for speech", retryable=False)
