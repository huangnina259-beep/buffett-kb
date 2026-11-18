"""Mechanical provenance and boundary checks; not generated-answer validation."""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import source_contexts as adapter

spec = importlib.util.spec_from_file_location("import_source_contexts", ROOT / "scripts" / "import_source_contexts.py")
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class SourceContextsTests(unittest.TestCase):
    def test_manifest_and_unique_composite_ids(self):
        contexts = adapter.load_contexts()
        expected = list(importer.INCLUDED_CONTEXT_IDS)
        if len(contexts) == 14:
            expected.append(importer.SUPPLEMENTAL_CONTEXT_ID)
        self.assertEqual(list(contexts), expected)
        composite = [(cid, paragraph["id"]) for cid, context in contexts.items() for paragraph in context["paragraphs"]]
        self.assertEqual(len(composite), len(set(composite)))
        packet = json.loads(adapter.DATA_PATH.read_text())
        self.assertEqual(packet["manifest"]["paragraph_count"], len(composite))

    @unittest.skipUnless(os.environ.get("SOURCE_CONTEXTS_IMPORT_INPUT"), "Set SOURCE_CONTEXTS_IMPORT_INPUT to independently compare the original import input")
    def test_every_context_and_paragraph_equal_original_input(self):
        path = Path(os.environ["SOURCE_CONTEXTS_IMPORT_INPUT"])
        raw = path.read_bytes()
        original = {context["context_id"]: context for context in json.loads(raw)["contexts"]}
        packet = json.loads(adapter.DATA_PATH.read_text())
        self.assertEqual(packet["manifest"]["input_sha256"], hashlib.sha256(raw).hexdigest())
        for cid in importer.INCLUDED_CONTEXT_IDS:
            self.assertEqual(adapter.expand_context(cid), original[cid])
        archive = None
        if packet["manifest"]["supplemental_inputs"]:
            archive = Path(os.environ.get("SOURCE_CONTEXTS_ARCHIVE_SHARD", path.parent / "archive-shards" / "cnbc-meeting-2004-afternoon.ts"))
            self.assertEqual(adapter.expand_context(importer.SUPPLEMENTAL_CONTEXT_ID), importer.read_archive_context(archive))
        self.assertEqual(importer.build_packet(path, archive), packet)

    def test_importer_preserves_unknown_metadata_and_paragraph_objects(self):
        contexts = [adapter.expand_context(cid) for cid in importer.INCLUDED_CONTEXT_IDS]
        original = json.loads(json.dumps({"language": "English", "originals_changed": False, "contexts": contexts}))
        original["contexts"][0]["future_provenance_field"] = {"status": None, "claims": [False, "pending"]}
        original["contexts"][0]["paragraphs"][0]["future_paragraph_field"] = {"value": None}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(original))
            result = importer.build_packet(path)
        self.assertEqual(result["contexts"], original["contexts"])

    def test_2002_full_question_and_three_chapters_survive_expansion(self):
        context = adapter.expand_context("meeting-2002-boundary")
        self.assertEqual(len(context["paragraphs"]), 67)
        self.assertEqual([chapter["chapter_number"] for chapter in context["chapters"]], [16, 17, 18])
        self.assertEqual(context["question_paragraph_ids"], ["cnbc-meeting-2002-afternoon-ch16-p004"])
        self.assertEqual(context["topic_answer_start_id"], "cnbc-meeting-2002-afternoon-ch18-p003")
        prompt, sources = adapter.format_contexts([context["context_id"]])
        for paragraph in context["paragraphs"]:
            self.assertIn(paragraph["id"], prompt)
            self.assertIn(adapter.paragraph_text(paragraph), prompt)
        self.assertEqual(sources[0]["paragraphs"], context["paragraphs"])
        self.assertEqual(sources[0]["full_context"], context["context_text"])
        self.assertEqual(sources[0]["author"], "Berkshire annual meeting")

    def test_1998_unknown_speaker_is_not_promoted_and_munger_remains(self):
        context = adapter.expand_context("cnbc-meeting-1998-afternoon-ch08")
        paragraph = next(p for p in context["paragraphs"] if p["id"].endswith("p003"))
        self.assertIsNone(paragraph["speaker"])
        self.assertEqual(paragraph["candidate_speaker"], "Audience member")
        prompt, sources = adapter.format_contexts([context["context_id"]])
        self.assertIn("Paragraph ID: " + paragraph["id"] + "\nSpeaker: Unknown (speaker is null; attribution not confirmed)", prompt)
        self.assertIn("Speaker: Charlie Munger", prompt)
        self.assertIsNone(sources[0]["paragraphs"][2]["speaker"])

    def test_2013_report_year_is_not_signature_or_publication_date(self):
        context = adapter.expand_context("letter-2013-investing-p001-p040")
        self.assertEqual(context["report_year"], 2013)
        self.assertEqual(context["date"], "2014-02-28")
        self.assertEqual(context["signature_date"], "2014-02-28")
        self.assertEqual(context["date_kind"], "signature_date")
        self.assertIsNone(context["publication_date"])

    def test_2004_supplement_preserves_full_chapter_and_review_limits(self):
        if importer.SUPPLEMENTAL_CONTEXT_ID not in adapter.load_contexts():
            self.skipTest("Optional complete 2004 chapter was not imported")
        context = adapter.expand_context(importer.SUPPLEMENTAL_CONTEXT_ID)
        self.assertEqual(len(context["paragraphs"]), 30)
        self.assertTrue(context["complete_within_boundary"])
        self.assertNotIn("context_text", context)
        self.assertEqual(context["paragraphs"][5]["speaker"], "Audience member")
        self.assertEqual(context["paragraphs"][12]["speaker"], "Warren Buffett")
        self.assertIsNone(context["paragraphs"][13]["speaker"])
        self.assertIn("semantic and audio review not established", context["verification_scope"])
        prompt, sources = adapter.format_contexts([context["context_id"]])
        self.assertIn(context["paragraphs"][10]["text"], prompt)
        self.assertEqual(sources[0]["paragraphs"], context["paragraphs"])
        self.assertEqual(sources[0]["full_context"], "\n\n".join(p["text"] for p in context["paragraphs"]))

    def test_search_units_preserve_every_complete_paragraph_in_order(self):
        grouped = {}
        seen = set()
        for unit in adapter.search_units():
            self.assertNotIn(unit["id"], seen)
            seen.add(unit["id"])
            context = adapter.expand_context(unit["context_id"])
            by_id = {paragraph["id"]: paragraph for paragraph in context["paragraphs"]}
            expected = "\n\n".join(adapter.paragraph_text(by_id[pid]) for pid in unit["paragraph_ids"])
            self.assertEqual(unit["text"], expected)
            if len(unit["text"]) > 2500:
                self.assertEqual(len(unit["paragraph_ids"]), 1)
            grouped.setdefault(unit["context_id"], []).extend(unit["paragraph_ids"])
        for cid, context in adapter.load_contexts().items():
            self.assertEqual(grouped[cid], [paragraph["id"] for paragraph in context["paragraphs"]])

    def test_numbered_aliases_unknown_ids_and_mutation_isolation(self):
        ids = list(importer.INCLUDED_CONTEXT_IDS[:2])
        prompt, sources = adapter.format_contexts(ids + ids[:1])
        self.assertEqual([source["citation_alias"] for source in sources], ["[1]", "[2]"])
        self.assertIn("[1] ", prompt)
        self.assertIn("[2] ", prompt)
        sources[0]["paragraphs"][0]["speaker"] = "Incorrect mutation"
        self.assertNotEqual(adapter.expand_context(ids[0])["paragraphs"][0]["speaker"], "Incorrect mutation")
        with self.assertRaises(KeyError):
            adapter.expand_context("not-a-source")


if __name__ == "__main__":
    unittest.main()
