import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

import ingest_md


class IngestionProgressTests(unittest.TestCase):
    def test_summary_is_namespaced_by_collection_and_written_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            ingest_md, "DB_DIR", Path(temp_dir)
        ), patch.object(ingest_md, "collection_name", return_value="collection-v2"):
            path = ingest_md.ingestion_summary_path()
            self.assertEqual(path.name, "ingestion_summary.collection-v2.json")
            summary = {
                "files": {"document.md": {"chunks": 3}},
                "total_chunks": 3,
            }
            ingest_md.write_ingestion_summary(path, summary)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), summary)
            self.assertFalse(path.with_suffix(path.suffix + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()


def test_resume_partial_source_only_embeds_missing_chunks(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    (tmp_path / 'source.md').write_text('source text')
    collection = MagicMock()
    collection.get.return_value = {'ids': ['source.md_0']}
    gateway = MagicMock()
    gateway.profile = SimpleNamespace(name='test', provider='test', model='test')
    gateway.embed_documents.return_value = [[0.1]]
    with (
        patch.object(ingest_md, 'MD_DIR', tmp_path),
        patch.object(ingest_md, 'DB_DIR', tmp_path / 'db'),
        patch.object(ingest_md, 'get_collection', return_value=collection),
        patch.object(ingest_md, 'get_embedding_gateway', return_value=gateway),
        patch.object(ingest_md, 'ensure_index_compatible'),
        patch.object(ingest_md, 'write_manifest'),
        patch.object(ingest_md, 'chunk_text', return_value=['already indexed', 'new chunk']),
        patch('sys.argv', ['ingest_md.py']),
    ):
        ingest_md.main()
        gateway.embed_documents.assert_called_once_with(['new chunk'])
        assert collection.upsert.call_args.kwargs['ids'] == ['source.md_1']
        assert json.loads(ingest_md.ingestion_summary_path().read_text())['total_chunks'] == 2
