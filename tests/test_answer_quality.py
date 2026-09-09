import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import rag

def result(docs, distances, author='Warren Buffett'):
    return {'documents':[docs], 'metadatas':[[{'author':author,'source_label':'Letter','year':2007} for _ in docs]], 'distances':[distances]}

def test_query_preserves_conditions_and_multiauthor_scope():
    q='比较巴菲特与芒格：一家亏损的公司是否可能有护城河？'
    query, params, where=rag._extract_search_params(q,[])
    assert q in query
    assert 'economic moat' in query
    assert params['author'] is None
    assert where is None

def test_year_filters_work_next_to_chinese_and_munger_is_not_doc_type():
    query, params, where=rag._extract_search_params('芒格在2001年怎么解释护城河？',[])
    assert params['year']==2001
    assert params['doc_type'] is None

def test_global_ranking_precedes_author_cap():
    merged=rag._merge_results(result(['weak1','weak2'],[0.9,0.8]),result(['best'],[0.1]),top_k=1,max_per_author=1)
    assert merged['documents'][0]==['best']

def test_matched_passage_not_document_start_is_sent_to_model(tmp_path):
    folder=tmp_path/'data'/'clean_mds'; folder.mkdir(parents=True)
    (folder/'letter.md').write_text('UNRELATED PREFACE '*1000+'\nexact evidence\n'+'UNRELATED FOOTER '*1000)
    r=result(['exact evidence'],[0.1]);r['metadatas'][0][0]['source_file']='letter.md'
    with patch.object(rag,'ROOT_DIR',tmp_path):
        context,sources=rag._format_context(r)
    assert 'exact evidence' in context
    assert 'UNRELATED' not in context
    assert sources[0]['title']=='Letter'
    assert 'exact evidence' in sources[0]['full_context']
