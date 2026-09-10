import json
import re
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import learning_guides as guides
import rag


def test_all_guides_have_real_evidence_and_valid_citations():
    for concept in guides.GUIDES:
        result=guides.find_guide(concept+'是什么？')
        assert result and '预先核对' in result['answer']
        for number in re.findall(r'\[来源(\d+)\]',result['answer']):
            assert 1 <= int(number) <= len(result['sources'])
        for source in result['sources']:
            original=(guides.ROOT/'data'/'clean_mds'/f'Buffett_{source["year"]}_Shareholder_Letter.md').read_text()
            assert source['text'] in original


def test_specific_questions_and_conversation_keep_live_retrieval():
    for q in ['护城河为什么消失？','芒格怎么定义护城河？','2000年护城河是什么？','请比较护城河和安全边际','what is a moat?']:
        assert guides.find_guide(q) is None
    assert guides.find_guide('护城河是什么？',[{'role':'user','content':'可口可乐'}]) is None


def test_reviewed_reading_stream_and_blocking_need_no_model_or_vector_calls():
    with patch.object(rag,'_retrieve',side_effect=AssertionError('not needed')), patch.object(rag,'get_generation_gateway',side_effect=AssertionError('not needed')):
        result=rag.query_knowledge_base('护城河是什么？')
        events=[json.loads(s[6:]) for s in rag.stream_query_knowledge_base('护城河是什么？')]
    assert events[-1]['type']=='done'
    assert events[-1]['final_answer']==result['answer']
    assert events[-1]['search_params']['answer_mode']=='reviewed_guide'


def test_missing_primary_source_does_not_serve_unverifiable_reading():
    with patch.object(guides,'_source',side_effect=FileNotFoundError):
        assert guides.find_guide('安全边际是什么？') is None
