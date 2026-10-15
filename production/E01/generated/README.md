# generated/ — AI가 만든 파일을 모으는 곳

| 폴더 | 내용 | git |
|---|---|---|
| `images/` | 입력 이미지 세트: `A-H.png` `A-L.png` `A-W.png` `B1.png` `B2.png` `C.png` | 추적 |
| `bakeoff/` | 도구 비교 테스트 클립: `<도구>_<번호>.mp4` (예: `kling_01.mp4`) | 무시 |
| `candidates/C1~C4, S6/` | 클립 후보: `<클립>_<도구>_k<번호>_s<시드>.mp4` | 무시 |
| `review/` | `review_clip.py`가 만든 `sheet.png`, `metrics.png` | 무시 |
| `selected/` | **최종 선택 파일**: `C1.mp4` `C2.mp4` `C3.mp4` `C4.mp4` `S6_C.png` | 추적 |
| `LOG.csv` | 생성 기록 (도구, 시드, 프롬프트 단계, 검수 수치, 판정) | 추적 |

`selected/`의 파일 이름은 **정확히** 위와 같아야 `assemble.py`가 인식한다. (파일 이름은 `../episode.json`의 `video.shots[].file`에서 정해진다)
후보 영상은 용량이 커서 git에 올리지 않는다. (본인 PC나 클라우드 드라이브에 보관)
