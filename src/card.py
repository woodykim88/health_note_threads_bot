"""오늘의 한 장 카드: 기사 핵심을 표·체크리스트 한 장(1080×1350)으로 그린다 (2026-10-31 사용자 승인).

- 저장·공유하고 싶은 정보 카드로 건강노트를 다른 건강 계정과 구별한다 ("리포스트해 줘" 같은 부탁은 쓰지 않는다).
- 글자는 이미지 AI가 아니라 코드가 Pretendard 글꼴로 정확히 넣는다 (한글이 깨지거나 수치가 바뀌지 않게, 비용 0원).
- 칸에 다 안 들어가면 CardError → 글로만 게시한다 (회차를 건너뛰지 않음).
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src import channel

FONTS = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
WIDTH, HEIGHT, MARGIN = 1080, 1350, 70
INNER = WIDTH - MARGIN * 2
WEEKDAYS = '월화수목금토일'

BG = '#FFF7EC'
INK = '#1F2A24'
SUB = '#6B6258'
GREEN = '#2F8F6B'
GREEN_SOFT = '#E3F1EA'
WHITE = '#FFFFFF'
LINE = '#EADFCF'

ITEM_SIZES = (40, 37, 34, 31)  # 칸이 넘치면 글자를 조금씩 줄여 다시 맞춘다


class CardError(Exception):
    """카드를 그리지 못했을 때 (글로만 게시하고 계속 진행)."""


@dataclass(frozen=True)
class CardContent:
    title: str
    subtitle: str
    items: tuple[str, ...]
    action: str
    source: str  # "헬스조선" 같은 매체 이름


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f'Pretendard-{weight}.otf'), size)


def wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """띄어쓰기 단위로 줄을 나누고, 한 단어가 너무 길면 글자 단위로 자른다."""
    lines: list[str] = []
    current = ''
    for word in ' '.join(text.split()).split(' '):
        trial = f'{current} {word}'.strip()
        if font.getlength(trial) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = ''
        for ch in word:
            if font.getlength(current + ch) > width:
                lines.append(current)
                current = ''
            current += ch
    if current:
        lines.append(current)
    return lines


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    return int(font.size * 1.32)


@dataclass(frozen=True)
class _Layout:
    title: list[str]
    subtitle: list[str]
    items: list[list[str]]
    action: list[str]
    item_font: ImageFont.FreeTypeFont


TITLE_FONT = ('ExtraBold', 74)
SUBTITLE_FONT = ('Medium', 36)
ACTION_FONT = ('Bold', 40)
ITEM_PAD, ITEM_GAP, BADGE = 26, 18, 56
TOP_Y, FOOTER_H = 150, 90
MAX_EXTRA = 26


def _layout(content: CardContent, item_size: int) -> tuple[_Layout, int]:
    """(줄 나눔 결과, 아래 여백 위치까지의 총 높이)."""
    title_f, sub_f, act_f = _font(*TITLE_FONT), _font(*SUBTITLE_FONT), _font(*ACTION_FONT)
    item_f = _font('SemiBold', item_size)
    layout = _Layout(wrap(content.title, title_f, INNER), wrap(content.subtitle, sub_f, INNER),
                     [wrap(t, item_f, INNER - BADGE - ITEM_PAD * 3) for t in content.items],
                     wrap(content.action, act_f, INNER - ITEM_PAD * 2), item_f)
    y = TOP_Y + len(layout.title) * _line_height(title_f) + 14 + len(layout.subtitle) * _line_height(sub_f) + 40
    for lines in layout.items:
        y += max(BADGE, len(lines) * _line_height(item_f)) + ITEM_PAD * 2 + ITEM_GAP
    y += 16 + 50 + len(layout.action) * _line_height(act_f) + ITEM_PAD * 2
    return layout, y


def fit(content: CardContent) -> tuple[_Layout, int]:
    """(줄 나눔 결과, 남는 세로 공간). 남는 공간은 항목 칸을 키우는 데 쓴다 (항목이 적을 때 아래가 비지 않게)."""
    if len(content.title.strip()) == 0 or not content.items:
        raise CardError('카드 제목이나 항목이 비어 있습니다.')
    for size in ITEM_SIZES:
        layout, bottom = _layout(content, size)
        if len(layout.title) <= 2 and len(layout.subtitle) <= 2 and bottom <= HEIGHT - FOOTER_H:
            return layout, HEIGHT - FOOTER_H - bottom
    raise CardError('카드 내용이 한 장에 다 들어가지 않습니다 (제목 2줄·항목 글자 수 초과).')


def _header(draw: ImageDraw.ImageDraw, day: date) -> None:
    label_f = _font('Bold', 30)
    label = f'{channel.NAME} · 오늘의 한 장'
    w = int(label_f.getlength(label))
    draw.rounded_rectangle((MARGIN, 64, MARGIN + w + 44, 64 + 56), radius=28, fill=GREEN)
    draw.text((MARGIN + 22, 64 + 28), label, font=label_f, fill=WHITE, anchor='lm')
    stamp = f'{day.month}.{day.day} ({WEEKDAYS[day.weekday()]})'
    draw.text((WIDTH - MARGIN, 64 + 28), stamp, font=_font('Medium', 30), fill=SUB, anchor='rm')


def _items(draw: ImageDraw.ImageDraw, layout: _Layout, y: int, extra: int) -> int:
    badge_f = _font('ExtraBold', 30)
    lh = _line_height(layout.item_font)
    for n, lines in enumerate(layout.items, start=1):
        text_h = len(lines) * lh
        box_h = max(BADGE, text_h) + (ITEM_PAD + extra) * 2
        draw.rounded_rectangle((MARGIN, y, WIDTH - MARGIN, y + box_h), radius=26, fill=WHITE, outline=LINE, width=2)
        cy = y + box_h // 2
        bx = MARGIN + ITEM_PAD
        draw.ellipse((bx, cy - BADGE // 2, bx + BADGE, cy + BADGE // 2), fill=GREEN_SOFT)
        draw.text((bx + BADGE // 2, cy), str(n), font=badge_f, fill=GREEN, anchor='mm')
        ty = cy - text_h // 2
        for line in lines:
            draw.text((bx + BADGE + ITEM_PAD, ty + lh // 2), line, font=layout.item_font, fill=INK, anchor='lm')
            ty += lh
        y += box_h + ITEM_GAP + extra
    return y


def _action(draw: ImageDraw.ImageDraw, layout: _Layout, y: int) -> None:
    act_f = _font(*ACTION_FONT)
    lh = _line_height(act_f)
    box_h = 50 + len(layout.action) * lh + ITEM_PAD * 2
    draw.rounded_rectangle((MARGIN, y, WIDTH - MARGIN, y + box_h), radius=30, fill=GREEN)
    draw.text((MARGIN + ITEM_PAD, y + ITEM_PAD), '그래서 오늘 할 일', font=_font('Bold', 30), fill='#CFEADD')
    ty = y + ITEM_PAD + 50
    for line in layout.action:
        draw.text((MARGIN + ITEM_PAD, ty), line, font=act_f, fill=WHITE)
        ty += lh


def render(content: CardContent, day: date) -> bytes:
    """카드 한 장을 JPEG 바이트로 그립니다. 칸에 안 들어가면 CardError."""
    layout, spare = fit(content)
    n = len(layout.items)
    extra = min(spare // (3 * n + 1), MAX_EXTRA)  # 칸 위아래 + 칸 사이에 나눠 준다
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _header(draw, day)
    title_f, sub_f = _font(*TITLE_FONT), _font(*SUBTITLE_FONT)
    y = TOP_Y
    for line in layout.title:
        draw.text((MARGIN, y), line, font=title_f, fill=INK)
        y += _line_height(title_f)
    y += 14
    for line in layout.subtitle:
        draw.text((MARGIN, y), line, font=sub_f, fill=SUB)
        y += _line_height(sub_f)
    y += 40 + extra
    y = _items(draw, layout, y, extra)
    _action(draw, layout, y + 16)
    foot_f = _font('Medium', 28)
    foot_y = HEIGHT - 52
    draw.line((MARGIN, foot_y - 34, WIDTH - MARGIN, foot_y - 34), fill=LINE, width=2)
    draw.text((MARGIN, foot_y), f'출처: {content.source} 기사 정리', font=foot_f, fill=SUB, anchor='lm')
    draw.text((WIDTH - MARGIN, foot_y), f'@{channel.HANDLE}', font=foot_f, fill=SUB, anchor='rm')
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=92, optimize=True)
    return out.getvalue()


def content_text(content: CardContent) -> str:
    """검수·사실 확인용: 카드에 들어간 글자를 그대로 이어 붙인 것."""
    return '\n'.join((content.title, content.subtitle, *content.items, content.action))


def numbered(items: Sequence[str]) -> str:
    return '\n'.join(f'{n}. {t}' for n, t in enumerate(items, start=1))
