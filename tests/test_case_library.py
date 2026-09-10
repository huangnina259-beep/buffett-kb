import json
from pathlib import Path
import server
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]

def test_cases_have_distinct_rounds_and_verifiable_readings():
    cases=server.CASE_LIBRARY
    assert len(cases)>=5
    questions=set()
    for key,case in cases.items():
        assert len(case['rounds'])==5
        assert case['reading']['excerpt'] in (ROOT/'data/clean_mds'/case['reading']['file']).read_text()
        assert case['synthesis_query']
        for item in case['rounds']:
            assert item['cn']['question'] not in questions
            questions.add(item['cn']['question'])
            assert item['en']['question'] and item['retrieval_query']

def test_catalog_is_injected_and_invalid_case_is_rejected():
    client=TestClient(server.app)
    page=client.get('/gym.html')
    assert page.status_code==200
    assert '__CASE_LIBRARY__' not in page.text
    assert all(key in page.text for key in server.CASE_LIBRARY)
    for case,round in [('unknown',0),('sees',-1),('geico',5)]:
        response=client.post('/gym/feedback',json={'case_id':case,'round':round,'question':'q','answer':'a'})
        assert response.status_code==422
