"""Prompt injection detector and output checks.

The detector is a first, code-only pass over vendor text in English, Hindi and Gujarati. It
runs when the quote is submitted, so a flagged quote shows its warning even with the AI down.
The LLM classifier in the quote review job catches rewordings this misses. Neither decides the
ranking: that is `rules.scoring`, which never sees free text.
"""

import re

_EN = [
    r"\b(rank|rate|score|place|put|list|choose|pick|select|recommend|prefer)\s+(this|our|us|me|my)\b"
    r"[^.\n]{0,40}\b(first|top|highest|best|number\s*one|#\s*1|winner)\b",
    r"\b(ignore|disregard|forget|override|bypass)\b[^.\n]{0,30}"
    r"\b(previous|prior|above|other|all|earlier|any)\b[^.\n]{0,20}"
    r"\b(instructions?|rules?|quotes?|vendors?|prompts?|scores?)\b",
    r"\b(ai|a\.i\.|llm|chatbot|gpt|gemini|assistant|model)\b\s*[:,-]",
    r"\b(system\s+prompt|new\s+instructions?|you\s+are\s+now|act\s+as)\b",
    r"\b(give|assign)\s+(this|us|our)\b[^.\n]{0,30}\b(100|full|maximum|max|highest)\b",
]
_HI = [
    r"(इस|हमारे|हमें|मेरे)\s*\S*\s*(विक्रेता|वेंडर|कोटेशन|कोट)?\S*\s*(को)?\s*"
    r"(पहले|प्रथम|सबसे\s*ऊपर|सबसे\s*अच्छा|नंबर\s*(एक|1))",
    r"(निर्देश|निर्देशों|नियमों|बाकी|अन्य)\S*(\s+\S+)?\s*(को)?\s*(अनदेखा|नजरअंदाज|भूल)",
]
_GU = [
    r"(આ|અમારા|અમને|મારા)\s*\S*\s*(વિક્રેતા|વેન્ડર|ક્વોટ)?\S*\s*"
    r"(પ્રથમ|પહેલા|પહેલો|સૌથી\s*ઉપર|શ્રેષ્ઠ|નંબર\s*(એક|1))",
    r"(સૂચના|સૂચનાઓ|નિયમો|બીજા|અન્ય)\S*(\s+\S+)?\s*(ને)?\s*(અવગણ|ભૂલી)",
]
PATTERNS = [re.compile(p, re.IGNORECASE) for p in (*_EN, *_HI, *_GU)]
_CONTEXT = 40


def scan(text: str | None) -> str | None:
    """The suspicious passage, with a little context, or None if nothing looks like one."""
    if not text:
        return None
    for pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            start, end = max(match.start() - _CONTEXT, 0), min(match.end() + _CONTEXT, len(text))
            return text[start:end].strip()
    return None


# Digits, currency and the amount words that always stand for a number. A unit on its own,
# as in "per kW", is not a figure.
_FIGURE = re.compile(r"[\d₹%]|\b(lakhs?|lacs?|crores?)\b", re.IGNORECASE)


def clean_notes(notes: list[str], limit: int = 4) -> list[str]:
    """Keeps plain-language notes only. A note with a figure in it is dropped: figures come
    from code, never from the model."""
    kept = []
    for note in notes:
        note = " ".join(note.split())
        if note and not _FIGURE.search(note):
            kept.append(note)
    return kept[:limit]


def quoted_from(excerpt: str | None, text: str) -> str | None:
    """An excerpt the model points to must really appear in the vendor's text."""
    if excerpt and excerpt.strip() and excerpt.strip() in text:
        return excerpt.strip()
    return None
