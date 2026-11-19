"""Bounded editorial caveats checked against the unchanged original packet."""
import hashlib
import json
from pathlib import Path
from functools import lru_cache
from source_contexts import DATA_PATH, load_contexts, paragraph_text


@lru_cache(maxsize=1)
def load_notes():
    path = Path(__file__).resolve().parents[1] / "data" / "source_reading_notes.json"
    data = json.loads(path.read_text())
    if hashlib.sha256(DATA_PATH.read_bytes()).hexdigest() != data["source_packet"]["sha256"]:
        raise ValueError("Reading caveats need re-review because the original packet changed.")
    contexts = load_contexts()
    for note in data["notes"]:
        for anchor in note["anchors"]:
            context = contexts[anchor["context_id"]]
            paragraph = next(p for p in context["paragraphs"] if p["id"] == anchor["paragraph_id"])
            text = paragraph_text(paragraph)
            if anchor["exact_anchor"] not in text or paragraph["speaker"] != anchor["speaker_as_supplied"]:
                raise ValueError("A reading caveat no longer matches its exact original anchor.")
            if hashlib.sha256(text.encode()).hexdigest() != anchor["paragraph_text_sha256"]:
                raise ValueError("A reading caveat paragraph hash changed.")
    return data["notes"]


def format_notes(sources):
    aliases = {source["context_id"]: i for i, source in enumerate(sources, 1)}
    notes = []
    for note in load_notes():
        if all(cid in aliases for cid in note["context_ids"]):
            labels = ", ".join("[" + str(aliases[cid]) + "]" for cid in note["context_ids"])
            notes.append("Reading caveat for " + labels + ": " + note["note"])
    return "\n".join(notes)
