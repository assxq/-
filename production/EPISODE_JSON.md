# episode.json 키 설명

`production/<EP>/episode.json` 하나가 한 편의 모든 설정이다. 모든 도구는 `--ep <EP>`로 이 파일을 읽고, 시작할 때 `tools/episode.py`가 키를 검사한다(빠진 키는 렌더 전에 오류로 알려 준다).
새 편은 `production/_template/episode.json`을 `production/<EP>/`로 복사해서 시작한다. 시간 단위는 모두 **초**, 좌표는 **1080×1920 픽셀**이다.

## 최상위
| 키 | 뜻 |
|---|---|
| `id` `title` | 편 번호, 화면에 표시되는 제목 (`TRANSMISSION #001`) |
| `tape_id` `side` | `TAPE 027-001`, `A` |
| `duration` `fps` | 길이(초), 24 고정 |

## overlay (make_overlay.py)
| 키 | 뜻 |
|---|---|
| `date_text` | 항상 마스킹된 날짜 문구 `DATE --/--/----` |
| `rec.period` `rec.on` | REC 점멸 주기 1.6 / 켜짐 0.8 |
| `flicker_until` | 이 시각 전까지 전원 투입 깜빡임(3프레임마다) |
| `ui_static_t` `cover_t` | 정지 UI 이미지 / 커버 프레임으로 뽑을 시각 |
| `type_s` | 자막 한 글자 타이핑 간격 (0.04) |
| `captions[]` | `start`, `until`, `text`(영어 로그 한 줄), `icon`(`icons/png`의 id) |

## audio (make_audio.py)
| 키 | 뜻 |
|---|---|
| `seed` `target_lufs` `ceiling_db` `breath` | 난수 시드, 목표 −16 LUFS, 피크 한계, 숨소리 사용 여부 |
| `mix` | 레벨(dB) 덮어쓰기. 기본값 위에 얹힘 (`room hiss hum reels pad` 베드, 효과음 이름, `reverb_wet`, `reverb_rt60`) |
| `timing.hiss_ramp / hum_ramp / reel_ramp / pad_env / pad_bright / pad_vib / hum_dip_db` | `[시각, 값]` 쌍의 선형 곡선 |
| `timing.pad_env_pow` | 패드 포락선 지수 (기본 1.2) |
| `timing.tape_stop` | `{t, len}` 테이프 멈춤 시점과 길이 |
| `timing.dropouts[]` | 드롭아웃 시작 시각들 |
| `events_start[]`, `events[]` | `[시각, 효과음 이름, 레벨 키, 패닝(−1~1), 리버브 센드]` |
| `relay_ticks` | REC 릴레이 틱: `from until every level wet` |
| `type_ticks` | 자막 글자마다 부드러운 틱: `level wet` |
| `breath_event` | 숨소리 이벤트 하나 (`breath: true`일 때) |
| `marks[]` | `[시각, 설명]` 타임라인 그림(plot_audio.py)용 표식 |

## video (assemble.py)
| 키 | 뜻 |
|---|---|
| `base_image` | 승인된 정지 이미지 (대체 컷과 램프 합성에 사용) |
| `lamp` | `src` 원본 이미지 속 REC 램프 좌표, `out` 화면 좌표, `period` `on` |
| `shots[]` | `id`, `t0`, `t1`. 클립 컷은 `file`(`generated/selected/`), `head`(앞에서 버릴 초), `push{z:[시작,끝], c:[x,y 비율]}`(고정점 기준 줌), `standin[]`(`[시각, 중심x, 중심y, 배율]` 키프레임), `label`. 편집기 컷은 `kind`: `rec_dot`(검정+REC 점), `crt_off`(`from`=이어받을 컷, `len`=꺼지는 길이) |
| `effects[]` | `dissolve{from,to,t0,t1}`, `impact{t,offsets[]}`(픽셀 흔들림), `glitch{t,frames,seed}` |

## review (review_clip.py)
| 키 | 뜻 |
|---|---|
| `ref` | 비교 기준 이미지 (`production/<EP>/` 기준 상대경로) |
| `boxes` | `face` `eyes` `mouth` `lamp` 분석 영역 `[x0,y0,x1,y1]` |

## 규칙
- 프레임은 24fps, 효과는 `t ≥ 시작`인 첫 프레임부터 적용(올림). 램프 위상은 밀리초 정수로 계산한다.
- 자막 문구는 영어 로그 한 줄. 날짜는 항상 마스킹.
- 키를 바꾼 뒤에는 `make_overlay.py` → `make_audio.py` → `make_animatic.py` 순으로 다시 만들고 `--help` 대신 실제로 한 번 돌려 본다.
