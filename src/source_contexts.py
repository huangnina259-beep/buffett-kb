"""Read-only original context adapter; no model, embedding or network calls.

Search units are discovery windows only. Expand each hit to its complete stored
context before generation, so an audience question or later qualification is
never discarded merely because it did not match the query.
"""
from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "source_contexts.json"
ALLOWED_SOURCE_HOSTS = {"www.berkshirehathaway.com", "berkshirehathaway.com", "buffett.cnbc.com"}


def canonical_sha256(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def paragraph_text(paragraph: dict) -> str:
    # Preserve the original object and use its already recorded reading layer.
    text = paragraph.get("reading_text", paragraph.get("text"))
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Source paragraph has no readable original text")
    return text


def validate_context(context: dict) -> None:
    for field in ("context_id", "source_id", "title", "source_url", "boundary"):
        if not isinstance(context.get(field), str) or not context[field].strip():
            raise ValueError(f"Missing source context field: {field}")
    url = urlparse(context["source_url"])
    if url.scheme != "https" or url.hostname not in ALLOWED_SOURCE_HOSTS or url.username or url.password:
        raise ValueError("Source URL is outside the selected primary publishers")
    if "context_text" in context:
        if not isinstance(context["context_text"], str) or not context["context_text"].strip():
            raise ValueError("Invalid complete original context text")
    elif context.get("complete_within_boundary") is not True:
        raise ValueError("Missing complete original context text or explicit complete boundary")
    paragraphs = context.get("paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError("Missing complete source paragraphs")
    seen = set()
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            raise ValueError("Invalid source paragraph")
        paragraph_id = paragraph.get("id")
        if not isinstance(paragraph_id, str) or not paragraph_id or paragraph_id in seen:
            raise ValueError("Missing or duplicate paragraph ID within a context")
        seen.add(paragraph_id)
        if "speaker" not in paragraph or not (paragraph["speaker"] is None or isinstance(paragraph["speaker"], str)):
            raise ValueError("A paragraph must preserve its explicit speaker or null")
        paragraph_text(paragraph)
    for paragraph_id in context.get("question_paragraph_ids", []):
        if paragraph_id not in seen:
            raise ValueError("Original question paragraph is missing")
    answer_start = context.get("topic_answer_start_id")
    if answer_start is not None and answer_start not in seen:
        raise ValueError("Original topic answer boundary is missing")


@lru_cache(maxsize=1)
def load_contexts() -> dict[str, dict]:
    """Return the cached context ID map. Treat this shared map as read-only."""
    packet = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if packet.get("schema_version") != "source-contexts-1":
        raise ValueError("Unsupported source context packet")
    contexts = packet.get("contexts")
    manifest = packet.get("manifest", {})
    if not isinstance(contexts, list) or canonical_sha256(contexts) != manifest.get("contexts_sha256"):
        raise ValueError("Source context packet hash mismatch")
    mapped = {}
    for context in contexts:
        validate_context(context)
        context_id = context["context_id"]
        if context_id in mapped:
            raise ValueError("Duplicate source context ID")
        if canonical_sha256(context) != manifest.get("context_sha256", {}).get(context_id):
            raise ValueError("Source context object hash mismatch")
        mapped[context_id] = context
    if list(mapped) != manifest.get("included_context_ids") or len(mapped) != manifest.get("context_count"):
        raise ValueError("Source context manifest does not match its objects")
    for context in contexts:
        for required_id in context.get("required_companion_context_ids", []):
            if required_id not in mapped:
                raise ValueError("Required companion source context is missing")
    return mapped


def expand_context(context_id: str) -> dict:
    """Return an unchanged copy, protecting the cached originals from callers."""
    return copy.deepcopy(load_contexts()[context_id])


def search_units() -> list[dict]:
    """Whole-paragraph windows, generally 1,500–2,500 characters.

No paragraph is split, normalized or rewritten. An unusually long paragraph
may exceed the target; a final short group is retained. The full parent is
always available through context_id, regardless of which window was found.
"""
    units = []
    for context_id, context in load_contexts().items():
        pending = []
        characters = 0
        ordinal = 0

        def flush():
            nonlocal pending, characters, ordinal
            if not pending:
                return
            ordinal += 1
            units.append({
                "id": f"{context_id}::unit-{ordinal:04d}",
                "context_id": context_id,
                "paragraph_ids": [paragraph["id"] for paragraph in pending],
                "text": "\n\n".join(paragraph_text(paragraph) for paragraph in pending),
            })
            pending = []
            characters = 0

        for paragraph in context["paragraphs"]:
            length = len(paragraph_text(paragraph))
            combined = characters + (2 if pending else 0) + length
            if pending and (combined > 2500 or (characters >= 1500 and combined > 2000)):
                flush()
            characters += (2 if pending else 0) + length
            pending.append(paragraph)
        flush()
    return units


def _context_author(context: dict) -> str:
    # These are source-level display labels, never paragraph attribution.
    if context["source_id"].startswith("cnbc-meeting-"):
        return "Berkshire annual meeting"
    speakers = list(dict.fromkeys(p["speaker"] for p in context["paragraphs"] if p["speaker"]))
    return speakers[0] if len(speakers) == 1 else "Berkshire shareholder letter"


def format_contexts(context_ids) -> tuple[str, list[dict]]:
    """Format complete parent contexts with numbered English citation aliases.

Aliases [1], [2], ... identify source contexts for this request. Paragraph IDs
remain visible and immutable; the aliases alone do not imply that every claim
in a generated answer has been checked against a particular paragraph.
"""
    blocks = []
    sources = []
    selected = list(dict.fromkeys(context_ids))
    # Companion contexts, if present in a later packet, are not optional.
    for context_id in selected:
        for required_id in load_contexts()[context_id].get("required_companion_context_ids", []):
            if required_id not in selected:
                selected.append(required_id)
    for number, context_id in enumerate(selected, 1):
        context = expand_context(context_id)
        headers = [
            f"[{number}] {context['title']}",
            f"Context ID: {context_id}",
            f"Source ID: {context['source_id']}",
            f"Publisher URL: {context['source_url']}",
            f"Date: {context.get('date') or 'Unknown'} ({context.get('date_kind') or 'unknown kind'})",
            f"Event date: {context.get('event_date') or 'Unknown'}; signature date: {context.get('signature_date') or 'Unknown'}; publication date: {context.get('publication_date') or 'Unknown'}; report year: {context.get('report_year') or 'Unknown'}",
            f"Complete stored boundary: {context['boundary']}",
            f"Source verification scope: {context.get('verification_scope') or 'Not specified'}",
        ]
        for field in ("title_kind", "title_note", "embedded_quotation_note", "review_status", "question_paragraph_ids", "topic_answer_start_id", "chapters"):
            if field in context:
                headers.append(f"{field}: {json.dumps(context[field], ensure_ascii=False)}")
        paragraphs = []
        for paragraph in context["paragraphs"]:
            speaker = paragraph["speaker"] if paragraph["speaker"] is not None else "Unknown (speaker is null; attribution not confirmed)"
            paragraphs.append(
                f"Paragraph ID: {paragraph['id']}\nSpeaker: {speaker}\n"
                f"{paragraph_text(paragraph)}"
            )
        blocks.append("\n".join(headers) + "\n\n" + "\n\n".join(paragraphs))
        # Add compatibility fields without dropping original context metadata.
        source = context
        source.update({
            "citation_alias": f"[{number}]",
            "label": context["title"],
            "author": _context_author(context),
            "text": "\n\n".join(paragraph_text(paragraph) for paragraph in context["paragraphs"]),
            "full_context": context.get("context_text", "\n\n".join(paragraph_text(paragraph) for paragraph in context["paragraphs"])),
            "url": context["source_url"],
            "paragraph_ids": [paragraph["id"] for paragraph in context["paragraphs"]],
            "speakers": list(dict.fromkeys(paragraph["speaker"] for paragraph in context["paragraphs"])),
        })
        sources.append(source)
    return "\n\n---\n\n".join(blocks), sources
