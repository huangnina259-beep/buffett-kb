"""Offline provenance and source-presence checks, not semantic certification."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import source_contexts as originals
import source_reading_notes as reading


class SourceReadingNotesTests(unittest.TestCase):
    def setUp(self):
        reading.load_notes.cache_clear()

    def tearDown(self):
        reading.load_notes.cache_clear()

    def changed_contexts(self):
        contexts = copy.deepcopy(originals.load_contexts())
        anchor = reading.load_notes()[0]["anchors"][0]
        paragraph = next(
            p for p in contexts[anchor["context_id"]]["paragraphs"]
            if p["id"] == anchor["paragraph_id"]
        )
        reading.load_notes.cache_clear()
        return contexts, paragraph, anchor

    def test_actual_notes_validate_against_current_original_packet(self):
        notes = reading.load_notes()
        self.assertEqual(len(notes), 5)
        self.assertTrue(all(note["anchors"] for note in notes))
        self.assertTrue(any(
            anchor["speaker_as_supplied"] is None
            for note in notes for anchor in note["anchors"]
        ), "Unknown attribution must remain represented, not silently filled in")

    def test_changed_packet_is_rejected_before_notes_are_used(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed-packet.json"
            changed.write_bytes(originals.DATA_PATH.read_bytes() + b"\n")
            with patch.object(reading, "DATA_PATH", changed):
                with self.assertRaisesRegex(ValueError, "original packet changed"):
                    reading.load_notes()

    def test_missing_exact_anchor_is_rejected(self):
        contexts, paragraph, anchor = self.changed_contexts()
        field = "reading_text" if "reading_text" in paragraph else "text"
        paragraph[field] = paragraph[field].replace(anchor["exact_anchor"], "Altered source wording", 1)
        with patch.object(reading, "load_contexts", return_value=contexts):
            with self.assertRaisesRegex(ValueError, "exact original anchor"):
                reading.load_notes()

    def test_speaker_change_is_rejected(self):
        contexts, paragraph, _ = self.changed_contexts()
        paragraph["speaker"] = "Charlie Munger"
        with patch.object(reading, "load_contexts", return_value=contexts):
            with self.assertRaisesRegex(ValueError, "exact original anchor"):
                reading.load_notes()

    def test_changed_qualification_outside_anchor_is_rejected(self):
        contexts, paragraph, _ = self.changed_contexts()
        field = "reading_text" if "reading_text" in paragraph else "text"
        paragraph[field] += " A new unsupported qualification."
        with patch.object(reading, "load_contexts", return_value=contexts):
            with self.assertRaisesRegex(ValueError, "paragraph hash changed"):
                reading.load_notes()

    def test_each_note_requires_all_of_its_original_contexts(self):
        self.assertEqual(reading.format_notes([]), "")
        for note in reading.load_notes():
            required = note["context_ids"]
            with self.subTest(note=note["id"], selection="complete"):
                _, sources = originals.format_contexts(required)
                self.assertIn(note["note"], reading.format_notes(sources))
            for omitted in required:
                with self.subTest(note=note["id"], omitted=omitted):
                    _, sources = originals.format_contexts([cid for cid in required if cid != omitted])
                    self.assertNotIn(note["note"], reading.format_notes(sources))

    def test_note_citation_labels_follow_selected_source_order(self):
        note = next(n for n in reading.load_notes() if len(n["context_ids"]) == 2)
        first, second = note["context_ids"]
        unrelated = next(cid for cid in originals.load_contexts() if cid not in note["context_ids"])
        _, sources = originals.format_contexts([second, unrelated, first])
        self.assertIn("Reading caveat for [3], [1]: " + note["note"], reading.format_notes(sources))


if __name__ == "__main__":
    unittest.main()
