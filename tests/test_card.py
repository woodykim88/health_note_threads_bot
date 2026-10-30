"""오늘의 한 장 카드 (2026-10-31): 카드 그리기, 카드 원고 검수, 그림 글 게시와 실패 시 글 게시."""
import io
from datetime import date

import pytest
from PIL import Image

from src import card, channel, compose, history, post, r2
from src.models import CardPost, ClaimCheck, FactCheck
from tests.helpers import AT_08, ARTICLES, BODY, fake_llm, selection
from tests.test_threads_bot import MODELS, OK_FACTS, OK_ROUTES, POST, client

CARD_POST = CardPost(
    hook='목 따끔한데 감긴지 독감인지 매번 헷갈리지 ㅠㅠ 한 장으로 정리함 📌\n너는 아프면 병원파 vs 버티기파?',
    title='감기 vs 독감, 이렇게 달라', subtitle='환절기 열·기침 날 때 구별법',
    items=['감기: 콧물·목 아픔부터 서서히', '독감: 고열이 갑자기 훅', '독감은 온몸 근육통이 같이 와'],
    action='고열이 갑자기 오르면 진료 받기')
CONTENT = compose.to_content(CARD_POST, '헬스조선')
ENV = {'PUBLISH_TIMES': '08:00,12:30'}
SLOT = '2026-09-27T08:00'


def test_render_makes_portrait_jpeg():
    body = card.render(CONTENT, date(2026, 10, 31))
    img = Image.open(io.BytesIO(body))
    assert img.format == 'JPEG' and img.size == (card.WIDTH, card.HEIGHT)


def test_render_rejects_content_that_does_not_fit():
    long = card.CardContent('제목', '부제', tuple('아주 긴 항목 문장 ' * 12 for _ in range(5)), '할 일', '매체')
    with pytest.raises(card.CardError):
        card.render(long, date(2026, 10, 31))


def test_wrap_breaks_long_word_by_characters():
    font = card._font('SemiBold', 40)  # noqa: SLF001
    lines = card.wrap('가' * 60, font, 400)
    assert len(lines) > 1 and all(font.getlength(ln) <= 400 for ln in lines)


def test_card_issues_pass_for_good_card():
    assert compose.card_issues(CARD_POST, CONTENT) == []


@pytest.mark.parametrize('change, expected', [
    ({'items': ['하나', '둘']}, '3~5개'),
    ({'title': '가' * 30}, 'title'),
    ({'hook': '물음표 없는 첫 글이야'}, '질문'),
    ({'hook': '이거 리포스트해 둬! 너는 어때?'}, '직접 참여 부탁'),
    ({'action': '영양제 챙겨 먹기'}, '과장·단정'),
])
def test_card_issues_catch_problems(change, expected):
    bad = CARD_POST.model_copy(update=change)
    issues = compose.card_issues(bad, compose.to_content(bad, '헬스조선'))
    assert any(expected in i for i in issues), issues


def run_card(responses, bodies=None):
    llm, client_ = fake_llm(responses)
    bodies = bodies or {}
    draft = compose.compose(llm, MODELS, (), lambda: list(ARTICLES), lambda a: bodies.get(a.doc_id, BODY),
                            '2026-09-27', 8)
    return draft, client_


def test_card_slot_writes_card_with_text_fallback_and_source_reply():
    draft, _ = run_card({'SelectionResult': [selection((0, 8))], 'CardPost': [CARD_POST], 'FactCheck': [OK_FACTS]})
    assert draft.kind == compose.CARD and draft.card == compose.to_content(CARD_POST, '컨슈머치')
    assert draft.parts[0] == CARD_POST.hook
    assert '1. 감기: 콧물·목 아픔부터 서서히' in draft.parts[1] and '오늘 할 일' in draft.parts[1]
    assert draft.card_reply == '📰 출처: 컨슈머치\nhttps://news.example/a1'


def test_card_rewrites_after_fact_fail_then_falls_back_to_news():
    bad = FactCheck(claims=[ClaimCheck(sentence='고열', kind='unsupported_fact', reason='기사에 없음')])
    responses = {'SelectionResult': [selection((0, 8), (1, 7))], 'CardPost': [CARD_POST] * 4,
                 'FactCheck': [bad] * 4 + [OK_FACTS], 'ThreadPost': [POST]}
    draft, client_ = run_card(responses)
    assert draft.kind == compose.NEWS and draft.card is None
    assert sum(1 for r in client_.requests if r['text_format'].__name__ == 'SelectionResult') == 1  # 선별은 한 번만


def test_no_card_outside_card_hours(monkeypatch):
    monkeypatch.setattr(channel, 'CARD_HOURS', ())
    draft, _ = run_card({'SelectionResult': [selection((0, 8))], 'ThreadPost': [POST], 'FactCheck': [OK_FACTS]})
    assert draft.kind == compose.NEWS


GOOD_CARD_RUN = {'SelectionResult': [selection((0, 8))], 'CardPost': [CARD_POST], 'FactCheck': [OK_FACTS]}


def card_deps(upload):
    c, graph = client(OK_ROUTES)
    backend = fake_llm(GOOD_CARD_RUN)[0]._backend  # noqa: SLF001
    return post.PostDeps(backend, MODELS, c, lambda: list(ARTICLES), lambda a: BODY, upload_card=upload), graph


def test_card_posts_image_with_source_reply():
    uploaded = []

    def upload(body, slot):
        uploaded.append((body[:2], slot))
        return 'https://cdn.example/card.jpg'

    d, graph = card_deps(upload)
    assert post.run_post(ENV, d, None, AT_08).outcome == 'success'
    creates = [p for m, u, p in graph.calls if u.endswith('/threads')]
    assert creates[0]['media_type'] == 'IMAGE' and creates[0]['image_url'] == 'https://cdn.example/card.jpg'
    assert creates[0]['text'] == CARD_POST.hook
    assert creates[1]['text'].startswith('📰 출처:') and len(creates) == 2
    assert uploaded == [(b'\xff\xd8', SLOT)]  # JPEG
    assert history.find(history.load_history(), SLOT).seed == compose.CARD


def test_card_upload_failure_posts_same_content_as_text():
    def upload(body, slot):
        raise r2.R2Error('down')

    d, graph = card_deps(upload)
    assert post.run_post(ENV, d, None, AT_08).outcome == 'success'
    creates = [p for m, u, p in graph.calls if u.endswith('/threads')]
    assert creates[0]['media_type'] == 'TEXT' and '1. 감기' in creates[1]['text']
    assert history.find(history.load_history(), SLOT).seed == compose.NEWS


def test_r2_config_off_when_empty_and_error_when_partial():
    assert r2.load_r2_config({}) is None
    with pytest.raises(r2.R2Error):
        r2.load_r2_config({'R2_BUCKET': 'b'})
    assert r2.object_key(SLOT).startswith('threads-health/2026/09/2026-09-27T0800-')


def test_r2_upload_returns_public_url():
    class S3:
        def put_object(self, **kw):
            self.kw = kw

    s3 = S3()
    config = r2.R2Config('acc', 'k', 's', 'bucket', 'https://img.example')
    url = r2.upload(config, SLOT, b'jpg', s3)
    assert url == f'https://img.example/{r2.object_key(SLOT)}' and s3.kw['ContentType'] == 'image/jpeg'


def test_repo_host_only_inside_actions():
    from src import repo_host
    assert repo_host.make_uploader({}) is None
    assert repo_host.make_uploader({'GITHUB_ACTIONS': 'true'}) is None  # 저장소 이름 없음


def test_repo_host_commits_pushes_and_waits_for_url(monkeypatch, tmp_path):
    from src import repo_host
    monkeypatch.setattr(repo_host, 'CARDS_DIR', tmp_path)
    calls, checks = [], iter([False, True])
    up = repo_host.make_uploader({'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'me/repo', 'GITHUB_REF_NAME': 'main'},
                                 git=lambda *a: calls.append(a[0]), check=lambda u: next(checks), sleep=lambda s: None)
    url = up(b'jpg', SLOT)
    assert url == 'https://raw.githubusercontent.com/me/repo/main/data/cards/2026-09-27T0800.jpg'
    assert calls == ['add', 'commit', 'pull', 'push'] and (tmp_path / '2026-09-27T0800.jpg').read_bytes() == b'jpg'


def test_repo_host_raises_when_url_never_opens(monkeypatch, tmp_path):
    from src import repo_host
    monkeypatch.setattr(repo_host, 'CARDS_DIR', tmp_path)
    up = repo_host.make_uploader({'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'me/repo'},
                                 git=lambda *a: None, check=lambda u: False, sleep=lambda s: None)
    with pytest.raises(repo_host.HostError):
        up(b'jpg', SLOT)


# --- 같이 보면 좋은 병원 공식 영상 ---

FEED = '''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
<title>세브란스</title>
<entry><yt:videoId>v1</yt:videoId><title>감기와 독감 구별하는 법</title></entry>
<entry><yt:videoId>v2</yt:videoId><title>신장암 수술 후 관리</title></entry>
</feed>'''


def test_parse_feed_drops_sensitive_titles():
    from src import videos
    got = videos.parse_feed(FEED, '세브란스')
    assert got == [videos.Video('세브란스', '감기와 독감 구별하는 법', 'v1')]
    assert got[0].url == 'https://www.youtube.com/watch?v=v1'
    assert videos.parse_feed('not xml', '세브란스') == []


def test_video_only_on_mon_wed_fri():
    from src import videos
    assert videos.wanted(date(2026, 9, 28)) and not videos.wanted(date(2026, 9, 27)) and not videos.wanted(None)


def run_card_on(today, responses, vids):
    llm, client_ = fake_llm(responses)
    draft = compose.compose(llm, MODELS, (), lambda: list(ARTICLES), lambda a: BODY, today, 8, load_videos=lambda: vids)
    return draft, client_


def test_card_adds_matching_video_to_source_reply_on_monday():
    from src import videos
    from src.videos import VideoPick
    vids = [videos.Video('세브란스', '감기와 독감 구별하는 법', 'v1')]
    responses = {'SelectionResult': [selection((0, 8))], 'CardPost': [CARD_POST], 'FactCheck': [OK_FACTS],
                 'VideoPick': [VideoPick(index=0, score=9, reason='같은 주제')]}
    draft, _ = run_card_on('2026-09-28', responses, vids)
    assert draft.card_reply.endswith('🎥 같이 보면 좋은 영상 (세브란스)\n감기와 독감 구별하는 법\nhttps://www.youtube.com/watch?v=v1')
    assert draft.card_reply.startswith('📰 출처:') and 'watch?v=v1' in draft.parts[1]


def test_card_skips_weak_video_match():
    from src import videos
    from src.videos import VideoPick
    vids = [videos.Video('세브란스', '위암 이야기', 'v9')]
    responses = {'SelectionResult': [selection((0, 8))], 'CardPost': [CARD_POST], 'FactCheck': [OK_FACTS],
                 'VideoPick': [VideoPick(index=0, score=5, reason='부위만 겹침')]}
    draft, _ = run_card_on('2026-09-28', responses, vids)
    assert '🎥' not in draft.card_reply


def test_card_survives_video_failure():
    def boom():
        raise RuntimeError('rss down')
    llm, _ = fake_llm({'SelectionResult': [selection((0, 8))], 'CardPost': [CARD_POST], 'FactCheck': [OK_FACTS]})
    draft = compose.compose(llm, MODELS, (), lambda: list(ARTICLES), lambda a: BODY, '2026-09-28', 8, load_videos=boom)
    assert draft.kind == compose.CARD and '🎥' not in draft.card_reply
