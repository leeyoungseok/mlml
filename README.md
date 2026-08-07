# 🎵 MLML — Music-to-Light Markup Language

> An open specification for music-synchronized K-pop lightstick choreography
> 음악의 구조와 감성을 BLE / Wi-Fi / Zigbee 조명 장치의 실시간 색상 제어로 변환하기 위한
> YAML 기반 선언형 중간 표현 언어 (Spec v1.3)

[![ACM Multimedia 2026 - Interactive Art](https://img.shields.io/badge/ACM%20MM%202026-Interactive%20Art%20(Accepted)-purple)](#research)
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)](https://youtu.be/4xf9s3fa-oU)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**Data Networks Lab, Chungnam National University** · [networks.cnu.ac.kr](https://networks.cnu.ac.kr)

---

## Demo — 16 Lightsticks Synchronized

[![MLML Demo](https://img.youtube.com/vi/4xf9s3fa-oU/0.jpg)](https://youtu.be/4xf9s3fa-oU)

*16 IU (유애나) lightsticks synchronized in real-time using the MLML player — no manual control.*

---

## What is MLML?

**MLML (Music-to-Light Markup Language)** is a YAML-based open specification that maps
music structure and emotion to lightstick lighting events — automatically.

- 현재 K-pop 공연장의 응원봉 조명은 기획사 서버가 무선 RF로 일괄 제어합니다.
- 본 연구는 팬이 집이나 소규모 팬 모임에서 소규모(10-20개 정도)로 직접 조명을 음악과 동기화하는 것을 목표로 합니다.
- 음악과 동기화되는 조명 시나리오를 만들고 공유할 수 있는 개방형 대안으로 MLML을 제안하고 개발하고 있습니다.

### Key Features

- 🎵 Automatic music analysis (beat, section, mood, lyric sentiment)
- 💡 Hardware-independent — the same script drives lightsticks, LED strips, Philips Hue, matrix panels
- 📝 Human-readable, declarative YAML scenario format (4-layer structure)
- 🤖 LLM-assisted scenario generation (single-inference full script from Claude, etc.)
- 🎮 Real-time synchronization (≤100ms latency)

---

## 4-Layer Structure

| Layer | Blocks | Role |
|---|---|---|
| Global | `metadata`, `palette`, `global_mood`, `global_arc` | Song-wide settings |
| Structural | `timeline`, `section_defaults`, `bookend`, `expectation_break` | Section structure |
| Rhythmic | `beat_reactive`, `bass_track`, `color_cycle`, `spotlight` | Rhythm response |
| Semantic | `lyric_map`, `spatial`, `motifs` | Emotion & spatial layout |

전체 블록 명세, 13단계 색상 합산 알고리즘(50fps), 이펙트 28종(단일 16 + 공간 12),
자동 평가 메트릭 9종(EIC/SAS/TA/KFA/BBC/CCR/CS/EBS/LCC)은 [`SPEC.md`](SPEC.md)에서
확인할 수 있습니다.

---

## Supported Lightsticks (protocol families analyzed)

| Artist | Device | Status |
|--------|--------|--------|
| IU (아이유) | 유애나봉 | ✅ Analyzed |
| NMIXX | 공식 응원봉 | ✅ Analyzed |
| Blackpink | 공식 응원봉 | ✅ Analyzed |

> BLE 역공학 레퍼런스 코드(10종 확장판)는 별도 연구 논문 심사가 완료된 이후
> 별도 저장소로 공개될 예정입니다.

---

## MLML Scenario Example

```yaml
metadata:
  title: "관객이 될게"
  artist: "아이유 (IU)"
  bpm: 161.5
  key: G_major
  archetype: BGM_SONG

timeline:
  - {t: 0.0,  group: 0, color: neutral, effect: breath,        intensity: 0.30}
  - {t: 47.5, group: 0, color: null,    effect: expectation_break}
  - {t: 48.0, group: 0, color: peak,    effect: release_burst, spatial: explosion}
```

전체 예시는 [`examples/iu_istanu.mlml`](examples/iu_istanu.mlml)에서
볼 수 있습니다.

---

## Demo Videos

| Song | Lightsticks | Link |
|------|-------------|------|
| IU - 관객이 될게 (I Stan U) — ACM MM 2026 paper demo | 12 | [▶ YouTube](https://youtu.be/cPKkz_UI0TA) |
| IU - 관객이 될게 (I Stan U) | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
| IU - Blueming | 16 | [▶ YouTube](https://youtu.be/KHmO7usMysU) |
| IU - Shopper | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
| Aespa - Supernova | 16 | [▶ YouTube](https://youtu.be/a_pUyoQBCkE) |
| Michael Jackson - Billie Jean | 16 | [▶ YouTube](https://youtu.be/BQ4oGPVca64) |

---

## Version History

| Version | Key additions |
|---|---|
| v1.0 | 4-layer structure, 16 single-device effects, 12 spatial effects, EIC/SAS/TA |
| v1.1 | `beat_reactive.on_kick`, `bass_track`, `color_cycle`, KFA/BBC/CCR |
| v1.2 | `global_mood`, `section_defaults`, `expectation_break`, `bookend`, `lyric_map`, `spotlight`, CS/EBS/LCC |
| v1.3 | `lyric_map` SRT auto-parsing + 8-emotion dictionary, `mp3_to_mlml` 4-stage pipeline, radio 3-class segmentation profile, 6 archetypes, LCC metric |

---

## Research

This project is part of ongoing research at
**[Data Networks Lab](https://networks.cnu.ac.kr)**,
**Chungnam National University, Dept. of Computer Science & AI**

- 📄 **"MLML: An Open Music-to-Light Markup Language for Democratizing Fan Lightstick
  Choreography"** — accepted, **ACM Multimedia 2026, Interactive Art Track**
  (Rio de Janeiro, Nov 10–14, 2026)
- 🔬 Full specification released here; BLE control reference code releasing after the
  companion systems paper is decided

### Citation

```bibtex
@inproceedings{mlml2026,
  title={MLML: An Open Music-to-Light Markup Language
         for Democratizing Fan Lightstick Choreography},
  author={Lee, Youngseok and Jin, Minhyuk},
  booktitle={ACM Multimedia 2026, Interactive Art Track},
  year={2026}
}
```

See [`CITATION.cff`](CITATION.cff) for the machine-readable version.

---

## Roadmap

- [x] BLE protocol analysis (IU, Blackpink, SEVENTEEN, NMIXX)
- [x] MLML v1.3 specification
- [x] Real-time player (16 lightsticks)
- [x] LLM-based scenario generation
- [x] ACM MM 2026 demo video
- [ ] BLE control reference code (after companion paper decision)
- [ ] MLML Hub (community sharing platform)
- [ ] Web-based editor
- [ ] Mobile app
- [ ] Open SDK release

---

## Contact & Collaboration

연구 협력, 파트너십 문의:
📧 lee@cnu.ac.kr
🏫 Data Networks Lab, Chungnam National University

⭐ **Star this repo** to get notified when the full reference code is released!

## License

This specification and its documentation are released under the [Apache License 2.0](LICENSE).
