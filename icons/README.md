# Station 7 도상 세트 (Icon Set) v1

글자 없이 읽히는 23개 기호. 영상 자막 옆, 웹페이지, 프로필 하이라이트 커버 등에 같은 기호를 반복해서 쓴다.
선례: *Alien*(1979)의 Ron Cobb "Semiotic Standard". (`낡은미래_카세트퓨처리즘_리서치.md` 참고)

**미리 보기: `index.html`을 브라우저로 열면 전체 목록과 규칙이 보인다.**

## 설계 규칙
| 요소 | 의미 |
|---|---|
| **원 틀** | 조작 (CONTROL). 담당관이 하는 일 |
| **사각 틀** | 상태 (STATUS). 관측소의 상태 |
| **삼각 틀** | 경고·부재 (WARNING / ABSENCE) |
| **채워진 그림** | 있다 |
| **속이 빈 그림** | 없다·비어 있다 (예: 보관고의 마지막 빈 칸, 신호 없음, 연락 두절, 회신 없음) |
| **녹색** `#4dff88` | 정상 |
| **앰버** `#ffb000` | 주의 |
| **적색** `#ff3b2f` | 경고·기록 중 |

격자 48×48, 선 굵기 3, 둥근 모서리 없음(miter, butt). 세계관 13-3의 기술·소품 규칙(산업 표지 느낌)에 맞춘다.

## 목록
| 분류 | id | 뜻 | 색 |
|---|---|---|---|
| 조작 | `play` `stop` `rewind` `fast-forward` `eject` | 재생 정지 되감기 빨리감기 꺼내기 | 녹색 |
| 조작 | `record` | 기록 중 | 적색 |
| 조작 | `transmit` `receive` | 송신(퍼져 나가는 호) / 수신(안으로 향하는 화살표) | 녹색 |
| 상태 | `battery` `signal` `tape` `archive` `operator` `station` `city` `time-playing` | 배터리 신호 테이프 보관고 담당관 관측소 도시 재생 중인 시간 | 녹색 |
| 상태 | `door-locked` `date-masked` | 잠긴 문 / 가려진 날짜 | 앰버 |
| 경고 | `low-battery` `no-signal` `no-reply` `end-of-tape` | 배터리 부족 신호 없음 회신 없음 테이프 끝 | 앰버 |
| 경고 | `no-contact` | 연락 두절 | 적색 |

세계관 로그와의 대응 예: `OPERATORS 001-026: NO CONTACT` → `no-contact`, `DOOR: LOCKED.` → `door-locked`, `DATE --/--/----` → `date-masked`, `BATTERY: 62%` → `battery`, `TIME: PLAYING.` → `time-playing`, `CITY: ON. PEOPLE: 0.` → `city`.

## 파일
| 경로 | 용도 |
|---|---|
| `svg/<id>.svg` | 단색 (`currentColor`). 색은 CSS로 지정 |
| `svg-color/<id>.svg` | 기능 색이 고정된 버전 |
| `png/<id>.png` | **영상 편집용** 512px 투명 PNG (색 고정). CapCut·Premiere에 그대로 올린다 |
| `sprite.svg` | `<symbol>` 스프라이트 (`#s7-<id>`) |
| `index.html` | 목록 미리 보기 |
| `tools/build.py` | 아이콘 정의 + 생성기. 이 파일만 고치면 위 결과물이 모두 다시 만들어진다 |
| `tools/render_png.js` | PNG 렌더러 (Playwright 필요) |

## 사용 예
```html
<svg viewBox="0 0 48 48" width="40" height="40" style="color:#4dff88">
  <use href="icons/sprite.svg#s7-battery"/>
</svg>
```

## 사용 지침
- **최소 크기 32px.** 삼각 틀의 아이콘은 16px 이하에서 읽히지 않는다. 영상에서는 **64px 이상**을 권장한다.
- **한 화면에 아이콘은 1~2개.** 로그 자막 옆에 놓아 글을 보조한다.
- 아이콘 색을 임의로 바꾸지 않는다. (녹색/앰버/적색 규칙이 깨진다)
- 새 아이콘은 `tools/build.py`의 `ICONS`에 추가하고, **틀 모양 → 채움/빈 → 색** 순서로 정한다.

## 다시 만들기
```bash
python3 icons/tools/build.py                 # svg, svg-color, sprite, index.html
node icons/tools/render_png.js               # png (Playwright 필요)
# Chromium 경로가 필요하면: CHROMIUM_PATH=/path/to/chrome node icons/tools/render_png.js
```
