---
name: ai-feature
description: Build or change an AI feature with Gemini or Groq, including terrace photo assessment, quote review, vendor recommendation and voice input in English, Hindi or Gujarati. Use for any LLM prompt, provider, arq job, rate limiting or prompt injection work.
---

# AI features

Judging rewards features that are useful, explained, and whose numbers are calculated in code. The design is in sections 04, 05 and 10 of `SuryaSetu Architecture.html`. Load `/pm-surya-rules` as well when numbers are involved.

## What decides what

| Output | Decided by |
|---|---|
| Obstructions, rough boxes, usable fraction, shade risk | Gemini vision |
| Usable area and size cap | `rules/sizing.py` |
| Size, subsidy, payback | `rules/` |
| Facts from a paper quote | LLM, then Pydantic validation |
| Missing items | `rules/checklist.py` |
| Scores and ranking | `rules/scoring.py` |
| Reasons in plain language | LLM, given the score table only |
| Spoken request to form fields | Whisper, LLM extraction, then the household confirms |

## Structure

- `worker/jobs/`: `photo_assess`, `voice_extract`, `quote_review`, `recommend`, each idempotent on `(entity_id, job_type, input_hash)`.
- `worker/llm/gateway.py`: the only caller of providers.
- `worker/llm/ratelimit.py`: Redis token buckets per `(provider, model)` for RPM, TPM and RPD.
- `worker/llm/guard.py`: injection detector and output checks.
- `worker/llm/providers/`: `gemini`, `groq` and `fake`, selected by `AI_PROVIDER`.

## Calling a model

1. Request JSON and parse it with Pydantic. Reject extra keys and out-of-range values, retry once, then return a clear "AI unavailable" result.
2. Never interpolate user or vendor text into instructions.
3. Model names and limits come from env, copied from each provider's console. Free-tier limits change, so never hard-code them.
4. Log provider, model, duration and token usage. Never log photos or personal details.
5. Tests use `fake`. A test that reaches a real provider is a bug.

## Staying within limits

1. Workers take a token before each call. With none left, the job is re-queued with a delay, not failed.
2. `high` priority covers voice and on-demand compare and gets 70% of the bucket. `low` covers photo assessment and quote review.
3. Cache on `sha256(input + prompt_version)`. Send 1024 px images. Batch new quotes for one request into one call.
4. Debounce the recommendation for 2 minutes after the last quote.
5. On 429, back off exponentially with jitter. Fall back from Gemini to Groq for text. Open a circuit breaker after 5 failures.

## Prompt injection defence

1. **Ranking is code.** No text can change a weight or a number.
2. **Data isolation.** The recommendation prompt receives the score table only. Free text appears only in the extraction prompt, inside `<untrusted_vendor_text>` tags, and the system prompt says it is data.
3. **Detector.** A regex pass plus a cheap LLM classifier sets `quotes.injection_flag`.
4. **Schema lock.** Output must validate, or it is rejected and retried once.
5. **Winner check.** Code confirms the explanation names the code's chosen vendor. If not, discard it and use a template built from the scores.
6. **Visible to the user.** Flagged quotes show a warning.

Required test: two identical quotes, one containing the hidden instruction, score the same, and only that one is flagged. Add Hindi and Gujarati variants.

## Voice

The browser records with `MediaRecorder` and uploads. Whisper large-v3 transcribes with `language` set to `hi`, `gu` or `en`. The LLM extracts `monthly_units`, `monthly_bill`, `budget`, `roof_type`, `floors` and `address_hint`. The form prefills, and the household confirms. Nothing posts automatically. The fallback is the browser's Web Speech API. The microphone needs HTTPS or localhost.
