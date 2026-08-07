# 🎵 MLML — Music-to-Light Markup Language

[한국어](README.ko.md) | **English**

> An open specification for music-synchronized K-pop lightstick choreography —
> a YAML-based declarative intermediate representation language for translating
> music structure and emotion into real-time color control for BLE / Wi-Fi / Zigbee
> lighting devices (Spec v1.3)

[![ACM Multimedia 2026 - Interactive Art](https://img.shields.io/badge/ACM%20MM%202026-Interactive%20Art%20(Accepted)-purple)](#research)
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)](https://youtu.be/4xf9s3fa-oU)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**Data Networks Lab, Chungnam National University** · [networks.cnu.ac.kr](https://networks.cnu.ac.kr)

---

## Demo — 12 Lightsticks Synchronized (ACM MM 2026 Paper Demo)

[![MLML Demo](https://img.youtube.com/vi/cPKkz_UI0TA/maxresdefault.jpg)](https://youtu.be/cPKkz_UI0TA)

*12 IU "I Stan U" (관객이 될게) lightsticks synchronized in real-time using the MLML
player — the demo shown in the ACM MM 2026 Interactive Art paper. A larger-scale
16-lightstick demo is also available below under [Demo Videos](#demo-videos).*

---

## What is MLML?

**MLML (Music-to-Light Markup Language)** is a YAML-based open specification that maps
music structure and emotion to lightstick lighting events — automatically.

- Today, K-pop concert lightstick lighting is controlled centrally over wireless RF by the
  entertainment agency's server.
- This research aims to let fans synchronize a small number of lightsticks (roughly 10-20)
  directly with music themselves, at home or at small fan gatherings.
- We propose and develop MLML as an open alternative for creating and sharing
  music-synchronized lighting scenarios.

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

The full block specification, the 13-step color composition algorithm (50fps), the 28
effects (16 single-device + 12 spatial), and the 9 automatic evaluation metrics
(EIC/SAS/TA/KFA/BBC/CCR/CS/EBS/LCC) are documented in [`SPEC.md`](SPEC.md).

---

## Supported Lightsticks (protocol families analyzed)

| Artist | Device | Status |
|--------|--------|--------|
| IU | Official lightstick | ✅ Analyzed |
| NMIXX | Official lightstick | ✅ Analyzed |
| Blackpink | Official lightstick | ✅ Analyzed |

> The BLE reverse-engineering reference code (extended, 10-device version) will be
> released in a separate repository after the companion systems paper has completed
> peer review.

---

## MLML Scenario Example

```yaml
metadata:
  title: "I Stan U"
  artist: "IU"
  bpm: 161.5
  key: G_major
  archetype: BGM_SONG

timeline:
  - {t: 0.0,  group: 0, color: neutral, effect: breath,        intensity: 0.30}
  - {t: 47.5, group: 0, color: null,    effect: expectation_break}
  - {t: 48.0, group: 0, color: peak,    effect: release_burst, spatial: explosion}
```

The full example is available at [`examples/iu_istanu.mlml`](examples/iu_istanu.mlml).

---

## Demo Videos

| Song | Lightsticks | Link |
|------|-------------|------|
| IU - I Stan U (관객이 될게) — ACM MM 2026 paper demo | 12 | [▶ YouTube](https://youtu.be/cPKkz_UI0TA) |
| IU - I Stan U (관객이 될게) — larger-scale follow-up | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
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
**Chungnam National University, Dept. of Computer Engineering & Artificial Intelligence**

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

For research collaboration or partnership inquiries:
📧 lee@cnu.ac.kr
🏫 Data Networks Lab, Chungnam National University

⭐ **Star this repo** to get notified when the full reference code is released!

## License

This specification and its documentation are released under the [Apache License 2.0](LICENSE).
