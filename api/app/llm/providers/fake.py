"""A provider with scripted replies, for tests and the end-to-end run. It never calls out.

Each AI job registers a reply for its task, so `AI_PROVIDER=fake` gives a working demo
without keys.
"""

import json
from collections.abc import Callable
from typing import Any

from api.app.llm.base import Capability, Part, ProviderError, Reply

Script = Callable[[list[Part]], dict[str, Any] | str]

SCRIPTS: dict[str, Script] = {}
TRANSCRIPTS: dict[str | None, str] = {
    None: "My monthly bill is 2600 rupees and I use about 330 units. Budget 2 lakh.",
    "en": "My monthly bill is 2600 rupees and I use about 330 units. Budget 2 lakh.",
    "hi": "मेरा महीने का बिल 2600 रुपये है, लगभग 330 यूनिट। बजट 2 लाख है।",
    "gu": "મારું મહિનાનું બિલ 2600 રૂપિયા છે, લગભગ 330 યુનિટ. બજેટ 2 લાખ છે.",
}


def script(task: str) -> Callable[[Script], Script]:
    def register(fn: Script) -> Script:
        SCRIPTS[task] = fn
        return fn

    return register


class FakeProvider:
    name = "fake"

    def __init__(self, scripts: dict[str, Script] | None = None) -> None:
        self.scripts = SCRIPTS if scripts is None else scripts
        self.calls: list[str] = []
        self.languages: list[str | None] = []

    def model_for(self, capability: Capability) -> str | None:
        return f"fake-{capability}"

    def generate(
        self, *, task: str, model: str, system: str, parts: list[Part], schema: dict[str, Any]
    ) -> Reply:
        self.calls.append(task)
        if task not in self.scripts:
            raise ProviderError(f"no fake reply for {task!r}", retryable=False)
        reply = self.scripts[task](parts)
        text = reply if isinstance(reply, str) else json.dumps(reply)
        return Reply(text=text, tokens_in=len(system) // 4, tokens_out=len(text) // 4)

    def transcribe(
        self, *, model: str, audio: bytes, mime_type: str, language: str | None
    ) -> Reply:
        self.calls.append("transcribe")
        self.languages.append(language)
        return Reply(text=TRANSCRIPTS.get(language, TRANSCRIPTS[None]))
