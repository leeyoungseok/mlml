# MLML — Music-to-Light Markup Language

### Full Specification v1.3

| Field | Value |
|---|---|
| Version | 1.3 |
| Author | Youngseok Lee (Dept. of Computer Engineering & Artificial Intelligence, Chungnam National University) |
| License | Apache License 2.0 |
| Scope | v1.0 + v1.1 + v1.2 (all blocks) + v1.3 additions (`lyric_map` SRT parsing, `mp3_to_mlml` pipeline) |

## Version History

| Version | Key additions |
|---|---|
| v1.0 | 4-layer structure, 16 single-device effects, 12 spatial effects, EIC/SAS/TA |
| v1.1 | `beat_reactive.on_kick`, `bass_track`, `color_cycle`, KFA/BBC/CCR |
| v1.2 | `global_mood`, `section_defaults`, `expectation_break`, `bookend`, `lyric_map`, `spotlight`, CS/EBS/LCC |
| v1.3 | `lyric_map` SRT auto-parsing + 8-category emotion dictionary, `mp3_to_mlml` 4-stage pipeline, LCC metric |

---

## 1. Overview

MLML (Music-to-Light Markup Language) is a YAML-based declarative intermediate representation
language for translating music structure and emotion into real-time color control for
BLE / Wi-Fi / Zigbee lighting devices.

### 1.1 Design Principles

1. **Hardware independence** — the same script drives lightsticks, LED strips, Philips Hue, and matrix panels
2. **Music-structure awareness** — encodes section, mood, and lyric emotion, not just volume and beat
3. **LLM-friendly** — an LLM (e.g., Claude) can generate a complete script in a single inference pass
4. **Human readability** — a YAML structure that a lighting designer can edit by hand
5. **Extensibility** — new blocks can be added in a backward-compatible way

### 1.2 Four-Layer Structure

| Layer | Blocks | Role |
|---|---|---|
| Global | `metadata`, `palette`, `global_mood`, `global_arc` | Song-wide settings |
| Structural | `timeline`, `section_defaults`, `bookend`, `expectation_break` | Section structure |
| Rhythmic | `beat_reactive`, `bass_track`, `color_cycle`, `spotlight` | Rhythm response |
| Semantic | `lyric_map`, `spatial`, `motifs` | Emotion & spatial layout |

### 1.3 13-Step Color Composition Algorithm (50 fps)

The renderer applies the following 13 steps, in order, every frame (50 fps) to compute the final RGB value.

1. **`section_defaults`** → default color/intensity for the current section type
2. **`timeline` override** → per-event color/effect
3. **`global_mood`** → temperature correction (warm/cool/energetic)
4. **`lyric_map`** → apply the current lyric's emotion color
5. **`color_cycle`** → hue rotation on a per-bar basis
6. **`bass_track`** → low-frequency energy → brightness modulation
7. **`spotlight`** → verse background attenuation (`bg_brightness`)
8. **`base_rgb` composition** → `bar_rgb × bass_brightness`
9. **`expectation_break`** → if blackout, return RGB=(0,0,0) immediately
10. **`blink`** → determine `is_on`
11. **Priority overlay** → kick > onset > blink ON > blink OFF
12. **`bookend`** → outro fade-out
13. **Intensity scaling** → `× global_mood.intensity` → final (R, G, B)

---

## 2. `metadata` — Song Metadata

```yaml
metadata:
  title:     string   # song title (required)
  artist:    string   # artist (required)
  bpm:       float    # recommended: librosa.beat.beat_track()
  key:       string   # "G_major", "A_minor"
  time_sig:  string   # "4/4", "3/4", "6/8"
  duration:  float    # total length (seconds)
  genre:     string   # "k-pop", "ballad", "rock", "r&b"
  mood:      [string] # ["cheerful", "romantic"]
```

---

## 3. `palette` — Color Vocabulary

```yaml
palette:
  <name>:
    hue: int    # 0-360
    sat: float  # 0.0-1.0
    val: float  # 0.0-1.0
```

Default palette example:

| Name | hue | sat | val | Color | Usage |
|---|---|---|---|---|---|
| primary | 210 | 0.7 | 0.9 | sky blue | verse/intro default |
| secondary | 40 | 0.8 | 1.0 | gold | pre-chorus |
| warm | 15 | 0.9 | 1.0 | orange | warm emotion |
| cool | 240 | 0.6 | 0.8 | purple | bridge/sadness |
| peak | 0 | 1.0 | 1.0 | red | climax |
| neutral | 200 | 0.2 | 0.4 | blue-gray | intro/outro |
| white | 0 | 0.0 | 1.0 | white | kick flash |
| love | 350 | 0.9 | 1.0 | pink | "love" lyrics |
| sad | 220 | 0.7 | 0.7 | blue | "sad" lyrics |
| happy | 45 | 0.9 | 1.0 | yellow | "happy" lyrics |

---

## 4. `global_mood` — Emotional Temperature [v1.2]

```yaml
global_mood:
  temperature: warm   # warm|cool|energetic|mystic|neutral
  intensity:   0.85   # 0.0-1.0, overall brightness scale (Step 13)
  contrast:    0.75   # 0.0-1.0, section contrast strength
```

v1.3: `mp3_to_mlml` automatically sets `temperature` from the SRT's dominant emotion (`dominant_emotion`).

| temperature | hue center | Character | Representative genre |
|---|---|---|---|
| warm | 0-60° | Warmth, excitement | Ballad, love songs |
| cool | 180-270° | Coldness, sadness | Breakup, sad songs |
| energetic | full hue cycle | Explosive | Dance, party |
| mystic | 240-300° | Mysterious, dreamlike | R&B |
| neutral | as configured | Manual control | Direct control |

---

## 5. `tempo_mode` — Automatic BPM-Derived Parameters

```yaml
tempo_mode:
  auto: true
  override:
    bars_per_change: 2
    smooth: 0.05
    hz_hi: 20
```

| BPM range | bars_per_change | bass smooth | blink hz_hi |
|---|---|---|---|
| < 80 (ballad) | 8 | 0.20 | 6 |
| 80-120 (mid) | 4 | 0.10 | 12 |
| 120-160 (dance) | 2 | 0.05 | 20 |
| > 160 (very fast) | 4 | 0.03 | 12 |

---

## 6. `lyric_map` — Lyric Emotion Color [v1.2 / extended in v1.3]

v1.3 adds automatic SRT parsing, an 8-category emotion keyword dictionary, and the `manual` block.

```yaml
lyric_map:
  enabled: true
  source:  srt          # srt | text | whisper
  emotion_color:         # emotion -> HSV
    love:      {hue:350, sat:0.90, val:1.00}   # pink
    happy:     {hue:45,  sat:0.90, val:1.00}   # yellow
    romantic:  {hue:330, sat:0.85, val:0.95}   # rose
    sad:       {hue:220, sat:0.70, val:0.70}   # blue
    hope:      {hue:180, sat:0.55, val:0.90}   # sky
    nostalgic: {hue:30,  sat:0.70, val:0.80}   # tan
    excited:   {hue:0,   sat:1.00, val:1.00}   # red
    calm:      {hue:200, sat:0.40, val:0.75}   # blue-gray
  manual:                # auto-generated from SRT parsing, or entered manually [v1.3]
    - time:       24.0
      text:       "In front of the people I love"
      color:      love
      brightness: 0.80
      duration:   3.2
    - time:       156.0
      text:       "I trust my you"
      color:      hope
      brightness: 0.70
      duration:   3.2
```

### 6.1 Emotion Keyword Dictionary [v1.3]

| Emotion | Korean keywords (sample) | English keywords (sample) | intensity |
|---|---|---|---|
| love | 사랑, 좋아, 그리워, 설레, 두근 | love, adore, miss, heart | 0.80 |
| happy | 행복, 기뻐, 신나, 웃음 | happy, joy, smile, fun | 0.85 |
| romantic | 달빛, 꿈, 함께, 손잡 | dream, forever, together | 0.75 |
| sad | 슬퍼, 눈물, 아파, 힘들 | sad, cry, tears, hurt | 0.55 |
| hope | 희망, 믿어, 괜찮, 다시 | hope, believe, trust, okay | 0.70 |
| nostalgic | 그때, 추억, 기억, 옛날 | memory, remember, past | 0.60 |
| excited | 설레, 두근두근, 기대 | excited, thrill, amazing | 0.95 |
| calm | 편해, 쉬어, 평화, 위로 | calm, peace, comfort, still | 0.45 |

### 6.2 SRT Auto-Parsing Flow [v1.3]

```
parse_srt(path)         → [{start, end, text}, ...]
  ↓ detect_emotion(text)
analyze_lyrics()        → {manual_map, dominant_emotion, emotion_stats}
  ↓
merge_lyric_into_mlml()
  → lyric_map.source = "srt"
  → lyric_map.manual = emotion-tagged visual events
  → global_mood.temperature auto-corrected from the dominant emotion
  → timeline events reinforced during excited/happy segments
```

Automatic SRT discovery: if `--srt` is not specified, a `.srt` file with the same name and path as the MP3 is used automatically.

---

## 7. `bookend` & `expectation_break` [v1.2]

### 7.1 `bookend` — Thematic Bookending

```yaml
bookend:
  fade_out_start:    float     # fade start time (seconds)
  fade_out_duration: float     # fade duration (seconds)
  final_color:       love      # final color
  final_state:       blackout  # blackout|single_spot|hold
```

### 7.2 `expectation_break` — Blackout Technique

The "predict, then violate" principle: a blackout on the last beat of the pre-chorus, followed by an explosive chorus entry.

```yaml
expectation_break:
  enabled: true
  timing:  last_beat   # last_beat|last_2beats|last_bar
  recovery: peak

# used in timeline
- t: 47.5
  group: 0
  color: null
  effect: expectation_break
```

---

## 8. `section_defaults` — Section Defaults [v1.2]

| Section | brightness | blink_mode | Notes |
|---|---|---|---|
| intro | 0.25 | none | Starts low, builds anticipation |
| verse | 0.55 | beat_sync | spotlight on by default |
| prechorus | 0.75 | beat_sync | expectation_break on by default |
| chorus | 1.00 | beat_sync | explosion, kick 0.98 |
| bridge | 0.45 | beat_sync | palette_invert (complementary color) |
| climax | 1.00 | free | changes every bar, kick 1.0 |
| outro | 0.35 | none | fade_to_bookend |

---

## 9. `timeline` — Time-Based Events

```yaml
timeline:
  - t:           float   # event time (seconds, required)
    group:       int     # 0=all, 1=group A, 2=group B
    color:       string  # palette key | {hue,sat,val} | null
    effect:      string  # effect name
    intensity:   float   # 0.0-1.0
    bpm_sync:    bool
    hz:          float   # strobe frequency
    spatial:     string  # spatial effect
    spotlight:   bool
    bg_brightness: float
    period:      float   # breathe period (seconds)
    note:        string  # description (ignored by the renderer)
```

---

## 10. Rhythmic Response Blocks [v1.1]

### 10.1 `beat_reactive`

```yaml
beat_reactive:
  on_kick:  {color: white,     duration: 0.04, strength: 0.98}
  on_snare: {color: secondary, duration: 0.05, strength: 0.50}
```

| Property | on_onset (v1.0) | on_kick (v1.1) |
|---|---|---|
| Detection | full-spectrum onset | HPSS low-frequency, fmax=180Hz |
| duration | 60ms | 40ms |
| strength | 0.95 | 0.98 |
| Priority | 2nd | 1st |

### 10.2 `bass_track`

```yaml
bass_track:
  follow:   true   # brightness follows bass energy
  smooth:   0.1    # smoothing time (seconds)
  freq_max: 200    # tracked frequency ceiling (Hz)
  min_val:  0.30
  max_val:  1.00
  # bass_bri = min_val + bass[fi] × (max_val - min_val)
```

### 10.3 `color_cycle`

```yaml
color_cycle:
  unit:            bar
  bars_per_change: 4
  colors: [primary, cool, secondary, {hue:120,sat:0.8,val:0.9}]
  transition: 0.3
```

---

## 11. `spatial` — Device Layout and Grouping

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

| Effect | Delay formula |
|---|---|
| wave_lr | `delay = col × delay_per_col` |
| wave_fb | `delay = row × delay_per_row` |
| explosion | `delay = √((row−cy)²+(col−cx)²) × delay_per_unit` |
| diagonal | `delay = (row+col) × delay_per_unit` |

---

## 12. `global_arc` — Tension-Release Curve

```yaml
global_arc:
  tension_curve:
    - [0,   0.20]   # intro
    - [45,  0.90]   # chorus build
    - [148, 0.50]   # bridge
    - [170, 1.00]   # climax
    - [198, 0.10]   # complete release
  tension_rules:
    - {above: 0.80, apply: tension_build}
    - {below: 0.25, apply: breath}
```

| Tension range | Interpretation | Recommended effect |
|---|---|---|
| 0.0-0.3 | Release, calm | breath |
| 0.3-0.6 | Moderate, stable | default blink |
| 0.6-0.8 | Building, tense | heart_pulse, faster |
| 0.8-1.0 | Peak | tension_build (exponential increase) |

---

## 13. Effect Catalog

### 13.1 Single-Device Effects (16)

| # | Name | Parameters | Trigger |
|---|---|---|---|
| 1 | static / solid | color | section type |
| 2 | slow_pulse / breath | color, period | valence |
| 3 | fast_strobe / strobe | color, hz | energy |
| 4 | beat_flash / blink / sharp_onoff | color, duty | onset/beat |
| 5 | color_sweep | speed, direction | chorus |
| 6 | tension_build / brightness_ramp | curve, color_from/to | rising tension |
| 7 | breathe / fade_inout | period, min/max | intro/outro |
| 8 | double_blink | color, gap(ms) | downbeat |
| 9 | warm_to_cool | transition_time | valence change |
| 10 | dim_glow | color, val | bridge |
| 11 | flicker | color, variance | acoustic |
| 12 | accent / flash_all | color, threshold | climax onset |
| 13 | rainbow | — | high energy |
| 14 | pitch_track | hue_map[pitch→hue] | melody |
| 15 | call_and_response | period | chorus |
| 16 | release_burst | flash_color, then | tension release |

### 13.2 Spatial Effects (12)

| # | Name | Delay | Use |
|---|---|---|---|
| 1 | static_all | — | all identical |
| 2 | wave_lr | col × delay_per_col | left → right |
| 3 | wave_fb / wave_rl | row × delay_per_row | front → back / right → left |
| 4 | explosion | distance × delay_per_unit | center → outward |
| 5 | call_and_response | period | left ↔ right alternating |
| 6 | checkerboard | (row+col) % 2 | grid alternating |
| 7 | rainbow_row | — | hue split by row |
| 8 | diagonal_wave | (row+col) × factor | diagonal |
| 9 | breathe | — | synchronized sine wave, all devices |
| 10 | tension_build | — | gradual energy increase |
| 11 | front_back | — | front/back row split |
| 12 | frequency_band | — | frequency spectrum mapping |

---

## 14. `mp3_to_mlml` Pipeline [v1.3]

A reference implementation that automatically generates MLML v1.3 from an MP3 (with optional SRT input).

### 14.1 Usage

```bash
python mp3_to_mlml.py song.mp3
python mp3_to_mlml.py song.mp3 --srt song.srt
python mp3_to_mlml.py song.mp3 --title "I Stan U" --artist "IU" --srt song.srt
python mp3_to_mlml.py song.mp3 --no-llm          # rule-based only, no LLM
python mp3_to_mlml.py song.mp3 --save-analysis   # save the analysis JSON
```

### 14.2 Four-Stage Pipeline

| Stage | Function | Input | Output |
|---|---|---|---|
| 0. SRT parsing | `parse_srt()` / `analyze_lyrics()` | `*.srt` | lyric_analysis dict |
| 1. Audio analysis | `analyze()` | `*.mp3` | analysis dict (librosa) |
| 2. Rule-based generation | `build_mlml_rules()` / `merge_lyric_into_mlml()` | analysis + lyric_analysis | mlml dict |
| 3. LLM refinement | `refine_with_llm()` | mlml dict + summary | refined mlml dict |
| 4. Save | `save_mlml()` | mlml dict | `*.mlml` (YAML) |

### 14.3 Features Extracted by `analyze()`

| Feature | Extraction method | MLML usage |
|---|---|---|
| BPM | `librosa.beat.beat_track()` autocorrelation | metadata.bpm |
| Beat timestamps | beat_frames conversion | timeline alignment reference |
| Kick drum | HPSS low-frequency onset (fmax=180Hz) | beat_reactive.on_kick |
| Bass energy | STFT average ≤200Hz | bass_track brightness |
| RMS energy | `librosa.feature.rms()` | section classification, global_arc |
| Key | Chroma CQT → major/minor detection | automatic palette hue |
| Section classification | 7-class energy percentile | section_defaults mapping |
| Stereo L/R | Per-channel bass energy separation | spatial left/right split |
| Genre/mood | BPM + energy + danceability rules | metadata, global_mood |

---

## 15. Automatic Evaluation Metrics (9)

### 16.1 Tier 1 — Required

| Metric | Formula | Ideal value | Version |
|---|---|---|---|
| EIC | Pearson(RMS_energy, brightness) | 1.0 | v1.0 |
| SAS | matched_bounds / total (±0.5s) | 1.0 | v1.0 |
| TA | mean(\|beat − event\|) ms | 0ms | v1.0 |
| KFA | kicks_with_flash / total (±30ms) | ≥0.9 | v1.1 |

### 16.2 Tier 2 — Optional

| Metric | Formula | Ideal value | Version |
|---|---|---|---|
| BBC | Pearson(bass_energy, brightness) | ≥0.7 | v1.1 |
| CCR | bar_color_changes_on_time / total | 1.0 | v1.1 |

### 16.3 Tier 3 — Future Work

| Metric | Meaning | Ideal value | Version |
|---|---|---|---|
| CS | Chorus/verse brightness contrast ratio | ≥1.8 | v1.2 |
| EBS | expectation_break timing accuracy (±50ms) | ≥0.9 | v1.2 |
| LCC | Lyric-emotion-to-color-temperature match | ≥0.7 | v1.3 |

*Core requirement: EIC/SAS/TA/KFA should be measured and validated against MOS (a 5-point subjective rating) with Spearman correlation to constitute a paper contribution.*

---

## 16. Complete Example — IU, "I Stan U"

```yaml
metadata:
  title: "I Stan U"
  artist: "IU"
  bpm: 161.5
  key: G_major
  duration: 247.69

global_mood: {temperature: warm, intensity: 0.85, contrast: 0.75}

beat_reactive:
  on_kick:  {color: white,     duration: 0.04, strength: 0.98}
  on_snare: {color: secondary, duration: 0.05, strength: 0.50}

lyric_map:
  enabled: true
  source: srt
  manual:
    - {time: 24.0,  text: "In front of the people I love", color: love, brightness: 0.80, duration: 3.2}
    - {time: 156.0, text: "I trust my you",                 color: hope, brightness: 0.70, duration: 3.2}

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

The full file is available at [`examples/iu_istanu.mlml`](examples/iu_istanu.mlml).

---

## 17. Dependencies & Installation

```bash
# Core packages
pip install librosa numpy scipy pyyaml anthropic

# BLE lightstick control
pip install bleak

# Video playback
pip install pygame opencv-python

# Run MLML generation
export ANTHROPIC_API_KEY="sk-ant-..."
python mp3_to_mlml.py song.mp3 --srt song.srt

# MLML playback
python mlml_player.py song.mlml song.mp3 video.mp4 song.srt 2
```

> Note: the full source code for the audio-analysis pipeline (`mp3_to_mlml.py`) and the
> BLE playback reference implementation (`mlml_player.py`) is not included in this
> repository. It will be released separately on its own schedule (BLE protocol
> reverse-engineering reference code follows peer review of the companion systems paper).
