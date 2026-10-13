# 테스트회사 라이브 대시보드

Paperclip 서버의 상태를 사무실(캐릭터)과 팀 채팅 형태로 보여 주는 조회 전용 대시보드입니다.

## 실시간 실행 (Paperclip과 같은 PC에서)
```
cd dashboard
PAPERCLIP_URL=http://127.0.0.1:3100 PORT=3200 node server.mjs   # Node 18 이상
# 브라우저에서 http://127.0.0.1:3200
```
- 3초마다 Paperclip API를 읽어 캐릭터 상태(작업 중/대기/방금 완료/휴식), 채팅, 일감 보드, 지출을 갱신합니다.
- `server.mjs`는 GET 요청만 중계하고 조회용 경로만 허용합니다. 에이전트·일감·예산을 바꾸지 못합니다.
- 회사가 여러 개면 `?company=<회사 ID>`로 고릅니다.
- 127.0.0.1에만 바인딩합니다. 외부에 노출하지 마세요.

## 재생 전용 페이지 만들기
```
python3 build_replay.py <스냅샷 폴더> replay.html
```
스냅샷 폴더에는 Paperclip API에서 받은 company/agents/issues/runs/comments(.json)가 필요합니다.
만들어진 replay.html은 서버 없이 열리며, 실제 실행 기록을 압축해서 재생합니다.

## 캐릭터
이름별 모양은 `index.html`의 `LOOKS`에 있습니다. 새 에이전트는 기본 모양으로 나옵니다.
