# MLML — Music-to-Light Markup Language

### 완전 명세서 Full Specification v1.3

| 항목 | 내용 |
|---|---|
| 버전 | 1.3 |
| 작성자 | 이영석 (충남대학교 컴퓨터인공지능학부 ) |
| 라이선스 | Apache License 2.0 |
| 포함 범위 | v1.0 + v1.1 + v1.2 전체 블록 + v1.3 신규 (lyric_map SRT, mp3_to_mlml) |

## 버전 히스토리

| 버전 | 핵심 추가 내용 |
|---|---|
| v1.0 | 4계층 구조, 16종 단일 이펙트, 12종 공간 이펙트, EIC/SAS/TA |
| v1.1 | `beat_reactive.on_kick`, `bass_track`, `color_cycle`, KFA/BBC/CCR |
| v1.2 | `global_mood`, `section_defaults`, `expectation_break`, `bookend`, `lyric_map`, `spotlight`|
| v1.3 | `lyric_map` SRT 자동 파싱 + 8종 감정 사전, `mp3_to_mlml` 4단계 파이프라인, archetype 6종, LCC 메트릭 |

---

## 1. 개요

MLML(Music-to-Light Markup Language)은 음악 구조·감성을 BLE/Wi-Fi/Zigbee 조명 장치의
실시간 색상 제어로 변환하기 위한 YAML 기반 선언형 중간 표현 언어입니다.

### 1.1 설계 원칙

1. **하드웨어 독립성** — 동일 스크립트가 응원봉·LED 스트립·Philips Hue·매트릭스 패널에서 동작
2. **음악 구조 이해** — 볼륨·비트를 넘어 구간·감성·가사 감정까지 인코딩
3. **LLM 친화적** — Claude 등 LLM이 단일 추론으로 완전한 스크립트 생성
4. **인간 가독성** — 조명 전문가가 수동 편집 가능한 YAML 구조
5. **확장성** — 새 블록을 하위 호환 방식으로 추가 가능

### 1.2 4계층 구조

| 계층 | 블록 | 역할 |
|---|---|---|
| Global | `metadata`, `palette`, `global_mood`, `global_arc` | 곡 전체 설정 |
| Structural | `timeline`, `section_defaults`, `bookend`, `expectation_break` | 구간 구조 |
| Rhythmic | `beat_reactive`, `bass_track`, `color_cycle`, `spotlight` | 리듬 반응 |
| Semantic | `lyric_map`, `spatial`, `motifs` | 감성·공간 |

### 1.3 13단계 색상 합산 알고리즘 (50fps)

렌더러는 매 프레임(50fps) 아래 13단계를 순서대로 적용해 최종 RGB를 계산합니다.

1. **section_defaults** → 구간 유형별 기본 색상·강도
2. **timeline override** → 개별 이벤트 색상·이펙트
3. **global_mood** → temperature 보정 (warm/cool/energetic)
4. **lyric_map** → 현재 가사 감정색 적용
5. **color_cycle** → 마디 기준 hue 순환
6. **bass_track** → 저주파 에너지 → 밝기 변조
7. **spotlight** → verse 배경 감쇠 (`bg_brightness`)
8. **base_rgb 합산** → `bar_rgb × bass_brightness`
9. **expectation_break** → 암전이면 RGB=(0,0,0) 즉시 반환
10. **blink** → `is_on` 판단
11. **우선순위 오버레이** → kick > onset > blink ON > blink OFF
12. **bookend** → 아웃트로 페이드아웃
13. **intensity 스케일** → `× global_mood.intensity` → 최종 (R,G,B)

---

## 2. metadata — 곡 메타데이터

```yaml
metadata:
  title:     string   # 곡 제목 (필수)
  artist:    string   # 아티스트 (필수)
  bpm:       float    # librosa.beat.beat_track() 권장
  key:       string   # "G_major", "A_minor"
  time_sig:  string   # "4/4", "3/4", "6/8"
  duration:  float    # 총 길이 (초)
  genre:     string   # "k-pop", "ballad", "rock", "r&b"
  mood:      [string] # ["cheerful", "romantic"]
  archetype: string   # KBS 음향 아키타입 6종 [v1.3]
```

### 2.1 archetype 값 — KBS 음향 아키타입 6종 [v1.3]

`mp3_to_mlml`이 BPM·에너지·댄스어빌리티로 자동 추정합니다.

| 값 | 설명 | 조명 전략 |
|---|---|---|
| `BGM_SONG` | 배경음악형 노래 (보컬+반주) | 구간 대비 중심, 풀 파이프라인 |
| `DRAMA_NARR` | 드라마 내레이션 (단일 화자) | 색온도 추적, 비트 반응 없음 |
| `DRAMA_MULTI` | 드라마 다화자 (음악 없음) | 화자 전환 감지 → 색상 전환 |
| `RHYTHM_FAST` | 빠른 리듬 (고에너지) | 스트로브, 폭발 이펙트 |
| `VO_CALM` | 차분한 보이스오버 | 배경음악 구간만 비트 반응 |
| `VO_STANDARD` | 일반 보이스오버 (아나운서) | 중성 백색, 반응 최소 |

---

## 3. palette — 색상 어휘

```yaml
palette:
  <name>:
    hue: int    # 0~360
    sat: float  # 0.0~1.0
    val: float  # 0.0~1.0
```

기본 팔레트 예시:

| 이름 | hue | sat | val | 색상 | 용도 |
|---|---|---|---|---|---|
| primary | 210 | 0.7 | 0.9 | 하늘색 | 버스·인트로 기본 |
| secondary | 40 | 0.8 | 1.0 | 골드 | 프리코러스 |
| warm | 15 | 0.9 | 1.0 | 주황 | 따뜻한 감성 |
| cool | 240 | 0.6 | 0.8 | 보라 | 브릿지·슬픔 |
| peak | 0 | 1.0 | 1.0 | 빨강 | 클라이맥스 |
| neutral | 200 | 0.2 | 0.4 | 회청 | 인트로·아웃트로 |
| white | 0 | 0.0 | 1.0 | 흰색 | 킥 플래시 |
| love | 350 | 0.9 | 1.0 | 분홍 | 사랑 가사 |
| sad | 220 | 0.7 | 0.7 | 파랑 | 슬픔 가사 |
| happy | 45 | 0.9 | 1.0 | 노랑 | 기쁨 가사 |

---

## 4. global_mood — 감성 온도 [v1.2]

```yaml
global_mood:
  temperature: warm   # warm|cool|energetic|mystic|neutral
  intensity:   0.85   # 0.0~1.0 전체 밝기 스케일 (Step 13)
  contrast:    0.75   # 0.0~1.0 구간 대비 강도
```

v1.3: `mp3_to_mlml`이 SRT 지배 감정(`dominant_emotion`)으로 `temperature`를 자동 설정합니다.

| temperature | hue 중심 | 특징 | 대표 장르 |
|---|---|---|---|
| warm | 0~60° | 따뜻함·설렘 | 발라드·사랑 노래 |
| cool | 180~270° | 차가움·슬픔 | 이별·슬픈 곡 |
| energetic | 원색 순환 | 폭발적 | 댄스·파티 |
| mystic | 240~300° | 신비·몽환 | R&B |
| neutral | 설정 그대로 | 수동 제어 | 직접 제어 |

---

## 5. tempo_mode — BPM 자동 파라미터

```yaml
tempo_mode:
  auto: true
  override:
    bars_per_change: 2
    smooth: 0.05
    hz_hi: 20
```

| BPM 범위 | bars_per_change | bass smooth | blink hz_hi |
|---|---|---|---|
| < 80 (발라드) | 8 | 0.20 | 6 |
| 80~120 (중간) | 4 | 0.10 | 12 |
| 120~160 (댄스) | 2 | 0.05 | 20 |
| > 160 (초고속) | 4 | 0.03 | 12 |

---

## 6. lyric_map — 가사 감정 색상 [v1.2 / v1.3 확장]

v1.3에서 SRT 자동 파싱과 8종 감정 키워드 사전, `manual` 블록이 추가됩니다.

```yaml
lyric_map:
  enabled: true
  source:  srt          # srt | text | whisper
  emotion_color:        # 감정 → HSV
    love:      {hue:350, sat:0.90, val:1.00}   # 분홍
    happy:     {hue:45,  sat:0.90, val:1.00}   # 노랑
    romantic:  {hue:330, sat:0.85, val:0.95}   # 로즈
    sad:       {hue:220, sat:0.70, val:0.70}   # 파랑
    hope:      {hue:180, sat:0.55, val:0.90}   # 하늘
    nostalgic: {hue:30,  sat:0.70, val:0.80}   # 황갈
    excited:   {hue:0,   sat:1.00, val:1.00}   # 빨강
    calm:      {hue:200, sat:0.40, val:0.75}   # 청회
  manual:               # SRT 파싱 자동 생성 또는 수동 입력 [v1.3]
    - time:       24.0
      text:       "사랑하는 사람들 앞에서"
      color:      love
      brightness: 0.80
      duration:   3.2
    - time:       156.0
      text:       "I trust my you"
      color:      hope
      brightness: 0.70
      duration:   3.2
```

### 6.1 감정 키워드 사전 [v1.3]

| 감정 | 한국어 키워드 (일부) | 영어 키워드 (일부) | intensity |
|---|---|---|---|
| love | 사랑, 좋아, 그리워, 설레, 두근 | love, adore, miss, heart | 0.80 |
| happy | 행복, 기뻐, 신나, 웃음 | happy, joy, smile, fun | 0.85 |
| romantic | 달빛, 꿈, 함께, 손잡 | dream, forever, together | 0.75 |
| sad | 슬퍼, 눈물, 아파, 힘들 | sad, cry, tears, hurt | 0.55 |
| hope | 희망, 믿어, 괜찮, 다시 | hope, believe, trust, okay | 0.70 |
| nostalgic | 그때, 추억, 기억, 옛날 | memory, remember, past | 0.60 |
| excited | 설레, 두근두근, 기대 | excited, thrill, amazing | 0.95 |
| calm | 편해, 쉬어, 평화, 위로 | calm, peace, comfort, still | 0.45 |

### 6.2 SRT 자동 파싱 흐름 [v1.3]

```
parse_srt(path)         → [{start, end, text}, ...]
  ↓ detect_emotion(text)
analyze_lyrics()        → {manual_map, dominant_emotion, emotion_stats}
  ↓
merge_lyric_into_mlml()
  → lyric_map.source = "srt"
  → lyric_map.manual = 감정별 시각 이벤트
  → global_mood.temperature 지배 감정으로 자동 보정
  → excited/happy 구간 timeline 이벤트 강화
```

SRT 자동 탐색: `--srt` 미지정 시 MP3와 동일 경로의 동일 이름 `.srt` 파일을 자동 사용.

---

## 7. bookend & expectation_break [v1.2]

### 7.1 bookend — 수미상관

```yaml
bookend:
  fade_out_start:    float     # 페이드 시작 시각 (초)
  fade_out_duration: float     # 페이드 지속 시간 (초)
  final_color:       love      # 마지막 색상
  final_state:       blackout  # blackout|single_spot|hold
```

### 7.2 expectation_break — 암전 기법

"예측 → 위반" 원칙. 프리코러스 마지막 1박 암전 후 코러스 폭발.

```yaml
expectation_break:
  enabled: true
  timing:  last_beat   # last_beat|last_2beats|last_bar
  recovery: peak
# timeline에서 사용
- t: 47.5
  group: 0
  color: null
  effect: expectation_break
```

---

## 8. section_defaults — 구간 기본값 [v1.2]

| 구간 | brightness | blink_mode | 특이사항 |
|---|---|---|---|
| intro | 0.25 | none | 낮게 시작, 기대감 조성 |
| verse | 0.55 | beat_sync | spotlight 기본 on |
| prechorus | 0.75 | beat_sync | expectation_break 기본 on |
| chorus | 1.00 | beat_sync | explosion, kick 0.98 |
| bridge | 0.45 | beat_sync | palette_invert (보색) |
| climax | 1.00 | free | 매 마디 전환, kick 1.0 |
| outro | 0.35 | none | fade_to_bookend |

---

## 9. timeline — 시간 기반 이벤트

```yaml
timeline:
  - t:           float   # 이벤트 시각 (초, 필수)
    group:       int     # 0=전체, 1=그룹A, 2=그룹B
    color:       string  # palette 키 | {hue,sat,val} | null
    effect:      string  # 이펙트 이름
    intensity:   float   # 0.0~1.0
    bpm_sync:    bool
    hz:          float   # strobe 주파수
    spatial:     string  # 공간 이펙트
    spotlight:   bool
    bg_brightness: float
    period:      float   # breathe 주기 (초)
    note:        string  # 설명 (렌더러 무시)
```

---

## 10. 리듬 반응 블록 [v1.1]

### 10.1 beat_reactive

```yaml
beat_reactive:
  on_kick:  {color: white,     duration: 0.04, strength: 0.98}
  on_snare: {color: secondary, duration: 0.05, strength: 0.50}
```

| 항목 | on_onset (v1.0) | on_kick (v1.1) |
|---|---|---|
| 감지 | 전 주파수 onset | HPSS 저주파 fmax=180Hz |
| duration | 60ms | 40ms |
| strength | 0.95 | 0.98 |
| 우선순위 | 2순위 | 1순위 |

### 10.2 bass_track

```yaml
bass_track:
  follow:   true   # 베이스 에너지로 밝기 제어
  smooth:   0.1    # 스무딩 시간 (초)
  freq_max: 200    # 추적 최대 주파수 (Hz)
  min_val:  0.30
  max_val:  1.00
  # bass_bri = min_val + bass[fi] × (max_val - min_val)
```

### 10.3 color_cycle

```yaml
color_cycle:
  unit:            bar
  bars_per_change: 4
  colors: [primary, cool, secondary, {hue:120,sat:0.8,val:0.9}]
  transition: 0.3
```

---

## 11. spatial — 기기 배치 및 그룹

```yaml
spatial:
  layout:     arena
  dimensions: {rows:4, cols:5}
  groups:
    left_half:  {cols: [0,1]}
    right_half: {cols: [3,4]}
    front_row:  {rows: [0]}
    back_row:   {rows: [3]}
    center:     {rows:[1,2], cols:[2]}
  wave_origin:       {row:0,   col:0}
  explosion_center:  {row:1.5, col:2}
  delay_per_col:  0.05
  delay_per_row:  0.05
  delay_per_unit: 0.03
```

| 이펙트 | 딜레이 수식 |
|---|---|
| wave_lr | `delay = col × delay_per_col` |
| wave_fb | `delay = row × delay_per_row` |
| explosion | `delay = √((row−cy)²+(col−cx)²) × delay_per_unit` |
| diagonal | `delay = (row+col) × delay_per_unit` |

---

## 12. global_arc — 긴장-해소 곡선

```yaml
global_arc:
  tension_curve:
    - [0,   0.20]   # 인트로
    - [45,  0.90]   # 코러스 고조
    - [148, 0.50]   # 브릿지
    - [170, 1.00]   # 클라이맥스
    - [198, 0.10]   # 완전 소멸
  tension_rules:
    - {above: 0.80, apply: tension_build}
    - {below: 0.25, apply: breath}
```

| tension 범위 | 해석 | 권장 이펙트 |
|---|---|---|
| 0.0~0.3 | 해소·편안함 | breath |
| 0.3~0.6 | 중간·안정 | 기본 blink |
| 0.6~0.8 | 고조·긴장 | heart_pulse 빠르게 |
| 0.8~1.0 | 최고조 | tension_build (지수 증가) |

---

## 13. 이펙트 목록

### 13.1 단일 기기 이펙트 16종

| # | 이름 | 파라미터 | 트리거 |
|---|---|---|---|
| 1 | static / solid | color | 구간 유형 |
| 2 | slow_pulse / breath | color, period | valence |
| 3 | fast_strobe / strobe | color, hz | energy |
| 4 | beat_flash / blink / sharp_onoff | color, duty | onset/beat |
| 5 | color_sweep | speed, direction | chorus |
| 6 | tension_build / brightness_ramp | curve, color_from/to | tension↑ |
| 7 | breathe / fade_inout | period, min/max | intro/outro |
| 8 | double_blink | color, gap(ms) | downbeat |
| 9 | warm_to_cool | transition_time | valence 변화 |
| 10 | dim_glow | color, val | bridge |
| 11 | flicker | color, variance | acoustic |
| 12 | accent / flash_all | color, threshold | climax onset |
| 13 | rainbow | — | high energy |
| 14 | pitch_track | hue_map[pitch→hue] | melody |
| 15 | call_and_response | period | chorus |
| 16 | release_burst | flash_color, then | tension 해소 |

### 13.2 공간 이펙트 12종

| # | 이름 | 딜레이 | 용도 |
|---|---|---|---|
| 1 | static_all | — | 전체 동일 |
| 2 | wave_lr | col × delay_per_col | 좌→우 |
| 3 | wave_fb / wave_rl | row × delay_per_row | 앞→뒤 / 우→좌 |
| 4 | explosion | distance × delay_per_unit | 중심→외곽 |
| 5 | call_and_response | period | 좌↔우 교대 |
| 6 | checkerboard | (row+col) % 2 | 격자 교대 |
| 7 | rainbow_row | — | 행별 hue 분할 |
| 8 | diagonal_wave | (row+col) × factor | 대각선 |
| 9 | breathe | — | 전체 동기 사인파 |
| 10 | tension_build | — | 에너지 점증 |
| 11 | front_back | — | 앞열/뒷열 분리 |
| 12 | frequency_band | — | 주파수 스펙트럼 |

---

## 14. mp3_to_mlml 파이프라인 [v1.3]

MP3 + 선택적 SRT 입력 → MLML v1.3 자동 생성 참조 구현.

### 14.1 사용법

```bash
python mp3_to_mlml.py song.mp3
python mp3_to_mlml.py song.mp3 --srt song.srt
python mp3_to_mlml.py song.mp3 --title "관객이 될게" --artist "아이유" --srt song.srt
python mp3_to_mlml.py song.mp3 --no-llm          # LLM 없이 규칙 기반만
python mp3_to_mlml.py song.mp3 --save-analysis   # 분석 JSON 저장
```

### 14.2 4단계 파이프라인

| 단계 | 함수 | 입력 | 출력 |
|---|---|---|---|
| 0. SRT 파싱 | `parse_srt()` / `analyze_lyrics()` | `*.srt` | lyric_analysis dict |
| 1. 오디오 분석 | `analyze()` | `*.mp3` | analysis dict (librosa) |
| 2. 규칙 기반 생성 | `build_mlml_rules()` / `merge_lyric_into_mlml()` | analysis + lyric_analysis | mlml dict |
| 3. LLM 개선 | `refine_with_llm()` | mlml dict + 요약 | refined mlml dict |
| 4. 저장 | `save_mlml()` | mlml dict | `*.mlml` (YAML) |

### 14.3 analyze() 추출 항목

| 항목 | 추출 방법 | MLML 활용 |
|---|---|---|
| BPM | `librosa.beat.beat_track()` 자기상관 | metadata.bpm |
| 비트 타임스탬프 | beat_frames 변환 | timeline 정렬 기준 |
| 킥드럼 | HPSS 저주파 onset (fmax=180Hz) | beat_reactive.on_kick |
| 베이스 에너지 | STFT ≤200Hz 평균 | bass_track 밝기 |
| RMS 에너지 | `librosa.feature.rms()` | 구간 분류, global_arc |
| 조성 | 크로마 CQT → 장/단조 판단 | palette hue 자동 설정 |
| 구간 분류 | 에너지 백분위 7-class | section_defaults 매핑 |
| 스테레오 L/R | 채널 분리 베이스 에너지 | spatial 좌우 분리 |
| 장르·기분 | BPM+에너지+댄스어빌리티 규칙 | metadata, global_mood |

---

## 15. 완성 예시 — 아이유 「관객이 될게」(발췌)

```yaml
metadata:
  title: "관객이 될게"
  artist: "아이유 (IU)"
  bpm: 161.5
  key: G_major
  duration: 247.69
  archetype: BGM_SONG

global_mood: {temperature: warm, intensity: 0.85, contrast: 0.75}

beat_reactive:
  on_kick:  {color: white,     duration: 0.04, strength: 0.98}
  on_snare: {color: secondary, duration: 0.05, strength: 0.50}

lyric_map:
  enabled: true
  source: srt
  manual:
    - {time: 24.0,  text: "사랑하는 사람들 앞에서", color: love, brightness: 0.80, duration: 3.2}
    - {time: 156.0, text: "I trust my you",        color: hope, brightness: 0.70, duration: 3.2}

timeline:
  - {t: 0.0,   group: 0, color: neutral,   effect: breath,          intensity: 0.30}
  - {t: 8.0,   group: 0, color: primary,   effect: heart_pulse,     intensity: 0.60}
  - {t: 8.0,   group: 1, spotlight: true,  bg_brightness: 0.15}
  - {t: 44.0,  group: 0, color: secondary, effect: tension_build,   intensity: 0.80}
  - {t: 47.5,  group: 0, color: null,      effect: expectation_break}
  - {t: 48.0,  group: 0, color: peak,      effect: release_burst,   spatial: explosion}
  - {t: 208.0, group: 0, color: love,      effect: breath,          intensity: 0.40}

bookend: {fade_out_start: 240.0, fade_out_duration: 7.69, final_color: love}
```

전체 파일은 [`examples/iu_gwaekagi_excerpt.mlml`](examples/iu_gwaekagi_excerpt.mlml)에 있습니다.

---

## 16. 의존성 & 설치

```bash
# 핵심 패키지
pip install librosa numpy scipy pyyaml anthropic
# BLE 응원봉 제어
pip install bleak
# 영상 재생
pip install pygame opencv-python

# MLML 생성 실행
export ANTHROPIC_API_KEY="sk-ant-..."
python mp3_to_mlml.py song.mp3 --srt song.srt

# MLML 재생
python mlml_player.py song.mlml song.mp3 video.mp4 song.srt 2
```

> 참고: 오디오 분석 파이프라인(`mp3_to_mlml.py`) 및 BLE 재생 레퍼런스 구현(`mlml_player.py`)의
> 전체 소스코드는 이 저장소에는 포함되어 있지 않으며, 별도 공개 일정에 따라 추후 배포됩니다.
