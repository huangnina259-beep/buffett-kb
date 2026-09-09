import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import rag
import tutor
import vector_store

class KnowledgeReadinessTests(unittest.TestCase):
    def test_index_read_failure_is_not_reported_as_empty(self):
        with patch.object(vector_store, 'get_collection', side_effect=RuntimeError('internal-secret')):
            status = vector_store.index_status()
        self.assertIsNone(status['count'])
        self.assertEqual(status['status'], 'unavailable')
        self.assertNotIn('internal-secret', str(status))

    def test_empty_index_does_not_call_embedding_or_generation(self):
        collection = Mock()
        collection.count.return_value = 0
        with patch.object(rag, '_get_collection', return_value=collection), patch.object(rag, 'get_embedding_gateway') as embed, patch.object(rag, 'get_generation_gateway') as generate:
            result = rag.query_knowledge_base('能力圈')
            events = [json.loads(e.removeprefix('data: ')) for e in rag.stream_query_knowledge_base('能力圈')]
        self.assertEqual(result['error_code'], 'KNOWLEDGE_NOT_READY')
        self.assertEqual(events[-1]['code'], 'KNOWLEDGE_NOT_READY')
        embed.assert_not_called()
        generate.assert_not_called()

    def test_no_matches_is_not_an_empty_or_broken_index(self):
        with patch.object(rag, '_retrieve', return_value={'documents': [[]]}), patch.object(rag, 'get_generation_gateway') as generate:
            result = rag.query_knowledge_base('an unrelated question')
        self.assertIsNone(result['error'])
        self.assertIn('未找到', result['answer'])
        generate.assert_not_called()

    def test_tutor_does_not_generate_or_advance_without_reference_material(self):
        for value in [('', []), rag.KnowledgeUnavailable('KNOWLEDGE_NOT_READY', 'not ready')]:
            kw = {'side_effect': value} if isinstance(value, Exception) else {'return_value': value}
            with patch.object(tutor, '_retrieve_for_tutor', **kw), patch.object(tutor, 'get_generation_gateway') as generate:
                events = [json.loads(e.removeprefix('data: ')) for e in tutor.stream_tutor_response('', curriculum_state={'currentChapter': 'ch1'})]
            self.assertEqual(events[-1]['type'], 'error')
            generate.assert_not_called()

class RealIndexTests(unittest.TestCase):
    def test_real_chroma_index_returns_evidence_without_cloud_calls(self):
        import tempfile
        import chromadb
        from chromadb.config import Settings
        with tempfile.TemporaryDirectory() as directory:
            client = chromadb.PersistentClient(path=directory, settings=Settings(anonymized_telemetry=False))
            collection = client.create_collection('knowledge-test', embedding_function=None)
            collection.add(ids=['fixture-1'], embeddings=[[1.0, 0.0, 0.0]],
                           documents=['Fixture: study the boundaries of your understanding.'],
                           metadatas=[{'source_label': 'Test Letter', 'author': 'Warren Buffett', 'year': 1988}])
            gateway = SimpleNamespace(
                profile=SimpleNamespace(provider='local', model=vector_store.LEGACY_LOCAL_MODEL),
                embed_query=lambda text: [1.0, 0.0, 0.0],
            )
            generation = Mock()
            generation.complete.return_value = SimpleNamespace(text='测试回答[来源1]')
            with patch.object(rag, '_get_collection', return_value=collection), \
                 patch.object(rag, 'get_embedding_gateway', return_value=gateway), \
                 patch.object(vector_store, 'read_manifest', return_value=None), \
                 patch.object(rag, '_extract_search_params', return_value=('competence', {'author': 'Warren Buffett'}, {'author': 'Warren Buffett'})), \
                 patch.object(rag, 'get_generation_gateway', return_value=generation):
                result = rag.query_knowledge_base('能力圈', top_k=1)
            self.assertIsNone(result['error'])
            self.assertEqual(result['sources'][0]['year'], 1988)
            self.assertIn('Fixture:', result['sources'][0]['text'])
            self.assertIn('[来源1]', result['answer'])
            self.assertIn('Fixture:', str(generation.complete.call_args))
