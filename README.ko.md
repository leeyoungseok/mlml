# 🎵 MLML — Music-to-Light Markup Language

**한국어** | [English](README.md)

> 음악 기반 K-pop 응원봉 안무를 위한 개방형 명세
> 음악의 구조와 감성을 BLE / Wi-Fi / Zigbee 조명 장치의 실시간 색상 제어로 변환하기 위한
> YAML 기반 선언형 중간 표현 언어 (Spec v1.3)

[![ACM Multimedia 2026 - Interactive Art](https://img.shields.io/badge/ACM%20MM%202026-Interactive%20Art%20(Accepted)-purple)](#연구)
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)](https://youtu.be/a4oUMooHqgo)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**Data Networks Lab, 충남대학교** · [networks.cnu.ac.kr](https://networks.cnu.ac.kr)

---

## 데모 — 응원봉 12개 동기화 (ACM MM 2026 논문 데모)

[![MLML Demo](https://i.ytimg.com/vi/a4oUMooHqgo/maxresdefault.jpg)](https://youtu.be/a4oUMooHqgo)

*IU "I Stan U" (관객이 될게) 응원봉 12개를 MLML 플레이어로 실시간 동기화한, ACM MM 2026
Interactive Art 논문에 실린 데모입니다. 더 큰 규모의 응원봉 16개 데모는 아래
[데모 영상](#데모-영상) 섹션에서 확인할 수 있습니다.*

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

> BLE 역공학 레퍼런스 코드는 별도 연구 논문 심사가 완료된 이후
> 별도 저장소로 공개될 예정입니다.

---

## MLML 시나리오 예시

```yaml
metadata:
  title: I Stan U
  artist: IU
  bpm: 161.5
  key: G_major

timeline:
- {t: 0.0,   group: 0, color: neutral,   effect: breath,            intensity: 0.32, period: 4.0, note: intro #1}
- {t: 8.99,  group: 0, color: peak,      effect: flash_all,         intensity: 0.65, note: energy surge}
- {t: 12.14, group: 0, color: secondary, effect: tension_build,     intensity: 0.96, note: prechorus #1}
- {t: 23.92, group: 0, color: null,      effect: expectation_break, intensity: 0.0,  note: blackout (end of pre-chorus)}
```

모든 이벤트에는 `note` 필드가 붙어, 컴파일러가 **왜** 그 시점에 그 효과를 배치했는지가
남습니다 — 구간 라벨, 검출된 킥 세기, 트리거가 된 에너지 전이 등. 창작 의도가 산출물
안에서 그대로 읽힙니다.

전체 예시는 [`examples/iu_istanu.mlml`](examples/iu_istanu.mlml)에 있습니다. 247.7초 트랙에서
컴파일된 **timeline 이벤트 135개**로, 28개 효과 중 23개가 등장합니다.

```bash
# 예시 재현 (결정성을 위해 LLM 보정 비활성화)
python mp3_to_mlml.py istanu.mp3 --no-llm
```

> `metadata`의 `title` / `artist` / `genre`만 수동 보정했고, 나머지는 전부 컴파일러
> 출력입니다. 생성된 스크립트에는 가사가 포함되지 않습니다 — `lyric_map`은 감정 라벨과
> 타이밍만 담습니다.

---

## 컴파일러

`mp3_to_mlml.py`는 논문에 사용된 레퍼런스 구현입니다. 오디오를 분석해 MLML v1.3 스크립트를
생성합니다.

```bash
pip install -r requirements.txt
python mp3_to_mlml.py song.mp3 --no-llm
```

| 옵션 | 효과 |
|---|---|
| `--no-llm` | LLM 보정 생략. **재현 가능한 출력에 필수** — 보정은 비결정적입니다. |
| `--srt song.srt` | 가사 타이밍에서 조명 큐를 도출합니다. |
| `--include-lyric-text` | 가사 원문을 포함합니다. **기본은 꺼짐** — 가사는 대개 저작물이므로, 이 옵션을 쓰지 않으면 생성된 스크립트를 자유롭게 배포할 수 있습니다. |
| `--no-demucs` | 소스 분리 생략 (빠르지만 정확도 하락). |
| `--llm-model` | 보정에 쓸 모델명을 지정합니다. |

`madmom`과 `demucs`는 선택 사항이며, 없으면 librosa로 폴백합니다. 이때 비트 검출 결과가
달라지므로 모든 스크립트에 어느 경로가 실행됐는지 기록됩니다.

```yaml
metadata:
  analysis_meta:
    beat_source: madmom     # 또는: librosa
    bpm_confidence: 0.87
```

---

## 데모 영상

| 곡 | 응원봉 수 | 링크 |
|------|-------------|------|
| IU - 관객이 될게 (I Stan U) — ACM MM 2026 논문 데모 | 12 | [▶ YouTube](https://youtu.be/a4oUMooHqgo) |
| Bigbang - Sunset | 12 | [▶ YouTube](https://youtu.be/cPKkz_UI0TA) |
| IU - 관객이 될게 (I Stan U) — 확장 실험 (더 큰 규모) | 16 | [▶ YouTube](https://youtu.be/4xf9s3fa-oU) |
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
| v1.3 | `lyric_map` SRT 자동 파싱 + 8종 감정 사전, `mp3_to_mlml` 4단계 파이프라인, LCC 메트릭 |

---

## 연구

본 프로젝트는 **[Data Networks Lab](https://networks.cnu.ac.kr)**
(충남대학교 컴퓨터인공지능학부)의 진행 중인 연구의 일환입니다.

- 📄 **"MLML: An Open Music-to-Light Markup Language for Democratizing Fan Lightstick
  Choreography"** — **ACM Multimedia 2026, Interactive Art Track** 채택
  (리우데자네이루, 2026년 11월 10–14일) · [10.1145/3767308.3838318](https://doi.org/10.1145/3767308.3838318)
- 🔬 전체 명세는 여기에 공개되어 있으며, BLE 제어 레퍼런스 코드는 후속 시스템 논문
  진행 상황에 따라 공개될 예정입니다.

### 인용

```bibtex
@inproceedings{mlml2026,
  title={MLML: An Open Music-to-Light Markup Language
         for Democratizing Fan Lightstick Choreography},
  author={Lee, Youngseok and Jin, Minhyuk},
  booktitle={ACM Multimedia 2026, Interactive Art Track},
  year={2026},
  doi={10.1145/3767308.3838318}
}
```

기계가 읽을 수 있는 버전은 [`CITATION.cff`](CITATION.cff)를 참고하세요.

---

## 로드맵

- [x] BLE 프로토콜 분석 (IU, Blackpink, NMIXX)
- [x] MLML v1.3 명세
- [x] 실시간 플레이어 (응원봉 16개)
- [x] LLM 기반 시나리오 생성
- [x] ACM MM 2026 데모 영상
- [x] MLML 컴파일러 (`mp3_to_mlml.py`) 공개
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
