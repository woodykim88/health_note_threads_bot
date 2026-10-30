"""카드 그림 올리기: Cloudflare R2(인스타·하루 채널과 같은 버킷, threads-health/ 경로)에 올리고 공개 주소를 돌려준다.

하루 채널 src/image.py의 업로드 부분을 옮겨 왔다. 실패하면 R2Error → 글로만 게시한다.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

KEY_PREFIX = 'threads-health'
R2_ENV_KEYS = ('R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET', 'R2_PUBLIC_BASE_URL')


class R2Error(Exception):
    """그림을 올리지 못했을 때."""


@dataclass(frozen=True)
class R2Config:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket: str
    public_base_url: str


def load_r2_config(env: Mapping[str, str]) -> R2Config | None:
    """다섯 값이 모두 있으면 설정, 하나도 없으면 None (카드 끔). 일부만 있으면 R2Error."""
    values = {k: (env.get(k) or '').strip() for k in R2_ENV_KEYS}
    missing = [k for k, v in values.items() if not v]
    if len(missing) == len(R2_ENV_KEYS):
        return None
    if missing:
        raise R2Error(f'R2 설정이 비어 있습니다: {", ".join(missing)}')
    return R2Config(values['R2_ACCOUNT_ID'], values['R2_ACCESS_KEY_ID'], values['R2_SECRET_ACCESS_KEY'],
                    values['R2_BUCKET'], values['R2_PUBLIC_BASE_URL'].rstrip('/'))


def object_key(slot: str) -> str:
    """threads-health/2026/10/2026-10-31T0800-1a2b3c4d.jpg"""
    digest = hashlib.sha256(slot.encode()).hexdigest()[:8]
    return f'{KEY_PREFIX}/{slot[:4]}/{slot[5:7]}/{slot.replace(":", "")}-{digest}.jpg'


def upload(config: R2Config, slot: str, body: bytes, s3: Any = None) -> str:
    try:
        if s3 is None:
            import boto3

            s3 = boto3.client('s3', endpoint_url=f'https://{config.account_id}.r2.cloudflarestorage.com',
                              aws_access_key_id=config.access_key_id,
                              aws_secret_access_key=config.secret_access_key, region_name='auto')
        key = object_key(slot)
        s3.put_object(Bucket=config.bucket, Key=key, Body=body, ContentType='image/jpeg',
                      CacheControl='public, max-age=31536000, immutable')
    except Exception as e:  # noqa: BLE001 - 업로드 실패는 글 게시를 막지 않는다
        raise R2Error(f'{e.__class__.__name__}: {str(e)[:200]}') from e
    return f'{config.public_base_url}/{key}'
