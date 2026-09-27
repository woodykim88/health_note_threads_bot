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

# 수익화 (2026-09-27 사용자 결정): 건강 채널은 제휴 링크를 넣지 않는다 (신뢰·광고 규제). 교차 추천만 한다.
PRODUCT_HOUR: int | None = None
PRODUCT_FROM_END = False
# 교차 추천: 뉴스 글 3개에 1번, 답글 출처 아래에 붙인다 (첫 글에 링크를 달면 노출이 줄어드는 경향이 있어 답글에만)
CROSS_PROMO = '📸 건강 꿀팁은 카드로도 정리 중이에요: 인스타 @health_note_shorts\nhttps://www.instagram.com/health_note_shorts/'
CROSS_PROMO_EVERY = 3

# 일상글 (2026-09-27 사용자 결정): 매일 12:30, 링크·광고 없는 짧은 대화형 글. 지어낸 경험은 쓰지 않는다 (src/casual.py).
CASUAL_HOUR: int | None = 12
CASUAL_FALLBACKS = (  # AI 글이 검수에 두 번 떨어졌을 때 쓰는 준비된 질문 (회차를 건너뛰지 않기 위해)
    '여러분은 하루에 물 몇 잔 정도 드세요? 💧',
    '점심 먹고 졸릴 때 여러분만의 방법 있으세요?',
    '아침형 vs 저녁형, 여러분은 어느 쪽이에요?',
    '오늘 하루 몇 걸음 걸으셨어요? 🚶',
    '요즘 자기 전에 휴대폰 얼마나 보세요?',
)
