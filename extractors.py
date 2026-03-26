# extractors.py — a tiny example extractor that uses a prompt-completion to extract simple facts
import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """
Extract short JSON facts from the user message. Only output JSON. Keys: prefers_meetings_at, likes
User message: {message}
"""


def _normalize_facts(facts: dict) -> dict:
    normalized = {}

    prefers = facts.get("prefers_meetings_at")
    if isinstance(prefers, str):
        prefers = prefers.strip().lower()
        if prefers in {"morning", "afternoon", "evening"}:
            normalized["prefers_meetings_at"] = prefers

    likes = facts.get("likes")
    if isinstance(likes, str):
        likes = [likes]
    if likes:
        normalized["likes"] = likes

    return normalized


def _rule_based_extract(message: str) -> dict:
    text = message.lower()
    facts = {}

    if "meeting" in text:
        for slot in ("morning", "afternoon", "evening"):
            if slot in text:
                facts["prefers_meetings_at"] = slot
                break

    likes = []
    for pattern in (
        r"\bi love ([a-zA-Z0-9 ,'-]+)",
        r"\bi like ([a-zA-Z0-9 ,'-]+)",
    ):
        match = re.search(pattern, message, re.IGNORECASE)
        if not match:
            continue
        for item in re.split(r",| and ", match.group(1)):
            cleaned = item.strip(" .")
            if cleaned:
                likes.append(cleaned.lower())

    if likes:
        facts["likes"] = likes

    return _normalize_facts(facts)


def _validate_against_message(message: str, facts: dict) -> dict:
    validated = dict(facts)

    if not re.search(r"\bi (love|like)\b", message, re.IGNORECASE):
        validated.pop("likes", None)

    return validated

async def extract_facts(message: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(message=message)
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{"role":"user","content":prompt}],
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    text = resp.choices[0].message.content or "{}"
    try:
        return _validate_against_message(
            message,
            _normalize_facts(json.loads(text)),
        )
    except Exception:
        return _rule_based_extract(message)
