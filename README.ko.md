# 🎵 MLML — Music-to-Light Markup Language

**한국어** | [English](README.md)

> 음악 기반 K-pop 응원봉 안무를 위한 개방형 명세
> 음악의 구조와 감성을 BLE / Wi-Fi / Zigbee 조명 장치의 실시간 색상 제어로 변환하기 위한
> YAML 기반 선언형 중간 표현 언어 (Spec v1.3)

[![ACM Multimedia 2026 - Interactive Art](https://img.shields.io/badge/ACM%20MM%202026-Interactive%20Art%20(Accepted)-purple)](#연구)
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)](https://youtu.be/4xf9s3fa-oU)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**Data Networks Lab, 충남대학교** · [networks.cnu.ac.kr](https://networks.cnu.ac.kr)

---

## 데모 — 응원봉 16개 동기화

[![MLML Demo](https://img.youtube.com/vi/4xf9s3fa-oU/0.jpg)](https://youtu.be/4xf9s3fa-oU)

*IU (유애나) 응원봉 16개를 MLML 플레이어로 실시간 동기화 — 수동 제어 없이 동작합니다.*

---

## MLML이란?

**MLML (Music-to-Light Markup Language)**은 음악의 구조와 감성을 응원봉 조명 이벤트로
자동 변환하는 YAML 기반 개방형 명세입니다.

- 현재 K-pop 공연장의 응원봉 조명은 기획사 서버가 무선 RF로 일괄 제어합니다.
- 본 연구는 팬이 집이나 소규모 팬 모임에서 소규모(10-20개 정도)로 직접 조명을 음악과
  동기화하는 것을 목표로 합니다.
- 음악과 동기화되는 조명 시나리오를 만들고 공유할 수 있는 개방형 대안으로 MLML을
  제안하고 개발하고 있습니다.

### 주요 특징

- 🎵 자동 음악 분석 (비트, 구간, 분위기, 가사 감성)
- 💡 하드웨어 독립적 — 동일 스크립트가 응원봉·LED 스트립·Philips Hue·매트릭스 패널에서 동작
- 📝 사람이 읽을 수 있는 선언형 YAML 시나리오 포맷 (4계층 구조)
- 🤖 LLM 기반 시나리오 생성 (Claude 등으로 단일 추론으로 완전한 스크립트 생성)
- 🎮 실시간 동기화 (지연 ≤100ms)

---

## 4계층 구조

| 계층 | 블록 | 역할 |
|---|---|---|
| Global | `metadata`, `palette`, `global_mood`, `global_arc` | 곡 전체 설정 |
| Structural | `timeline`, `section_defaults`, `bookend`, `expectation_break` | 구간 구조 |
| Rhythmic | `beat_reactive`, `bass_track`, `color_cycle`, `spotlight` | 리듬 반응 |
| Semantic | `lyric_map`, `spatial`, `motifs` | 감성·공간 |

전체 블록 명세, 13단계 색상 합산 알고리즘(50fps), 이펙트 28종(단일 16 + 공간 12),
자동 평가 메트릭 9종(EIC/SAS/TA/KFA/BBC/CCR/CS/EBS/LCC)은 [`SPEC.md`](SPEC.md)에서
확인할 수 있습니다. (SPEC.md는 영문으로 작성되어 있습니다.)

---

## 분석 완료된 응원봉 (프로토콜 패밀리)

| 아티스트 | 기기 | 상태 |
|--------|--------|--------|
| IU (아이유) | 유애나봉 | ✅ 분석 완료 |
| NMIXX | 공식 응원봉 | ✅ 분석 완료 |
| Blackpink | 공식 응원봉 | ✅ 분석 완료 |

> BLE 역공학 레퍼런스 코드(10종 확장판)는 별도 연구 논문 심사가 완료된 이후
> 별도 저장소로 공개될 예정입니다.

---

## MLML 시나리오 예시

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

전체 예시는 [`examples/iu_istanu.mlml`](examples/iu_istanu.mlml)에서 볼 수 있습니다.

---

## 데모 영상

| 곡 | 응원봉 수 | 링크 |
|------|-------------|------|
| IU - 관객이 될게 (I Stan U) — ACM MM 2026 논문 데모 | 12 | [▶ YouTube](https://youtu.be/cPKkz_UI0TA) |
| IU - 관객이 될게 (I Stan U) | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
| IU - Blueming | 16 | [▶ YouTube](https://youtu.be/KHmO7usMysU) |
| IU - Shopper | 16 | [▶ YouTube](https://youtu.be/DDSjNIcno14) |
| Aespa - Supernova | 16 | [▶ YouTube](https://youtu.be/a_pUyoQBCkE) |
| Michael Jackson - Billie Jean | 16 | [▶ YouTube](https://youtu.be/BQ4oGPVca64) |

---

## 버전 히스토리

| 버전 | 핵심 추가 내용 |
|---|---|
| v1.0 | 4계층 구조, 16종 단일 이펙트, 12종 공간 이펙트, EIC/SAS/TA |
| v1.1 | `beat_reactive.on_kick`, `bass_track`, `color_cycle`, KFA/BBC/CCR |
| v1.2 | `global_mood`, `section_defaults`, `expectation_break`, `bookend`, `lyric_map`, `spotlight`, CS/EBS/LCC |
| v1.3 | `lyric_map` SRT 자동 파싱 + 8종 감정 사전, `mp3_to_mlml` 4단계 파이프라인, 라디오 3-class 세그멘테이션 프로파일, archetype 6종, LCC 메트릭 |

---

## 연구

본 프로젝트는 **[Data Networks Lab](https://networks.cnu.ac.kr)**
(충남대학교 컴퓨터인공지능학부)의 진행 중인 연구의 일환입니다.

- 📄 **"MLML: An Open Music-to-Light Markup Language for Democratizing Fan Lightstick
  Choreography"** — **ACM Multimedia 2026, Interactive Art Track** 채택
  (리우데자네이루, 2026년 11월 10–14일)
- 🔬 전체 명세는 여기에 공개되어 있으며, BLE 제어 레퍼런스 코드는 후속 시스템 논문
  진행 상황에 따라 공개될 예정입니다.

### 인용

```bibtex
@inproceedings{mlml2026,
  title={MLML: An Open Music-to-Light Markup Language
         for Democratizing Fan Lightstick Choreography},
  author={Lee, Youngseok and Jin, Minhyuk},
  booktitle={ACM Multimedia 2026, Interactive Art Track},
  year={2026}
}
```

기계가 읽을 수 있는 버전은 [`CITATION.cff`](CITATION.cff)를 참고하세요.

---

## 로드맵

- [x] BLE 프로토콜 분석 (IU, Blackpink, SEVENTEEN, NMIXX)
- [x] MLML v1.3 명세
- [x] 실시간 플레이어 (응원봉 16개)
- [x] LLM 기반 시나리오 생성
- [x] ACM MM 2026 데모 영상
- [ ] BLE 제어 레퍼런스 코드 (후속 논문 진행 상황에 따라)
- [ ] MLML Hub (커뮤니티 공유 플랫폼)
- [ ] 웹 기반 에디터
- [ ] 모바일 앱
- [ ] 오픈 SDK 공개

---

## 연락처 및 협업

연구 협력, 파트너십 문의:
📧 lee@cnu.ac.kr
🏫 Data Networks Lab, 충남대학교

⭐ 전체 레퍼런스 코드 공개 알림을 받으시려면 **이 저장소에 Star**를 눌러주세요!

## 라이선스

본 명세와 문서는 [Apache License 2.0](LICENSE)에 따라 공개됩니다.
