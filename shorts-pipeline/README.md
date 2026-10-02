# Shorts Pipeline (반자동 쇼츠 제작 시스템)

주제 수집 → 대본 생성(Claude) → 정책 린트 → 음성 → 자막 → 9:16 렌더 → 승인 → YouTube 업로드 → 성과 수집.

## 왜 "완전 자동"이 아닌가
YouTube는 2026.7부터 AI 음성·템플릿 양산·반복 콘텐츠를 수익화 제외(Generic or Repetitive Content)로 본다 (`../shorts-expert/04-policy-risk.md`).
그래서 **자동화 대상은 반복 작업**, **사람이 남기는 것은 가치를 만드는 3곳**으로 설계했다.

| 단계 | 자동/사람 | 설명 |
|---|---|---|
| 주제 수집 | 자동 | `topics.txt`(수동) + Hacker News, 과거 에피소드와 중복 제거 |
| 대본 | 자동 | Claude가 JSON 대본 생성, `policy.py`가 린트(필수 한계점·면책·과장 문구·과거 대본 유사도 0.6 초과 시 반려) |
| **실제 데모 녹화** | **사람** | `demo_steps`대로 툴을 진짜 실행해 `demo.mp4` 저장 (가짜 결과 금지) |
| **음성** | 사람(기본) | 본인 목소리 `voice.wav`. 옵션: `elevenlabs`/`espeak` 자동 |
| 자막·렌더 | 자동 | ffmpeg: 데모를 1080x1920에 맞추고 블러 배경 + 자막 + 보이스, 59초 상한 검사 |
| **승인** | **사람** | `final.mp4` 확인 후 `approve` (업로드 전 필수, 설정으로 해제 가능) |
| 업로드 | 자동 | 기본 `private` + 예약(`--publish-at`), 하루 상한 |
| 성과 | 자동 | `stats.csv` 누적 (조회/좋아요/댓글) |

## 설치
```bash
cd shorts-pipeline
pip install -r requirements.txt
cp config.example.yaml config.yaml          # 채널명/설정 수정
export ANTHROPIC_API_KEY=...                # 대본 생성
```
YouTube 업로드: Google Cloud에서 YouTube Data API v3 활성화 → OAuth 클라이언트(데스크톱) → `client_secret.json` 저장 → **브라우저 있는 PC에서** `python -m shorts_pipeline.cli auth` 1회 실행 → 생성된 `token.json` 사용. (클라우드 컨테이너엔 브라우저가 없으니 토큰만 복사)

## 사용
```bash
python -m shorts_pipeline.cli topics                 # 후보 주제 확인
python -m shorts_pipeline.cli run collect            # 주제 수집 → 에피소드 생성 → 가능한 데까지 진행
python -m shorts_pipeline.cli status                 # 각 에피소드 대기 단계 확인
#  awaiting_demo → work/<id>/demo.mp4 저장,  needs_voice → voice.wav 저장
python -m shorts_pipeline.cli run                    # 렌더까지 진행 (--mock 은 API키 없이 연습용)
python -m shorts_pipeline.cli approve <id>           # final.mp4 확인 후
python -m shorts_pipeline.cli run --publish-at 2026-10-05T13:00:00Z
python -m shorts_pipeline.cli stats
```
하루 루틴 예: 아침 `run collect` → 데모 3개 녹화(20분) → 목소리 녹음 → `run` → 승인 → 예약 업로드.

## 테스트 상태
- `pytest`: 정책 린트, 자막 타이밍, 단계 게이트, 실제 ffmpeg 렌더(1080x1920, 길이, 오디오), 59초 초과 거부 — **5개 통과**
- **검증 안 됨**(키·계정 필요): Claude 실호출, ElevenLabs, YouTube 업로드/통계, Hacker News 네트워크 호출. 처음엔 `private` 업로드로 확인할 것.
- `containsSyntheticMedia`/`publishAt` 필드는 API 문서 기준으로 작성, 실제 응답 확인 필요.

## 다음 확장 아이디어
- Playwright로 웹 툴 데모 자동 녹화 (로그인/약관 확인 필요, 실제 실행 결과여야 함)
- Studio 지표(이탈률/APV)를 읽어 다음 대본 프롬프트에 반영
- TikTok/Reels 업로드(각 플랫폼 API 승인 필요)
