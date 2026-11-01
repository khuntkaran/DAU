"""Voice input in English, Hindi and Gujarati (work plan 4.3). Nothing posts automatically."""

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.enums import Role
from api.app.jobs.voice_extract import MAX_PER_HOUR
from api.app.llm.base import Part, ProviderError, Text
from api.app.llm.providers.fake import TRANSCRIPTS, FakeProvider
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]
FIELDS = {"monthly_units": 330, "monthly_bill_inr": 2600, "budget_inr": 200000}


@pytest.fixture(autouse=True)
def _setup(settings: Settings, tmp_path: Path, fake_ai: FakeProvider) -> None:
    settings.upload_dir = tmp_path / "uploads"
    fake_ai.scripts = {"voice_extract": lambda parts: FIELDS}


@pytest.fixture
def household(make_user: MakeUser) -> models.User:
    return make_user()


def _audio(client: TestClient, headers: dict[str, str], purpose: str = "voice_audio") -> str:
    clip = b"\x1a\x45\xdf\xa3" + uuid.uuid4().bytes * 8
    response = client.post(
        "/uploads",
        data={"purpose": purpose},
        files={"file": ("voice.webm", clip, "audio/webm")},
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return str(response.json()["id"])


def _transcribe(
    client: TestClient, headers: dict[str, str], audio_id: str, language: str = "hi"
) -> Any:
    return client.post(
        "/voice/transcribe",
        json={"audio_file_id": audio_id, "language": language},
        headers=headers,
    )


def _job(client: TestClient, headers: dict[str, str], job_id: str) -> Any:
    return client.get(f"/jobs/{job_id}", headers=headers).json()


def test_speech_becomes_a_transcript_and_prefilled_fields(
    client: TestClient, db: Session, household: models.User, auth: Auth
) -> None:
    headers = auth(household)
    response = _transcribe(client, headers, _audio(client, headers), "hi")

    assert response.status_code == 202
    accepted = response.json()
    assert accepted["job_type"] == "voice_extract"
    job = _job(client, headers, accepted["job_id"])
    assert job["status"] == "succeeded"
    result = job["output"]
    assert result["kind"] == "voice_extract"
    assert result["language"] == "hi"
    assert result["transcript"] == TRANSCRIPTS["hi"]
    assert result["extracted_fields"]["monthly_units"] == 330
    assert result["extracted_fields"]["budget_inr"] == 200000

    voice = db.get(models.VoiceInput, uuid.UUID(accepted["entity_id"]))
    assert voice is not None
    db.refresh(voice)
    assert voice.transcript == TRANSCRIPTS["hi"]
    assert voice.applied_to_request is False


@pytest.mark.parametrize(
    ("chosen", "sent"), [("hi", "hi"), ("gu", "gu"), ("en", "en"), ("auto", None)]
)
def test_the_chosen_language_reaches_whisper(
    client: TestClient,
    household: models.User,
    auth: Auth,
    fake_ai: FakeProvider,
    chosen: str,
    sent: str | None,
) -> None:
    headers = auth(household)
    _transcribe(client, headers, _audio(client, headers), chosen)
    assert fake_ai.languages == [sent]


def test_the_transcript_reaches_the_model_as_data_not_instructions(
    client: TestClient, household: models.User, auth: Auth, fake_ai: FakeProvider
) -> None:
    seen: list[list[Part]] = []

    def capture(parts: list[Part]) -> dict[str, Any]:
        seen.append(parts)
        return FIELDS

    fake_ai.scripts = {"voice_extract": capture}
    headers = auth(household)
    _transcribe(client, headers, _audio(client, headers), "gu")

    text = " ".join(p.text for p in seen[0] if isinstance(p, Text))
    assert f"<transcript>\n{TRANSCRIPTS['gu']}\n</transcript>" in text


def test_if_extraction_fails_the_transcript_is_still_returned(
    client: TestClient, household: models.User, auth: Auth, fake_ai: FakeProvider
) -> None:
    fake_ai.scripts = {}
    headers = auth(household)
    accepted = _transcribe(client, headers, _audio(client, headers), "en").json()

    job = _job(client, headers, accepted["job_id"])
    assert job["status"] == "succeeded"
    assert job["output"]["transcript"] == TRANSCRIPTS["en"]
    assert all(v is None for v in job["output"]["extracted_fields"].values())


def test_if_speech_recognition_is_down_the_job_fails_cleanly(
    client: TestClient,
    household: models.User,
    auth: Auth,
    fake_ai: FakeProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def down(**_: Any) -> Any:
        raise ProviderError("whisper down", retryable=False)

    monkeypatch.setattr(fake_ai, "transcribe", down)
    headers = auth(household)
    accepted = _transcribe(client, headers, _audio(client, headers)).json()

    job = _job(client, headers, accepted["job_id"])
    assert job["status"] == "failed"
    assert job["error"].startswith("AI unavailable")


def test_out_of_range_fields_are_rejected(
    client: TestClient, household: models.User, auth: Auth, fake_ai: FakeProvider
) -> None:
    fake_ai.scripts = {"voice_extract": lambda parts: {**FIELDS, "monthly_units": -5}}
    headers = auth(household)
    accepted = _transcribe(client, headers, _audio(client, headers)).json()

    fields = _job(client, headers, accepted["job_id"])["output"]["extracted_fields"]
    assert fields["monthly_units"] is None


def test_the_same_clip_is_transcribed_once(
    client: TestClient, household: models.User, auth: Auth, fake_ai: FakeProvider
) -> None:
    headers = auth(household)
    audio = _audio(client, headers)
    first = _transcribe(client, headers, audio).json()
    second = _transcribe(client, headers, audio).json()

    assert fake_ai.calls.count("transcribe") == 1
    assert first["entity_id"] != second["entity_id"]
    assert _job(client, headers, second["job_id"])["output"]["transcript"] == TRANSCRIPTS["hi"]


def test_a_voice_note_prefills_a_request_only_when_the_household_submits(
    client: TestClient, db: Session, household: models.User, auth: Auth
) -> None:
    headers = auth(household)
    accepted = _transcribe(client, headers, _audio(client, headers)).json()
    body = {
        "lat": 23.0225,
        "lng": 72.5714,
        "location_source": "map_pin",
        "monthly_units": 330,
        "budget_inr": 200000,
        "roof_area_sqm": "40",
        "input_method": "voice",
        "voice_input_id": accepted["entity_id"],
    }

    created = client.post("/requests", json=body, headers=headers).json()

    voice = db.get(models.VoiceInput, uuid.UUID(accepted["entity_id"]))
    assert voice is not None
    db.refresh(voice)
    assert str(voice.request_id) == created["id"]
    assert voice.applied_to_request is True
    assert created["input_method"] == "voice"


@pytest.mark.parametrize("problem", ["someone_elses", "a_photo", "missing"])
def test_only_your_own_voice_uploads_can_be_transcribed(
    client: TestClient, household: models.User, make_user: MakeUser, auth: Auth, problem: str
) -> None:
    headers = auth(household)
    if problem == "someone_elses":
        audio = _audio(client, auth(make_user()))
    elif problem == "a_photo":
        from io import BytesIO

        from PIL import Image

        out = BytesIO()
        Image.new("RGB", (4, 4)).save(out, "PNG")
        audio = client.post(
            "/uploads",
            data={"purpose": "terrace_photo"},
            files={"file": ("p.png", out.getvalue(), "image/png")},
            headers=headers,
        ).json()["id"]
    else:
        audio = str(uuid.uuid4())

    response = _transcribe(client, headers, audio)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_attachment")


def test_vendors_cannot_use_voice_input(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    response = _transcribe(client, auth(make_user(Role.VENDOR)), str(uuid.uuid4()))
    assert response.status_code == 403


def test_voice_notes_are_limited_per_hour(
    client: TestClient, db: Session, household: models.User, auth: Auth
) -> None:
    headers = auth(household)
    for _ in range(MAX_PER_HOUR):
        assert _transcribe(client, headers, _audio(client, headers)).status_code == 202

    response = _transcribe(client, headers, _audio(client, headers))
    assert (response.status_code, response.json()["error"]["code"]) == (429, "too_many_voice_notes")
    assert len(db.scalars(select(models.VoiceInput)).all()) == MAX_PER_HOUR
