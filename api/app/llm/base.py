"""What every provider offers, so the gateway can treat Gemini, Groq and the fake alike."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

Capability = Literal["text", "vision", "speech"]


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Image:
    data: bytes
    mime_type: str


Part = Text | Image


@dataclass(frozen=True)
class Reply:
    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None


class ProviderError(Exception):
    def __init__(self, message: str, *, rate_limited: bool = False, retryable: bool = True):
        super().__init__(message)
        self.rate_limited = rate_limited
        self.retryable = retryable


class Provider(Protocol):
    name: str

    def model_for(self, capability: Capability) -> str | None:
        """The configured model for this capability, or None when it is not available."""

    def generate(
        self, *, task: str, model: str, system: str, parts: list[Part], schema: dict[str, Any]
    ) -> Reply:
        """Returns JSON text that should match `schema`. The gateway validates it."""

    def transcribe(
        self, *, model: str, audio: bytes, mime_type: str, language: str | None
    ) -> Reply: ...
