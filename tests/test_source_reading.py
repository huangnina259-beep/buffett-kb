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
