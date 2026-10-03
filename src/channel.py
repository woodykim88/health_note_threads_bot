"""채널별 설정. 두 Threads 뉴스 채널(혼자써봄·건강노트)은 이 파일과 prompts/만 다르고 나머지 코드는 같다."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    publisher: str
    url: str


NAME = '건강노트'
HANDLE = 'health_note_news'
TOPIC = '오늘의 건강 소식'
CMD_PREFIX = 'hn'  # 텔레그램 명령: /hn_stop /hn_skip /hn_resume (다른 Threads 채널과 겹치지 않게)

# 인스타 건강노트와 같은 건강 전문 매체 공식 RSS (네 곳 모두 robots.txt가 수집을 허용, 2026-09-27 확인)
FEEDS = (
    Feed('헬스조선', 'https://health.chosun.com/site/data/rss/rss.xml'),
    Feed('코메디닷컴', 'https://kormedi.com/feed/'),
    Feed('하이닥', 'https://news.hidoc.co.kr/rss/allArticle.xml'),
    Feed('헬스경향', 'https://www.k-health.com/rss/allArticle.xml'),
)

# 생활 속 건강 소식과 거리가 먼 기사 (선별 LLM 전에 걸러 비용 절약). 제목에서 찾는다.
EXCLUDED_TITLE_WORDS = (
    '[카드뉴스]', '[포토]', '[인사]', '[부고]', '반려동물', '고양이', '강아지', '의료계', '의대', '전공의', '병원장',
    '보험', '수가', '제약', '신약', '임상시험', '투자', '주가', '마약', '숨져', '사망', '응급수술', '성형', '시술', '노출',
)
# 자동 게시에서 빼는 주제 (인스타 건강노트 기준과 같음): 약·영양제·시술, 특정 환자군 치료, 연예인 외모, 사건사고
SENSITIVE_PATTERNS = (
    r'항암', r'암 치료', r'항우울', r'정신과 약', r'조현병', r'자살', r'임신', r'임산부', r'수유', r'신생아', r'영유아',
    r'소아', r'비만치료제', r'위고비', r'마운자로', r'다이어트약', r'영양제', r'보충제', r'건강기능식품',
    r'추출물', r'복용', r'처방', r'시술', r'수술', r'성형', r'필러', r'보톡스', r'줄기세포', r'주사',
    r'뒤태', r'몸매', r'비키니', r'숨진', r'사망', r'마약', r'응급실',
)

# 효능 단정·과장·의료광고성 표현 (본문 전체 검사, 인스타 건강노트 기준과 같음)
BANNED_WORDS = (
    '완치', '치료된다', '치료돼요', '치료 효과', '예방된다', '예방돼요', '예방할 수 있', '막아준', '막아줘',
    '특효', '기적', '무조건', '100%', '부작용 없', '약 대신', '낫는', '낫습니다', '만병', '해독', '디톡스',
    '충격', '경악', '소름', '암이 사라', '살이 쫙',
    '복용량', '약을 끊', '약을 줄', '영양제', '건강기능식품', '병원 추천',
)

# 수익화 (2026-09-27 사용자 결정): 건강 채널은 제휴 링크를 넣지 않는다 (신뢰·광고 규제).
PRODUCT_HOUR: int | None = None
PRODUCT_FROM_END = False
# 교차 추천 (2026-10-03 사용자 결정): 다른 채널 추천은 그만하고 답글 끝엔 기사 출처만 붙인다.
CROSS_PROMO = ''
CROSS_PROMO_EVERY = 3

# 말투 (2026-09-30 사용자 결정): 반말 + 친근하고 유머러스하게 (prompts/writer.md·casual.md)
# 일상글 (2026-09-27 사용자 결정): 매일 12:30, 링크·광고 없는 짧은 대화형 글. 지어낸 경험은 쓰지 않는다 (src/casual.py).
CASUAL_HOUR: int | None = 12
CASUAL_FALLBACKS = (  # AI 글이 검수에 두 번 떨어졌을 때 쓰는 준비된 질문 (회차를 건너뛰지 않기 위해)
    '솔직히 오늘 물 몇 잔 마셨어? 커피는 빼고 ㅋㅋ 💧',
    '점심 먹고 쏟아지는 졸음, 너만의 필살기 있어?',
    '아침형 인간 vs 새벽 2시까지 폰 보는 인간, 너는 어느 쪽? 🌙',
    '오늘 몇 걸음 걸었어? 집-회사-집 코스면 손 ✋',
    '자기 전에 "5분만" 하고 폰 본 거 몇 분 됐어? 📱',
)
