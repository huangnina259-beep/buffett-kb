#!/usr/bin/env python3
"""Import selected original objects without rewriting them or calling services."""
from __future__ import annotations

import argparse
import base64
import copy
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from source_contexts import canonical_sha256, validate_context

INCLUDED_CONTEXT_IDS = (
    "letter-1992-0074-0085",
    "letter-1996-0098-0118",
    "letter-2000-pdf-p12-p3-through-p13-p9",
    "meeting-2002-boundary",
    "meeting-2014-self-assessment",
    "meeting-2019-learning",
    "meeting-2019-expansion",
    "letter-2013-investing-p001-p040",
    "letter-1994-0013-0026",
    "letter-1986-0154-0297",
    "cnbc-meeting-1994-morning-ch13",
    "cnbc-meeting-1998-afternoon-ch08",
    "cnbc-meeting-1998-afternoon-ch44",
)
SUPPLEMENTAL_CONTEXT_ID = "chapter:cnbc-meeting-2004-afternoon-ch28"


def read_archive_context(archive_shard_path: Path) -> dict:
    """Decode the generated data literal only; never execute the TS module."""
    raw = archive_shard_path.read_bytes()
    if len(raw) > 20_000_000:
        raise ValueError("Unexpectedly large original source shard")
    matches = re.findall(rb'Buffer\.from\("([A-Za-z0-9+/=]+)"\s*,\s*"base64"\)', raw)
    if len(matches) != 1:
        raise ValueError("Unexpected original source shard data wrapper")
    decoded = gzip.decompress(base64.b64decode(matches[0], validate=True))
    archive = json.loads(decoded)
    context = archive[SUPPLEMENTAL_CONTEXT_ID]
    validate_context(context)
    if context["context_id"] != SUPPLEMENTAL_CONTEXT_ID or context.get("complete_within_boundary") is not True:
        raise ValueError("Expected the complete 2004 publisher chapter")
    return context


def build_packet(input_path: Path, archive_shard_path: Path | None = None) -> dict:
    raw = input_path.read_bytes()
    original = json.loads(raw)
    if original.get("language") != "English" or original.get("originals_changed") is not False:
        raise ValueError("Expected the unchanged original-English source packet")
    mapped = {}
    for context in original["contexts"]:
        context_id = context["context_id"]
        if context_id in mapped:
            raise ValueError("Duplicate source context in import input")
        mapped[context_id] = context
    contexts = []
    for context_id in INCLUDED_CONTEXT_IDS:
        context = mapped[context_id]
        validate_context(context)
        contexts.append(copy.deepcopy(context))
    supplemental_inputs = []
    if archive_shard_path is not None:
        context = read_archive_context(archive_shard_path)
        contexts.append(copy.deepcopy(context))
        supplemental_inputs.append({
            "input_name": archive_shard_path.name,
            "input_sha256": hashlib.sha256(archive_shard_path.read_bytes()).hexdigest(),
            "context_ids": [SUPPLEMENTAL_CONTEXT_ID],
            "context_sha256": canonical_sha256(context),
            "verification_scope": context.get("verification_scope"),
            "decode_policy": "Decode one generated base64/gzip JSON literal; no TypeScript execution and no source object rewriting.",
        })
    return {
        "schema_version": "source-contexts-1",
        "language": "English",
        "scope": "Representative bounded original Buffett letters and Berkshire meeting contexts, including Munger's same-meeting turns and audience questions. Not complete archive coverage, current market research, or verification of generated answers.",
        "manifest": {
            "input_name": input_path.name,
            "input_sha256": hashlib.sha256(raw).hexdigest(),
            "input_version": original.get("version"),
            "input_bundle_hash": original.get("bundle_hash"),
            "input_source_hashes": copy.deepcopy(original.get("source_input_hashes")),
            "input_scope": original.get("scope"),
            "input_review_status": copy.deepcopy(original.get("review_status")),
            "included_context_ids": [context["context_id"] for context in contexts],
            "supplemental_inputs": supplemental_inputs,
            "context_count": len(contexts),
            "paragraph_count": sum(len(context["paragraphs"]) for context in contexts),
            "contexts_sha256": canonical_sha256(contexts),
            "context_sha256": {context["context_id"]: canonical_sha256(context) for context in contexts},
            "object_policy": "Original selected context objects and ordered paragraph objects copied exactly; no editorial answers, translations, speaker inference or text rewriting imported.",
            "selection_policy": "Explicit thirteen-context packet allowlist, optionally supplemented by the complete 2004 afternoon chapter28 on valuation. Later compact selections requiring independent selection-boundary review are excluded. Existing verification limits remain unchanged.",
        },
        "originals_changed": False,
        "contexts": contexts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Existing live-evidence-packets.json")
    parser.add_argument("--archive-shard", type=Path, help="Existing cnbc-meeting-2004-afternoon.ts data shard for the complete supplemental valuation chapter")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "source_contexts.json")
    args = parser.parse_args()
    packet = build_packet(args.input, args.archive_shard)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "contexts": packet["manifest"]["context_count"], "paragraphs": packet["manifest"]["paragraph_count"], "input_sha256": packet["manifest"]["input_sha256"], "contexts_sha256": packet["manifest"]["contexts_sha256"]}))


if __name__ == "__main__":
    main()
