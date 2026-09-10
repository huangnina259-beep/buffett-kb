import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from types import SimpleNamespace
from unittest.mock import patch
import pytest
import source_reading as reader
from learning_guides import GUIDES,_source


def test_bundled_pairs_are_real_source_selections_and_skip_generation():
    compact=lambda s: ''.join(s.split())
    for entry in reader.bundled().values():
        original=reader.tidy_excerpt(reader._document(entry['source_file']))
        assert compact(entry['original']) in compact(original)
        assert entry['translation'] and entry['status']=='reviewed'
    with patch('ai_gateway.get_generation_gateway',side_effect=AssertionError('not needed')):
        for guide in GUIDES.values():
            for spec in guide['sources']:
                src=_source(*spec)
                cn=reader.source_reading(src['source_file'],src['text'],'cn')
                en=reader.source_reading(src['source_file'],src['text'],'en')
                assert cn['status']=='reviewed' and en['status']=='original'
                assert cn['original']==en['original']


def test_translation_cache_and_chinese_source_direction(tmp_path):
    text='这是一段中文原文。保持原文中的数字2007与条件，不添加额外观点。'
    gateway=SimpleNamespace(complete=lambda *a,**k: SimpleNamespace(text='An English translation with the number 2007.'))
    with patch.object(reader,'_document',return_value=text), patch.object(reader,'bundled',return_value={}), patch.dict('os.environ',{'SOURCE_TRANSLATION_CACHE':str(tmp_path/'cache.db')}), patch('ai_gateway.get_generation_gateway',return_value=gateway) as model:
        result=reader.source_reading('example.md',text,'en')
        again=reader.source_reading('example.md',text,'en')
        assert result==again and result['original_language']=='cn'
        assert result['status']=='machine' and model.call_count==1
        assert reader.source_reading('example.md',text,'cn')['translation'] is None


def test_unverified_or_path_traversal_excerpt_rejected_before_model():
    with pytest.raises(ValueError):reader.source_reading('../secret.md','anything','en')
    with patch.object(reader,'_document',return_value='the actual document'), pytest.raises(ValueError):
        reader.source_reading('letter.md','invented quotation','cn')


def test_formatting_joins_hard_wraps_and_preserves_table_rows():
    text='An example with\na hard wrap.\n\n7\n\nYear      Return\n1980      23.7%\n1981      (5.0)'
    cleaned=reader.tidy_excerpt(text)
    assert 'with a hard wrap' in cleaned
    assert '\n7\n' not in cleaned
    assert '1980      23.7%\n1981      (5.0)' in cleaned


def test_real_chinese_mid_sentence_pdf_page_break_is_recovered():
    file='LiLu_2015_Prospect_of_Value_Investing_in_China_CN.md'
    text=reader._document(file)
    start=text.index('其他人看来');end=text.index('到更多。',start)
    result=reader.source_reading(file,text[start:end],'original','投资股票是公司所有权')
    assert result['original'].startswith('可持续的东西都具有一个共同的特点')
    assert result['original'].endswith('在正确的时候会得到更多。')
    assert '不保 留' not in result['original'] and '\n13\n' not in result['original']
    assert result['boundary_repaired'] and result['original_language']=='cn'
    focus=next(s for s in result['segments'] if s['highlight'])
    assert '所有权' in focus['original']
    assert focus['core'] in focus['original']


def test_english_boundaries_do_not_cut_decimals_or_negations():
    text='An introduction ends here. Mr. Buffett paid $1.35 billion, but this does not guarantee future returns. Another sentence follows.'
    with patch.object(reader,'_clean_document',return_value=text):
        result=reader.source_reading('test.md','paid $1.35 billion, but this does not guarantee','original')
    assert result['original']=='Mr. Buffett paid $1.35 billion, but this does not guarantee future returns.'


def test_wrong_language_translation_is_rejected_and_not_cached(tmp_path):
    text='This source contains enough English to be translated.'
    model=SimpleNamespace(complete=lambda *a,**k:SimpleNamespace(text=text))
    with patch.object(reader,'_clean_document',return_value=text),patch.object(reader,'bundled',return_value={}),patch.dict('os.environ',{'SOURCE_TRANSLATION_CACHE':str(tmp_path/'wrong.db')}),patch('ai_gateway.get_generation_gateway',return_value=model):
        with pytest.raises(RuntimeError,match='language mismatch'):
            reader.source_reading('wrong.md',text,'cn')
        with reader._cache() as db: assert db.execute('SELECT count(*) FROM translations').fetchone()[0]==0


def test_legacy_source_resolution_requires_unique_document(tmp_path):
    folder=tmp_path/'data'/'clean_mds';folder.mkdir(parents=True)
    text='This is a distinctive historical excerpt with enough words.'
    (folder/'old.md').write_text(text)
    with patch.object(reader,'ROOT',tmp_path),patch.object(reader,'_clean_document',return_value=text):
        assert reader.source_reading('',text,'original')['source_file']=='old.md'
        (folder/'duplicate.md').write_text(text)
        with pytest.raises(ValueError,match='多个来源'):reader.source_reading('',text,'original')
