"""인스타 3D릴스 제작 폴더에서 게시 내용을 읽어 data/reels.json으로 옮긴다 (src/reels.py가 글쓰기에 참고로 쓴다).

사용: python3 scripts/sync_reels.py [릴스 제작 폴더]   (기본: ~/Projects/보관-중단/인스타/건강노트-3D릴스)
GitHub Actions는 그 폴더를 볼 수 없으므로, 릴스를 만든 뒤 이 스크립트를 돌리고 data/reels.json을 커밋·푸시한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import reels  # noqa: E402

DEFAULT_ROOT = Path.home() / 'Projects' / '보관-중단' / '인스타' / '건강노트-3D릴스'


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else DEFAULT_ROOT
    found = reels.build_reels(root)
    if not found:
        print(f'[릴스] {root}에서 캡션이 있는 릴스를 찾지 못했습니다. data/reels.json을 바꾸지 않습니다.')
        return 1
    reels.save(found)
    print(f'[릴스] {len(found)}편 저장: ' + ', '.join(f'{r.date} {r.topic}' for r in found))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
