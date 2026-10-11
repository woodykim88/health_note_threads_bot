import json
from datetime import date

from src import llm, reels

CAPTION = """허리에서 우두둑 소리가 나면, 괜찮은 걸까요?

소리의 원인은 척추 관절 속 기체 방울과 관련된 것으로 알려져 있어요.

핵심만 정리
1. 허리 우두둑은 기체 방울과 관련된 소리로 알려져 있어요
2. 통증이 없다면 대체로 괜찮다고 보지만, 세게 꺾는 건 피하세요
3. 뻐근할 땐 꺾기보다 천천히 스트레칭해 주세요
4. 저림이나 통증이 있으면 진료를 받으세요

여러분은 허리 꺾는 편인가요?
다음 편 예고: 다리 꼬는 습관

출처: Healthline 'What Happens When You Crack Your Back?'
※ 일반적인 건강 정보예요.

#허리 #허리우두둑
"""

LEDGER = """no,topic,flow_account,scheduled_for,reel_url
1,목 우두둑(목 꺾기),수동,2026-10-11 오후,https://x/1
3,허리 우두둑(허리 꺾기),u3,2026-10-13 20:00,(게시 후 기입)
"""


def test_parse_caption_keeps_hook_points_and_source():
    r = reels.parse_caption(CAPTION, '허리 우두둑', '2026-10-13')
    assert r.hook == '허리에서 우두둑 소리가 나면, 괜찮은 걸까요?'
    assert len(r.points) == 4 and r.points[0].startswith('허리 우두둑은')
    assert r.source.startswith('Healthline')
    assert r.topic == '허리 우두둑' and r.date == '2026-10-13'


def test_parse_caption_without_summary_has_no_points():
    r = reels.parse_caption('질문이에요?\n\n본문만 있어요.', '주제', '2026-10-13')
    assert r.points == () and r.hook == '질문이에요?'


def test_build_reels_reads_ledger_and_captions(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'ledger.csv').write_text(LEDGER, encoding='utf-8')
    (tmp_path / 'data' / 'example_caption.txt').write_text(CAPTION.replace('허리', '목'), encoding='utf-8')
    (tmp_path / 'work' / '2026-10-13').mkdir(parents=True)
    (tmp_path / 'work' / '2026-10-13' / 'caption.txt').write_text(CAPTION, encoding='utf-8')
    found = reels.build_reels(tmp_path)
    assert [(r.date, r.topic) for r in found] == [('2026-10-11', '목 우두둑'), ('2026-10-13', '허리 우두둑')]
    assert found[0].hook.startswith('목에서')


def test_build_reels_skips_rows_without_caption(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'ledger.csv').write_text(LEDGER, encoding='utf-8')
    assert reels.build_reels(tmp_path) == []


def _store(tmp_path, rows):
    path = tmp_path / 'reels.json'
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    return path


ROWS = [{'date': '2026-10-11', 'topic': '목', 'hook': '목 훅?', 'points': ['a'], 'source': 's'},
        {'date': '2026-10-12', 'topic': '이어폰', 'hook': '이어폰 훅?', 'points': ['b'], 'source': 's'},
        {'date': '2026-10-13', 'topic': '허리', 'hook': '허리 훅?', 'points': ['c'], 'source': 's'}]


def test_brief_only_includes_reels_already_posted(tmp_path):
    brief = reels.brief('casual', date(2026, 10, 13), _store(tmp_path, ROWS))
    assert '이어폰 훅?' in brief and '목 훅?' in brief
    assert '허리 훅?' not in brief  # 10/13 20:00 게시 전


def test_brief_drops_old_reels(tmp_path):
    brief = reels.brief('casual', date(2026, 10, 30), _store(tmp_path, ROWS))
    assert brief == ''


def test_brief_is_empty_without_file_or_for_other_prompts(tmp_path):
    assert reels.brief('casual', date(2026, 10, 13), tmp_path / 'none.json') == ''
    assert reels.brief('product', date(2026, 10, 13), _store(tmp_path, ROWS)) == ''


def test_brief_rules_differ_by_prompt(tmp_path):
    path = _store(tmp_path, ROWS)
    casual = reels.brief('casual', date(2026, 10, 13), path)
    writer = reels.brief('writer', date(2026, 10, 13), path)
    assert '질문' in casual and '핵심' not in casual
    assert '같은 주제일 때만' in writer


def test_load_prompt_appends_reel_brief(tmp_path, monkeypatch):
    monkeypatch.setattr(reels, 'REELS_PATH', _store(tmp_path, ROWS))
    monkeypatch.setattr(reels, 'today', lambda: date(2026, 10, 13))
    assert '이어폰 훅?' in llm.load_prompt('casual')
    assert '이어폰 훅?' not in llm.load_prompt('factcheck')
