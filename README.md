# 🎵 MLML — Music-to-Light Markup Language

> An open specification for music-synchronized 
> K-pop lightstick choreography

[![ACM Multimedia 2026 - Submitted](https://img.shields.io/badge/ACM%20MM%202026-Submitted-purple)]()
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)]([[https://youtu.be/4xf9s3fa-oU])
[![License](https://img.shields.io/badge/License-MIT-blue)]()

---

## Demo — 12 Lightsticks Synchronized

[![MLML Demo]([https://youtu.be/4xf9s3fa-oU])

*12 IU (유애나) lightsticks synchronized in real-time using MLML player — no manual control.*

---

## What is MLML?

**MLML (Music-to-Light Markup Language)** is a YAML-based 
open specification that maps music structure to lightstick 
lighting events — automatically.

현재 K-pop 공연장의 응원봉 조명은 기획사 서버가 RF로 일괄 제어합니다. M
LML은 팬이 직접 조명 시나리오를 
만들고 공유할 수 있는 개방형 대안입니다.

### Key Features
- 🎵 Automatic music analysis (beat, section, mood)
- 💡 BLE lightstick control (IU, Blackpink, Nmix, SEVENTEEN)
- 📝 Human-readable YAML scenario format
- 🤖 LLM-assisted scenario generation
- 🎮 Real-time synchronization (≤100ms latency)

---

## Supported Lightsticks

| Artist | Device | Status |
|--------|--------|--------|
| IU (아이유) | 유애나봉 | ✅ Supported |
| SEVENTEEN | 캐럿봉 | ✅ Supported |
| NMIX | 공식 응원봉 | ✅ Supported |
| Blackpink | 공식 응원봉 | ✅ Supported |
---

## MLML Scenario Example

```yaml
# IU - 좋은 날 (Good Day)
meta:
  title: "좋은 날"
  artist: "아이유"
  bpm: 116
  key: "G"

events:
  - time: 0.0
    type: color
    value: [255, 200, 100]   # warm yellow (intro)
  - time: 32.5
    type: effect
    value: wave              # chorus wave effect
  - time: 65.0
    type: color
    value: [255, 255, 255]   # white (high note)
```

---

## Demo Videos

| Song | Lightsticks | Link |
|------|-------------|------|
| IU - 관객이 될께 | 16 | [▶ YouTube](링크) https://youtu.be/DDSjNIcno14  |
| IU - Blueming | 16 | [▶ YouTube]([링크](https://youtu.be/KHmO7usMysU)) |
| IU - Shopper | 16 | [▶ YouTube]([링크](https://youtu.be/DDSjNIcno14)) |
| aespa - Supernova | 16 | [▶ YouTube]([링크](https://youtu.be/a_pUyoQBCkE)) |
| MJ - Billie Jean | 16 | [▶ YouTube]([링크](https://youtu.be/BQ4oGPVca64)) |

---

## Research

This project is part of ongoing research at  
**Data networks lab (https://networks.cnu.ac.kr **
**Chungnam National University, Dept. of Computer Science & AI**

- 📄 Paper submitted to **ACM Multimedia 2026** 
  Interactive Art Track
- 🔬 Full specification and code releasing   after publication

### Citation (upcoming)
```bibtex
@inproceedings{mlml2026,
  title={MLML: An Open Music-to-Light Markup Language 
         for Democratizing Fan Lightstick Choreography},
  author={Lee, Youngseok},
  booktitle={ACM Multimedia 2026},
  year={2026}
}
```

---

## Roadmap

- [x] BLE protocol analysis (IU, Blackpink, SEVENTEEN, Nmix)
- [x] MLML v2.0 specification
- [x] Real-time player (16 lightsticks)
- [x] LLM-based scenario generation
- [ ] MLML Hub (community sharing platform)
- [ ] Web-based editor
- [ ] Mobile app
- [ ] Open SDK release

---

## Contact & Collaboration

연구 협력, 파트너십 문의:  
📧 lee@cnu.ac.kr  
🏫 Chungnam National University

⭐ **Star this repo** to get notified when 
   spec and code are released!
