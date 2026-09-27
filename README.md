# Threads @health_note_news 자동 게시 (건강노트 · 오늘의 건강 소식)

오늘의 건강 소식 기사 한 건을 스레드(첫 글 + 답글 1개)로 바꿔 하루 2번(08:00, 20:00) Threads에 자동으로 올립니다. 말투는 다정한 해요체입니다.

- 재료: 헬스조선·코메디닷컴·하이닥·헬스경향 공식 RSS. 선별 AI가 채점해서 가장 쓸모 있는 기사를 고르고, 본문을 읽어 글을 씁니다.
- 안전장치: 기사 본문과 사실 대조(근거 없는 숫자·효과 차단), 과장·단정 표현 차단, 1인칭 경험담 차단, 민감 주제 제외.
- 출처: 답글 맨 아래에 매체명과 기사 링크를 코드가 붙입니다. 제휴 링크·광고는 없습니다.
- 텔레그램: 같은 봇, `[Threads 건강노트]`, 명령 `/hn_stop` `/hn_skip` `/hn_resume`
- 정시 실행: `~/Projects/인스타피드 건강뉴스 자동화/scheduler` (Cloudflare 정시 알람). GitHub cron은 예비.
- 채널별 차이는 `src/channel.py`와 `prompts/`뿐입니다. 다른 뉴스 채널(혼자써봄·건강노트)과 코드가 같으니 고칠 때 둘 다 확인하세요.

```
python -m pytest -q
python -m src.main --job preview   # 게시하지 않고 글만 만들기 (output/preview.txt)
```
