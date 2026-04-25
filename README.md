# 🎵 MLML — Music-to-Light Markup Language

> An open specification for music-synchronized K-pop lightstick choreography

[![ACM Multimedia 2026 - Submitted](https://img.shields.io/badge/ACM%20MM%202026-Submitted-purple)]()
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)](https://youtu.be/4xf9s3fa-oU)
[![License](https://img.shields.io/badge/License-Apache-blue)]()

---

## Demo — 16 Lightsticks Synchronized

[![MLML Demo](https://img.youtube.com/vi/4xf9s3fa-oU/0.jpg)](https://youtu.be/4xf9s3fa-oU)

*16 IU (유애나) lightsticks synchronized in real-time using MLML player — no manual control.*

---

## What is MLML?

**MLML (Music-to-Light Markup Language)** is a YAML-based open specification that maps music structure to lightstick lighting events — automatically.

- 현재 K-pop 공연장의 응원봉 조명은 기획사 서버가 무선 RF로 일괄 제어합니다. 
- 본 연구는 팬이 집이나 소규모 팬 모임에서 소규모(10-20개 정도)로 직접 조명을 음악과 동기화를 하는 것을 목표로 합니다.
- 음악과 동기화되는 조명 시나리오를 만들고 공유할 수 있는 개방형 대안으로 MLML을 제안하고 개발하고 있습니다. 

### Key Features

- 🎵 Automatic music analysis (beat, section, mood)
- 💡 BLE lightstick control (IU, Blackpink, NMIX)
- 📝 Human-readable YAML scenario format
- 🤖 LLM-assisted scenario generation
- 🎮 Real-time synchronization (≤100ms latency)

---

## Supported Lightsticks

| Artist | Device | Status |
|--------|--------|--------|
| IU (아이유) | 유애나봉 | ✅ Supported |
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
| IU - 관객이 될께 | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
| IU - Blueming | 16 | [▶ YouTube](https://youtu.be/KHmO7usMysU) |
| IU - Shopper | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
| Aespa - Supernova | 16 | [▶ YouTube](https://youtu.be/a_pUyoQBCkE) |
| Michael Jackson - Billie Jean | 16 | [▶ YouTube](https://youtu.be/BQ4oGPVca64) |

---

## Research

This project is part of ongoing research at
**[Data Networks Lab](https://networks.cnu.ac.kr)**,
**Chungnam National University, Dept. of Computer Science & AI**

- 📄 Paper submitted to **ACM Multimedia 2026** Interactive Art Track
- 🔬 Full specification and code releasing after publication

### Citation (submitted for ACM MM Interactive Art Track, waiting for the result by June 2026)

```bibtex
@inproceedings{mlml2026,
  title={MLML: An Open Music-to-Light Markup Language
         for Democratizing Fan Lightstick Choreography},
  author={Lee, Youngseok},
  booktitle={submitted for ACM Multimedia 2026},
  year={2026}
}
```

---

## Roadmap

- [x] BLE protocol analysis (IU, Blackpink, SEVENTEEN, NMIX)
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
🏫 Data Network Lab. Chungnam National University

⭐ **Star this repo** to get notified when spec and code are released!
