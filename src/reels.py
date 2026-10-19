"""인스타 건강노트 3D릴스(@health_note_shorts) 내용을 Threads 글쓰기에 참고로 붙인다 (2026-10-11 사용자 결정).

- 릴스 제작 폴더(~/Projects/보관-중단/인스타/건강노트-3D릴스)의 ledger.csv·캡션을 scripts/sync_reels.py가 data/reels.json으로 옮긴다
  (GitHub Actions에서는 그 폴더를 볼 수 없어서 저장소에 파일로 둔다).
- 이미 게시된 릴스(날짜가 오늘보다 앞)의 최근 RECENT_DAYS일 분만 쓴다. 예약만 된 릴스를 먼저 말하지 않는다.
- 일상글(casual)은 릴스 주제를 가볍게 묻는 질문의 소재로, 뉴스 글(writer)은 기사가 같은 주제일 때 영상 한 줄 언급으로만 쓴다.
  릴스의 사실 문장은 뉴스 글에 가져오지 않는다 (사실 검증은 기사 본문 기준이라서).
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REELS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'reels.json'
# 2026-10-20 끔: 건강 릴스는 10/18 중단, @health_note_shorts 는 쇼핑 채널 @jjintem.note 로 이름이 바뀌어
# 없는 계정·영상을 글에서 언급하게 된다. 건강 릴스를 다시 시작할 때만 True 로 되돌린다.
ENABLED = False
ACCOUNT = '@health_note_shorts'
RECENT_DAYS = 7
MAX_REELS = 3
PROMPTS = frozenset({'casual', 'writer'})
_POINT_RE = re.compile(r'^\s*\d+\.\s*(.+?)\s*$')
_KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class Reel:
    date: str            # 게시일 (20:00 게시)
    topic: str
    hook: str            # 캡션 첫 줄 (영상 훅 질문)
    points: tuple[str, ...]
    source: str


def today() -> date:
    return datetime.now(_KST).date()


def parse_caption(text: str, topic: str, day: str) -> Reel:
    lines = [ln.strip() for ln in text.splitlines()]
    hook = next((ln for ln in lines if ln), '')
    points: list[str] = []
    if '핵심만 정리' in lines:
        for ln in lines[lines.index('핵심만 정리') + 1:]:
            m = _POINT_RE.match(ln)
            if not m:
                break
            points.append(m.group(1))
    source = next((ln.removeprefix('출처:').strip() for ln in lines if ln.startswith('출처:')), '')
    return Reel(day, topic, hook, tuple(points), source)


def _caption_path(root: Path, day: str, no: str) -> Path | None:
    for path in (root / 'work' / day / 'caption.txt', *([root / 'data' / 'example_caption.txt'] if no == '1' else [])):
        if path.exists():
            return path
    return None


def build_reels(root: Path) -> list[Reel]:
    """제작 폴더의 ledger.csv에서 캡션이 있는 릴스를 날짜순으로 읽는다."""
    ledger = root / 'data' / 'ledger.csv'
    if not ledger.exists():
        return []
    found = []
    with ledger.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            day = (row.get('scheduled_for') or '')[:10]
            topic = re.sub(r'\(.*?\)', '', row.get('topic') or '').strip()
            path = _caption_path(root, day, row.get('no') or '')
            if day and topic and path:
                found.append(parse_caption(path.read_text(encoding='utf-8'), topic, day))
    return sorted(found, key=lambda r: r.date)


def save(found: list[Reel], path: Path = REELS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(r) for r in found], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _load(path: Path) -> list[Reel]:
    try:
        rows = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [Reel(r['date'], r['topic'], r['hook'], tuple(r.get('points', ())), r.get('source', ''))
            for r in rows if isinstance(r, dict) and {'date', 'topic', 'hook'} <= r.keys()]


def recent(now: date, path: Path | None = None) -> list[Reel]:
    """이미 게시된(날짜 < 오늘) 최근 릴스, 최신순 MAX_REELS개."""
    oldest = (now - timedelta(days=RECENT_DAYS)).isoformat()
    rows = [r for r in _load(path or REELS_PATH) if oldest <= r.date < now.isoformat()]
    return sorted(rows, key=lambda r: r.date, reverse=True)[:MAX_REELS]


_CASUAL_RULES = ('이번 일상글은 위 영상 주제 중 하나를 소재로, 그 주제를 가볍게 묻는 질문으로 써 ("너는 ~하는 편이야?", A vs B 고르기 등).\n'
                 '영상 훅 문장을 그대로 베끼지 말고, 영상 속 사실·숫자·효과는 쓰지 마. 링크·계정 이름도 쓰지 마.\n')
_WRITER_RULES = ('기사가 위 영상 중 하나와 같은 주제일 때만, tips의 번호 정리 다음 줄에 "인스타 ' + ACCOUNT +
                 '에 영상으로도 올렸어 🎬"처럼 한 줄을 넣어 (말투는 매번 바꿔). 주제가 다르면 영상 얘기는 하지 마.\n'
                 '영상의 설명·사실은 가져오지 마. 글의 사실은 기사 본문에서만 써.\n')


def brief(name: str, now: date, path: Path | None = None) -> str:
    """name 프롬프트에 붙일 릴스 참고 문단. 해당 없거나 최근 릴스가 없으면 빈 문자열."""
    if not ENABLED or name not in PROMPTS:
        return ''
    rows = recent(now, path)
    if not rows:
        return ''
    lines = [f'- {r.date[5:]} {r.topic}: "{r.hook}"' for r in rows]
    return ('\n\n## 우리 인스타 3D릴스 (' + ACCOUNT + ') 최근 게시 주제\n' + '\n'.join(lines) + '\n'
            + (_CASUAL_RULES if name == 'casual' else _WRITER_RULES))
