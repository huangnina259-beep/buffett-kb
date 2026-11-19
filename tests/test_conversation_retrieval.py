from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evidence_retrieval import retrieval_question, select_contexts


class ConversationRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.topic = "How do I know where my circle of competence ends?"
        self.history = [
            {"role": "user", "content": "How should I value a stock?"},
            {"role": "assistant", "content": "Old citation [1]."},
            {"role": "user", "content": self.topic},
            {"role": "assistant", "content": "A retail example [2]."},
        ]

    def test_pronoun_keeps_topic_across_two_followups(self):
        example = "Where did he go wrong in retail?"
        self.assertIn(self.topic, retrieval_question(example, self.history))
        self.history.append({"role": "user", "content": example})
        query = retrieval_question("Should I try to expand it as the world changes?", self.history)
        self.assertIn(self.topic, query)
        self.assertIn(example, query)
        self.assertNotIn("value a stock", query)
        self.assertNotIn("[2]", query)

    def test_independent_question_and_empty_conversation(self):
        question = "How are owner earnings calculated?"
        self.assertEqual(retrieval_question(question, self.history), question)
        self.assertEqual(retrieval_question("How did he learn that?", []), "How did he learn that?")

    def test_clicked_source_uses_one_of_the_five_slots_and_free_questions_keep_search_order(self):
        groups = {str(i): {"score": 1 / i, "hits": [f"p{i}"]} for i in range(1, 7)}
        contexts = {cid: {"paragraphs": [{"text": "x" * 11000}]} for cid in [*groups, "clicked"]}
        for anchor, expected in [
            (None, ["1", "2", "3", "4"]),
            ("6", ["6", "1", "2", "3"]),
            ("clicked", ["clicked", "1", "2", "3"]),
        ]:
            with self.subTest(anchor=anchor):
                chosen, size = select_contexts(groups, contexts, anchor)
                self.assertEqual([item["context_id"] for item in chosen], expected)
                self.assertEqual(size, 44000)
                self.assertEqual(chosen[0]["matched_paragraph_ids"], [] if anchor == "clicked" else groups[expected[0]]["hits"])
        for c in contexts.values():
            c["paragraphs"] = [{"text": "small"}]
        chosen, _ = select_contexts(groups, contexts, "2")
        self.assertEqual([item["context_id"] for item in chosen], ["2", "1", "3", "4", "5"])
