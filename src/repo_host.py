"""카드 그림을 이 저장소(공개)에 올려 raw.githubusercontent.com 주소로 쓴다 (R2 비밀값이 없을 때, 2026-10-31).

GitHub Actions 안에서만 쓴다: data/cards/에 저장 → 커밋·푸시 → 주소가 실제로 열릴 때까지 잠깐 기다린다.
실패하면 HostError → 같은 내용을 글로 게시한다.
"""
from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, Mapping
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = ROOT / 'data' / 'cards'
RAW_BASE = 'https://raw.githubusercontent.com'
CHECK_TRIES, CHECK_WAIT_SECONDS = 6, 5


class HostError(Exception):
    """그림을 저장소에 올리지 못했을 때."""


def file_name(slot: str) -> str:
    return f'{slot.replace(":", "")}.jpg'


def raw_url(repository: str, branch: str, slot: str) -> str:
    return f'{RAW_BASE}/{repository}/{branch}/data/cards/{file_name(slot)}'


def _git(*args: str) -> None:
    result = subprocess.run(['git', '-c', 'user.name=github-actions[bot]',
                             '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com', *args],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise HostError(f'git {args[0]} 실패: {result.stderr.strip()[:200]}')


def reachable(url: str) -> bool:
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
    except requests.RequestException:
        return False
    return response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image/')


def make_uploader(env: Mapping[str, str], git: Callable[..., None] = _git, check: Callable[[str], bool] = reachable,
                  sleep: Callable[[float], None] = time.sleep) -> Callable[[bytes, str], str] | None:
    """Actions 안이면 (그림, 슬롯) → 공개 주소 함수, 아니면 None."""
    repository = env.get('GITHUB_REPOSITORY', '').strip()
    branch = env.get('GITHUB_REF_NAME', '').strip() or 'main'
    if env.get('GITHUB_ACTIONS') != 'true' or not repository:
        return None

    def upload(body: bytes, slot: str) -> str:
        CARDS_DIR.mkdir(parents=True, exist_ok=True)
        path = CARDS_DIR / file_name(slot)
        path.write_bytes(body)
        git('add', str(path))
        git('commit', '-m', f'chore: card image {slot} [skip ci]')
        git('pull', '--rebase', '--autostash', '--quiet')  # 기록 파일이 아직 안 커밋된 상태라 autostash
        git('push', '--quiet')
        url = raw_url(repository, branch, slot)
        for _ in range(CHECK_TRIES):
            if check(url):
                return url
            sleep(CHECK_WAIT_SECONDS)
        raise HostError(f'올린 그림 주소가 열리지 않습니다: {url}')

    return upload
