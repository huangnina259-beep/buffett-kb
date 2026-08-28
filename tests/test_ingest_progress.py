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
