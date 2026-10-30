"""카드와 같이 보면 좋은 병원 공식 유튜브 영상 (2026-10-31 사용자 승인, 주 3회 실험).

- 대학병원 공식 채널의 공개 RSS(API 키 불필요)에서 최신 영상을 모은다. 개인 유튜버는 의학적으로 틀린 내용이 섞일 수 있어 쓰지 않는다.
- 카드 주제와 확실히 맞는 영상이 있을 때만 출처 답글에 붙인다 (본문 대신 답글: 외부 링크는 첫 글에 두지 않는다).
- RSS·판단이 실패해도 카드 게시는 그대로 한다.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, Field

from src.channel import BANNED_WORDS, SENSITIVE_PATTERNS
from src.http_client import HttpGet
from src.llm import LLMClient, load_prompt

FEED_URL = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'
# 2026-10-31 확인한 공식 채널 (채널 페이지 이름 확인). 질병관리청은 공식 채널 주소를 확정하지 못해 뺐다.
CHANNELS = (
    ('서울아산병원', 'UC08tP3KIyCK9vYNZm5qQuiw'),
    ('삼성서울병원', 'UCB3BKKiUtMYuPoagCSTyn1Q'),
    ('세브란스', 'UCIqNAJC8l8rCAXOZPyfyG0Q'),
    ('분당서울대병원', 'UCzp_EKglYlon4-hOCF6tdfw'),
)
WEEKDAYS = (0, 2, 4)  # 월·수·금 카드에만 (성과를 영상 없는 날과 비교하려고)
MIN_SCORE = 8
_ATOM = '{http://www.w3.org/2005/Atom}'
_YT = '{http://www.youtube.com/xml/schemas/2015}'
_SENSITIVE_RE = re.compile('|'.join(SENSITIVE_PATTERNS)) if SENSITIVE_PATTERNS else None


@dataclass(frozen=True)
class Video:
    channel: str
    title: str
    video_id: str

    @property
    def url(self) -> str:
        return f'https://www.youtube.com/watch?v={self.video_id}'


class VideoPick(BaseModel):
    index: int = Field(description='고른 영상 번호, 맞는 영상이 없으면 -1')
    score: int = Field(description='카드 주제와 맞는 정도 1~10점')
    reason: str = Field(description='판단 근거 한 문장')


def parse_feed(xml_text: str, channel: str) -> list[Video]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    videos = []
    for entry in root.findall(f'{_ATOM}entry'):
        title = ' '.join((entry.findtext(f'{_ATOM}title') or '').split())  # \xa0 등 공백 정리
        video_id = (entry.findtext(f'{_YT}videoId') or '').strip()
        if title and video_id and allowed(title):
            videos.append(Video(channel, title, video_id))
    return videos


def allowed(title: str) -> bool:
    """약·시술·특정 환자군 같은 민감 주제, 과장 표현이 든 제목은 뺀다 (뉴스 기사와 같은 기준)."""
    if _SENSITIVE_RE and _SENSITIVE_RE.search(title):
        return False
    return not any(w in title for w in BANNED_WORDS)


def fetch_videos(get: HttpGet) -> list[Video]:
    videos: list[Video] = []
    for name, channel_id in CHANNELS:
        try:
            videos += parse_feed(get(FEED_URL.format(channel_id)), name)
        except Exception as e:  # noqa: BLE001 - 한 채널이 안 열려도 나머지는 계속
            print(f'[영상] {name} RSS 실패: {e.__class__.__name__}')
    return videos


def wanted(day: date | None) -> bool:
    return day is not None and day.weekday() in WEEKDAYS


def pick_video(llm: LLMClient, model: str, card_text: str, videos: Sequence[Video]) -> Video | None:
    if not videos:
        return None
    listing = '\n'.join(f'{i}. [{v.channel}] {v.title}' for i, v in enumerate(videos))
    result = llm.parse(model, load_prompt('video'), f'--- 카드 ---\n{card_text}\n\n--- 영상 목록 ---\n{listing}', VideoPick)
    print(f'[영상 판단] {result.index}번 {result.score}점: {result.reason}')
    if result.score < MIN_SCORE or not 0 <= result.index < len(videos):
        return None
    return videos[result.index]


def video_tail(video: Video) -> str:
    return f'\n\n🎥 같이 보면 좋은 영상 ({video.channel})\n{video.title}\n{video.url}'
