import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from lexical_search import search_evidence, fuse_evidence, useful_passage

def test_definition_lookup_finds_real_primary_evidence():
    result=search_evidence('economic moat',24)
    result=fuse_evidence({'documents':[[]],'metadatas':[[]]},result,12)
    assert any(m['source_file']=='Buffett_2007_Shareholder_Letter.md' for m in result['metadatas'][0])
    assert all(useful_passage(d) for d in result['documents'][0])
    assert not useful_passage('---\n\n---')
    assert not useful_passage('BERKSHIRE HATHAWAY INC.')

def test_basic_definition_uses_local_evidence_without_remote_embedding():
    from unittest.mock import Mock, patch
    import rag
    collection=Mock();collection.count.return_value=100
    gateway=Mock()
    docs=['Evidence '+str(i)+' supports this specific business mechanism. '*5 for i in range(4)]
    result={'documents':[docs],'metadatas':[[{'source_file':str(i),'source_label':str(i)} for i in range(4)]],'distances':[[0.1]*4]}
    with patch.object(rag,'_get_collection',return_value=collection),patch.object(rag,'get_embedding_gateway',return_value=gateway),patch.object(rag,'ensure_index_compatible'),patch.object(rag,'search_evidence',return_value=result):
        response=rag._retrieve('护城河是什么？ | economic moat',None,4)
    assert len(response['documents'][0])==4
    gateway.embed_query.assert_not_called()


def test_local_lookup_failure_falls_back_to_semantic_search():
    from unittest.mock import Mock, patch
    import rag
    collection=Mock();collection.count.return_value=100
    document='A substantive passage about a durable cost advantage and the returns it protects. '*3
    collection.query.return_value={'documents':[[document]],'metadatas':[[{'source_file':'letter','source_label':'Letter','author':'Warren Buffett'}]],'distances':[[0.1]]}
    gateway=Mock();gateway.embed_query.return_value=[1.,0.]
    with patch.object(rag,'_get_collection',return_value=collection),patch.object(rag,'get_embedding_gateway',return_value=gateway),patch.object(rag,'ensure_index_compatible'),patch.object(rag,'search_evidence',side_effect=OSError('fixture')):
        response=rag._retrieve('护城河是什么？ | economic moat',None,4)
    assert response['documents'][0]==[document]
    gateway.embed_query.assert_called_once()
