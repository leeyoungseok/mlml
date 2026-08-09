#!/usr/bin/env python3
# Copyright 2026 Youngseok Lee, Data Networks Lab, Chungnam National University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
"""
mp3_to_mlml.py - compile an MP3 into an MLML v1.3 lighting script.

Reference implementation for:
  MLML: An Open Music-to-Light Markup Language for Democratizing Fan
  Lightstick Choreography. ACM Multimedia 2026, Interactive Art Track.

Pipeline: demucs (source separation) -> madmom (beat/downbeat tracking)
-> librosa (spectral features) -> MLML YAML.  Every stage degrades
gracefully: with none of the optional packages installed, librosa alone
still produces a complete script.  The block that actually ran is
recorded in `metadata.analysis_meta.beat_source`, so results stay
auditable.

Adaptive rhythm lighting with restrained flash/strobe:

  Three rhythm-response layers:
    1. bass_track.follow  - brightness follows low-band energy (whole song)
    2. beat_reactive      - global kick/snare/hi-hat response, BPM-scaled
    3. timeline kicks     - selected kicks in emphasised sections only

  beat_flash thresholds (BPM adaptive):
    slow      (< 90) : no timeline kick events, beat_reactive only
    mid    (90-120)  : late-prechorus kicks only, chorus every 2 beats
    fast  (120-150)  : chorus every beat, top 40% energy only
    very fast (>=150): every 0.5 beat, top 30% energy only

  fast_strobe: BPM>=128 + high energy + climax + preceded by prechorus,
               capped at 2 per song
  Energy-surge flash: top 3% only, capped at 4 events

Reproducibility:
    Pass --no-llm for deterministic output.  LLM refinement is
    non-deterministic and will not reproduce a byte-identical script.

Privacy / copyright:
    Lyric text from --srt is NOT written to the output by default; only
    emotion labels and timings are kept.  Pass --include-lyric-text to
    embed the raw lines (do not redistribute the result if the lyrics
    are copyrighted).

Usage:
    python mp3_to_mlml.py song.mp3
    python mp3_to_mlml.py song.mp3 --srt song.srt
    python mp3_to_mlml.py song.mp3 --no-demucs
    python mp3_to_mlml.py song.mp3 --device cuda
    python mp3_to_mlml.py song.mp3 --llm gpt
    python mp3_to_mlml.py song.mp3 --no-llm
    python mp3_to_mlml.py song.mp3 --prompt "bright, airy summer mood"
    python mp3_to_mlml.py song.mp3 --save-analysis

Dependencies:
    pip install librosa madmom demucs numpy scipy pyyaml anthropic openai soundfile
    # madmom, demucs, anthropic and openai are all optional
"""

import sys
import os
import re
import copy
import json
import argparse
import warnings
import tempfile
import shutil
import subprocess
from pathlib import Path

import numpy as np
import yaml
import librosa
import librosa.effects
import soundfile as sf

warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════════════
# Global constants
# ══════════════════════════════════════════════════════════════════

SR  = 22050
HOP = 512

# Optional LLM refinement. Override with MLML_ANTHROPIC_MODEL /
# MLML_OPENAI_MODEL, or --llm-model. Model names age quickly; check the
# provider's current catalogue before relying on these defaults.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_OPENAI_MODEL    = "gpt-4o-mini"

KEY_TO_HUE = {
    "C": 0,   "C#": 30,  "D": 60,  "D#": 90,
    "E": 120, "F": 150,  "F#": 180, "G": 210,
    "G#": 240, "A": 270, "A#": 300, "B": 330,
}

EMOTION_DICT = {
    "love":      ["사랑", "좋아", "사랑해", "그리워", "보고싶", "두근", "설레",
                  "love", "adore", "heart", "darling"],
    "happy":     ["행복", "기뻐", "기쁨", "즐거", "웃음", "신나",
                  "happy", "joy", "smile", "laugh", "fun"],
    "romantic":  ["달빛", "별", "꿈", "영원", "함께", "곁에", "손잡",
                  "romantic", "dream", "forever", "together", "moonlight"],
    "sad":       ["슬퍼", "눈물", "울어", "아파", "힘들", "그리움", "떠나",
                  "sad", "cry", "tears", "hurt", "pain", "lonely"],
    "hope":      ["희망", "기다려", "믿어", "괜찮", "다시", "내일",
                  "hope", "believe", "trust", "okay", "again", "tomorrow"],
    "nostalgic": ["그때", "추억", "기억", "옛날", "예전", "돌아",
                  "memory", "remember", "past", "nostalgic"],
    "excited":   ["설레", "두근두근", "떨려", "기대", "신기",
                  "excited", "thrill", "nervous", "anticipate", "amazing"],
    "calm":      ["괜찮아", "편해", "쉬어", "잠들", "조용", "평화", "위로",
                  "calm", "peace", "rest", "comfort", "still"],
    "powerful":  ["강해", "외쳐", "달려", "폭발", "지지않아", "싸워",
                  "strong", "fight", "run", "power", "roar", "fire"],
    "dreamy":    ["몽환", "흐릿", "구름", "잠겨", "부유", "환상",
                  "dreamy", "float", "haze", "blur", "fantasy", "ethereal"],
}

EMOTION_COLOR = {
    "love":      {"hue": 350, "sat": 0.90, "val": 1.00},
    "happy":     {"hue":  45, "sat": 0.90, "val": 1.00},
    "romantic":  {"hue": 330, "sat": 0.85, "val": 0.95},
    "sad":       {"hue": 220, "sat": 0.70, "val": 0.70},
    "hope":      {"hue": 180, "sat": 0.55, "val": 0.90},
    "nostalgic": {"hue":  30, "sat": 0.70, "val": 0.80},
    "excited":   {"hue":   0, "sat": 1.00, "val": 1.00},
    "calm":      {"hue": 200, "sat": 0.40, "val": 0.75},
    "powerful":  {"hue":  15, "sat": 1.00, "val": 1.00},
    "dreamy":    {"hue": 280, "sat": 0.60, "val": 0.85},
}

EMOTION_INTENSITY = {
    "love": 0.80, "happy": 0.85, "romantic": 0.75,
    "sad":  0.55, "hope":  0.70, "nostalgic": 0.60,
    "excited": 0.95, "calm": 0.45,
    "powerful": 1.00, "dreamy": 0.65,
}

TEMP_MAP = {
    "love": "warm", "happy": "energetic", "romantic": "warm",
    "sad": "cool", "hope": "warm", "nostalgic": "cool",
    "excited": "energetic", "calm": "cool",
    "powerful": "energetic", "dreamy": "mystic",
}

# Effect rotation per section type (cycled when a section repeats)
SECTION_EFFECTS = {
    "intro":     ["breath", "slow_pulse", "dim_glow", "fade_inout"],
    "verse":     ["heart_pulse", "slow_pulse", "pitch_track", "call_and_response", "double_blink"],
    "prechorus": ["tension_build", "chase", "bounce", "color_sweep"],
    "chorus":    ["release_burst", "rainbow", "wave_lr", "flash_all", "sparkle"],
    "climax":    ["release_burst", "color_wipe", "rainbow", "flash_all", "bounce"],
    "bridge":    ["dim_glow", "twinkle", "fade_inout", "shimmer", "breath"],
    "outro":     ["slow_pulse", "breath", "fade_inout", "dim_glow"],
}

SECTION_COLORS = {
    "intro":     ["neutral", "cool", "primary"],
    "verse":     ["primary", "warm", "secondary", "cool"],
    "prechorus": ["secondary", "warm", "peak"],
    "chorus":    ["peak", "love", "happy", "complement", "triad_a"],
    "climax":    ["peak", "white", "love", "gold"],
    "bridge":    ["cool", "dreamy", "moonlight", "neutral"],
    "outro":     ["love", "warm", "primary"],
}


# ══════════════════════════════════════════════════════════════════
# 0. SRT parsing and lyric analysis
# ══════════════════════════════════════════════════════════════════

def parse_srt(path: str) -> list:
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    entries = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.strip().splitlines()
        time_line, text_start = None, 0
        for i, ln in enumerate(lines):
            if "-->" in ln:
                time_line, text_start = ln, i + 1
                break
        if not time_line:
            continue
        m = re.match(
            r"(\d+):(\d+):(\d+)[,\.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,\.](\d+)",
            time_line.strip(),
        )
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
        end   = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
        text  = re.sub(r"<[^>]+>", "", " ".join(lines[text_start:])).strip()
        if text:
            entries.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return entries


def detect_emotion(text: str) -> tuple:
    tl = text.lower()
    scores = {}
    for emotion, keywords in EMOTION_DICT.items():
        hit = sum(1 for kw in keywords if kw in tl)
        if hit > 0:
            scores[emotion] = hit * EMOTION_INTENSITY.get(emotion, 0.7)
    if not scores:
        return None, 0.0
    best = max(scores, key=lambda e: scores[e])
    return best, scores[best]


def analyze_lyrics(srt_entries: list) -> dict:
    manual_map = []
    emotion_stats = {e: 0.0 for e in EMOTION_DICT}
    for entry in srt_entries:
        emotion, score = detect_emotion(entry["text"])
        dur = round(entry["end"] - entry["start"], 2)
        item = {
            "time": entry["start"], "text": entry["text"], "duration": dur,
            "emotion": emotion, "color": emotion,
            "brightness": EMOTION_INTENSITY.get(emotion, 0.7) if emotion else None,
        }
        if emotion:
            emotion_stats[emotion] += score
        manual_map.append(item)
    dominant = max(emotion_stats, key=lambda e: emotion_stats[e])
    if emotion_stats[dominant] == 0:
        dominant = None
    return {
        "manual_map": manual_map, "emotion_stats": emotion_stats,
        "dominant_emotion": dominant, "n_lines": len(srt_entries),
    }


# ══════════════════════════════════════════════════════════════════
# 1-A. demucs source separation (returns None when unavailable)
# ══════════════════════════════════════════════════════════════════

def run_demucs(mp3_path: str, device: str = "cpu") -> dict | None:
    """
    htdemucs 4-stem 분리 → {drums, bass, vocals, other}
    실패 시 None 반환 (graceful fallback)
    """
    try:
        import demucs.separate  # noqa: F401
    except ImportError:
        print("  ! demucs not installed (pip install demucs) - continuing with librosa")
        return None

    tmp_dir = tempfile.mkdtemp(prefix="demucs_")
    try:
        print(f"  running demucs (device={device})...")
        # 1차: htdemucs 4-stem (정확)
        cmd_4stem = [
            sys.executable, "-m", "demucs",
            "-n", "htdemucs", "-o", tmp_dir, "-d", device, mp3_path,
        ]
        # 2차 fallback: 2-stem vocals/no_vocals (빠름)
        cmd_2stem = [
            sys.executable, "-m", "demucs",
            "--two-stems", "vocals", "-o", tmp_dir, "-d", device, mp3_path,
        ]
        res = subprocess.run(cmd_4stem, capture_output=True, text=True, timeout=600)
        if res.returncode != 0:
            print("  -> htdemucs failed, retrying with 2 stems...")
            res = subprocess.run(cmd_2stem, capture_output=True, text=True, timeout=600)
            if res.returncode != 0:
                print(f"  ! demucs failed: {res.stderr[-200:]}")
                return None

        # 출력 wav 탐색
        stem_dir = None
        for root, _, files in os.walk(tmp_dir):
            if any(f.endswith(".wav") for f in files):
                stem_dir = root
                break
        if not stem_dir:
            return None

        stems = {}
        for name in ["drums", "bass", "vocals", "other", "no_vocals"]:
            p = os.path.join(stem_dir, f"{name}.wav")
            if os.path.exists(p):
                y, sr_orig = sf.read(p)
                if y.ndim == 2:
                    y = y.mean(axis=1)
                if sr_orig != SR:
                    y = librosa.resample(y, orig_sr=sr_orig, target_sr=SR)
                stems[name] = y.astype(np.float32)

        print(f"  demucs done: {list(stems.keys())}")
        return stems if stems else None

    except subprocess.TimeoutExpired:
        print("  ! demucs timed out (600s)")
        return None
    except Exception as e:
        print(f"  ! demucs error: {e}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
# 1-B. madmom beat / downbeat tracking (falls back to librosa)
# ══════════════════════════════════════════════════════════════════

def madmom_beats(mp3_path: str, drums_y: np.ndarray | None = None) -> dict:
    """
    RNN 기반 비트 + 다운비트 추적.
    drums_y: demucs 드럼 신호 (있으면 더 정확)
    반환: {beat_times, downbeat_times, bpm, bpm_confidence}
    """
    try:
        from madmom.features.beats import RNNBeatProcessor, BeatTrackingProcessor
        from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
    except ImportError:
        print("  ! madmom not installed (pip install madmom) - falling back to librosa")
        return {"beat_source": "librosa", "fallback_reason": "madmom_not_installed"}

    try:
        print("  madmom beat tracking...")
        input_path = mp3_path
        tmp_wav = None

        # 드럼 신호 있으면 임시 wav 사용 (더 정확)
        if drums_y is not None:
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(tmp_wav.name, drums_y, SR)
            input_path = tmp_wav.name
            print("  -> tracking on the separated drum stem")

        beat_proc  = RNNBeatProcessor()(input_path)
        beat_times = BeatTrackingProcessor(fps=100)(beat_proc).tolist()

        try:
            db_proc  = RNNDownBeatProcessor()(input_path)
            db_res   = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)(db_proc)
            downbeat_times = [row[0] for row in db_res if int(row[1]) == 1]
        except Exception:
            downbeat_times = beat_times[::4] if beat_times else []

        if tmp_wav:
            os.unlink(tmp_wav.name)

        if len(beat_times) > 4:
            intervals      = np.diff(beat_times)
            median_iv      = float(np.median(intervals))
            bpm            = round(60.0 / median_iv, 1)
            bpm_confidence = float(max(0.0, 1.0 - np.std(intervals) / (median_iv + 1e-6)))
        else:
            bpm, bpm_confidence = 120.0, 0.5

        print(f"  madmom: BPM={bpm} (confidence={bpm_confidence:.2f}), "
              f"beats={len(beat_times)}, downbeats={len(downbeat_times)}")
        return {
            "beat_times": beat_times, "downbeat_times": downbeat_times,
            "bpm": bpm, "bpm_confidence": bpm_confidence,
            "beat_source": "madmom",
        }
    except Exception as e:
        print(f"  ! madmom failed: {e}")
        return {"beat_source": "librosa", "fallback_reason": f"madmom_error: {e}"}


# ══════════════════════════════════════════════════════════════════
# 1-C. librosa feature extraction
# ══════════════════════════════════════════════════════════════════

def _calc_kfa(kick_times: list, beat_times: list, tol: float = 0.030) -> float:
    if not kick_times or not beat_times:
        return 0.0
    matched = sum(1 for k in kick_times if any(abs(k - b) <= tol for b in beat_times))
    return matched / len(kick_times)


def _classify_segments(rms_smooth, times, duration, seg_dur, bpm, downbeat_times) -> list:
    bar_len    = 60.0 / bpm * 4
    boundaries = [0.0]
    t = seg_dur
    while t < duration:
        if downbeat_times:
            closest = min(downbeat_times, key=lambda db: abs(db - t))
            if abs(closest - t) < bar_len / 2:
                t = closest
        boundaries.append(round(t, 2))
        t += seg_dur
    boundaries.append(round(duration, 2))
    boundaries = sorted(set(boundaries))

    seg_energies = []
    for i in range(len(boundaries) - 1):
        t0, t1 = boundaries[i], boundaries[i+1]
        mask = (times >= t0) & (times < t1)
        e = float(np.mean(rms_smooth[mask])) if mask.any() else 0.0
        seg_energies.append(e)

    arr = np.array(seg_energies)
    hi  = np.percentile(arr, 72)
    lo  = np.percentile(arr, 22)
    n   = len(arr)
    segs = []
    for i, e in enumerate(arr):
        t0, t1 = boundaries[i], boundaries[i+1]
        frac   = i / max(1, n - 1)
        if i == 0:
            stype = "intro"
        elif i >= n - 2:
            stype = "outro"
        elif e >= hi:
            stype = "climax" if frac > 0.55 else "chorus"
        elif e <= lo:
            stype = "bridge"
        elif e >= hi * 0.78:
            stype = "prechorus"
        else:
            stype = "verse"
        segs.append(dict(start=t0, end=t1, type=stype, energy=round(float(e), 3)))
    return segs


def _infer_genre_mood(bpm, energy_ratio, danceability, is_major,
                      sc_mean, zcr_mean, dynamic_range):
    sc_norm     = min(1.0, sc_mean / 4000.0)
    is_acoustic = zcr_mean < 0.05
    is_dynamic  = dynamic_range > 20.0

    if bpm > 140 and danceability > 0.70 and sc_norm > 0.45:
        return "k-pop", ["cheerful", "energetic", "exciting"], "RHYTHM_FAST", "energetic"
    elif bpm > 120 and danceability > 0.60:
        mood = ["cheerful", "romantic"] if is_major else ["energetic", "mysterious"]
        return "k-pop", mood, "RHYTHM_FAST", "warm" if is_major else "cool"
    elif bpm < 80 and energy_ratio < 0.45 and is_acoustic:
        mood = ["romantic", "nostalgic", "calm"] if is_major else ["sad", "lonely", "nostalgic"]
        return "ballad", mood, "BGM_SONG", "warm" if is_major else "cool"
    elif bpm < 100 and sc_norm < 0.40:
        genre = "ballad" if energy_ratio < 0.55 else "r&b"
        mood  = ["romantic", "dreamy"] if is_major else ["sad", "nostalgic"]
        return genre, mood, "BGM_SONG", "warm" if is_major else "mystic"
    elif not is_major and sc_norm > 0.35:
        return "r&b", ["mysterious", "dreamy", "powerful"], "BGM_SONG", "mystic"
    elif is_dynamic and energy_ratio > 0.6:
        mood = ["powerful", "excited", "hopeful"] if is_major else ["powerful", "mysterious"]
        return "pop", mood, "RHYTHM_FAST", "energetic"
    else:
        mood = ["cheerful", "romantic"] if is_major else ["calm", "dreamy"]
        return "pop", mood, "BGM_SONG", "warm" if is_major else "mystic"


def librosa_features(
    y_mono: np.ndarray,
    stems: dict | None,
    madmom_result: dict,
) -> dict:
    """
    librosa 기반 전체 특징 추출.
    madmom 결과 우선, fallback → librosa 3-way 앙상블.
    stems 있으면 더 정확한 드럼/베이스 에너지 계산.
    """
    duration = librosa.get_duration(y=y_mono, sr=SR)

    # ── BPM: madmom 우선, fallback librosa 앙상블 ──────────────────
    if madmom_result.get("bpm") and madmom_result.get("bpm_confidence", 0) > 0.65:
        bpm            = madmom_result["bpm"]
        bpm_confidence = madmom_result["bpm_confidence"]
        beat_times     = madmom_result["beat_times"]
        downbeat_times = madmom_result.get("downbeat_times", beat_times[::4])
        beat_source    = "madmom"
        fallback_reason = ""
        print(f"  BPM (madmom): {bpm} | confidence={bpm_confidence:.2f}")
    else:
        beat_source = "librosa"
        if madmom_result.get("bpm"):
            fallback_reason = (f"madmom_low_confidence: "
                               f"{madmom_result.get('bpm_confidence', 0):.2f} <= 0.65")
        else:
            fallback_reason = madmom_result.get("fallback_reason", "madmom_unavailable")
        # librosa 3-way
        t1_raw, bf = librosa.beat.beat_track(y=y_mono, sr=SR, hop_length=HOP, units="time")
        bpm1 = float(np.atleast_1d(t1_raw)[0])
        bt_raw = list(bf) if isinstance(bf, (list, np.ndarray)) else []
        if len(bt_raw) > 0 and isinstance(bt_raw[0], (int, np.integer)):
            bt_raw = librosa.frames_to_time(
                np.array(bt_raw, dtype=int), sr=SR, hop_length=HOP).tolist()

        onset_env = librosa.onset.onset_strength(y=y_mono, sr=SR, hop_length=HOP)
        tg        = librosa.feature.tempogram(onset_envelope=onset_env, sr=SR, hop_length=HOP)
        tg_freqs  = librosa.tempo_frequencies(tg.shape[0], sr=SR, hop_length=HOP)
        bpm2      = float(tg_freqs[np.argmax(tg.mean(axis=1))])

        try:
            pulse = librosa.beat.plp(onset_envelope=onset_env, sr=SR, hop_length=HOP)
            plp_pk = librosa.util.peak_pick(
                pulse, pre_max=3, post_max=3, pre_avg=5, post_avg=5, delta=0.1, wait=5)
            plp_t = librosa.frames_to_time(plp_pk, sr=SR, hop_length=HOP).tolist()
            bpm3  = round(60.0 / float(np.median(np.diff(plp_t))), 1) if len(plp_t) > 4 else bpm1
        except Exception:
            bpm3 = bpm1

        bpm_arr        = np.array([bpm1, bpm2, bpm3])
        bpm            = float(np.median(bpm_arr))
        bpm_confidence = float(max(0.0, 1.0 - np.std(bpm_arr) / (bpm + 1e-6)))
        beat_times     = bt_raw
        downbeat_times = beat_times[::4] if beat_times else []
        print(f"  BPM (librosa ensemble): {bpm:.1f} [{bpm1:.1f}, {bpm2:.1f}, {bpm3:.1f}]"
              f" confidence={bpm_confidence:.2f}")

    # ── RMS 에너지 ───────────────────────────────────────────────
    rms         = librosa.feature.rms(y=y_mono, hop_length=HOP)[0]
    rms_norm    = rms / (np.max(rms) + 1e-6)
    rms_smooth  = np.convolve(rms_norm, np.ones(8) / 8, mode="same")
    times       = librosa.frames_to_time(np.arange(len(rms_norm)), sr=SR, hop_length=HOP)
    p95         = float(np.percentile(rms_norm, 95))
    energy_ratio = min(1.0, float(np.mean(rms_norm)) / (p95 + 1e-6))

    # ── HPSS ────────────────────────────────────────────────────
    y_harm, y_perc = librosa.effects.hpss(y_mono, margin=3.0)

    # ── STFT 전체 스펙트럼 ───────────────────────────────────────
    S_full = np.abs(librosa.stft(y_mono, hop_length=HOP))
    freqs  = librosa.fft_frequencies(sr=SR)

    # ── 베이스 에너지 (demucs bass 우선) ────────────────────────
    if stems and "bass" in stems:
        bass_y_s    = stems["bass"][:len(y_mono)]
        S_bass      = np.abs(librosa.stft(bass_y_s, hop_length=HOP))
        b_mask      = freqs <= 200
        bass_energy = np.mean(S_bass[b_mask, :], axis=0)
        print("  bass energy: using demucs bass stem")
    else:
        b_mask      = freqs <= 200
        bass_energy = np.mean(S_full[b_mask, :], axis=0)

    bass_norm   = bass_energy / (np.max(bass_energy) + 1e-6)
    bass_smooth = np.convolve(bass_norm, np.ones(5) / 5, mode="same")

    # Low-mid (200~500Hz)
    lm_mask      = (freqs >= 200) & (freqs <= 500)
    lowmid_norm  = np.mean(S_full[lm_mask, :], axis=0) if lm_mask.any() else np.zeros(S_full.shape[1])
    lowmid_norm  = lowmid_norm / (np.max(lowmid_norm) + 1e-6)

    # ── Sub-bass (20~100Hz) 킥 감지용 ───────────────────────────
    sub_mask = (freqs >= 20) & (freqs <= 100)

    if stems and "drums" in stems:
        drums_y_s    = stems["drums"][:len(y_mono)]
        S_drums      = np.abs(librosa.stft(drums_y_s, hop_length=HOP))
        subbass_norm = np.mean(S_drums[sub_mask, :], axis=0)
        kick_env     = librosa.onset.onset_strength(y=drums_y_s, sr=SR, hop_length=HOP, fmax=180)
        print("  kick / sub-bass: using demucs drum stem")
    else:
        subbass_norm = np.mean(S_full[sub_mask, :], axis=0)
        kick_env     = librosa.onset.onset_strength(y=y_perc, sr=SR, hop_length=HOP, fmax=180)

    subbass_norm = subbass_norm / (np.max(subbass_norm) + 1e-6)
    kick_norm    = kick_env / (np.max(kick_env) + 1e-6)

    # ── 킥드럼 피크 감지 (구간별 적응형 threshold) ──────────────
    bar_len        = 60.0 / bpm * 4
    frame_dur      = HOP / SR
    frames_per_bar = max(1, int(bar_len / frame_dur))
    n_frames       = len(kick_norm)
    kick_peaks_all = []
    for sf_ in range(0, n_frames, frames_per_bar * 4):
        ef_   = min(sf_ + frames_per_bar * 4, n_frames)
        chunk = kick_norm[sf_:ef_]
        delta = max(float(np.percentile(chunk, 75)) * 0.6, 0.15)
        peaks = librosa.util.peak_pick(
            chunk, pre_max=2, post_max=2,
            pre_avg=3, post_avg=5, delta=delta, wait=3)
        kick_peaks_all.extend((peaks + sf_).tolist())

    kick_times = (times[np.array(kick_peaks_all, dtype=int)].tolist()
                  if kick_peaks_all else [])

    kfa = _calc_kfa(kick_times, beat_times)
    print(f"  kicks: {len(kick_times)} | KFA={kfa:.3f}")

    # ── 하이햇 / 스네어 ─────────────────────────────────────────
    hi_mask   = freqs >= 4000
    hi_norm   = np.mean(S_full[hi_mask, :], axis=0)
    hi_norm   = hi_norm / (np.max(hi_norm) + 1e-6)
    snare_env = librosa.onset.onset_strength(y=y_perc, sr=SR, hop_length=HOP, fmin=200, fmax=4000)
    snare_norm = snare_env / (np.max(snare_env) + 1e-6)

    # ── 보컬 존재 구간 (demucs vocals 우선) ─────────────────────
    if stems and "vocals" in stems:
        voc_y    = stems["vocals"][:len(y_mono)]
        voc_rms  = librosa.feature.rms(y=voc_y, hop_length=HOP)[0]
        voc_norm = voc_rms / (np.max(voc_rms) + 1e-6)
        vocal_mask = (voc_norm > 0.15).tolist()
        print(f"  vocal frames: {sum(vocal_mask)}/{len(vocal_mask)} (demucs)")
    else:
        # HPSS 하모닉으로 보컬 근사
        voc_rms  = librosa.feature.rms(y=y_harm, hop_length=HOP)[0]
        voc_norm = voc_rms / (np.max(voc_rms) + 1e-6)
        vocal_mask = (voc_norm > 0.20).tolist()

    # ── 크로마 + 조성 ────────────────────────────────────────────
    chroma      = librosa.feature.chroma_cqt(y=y_harm, sr=SR, hop_length=HOP)
    chroma_mean = np.mean(chroma, axis=1)
    dom_pitch   = int(np.argmax(chroma_mean))
    is_major    = bool(chroma_mean[(dom_pitch + 4) % 12] >= chroma_mean[(dom_pitch + 3) % 12])
    key_names   = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    key_str     = f"{key_names[dom_pitch]}_{'major' if is_major else 'minor'}"
    chroma_entropy = float(-np.sum(
        (chroma_mean / (chroma_mean.sum() + 1e-6)) *
        np.log(chroma_mean / (chroma_mean.sum() + 1e-6) + 1e-9)))

    # ── 스펙트럴 특징 ────────────────────────────────────────────
    sc           = librosa.feature.spectral_centroid(y=y_mono, sr=SR, hop_length=HOP)[0]
    zcr          = librosa.feature.zero_crossing_rate(y_mono, hop_length=HOP)[0]
    spec_rolloff = librosa.feature.spectral_rolloff(y=y_mono, sr=SR, hop_length=HOP)[0]
    sc_mean      = float(np.mean(sc))
    zcr_mean     = float(np.mean(zcr))
    rolloff_mean = float(np.mean(spec_rolloff))

    # ── MFCC ────────────────────────────────────────────────────
    mfcc      = librosa.feature.mfcc(y=y_mono, sr=SR, n_mfcc=13, hop_length=HOP)
    mfcc_mean = np.mean(mfcc, axis=1).tolist()

    # ── 댄스어빌리티 ────────────────────────────────────────────
    onset_env2 = librosa.onset.onset_strength(y=y_mono, sr=SR, hop_length=HOP)
    bt_fr = librosa.time_to_frames(
        np.clip(np.array(beat_times), 0, duration - 0.01), sr=SR, hop_length=HOP)
    bt_fr = bt_fr[bt_fr < len(onset_env2)]
    beat_strength = (float(np.mean(onset_env2[bt_fr] / (onset_env2.max() + 1e-6)))
                     if len(bt_fr) > 0 else 0.5)
    danceability = min(1.0, max(0.0,
        (bpm / 180) * 0.35 + beat_strength * 0.40 +
        (1 - zcr_mean * 10) * 0.15 + energy_ratio * 0.10))

    # ── 다이나믹 레인지 ─────────────────────────────────────────
    rms_db        = librosa.amplitude_to_db(rms_norm + 1e-6)
    dynamic_range = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 10))

    # ── 구간 분류 ────────────────────────────────────────────────
    n_bars  = 8 if bpm > 140 else 4
    seg_dur = bar_len * n_bars
    segments = _classify_segments(rms_smooth, times, duration, seg_dur, bpm, downbeat_times)

    genre, mood, archetype, temperature = _infer_genre_mood(
        bpm, energy_ratio, danceability, is_major, sc_mean, zcr_mean, dynamic_range)

    print(f"  key: {key_str} | genre: {genre} | energy: {energy_ratio:.3f} "
          f"| danceability: {danceability:.3f}")

    return dict(
        duration=round(duration, 2),
        bpm=round(bpm, 1),
        bpm_confidence=round(bpm_confidence, 3),
        beat_source=beat_source,
        fallback_reason=fallback_reason,
        key=key_str, is_major=is_major, dominant_pitch=dom_pitch,
        chroma_entropy=round(chroma_entropy, 3),
        energy_ratio=round(energy_ratio, 3),
        danceability=round(danceability, 3),
        dynamic_range=round(dynamic_range, 2),
        sc_mean=round(sc_mean, 1),
        zcr_mean=round(zcr_mean, 4),
        rolloff_mean=round(rolloff_mean, 1),
        mfcc_mean=[round(v, 2) for v in mfcc_mean],
        genre=genre, mood=mood, archetype=archetype, temperature=temperature,
        beat_times=beat_times,
        downbeat_times=downbeat_times,
        kick_times=kick_times,
        kfa=round(kfa, 3),
        times=times.tolist(),
        rms_norm=rms_norm.tolist(),
        rms_smooth=rms_smooth.tolist(),
        bass_smooth=bass_smooth.tolist(),
        subbass_norm=subbass_norm.tolist(),
        lowmid_norm=lowmid_norm.tolist(),
        hi_norm=hi_norm.tolist(),
        snare_norm=snare_norm.tolist(),
        vocal_mask=vocal_mask,
        segments=segments,
        has_stems=stems is not None,
    )


# ══════════════════════════════════════════════════════════════════
# 2. Combined analysis entry point
# ══════════════════════════════════════════════════════════════════

def analyze(mp3_path: str, use_demucs: bool = True,
            device: str = "cpu", verbose: bool = True) -> dict:
    """
    demucs 소스 분리 → madmom 비트 추적 → librosa 특징 추출
    각 단계 미설치 시 자동 fallback
    """
    def log(msg):
        if verbose: print(f"  {msg}")

    log(f"loading: {mp3_path}")
    y, _ = librosa.load(mp3_path, sr=SR, mono=False)
    y_mono = librosa.to_mono(y) if y.ndim == 2 else y
    log(f"duration: {librosa.get_duration(y=y_mono, sr=SR):.1f}s | SR={SR}")

    # Step A: demucs
    stems = None
    if use_demucs:
        print("\n[A] demucs source separation")
        stems = run_demucs(mp3_path, device=device)
    else:
        print("\n[A] demucs skipped (--no-demucs)")

    # Step B: madmom
    print("\n[B] madmom beat tracking")
    drums_y = stems.get("drums") if stems else None
    madmom_result = madmom_beats(mp3_path, drums_y=drums_y)

    # Step C: librosa 특징
    print("\n[C] librosa feature extraction")
    return librosa_features(y_mono, stems, madmom_result)


# ══════════════════════════════════════════════════════════════════
# 3. Palette construction
# ══════════════════════════════════════════════════════════════════

def _build_rich_palette(a: dict) -> dict:
    """
    조성 + 장르 + 에너지 기반 20색 팔레트.
    색채 이론 (보색/유사색/삼각/분열보색) 자동 적용.
    """
    key_root = a["key"].split("_")[0]
    base_hue = KEY_TO_HUE.get(key_root, 210)
    is_major = a["is_major"]
    energy   = a["energy_ratio"]
    genre    = a["genre"]
    temp     = a["temperature"]

    sat_base = round(0.75 + energy * 0.20, 2)
    val_base = round(0.85 + energy * 0.10, 2)

    if temp == "energetic":   base_hue = (base_hue + 10) % 360
    elif temp == "cool":      base_hue = (base_hue - 10) % 360
    elif temp == "mystic":    base_hue = (base_hue + 270) % 360

    comp_hue  = (base_hue + 180) % 360
    tri1_hue  = (base_hue + 120) % 360
    tri2_hue  = (base_hue + 240) % 360
    split1    = (base_hue + 150) % 360
    split2    = (base_hue + 210) % 360
    analog1   = (base_hue + 30) % 360
    analog2   = (base_hue - 30) % 360

    secondary_hue = split1 if is_major else split2
    peak_hue      = comp_hue if energy > 0.6 else tri1_hue

    palette = {
        "primary":    {"hue": base_hue,      "sat": sat_base,             "val": val_base},
        "secondary":  {"hue": secondary_hue, "sat": round(sat_base+.05,2),"val": 1.00},
        "peak":       {"hue": peak_hue,      "sat": 1.00,                 "val": 1.00},
        "neutral":    {"hue": base_hue,      "sat": 0.15,                 "val": 0.40},
        "white":      {"hue": 0,             "sat": 0.00,                 "val": 1.00},
        "warm":       {"hue": 18,            "sat": 0.92,                 "val": 1.00},
        "cool":       {"hue": (base_hue+120)%360, "sat": 0.65,           "val": 0.82},
        # 감정 색
        "love":       {"hue": 350, "sat": 0.90, "val": 1.00},
        "happy":      {"hue":  45, "sat": 0.92, "val": 1.00},
        "sad":        {"hue": 220, "sat": 0.65, "val": 0.65},
        "hope":       {"hue": 175, "sat": 0.55, "val": 0.90},
        "dreamy":     {"hue": 280, "sat": 0.60, "val": 0.85},
        "powerful":   {"hue":  15, "sat": 1.00, "val": 1.00},
        # 색채 이론 배색
        "complement": {"hue": comp_hue,  "sat": sat_base,            "val": round(val_base+.05,2)},
        "triad_a":    {"hue": tri1_hue,  "sat": round(sat_base-.05,2),"val": val_base},
        "triad_b":    {"hue": tri2_hue,  "sat": round(sat_base-.05,2),"val": val_base},
        "analog_a":   {"hue": analog1,   "sat": sat_base,             "val": val_base},
        "analog_b":   {"hue": analog2,   "sat": sat_base,             "val": val_base},
        # 특화 색
        "gold":       {"hue": 42,  "sat": 1.00, "val": 1.00},
        "neon":       {"hue": 120, "sat": 1.00, "val": 1.00},
        "purple":     {"hue": 280, "sat": 0.85, "val": 0.95},
        "teal":       {"hue": 175, "sat": 0.90, "val": 0.90},
    }

    if genre == "k-pop":
        palette["signature"] = {"hue": (base_hue + 30) % 360, "sat": 1.00, "val": 1.00}
    elif genre == "ballad":
        palette["moonlight"] = {"hue": 225, "sat": 0.45, "val": 0.80}
        palette["candle"]    = {"hue": 35,  "sat": 0.70, "val": 0.85}
    elif genre == "r&b":
        palette["midnight"]  = {"hue": 250, "sat": 0.80, "val": 0.60}
        palette["sunset"]    = {"hue": 20,  "sat": 0.95, "val": 0.95}

    return palette


# ══════════════════════════════════════════════════════════════════
# 4. Timeline construction (kick-driven strobe + per-section effects)
# ══════════════════════════════════════════════════════════════════

def _build_rich_timeline(a: dict, palette: dict) -> list:
    """
    BPM/장르/에너지 적응형 조명 타임라인.

    핵심 설계 원칙
    ──────────────
    1. 깜빡임(flash/strobe)은 "꼭 필요한 순간"만:
       - beat_flash: 박자 에너지 상위 25%인 킥만 선별, BPM 느릴수록 더 줄임
       - fast_strobe: BPM≥128 + 고에너지 climax 에서만, 곡 전체에 최대 2회
       - 에너지 급변 flash: 전체 상위 3% 이상 급변만 (기존 8% → 3%)

    2. 리듬 조명은 bass_track(실시간) + beat_reactive(전역)로 처리:
       - bass_track.follow=True → 저주파 베이스에 맞춰 밝기 실시간 추종
       - beat_reactive.on_kick → 플레이어가 킥마다 자동 반응 (타임라인 중복 불필요)
       - 타임라인 킥 이벤트는 "강조가 필요한 구간의 선별된 킥"만 추가

    3. 구간별 BPM 적응:
       - slow (BPM < 90):  beat_flash 완전 비활성, color_change + breath 위주
       - mid  (90~120):    verse 킥 생략, prechorus 후반 킥만 일부
       - fast (120~150):   chorus 킥 2박마다 1개
       - very_fast (≥150): chorus/climax 킥 매박 허용

    4. verse double_blink: BPM≥110 이고 고에너지 곡에서만, 구간당 최대 2개
    """
    segs           = a["segments"]
    bpm            = a["bpm"]
    beat_len       = 60.0 / bpm
    kick_times_raw = sorted(set(round(t, 2) for t in a.get("kick_times", [])))
    downbeats      = a.get("downbeat_times", [])
    vocal_mask     = a.get("vocal_mask")
    frame_dur      = HOP / SR
    danceability   = a.get("danceability", 0.5)
    energy_ratio   = a.get("energy_ratio", 0.5)
    genre          = a.get("genre", "pop")
    events         = []
    seen           = {}
    prev_stype     = None
    strobe_count   = 0   # 곡 전체 strobe 횟수 제한용

    max_e = max(s["energy"] for s in segs) + 1e-6

    # ── BPM 계층: 각종 임계값 결정 ─────────────────────────────
    # slow: 발라드/R&B계열, fast: K-pop/댄스, very_fast: EDM/록
    is_slow      = bpm < 90
    is_mid       = 90 <= bpm < 120
    is_fast      = 120 <= bpm < 150
    is_very_fast = bpm >= 150

    # fast_strobe 허용 조건:
    #   BPM≥128 AND (에너지 높음 OR 장르가 댄스계열) AND 전체 2회 이하
    strobe_allowed = (bpm >= 128 and
                      (energy_ratio > 0.65 or genre in ("k-pop", "pop") and danceability > 0.65))

    # 킥 beat_flash 최소 간격: 느릴수록 더 넓게 → 덜 깜빡임
    if is_slow:
        kick_min_gap = 9999.0      # 완전 비활성
    elif is_mid:
        kick_min_gap = beat_len * 2.0  # 2박마다 1개
    elif is_fast:
        kick_min_gap = beat_len * 1.0  # 1박마다 1개
    else:
        kick_min_gap = beat_len * 0.5  # 0.5박마다 1개 (very fast)

    # 킥 에너지 상위 N% 선별 — 강한 킥만 이벤트로 올림
    # 느릴수록 더 엄격하게 (상위 20% → 상위 50%)
    kick_energy_pct = 70 if is_slow else 55 if is_mid else 40 if is_fast else 30

    # 팔레트 순환색 (neutral/white/sad 제외)
    kick_colors = [k for k in palette if k not in ("neutral", "white", "sad", "neutral")]
    if not kick_colors:
        kick_colors = ["primary", "secondary", "peak"]

    # 구간 내부 이펙트 순환 (strobe 없음)
    CHORUS_MID = ["rainbow", "color_wipe", "bounce", "sparkle", "wave_fb"]
    CLIMAX_MID = ["color_wipe", "flash_all", "bounce", "rainbow", "color_sweep"]
    PRE_MID    = ["chase", "ripple", "color_sweep", "chase"]
    BRIDGE_MID = ["twinkle", "shimmer"]

    # ── 킥 에너지 기반 선별 함수 ────────────────────────────────
    subbass_norm = np.array(a.get("subbass_norm", []))
    times_arr    = np.array(a.get("times", []))

    def _strong_kicks(seg_start: float, seg_end: float,
                      min_gap: float, top_pct: int) -> list:
        """구간 내 강한 킥만 선별 (에너지 상위 top_pct%, 최소 간격 min_gap)"""
        cands = [kt for kt in kick_times_raw if seg_start <= kt < seg_end]
        if not cands or len(subbass_norm) == 0:
            return cands  # 에너지 정보 없으면 그대로

        # 각 킥 시각의 subbass 에너지 조회
        def _energy(kt):
            idx = np.searchsorted(times_arr, kt)
            idx = min(idx, len(subbass_norm) - 1)
            return float(subbass_norm[idx])

        energies   = [_energy(kt) for kt in cands]
        threshold  = float(np.percentile(energies, 100 - top_pct)) if energies else 0.0
        strong     = [kt for kt, e in zip(cands, energies) if e >= threshold]

        # 최소 간격 적용
        result, last = [], -999.0
        for kt in strong:
            if kt - last >= min_gap:
                result.append(kt)
                last = kt
        return result

    # ────────────────────────────────────────────────────────────
    for seg in segs:
        t     = seg["start"]
        tend  = seg["end"]
        stype = seg["type"]
        seg_e = seg["energy"]
        count = seen.get(stype, 0)
        seen[stype] = count + 1

        eff_list  = SECTION_EFFECTS.get(stype, ["solid"])
        col_list  = SECTION_COLORS.get(stype, ["primary"])
        effect    = eff_list[count % len(eff_list)]
        color     = col_list[count % len(col_list)]
        if color not in palette and not isinstance(color, dict):
            color = "primary"
        intensity = round(0.30 + (seg_e / max_e) * 0.70, 2)

        ev = {
            "t": round(t, 2), "group": 0,
            "color": color, "effect": effect,
            "intensity": intensity,
            "note": f"{stype} #{count+1}",
        }

        # ── 구간별 처리 ──────────────────────────────────────────

        if stype == "intro":
            ev["intensity"] = min(intensity, 0.32)
            ev["period"]    = 4.0

        elif stype == "verse":
            ev["bpm_sync"]  = True
            ev["color"]     = "warm" if count % 2 == 0 else "cool"
            ev["intensity"] = min(intensity, 0.58)

            # 보컬 spotlight (보컬 있는 구간에만)
            mid_f = min(int(((t + tend) / 2) / frame_dur), len(vocal_mask) - 1) \
                    if vocal_mask else 0
            has_vocal = bool(vocal_mask[mid_f]) if vocal_mask else True
            if has_vocal:
                events.append({
                    "t": round(t + beat_len, 2), "group": 1,
                    "spotlight": True, "bg_brightness": 0.10,
                    "color": "white", "note": "보컬 spotlight",
                })

            # double_blink: BPM≥110 이고 에너지 높은 경우만, 구간당 최대 2개
            if bpm >= 110 and energy_ratio > 0.55:
                seg_dbs  = [db for db in downbeats if t <= db < tend][:2]
                alt_col  = col_list[(count + 1) % len(col_list)]
                if alt_col not in palette: alt_col = "secondary"
                for db in seg_dbs:
                    events.append({
                        "t": round(db, 2), "group": 2,
                        "color": alt_col, "effect": "double_blink",
                        "intensity": 0.50, "note": "다운비트",
                    })

        elif stype == "prechorus":
            ev["intensity"] = min(intensity * 1.12, 1.0)
            # 구간 끝 암전
            blackout_t = round(tend - beat_len, 2)
            if blackout_t > t:
                events.append({
                    "t": blackout_t, "group": 0,
                    "color": None, "effect": "expectation_break",
                    "intensity": 0.0, "note": "암전 (프리코러스 끝)",
                })
            # 구간 중반 빌드업 이펙트
            mid_t   = round((t + tend) / 2, 2)
            mid_eff = PRE_MID[count % len(PRE_MID)]
            events.append({
                "t": mid_t, "group": 1,
                "color": "peak", "effect": mid_eff,
                "intensity": 0.80, "note": f"pre mid ({mid_eff})",
            })

        elif stype in ("chorus", "climax"):
            chorus_col_pool = [k for k in ("peak","love","triad_a","complement",
                                           "analog_a","happy","secondary","gold")
                               if k in palette]
            if not chorus_col_pool: chorus_col_pool = ["peak"]
            ev["color"]     = chorus_col_pool[count % len(chorus_col_pool)]
            ev["effect"]    = "release_burst"
            ev["intensity"] = 1.00
            ev["spatial"]   = "explosion"

            seg_dur_s = tend - t
            pct25 = round(t + seg_dur_s * 0.25, 2)
            pct50 = round(t + seg_dur_s * 0.50, 2)
            pct75 = round(t + seg_dur_s * 0.75, 2)

            # 25% — 색/이펙트 변화
            mid_pool = CLIMAX_MID if stype == "climax" else CHORUS_MID
            mid_eff  = mid_pool[count % len(mid_pool)]
            mid_col  = kick_colors[count % len(kick_colors)]
            events.append({
                "t": pct25, "group": 0,
                "color": mid_col, "effect": mid_eff,
                "bpm_sync": True, "intensity": 0.92,
                "note": f"mid ({mid_eff})",
            })

            # 50% — 좌우 wave (느린 곡에선 생략)
            if not is_slow:
                wl = "complement" if "complement" in palette else "secondary"
                wr = "triad_a"    if "triad_a"    in palette else "cool"
                events.append({"t": pct50, "group": 1,
                               "color": wl, "effect": "wave_lr",
                               "intensity": 1.0, "note": "wave L→R"})
                events.append({"t": pct50, "group": 2,
                               "color": wr, "effect": "wave_rl",
                               "intensity": 0.88, "note": "wave R→L"})

            # 75% — sparkle / ripple 교대 (is_slow엔 color_sweep으로 대체)
            if is_slow:
                tail_eff = "color_sweep"
                tail_col = "secondary"
            else:
                tail_eff = "sparkle" if count % 2 == 0 else "ripple"
                tail_col = "white" if tail_eff == "sparkle" else (
                           "moonlight" if "moonlight" in palette else "cool")
            events.append({
                "t": pct75, "group": 0,
                "color": tail_col, "effect": tail_eff,
                "intensity": 0.82, "note": f"tail ({tail_eff})",
            })

            # ── fast_strobe: 매우 엄격한 조건 ───────────────────
            # · strobe_allowed (BPM≥128 + 고에너지) 이어야 함
            # · 직전 구간이 prechorus 이어야 함 (기대감 해소 맥락)
            # · 곡 전체 최대 2회 (strobe_count)
            # · climax 이고 구간 에너지가 상위권일 때만
            seg_energy_pct = seg_e / max_e
            do_strobe = (
                strobe_allowed
                and prev_stype == "prechorus"
                and strobe_count < 2
                and stype == "climax"          # chorus에선 사용 안 함
                and seg_energy_pct > 0.80      # 에너지 상위 20% 구간만
                and seg_dur_s > beat_len * 8   # 충분히 긴 구간만
            )
            if do_strobe:
                # hz는 BPM에 비례 (빠를수록 조금 더 높게, 최대 10hz)
                strobe_hz  = min(10.0, round(bpm / 16, 1))
                strobe_dur = min(seg_dur_s * 0.10, 2.0)   # 최대 2초 (기존 4초 → 2초)
                strobe_t   = round(t + beat_len, 2)        # 1박 후 시작
                events.append({
                    "t": strobe_t, "group": 0,
                    "color": "white", "effect": "fast_strobe",
                    "hz": strobe_hz,
                    "duration": round(strobe_dur, 2),
                    "intensity": 0.85,
                    "note": f"strobe ({strobe_hz}hz {strobe_dur:.1f}s) — 최고조",
                })
                strobe_count += 1

            # climax 끝 직전 단일 flash (strobe 아님)
            if stype == "climax":
                flash_t = round(tend - beat_len * 2, 2)
                if flash_t > pct75:
                    events.append({
                        "t": flash_t, "group": 0,
                        "color": "gold" if "gold" in palette else "peak",
                        "effect": "flash_all", "intensity": 1.0,
                        "note": "climax 최종 flash",
                    })

        elif stype == "bridge":
            ev["color"]     = "dreamy" if "dreamy" in palette else "cool"
            ev["intensity"] = min(intensity, 0.50)
            mid_t   = round((t + tend) / 2, 2)
            mid_eff = BRIDGE_MID[count % len(BRIDGE_MID)]
            mid_col = "moonlight" if "moonlight" in palette else "cool"
            events.append({
                "t": mid_t, "group": 1,
                "color": mid_col, "effect": mid_eff,
                "intensity": 0.45, "note": f"bridge mid ({mid_eff})",
            })

        elif stype == "outro":
            ev["period"]    = 6.0
            ev["intensity"] = min(intensity, 0.38)

        events.append(ev)

        # ── 킥드럼 선별 이벤트 ───────────────────────────────────
        # bass_track + beat_reactive 가 전역적으로 리듬을 맞추므로
        # 타임라인 킥 이벤트는 "구간 강조"가 필요한 곳의 선별된 킥만.
        #
        # · intro/bridge/outro: 킥 이벤트 없음 (분위기 보호)
        # · verse: slow/mid 에선 없음, fast 이상에서만 선별 킥
        # · prechorus: 후반부(75%~) 킥만 (빌드업 강조)
        # · chorus/climax: BPM 적응 간격으로 선별

        if stype == "verse" and (is_fast or is_very_fast):
            strong = _strong_kicks(t, tend, kick_min_gap, kick_energy_pct)
            for kt in strong:
                events.append({
                    "t": kt, "group": 3,
                    "color": "white", "effect": "beat_flash",
                    "duration": 0.04, "intensity": 0.65,
                    "note": "킥 (verse)",
                })

        elif stype == "prechorus":
            # 후반 3/4 구간 킥만 — 빌드업 강조
            seg_len   = tend - t
            pre_start = t + seg_len * 0.60
            strong = _strong_kicks(pre_start, tend,
                                   max(kick_min_gap, beat_len), kick_energy_pct)
            for ki_idx, kt in enumerate(strong):
                prog  = (kt - pre_start) / max(tend - pre_start, 1e-6)
                inten = round(0.55 + prog * 0.35, 2)
                events.append({
                    "t": kt, "group": 3,
                    "color": "peak", "effect": "beat_flash",
                    "duration": 0.04, "intensity": inten,
                    "note": f"킥 (pre build {inten:.2f})",
                })

        elif stype in ("chorus", "climax"):
            # chorus: BPM 적응 간격 / climax: 조금 더 허용
            gap    = kick_min_gap * (0.8 if stype == "climax" else 1.0)
            gap    = max(gap, beat_len * 0.5)  # 최소 반박 간격 보장
            strong = _strong_kicks(t, tend, gap, kick_energy_pct)
            for ki_idx, kt in enumerate(strong):
                kcol  = kick_colors[(count * 5 + ki_idx) % len(kick_colors)]
                inten = 0.88 if stype == "climax" else 0.78
                events.append({
                    "t": kt, "group": 3,
                    "color": kcol, "effect": "beat_flash",
                    "duration": 0.05, "intensity": inten,
                    "note": f"킥 ({stype})",
                })

        prev_stype = stype

    # ── 에너지 급변 flash: 상위 3%만 (기존 8% → 3%) ─────────────
    # 구간 시작/끝과 0.5초 이내는 제외 (이미 이벤트 있음)
    rms_s    = np.array(a["rms_smooth"])
    t_arr    = np.array(a["times"])
    diff_rms = np.diff(rms_s)
    # 상위 3% 급변: 곡 길이에 따라 적게 (max 4개)
    surge_thr = float(np.percentile(np.abs(diff_rms), 97))
    existing  = {round(ev["t"], 0) for ev in events}
    seg_bounds = set()
    for seg in segs:
        for b in (seg["start"], seg["end"]):
            seg_bounds.update({round(b + d, 0) for d in (-1, 0, 1)})

    surge_count = 0
    for sf_ in np.where(diff_rms > surge_thr)[0]:
        if surge_count >= 4:
            break
        st = round(float(t_arr[sf_]), 2)
        if round(st, 0) not in existing and round(st, 0) not in seg_bounds and st > 2.0:
            events.append({
                "t": st, "group": 0,
                "color": "peak", "effect": "flash_all",
                "intensity": 0.65, "note": "에너지 급상승",
            })
            existing.add(round(st, 0))
            surge_count += 1

    events.sort(key=lambda x: (x["t"], x.get("group", 0)))
    return events


# ══════════════════════════════════════════════════════════════════
# 5. MLML assembly
# ══════════════════════════════════════════════════════════════════

def _build_motifs() -> dict:
    return {
        "heart_pulse":       {"type": "blink", "on_beat": True, "duty": 0.30,
                              "attack": "fast", "decay": "slow", "color": "primary"},
        "tension_build":     {"type": "brightness_ramp", "curve": "exponential",
                              "color_shift": "toward_peak", "blink_accelerate": True},
        "release_burst":     {"type": "flash_all", "color": "peak",
                              "duration": 0.10, "then": "fade_to_primary"},
        "breath":            {"type": "brightness_sine", "period": 4.0,
                              "min_val": 0.15, "max_val": 0.85, "color": "neutral"},
        "slow_pulse":        {"type": "brightness_sine", "period": 2.0,
                              "min_val": 0.20, "max_val": 0.75, "color": "primary"},
        "expectation_break": {"type": "blackout_then_burst", "blackout_duration": 0.50,
                              "blackout_beats": 1, "burst_color": "peak"},
        "rainbow":           {"type": "hue_sweep", "speed": 1.0, "sat": 1.0, "val": 1.0},
        "sparkle":           {"type": "random_flash", "density": 0.30,
                              "color": "white", "duration": 0.05},
        "chase":             {"type": "sequential_on", "direction": "forward",
                              "color": "primary", "trail": 3},
        "twinkle":           {"type": "random_dim", "density": 0.40,
                              "period": 2.0, "color": "cool"},
        "shimmer":           {"type": "shimmer", "density": 0.40,
                              "color_spread": 60, "color": "dreamy"},
        "wave_lr":           {"type": "spatial_wave", "axis": "horizontal",
                              "delay_per_col": 0.05, "color": "primary"},
        "wave_rl":           {"type": "spatial_wave", "axis": "horizontal",
                              "delay_per_col": -0.05, "color": "secondary"},
        "color_wipe":        {"type": "fill_sweep", "direction": "left_to_right",
                              "color": "secondary", "duration_beats": 2},
        "bounce":            {"type": "ping_pong", "axis": "vertical",
                              "color": "peak", "speed_mult": 1.5},
        "beat_flash":        {"type": "flash_all", "duration": 0.04,
                              "color": "white", "decay": "instant"},
        "ripple":            {"type": "ripple", "origin": "center",
                              "speed": 1.2, "color": "primary"},
        "color_sweep":       {"type": "hue_rotate", "speed": 0.5,
                              "sat": 0.9, "val": 1.0},
        "fast_strobe":       {"type": "strobe", "duty": 0.5, "color": "white"},
        "dim_glow":          {"type": "brightness_sine", "period": 6.0,
                              "min_val": 0.10, "max_val": 0.55, "color": "neutral"},
        "double_blink":      {"type": "blink_twice", "duty": 0.25,
                              "attack": "instant", "decay": "fast"},
    }


def _build_beat_reactive(a: dict) -> dict:
    """
    BPM + 에너지 + 장르 기반 beat_reactive 파라미터 결정.

    beat_reactive는 플레이어가 실시간으로 킥/스네어/하이햇에 반응하는
    전역 설정. strength를 잘 조절하는 것이 핵심:
    - 느린 곡(발라드): 약하게 → 부드러운 맥박처럼
    - 중간(팝/R&B): 중간 강도
    - 빠른(K-pop/댄스): 강하게 반응해야 리듬감 살아남

    on_hi (하이햇): BPM < 110 에선 비활성 (잦은 깜빡임 방지)
    """
    bpm   = a.get("bpm", 120)
    energy = a.get("energy_ratio", 0.5)
    kfa    = a.get("kfa", 0.5)

    # 킥 반응 강도: BPM·에너지·KFA 복합
    kick_str = round(
        0.38
        + min(bpm / 200, 0.35) * 0.28
        + energy * 0.18
        + (kfa - 0.5) * 0.10,
        2
    )
    kick_str = round(min(max(kick_str, 0.28), 0.90), 2)

    # 킥 flash 지속: 느릴수록 길게(여운), 빠를수록 짧게(선명)
    kick_dur = round(max(0.03, min(0.07, 0.10 - bpm / 2500)), 3)

    snare_str = round(min(0.42, kick_str * 0.52), 2)
    hi_str    = 0.0 if bpm < 110 else round(min(0.20, (bpm - 110) / 500), 2)

    result = {
        "on_kick":  {"color": "white",     "duration": kick_dur, "strength": kick_str},
        "on_snare": {"color": "secondary", "duration": 0.05,     "strength": snare_str},
    }
    if hi_str > 0.0:
        result["on_hi"] = {"color": "teal", "duration": 0.02, "strength": hi_str}
    return result


def _build_spatial() -> dict:
    return {
        "layout":            "arena",
        "dimensions":        {"rows": 4, "cols": 5},
        "groups": {
            "left_half":     {"cols": [0, 1]},
            "right_half":    {"cols": [3, 4]},
            "front_row":     {"rows": [0]},
            "back_row":      {"rows": [3]},
            "center":        {"rows": [1, 2], "cols": [2]},
            "diagonal_a":    {"cells": [[0,0],[1,1],[2,2],[3,3]]},
            "diagonal_b":    {"cells": [[0,4],[1,3],[2,2],[3,1]]},
        },
        "wave_origin":       {"row": 0, "col": 0},
        "explosion_center":  {"row": 1.5, "col": 2},
        "delay_per_col":     0.05,
        "delay_per_row":     0.05,
        "delay_per_unit":    0.03,
    }


def _build_tension_curve(segments: list) -> list:
    energies = [s["energy"] for s in segments]
    max_e    = max(energies) + 1e-6
    curve    = []
    for seg in segments:
        tension = round(seg["energy"] / max_e, 2)
        if seg["type"] == "intro":   tension = min(tension, 0.30)
        elif seg["type"] == "outro": tension = min(tension, 0.35)
        curve.append([seg["start"], tension])
    return curve


def build_mlml(a: dict, title: str, artist: str) -> dict:
    bpm = a["bpm"]
    dur = a["duration"]

    palette       = _build_rich_palette(a)
    timeline      = _build_rich_timeline(a, palette)
    tension_curve = _build_tension_curve(a["segments"])

    if bpm > 160:   bpc, smooth, hz_hi = 2, 0.04, 20
    elif bpm > 120: bpc, smooth, hz_hi = 2, 0.05, 20
    elif bpm > 90:  bpc, smooth, hz_hi = 4, 0.08, 12
    else:           bpc, smooth, hz_hi = 8, 0.15,  6

    intensity = round(0.70 + a["energy_ratio"] * 0.30, 2)
    contrast  = round(0.50 + a["danceability"] * 0.40, 2)

    fade_start = max(dur - 10.0, dur * 0.92)
    bookend = {
        "fade_out_start":    round(fade_start, 1),
        "fade_out_duration": round(dur - fade_start, 2),
        "final_color":       "love",
    }

    pk = list(palette.keys())
    cycle_colors = [c for c in ["primary","secondary","complement","triad_a"] if c in pk]
    if not cycle_colors:
        cycle_colors = ["primary", "secondary"]

    color_cycle = {
        "unit":            "downbeat" if a.get("downbeat_times") else "bar",
        "bars_per_change": bpc,
        "colors":          cycle_colors,
        "transition":      0.30,
    }

    section_defaults = {
        "intro":     {"effect": "breath",       "color": "neutral",   "intensity": 0.30},
        "verse":     {"effect": "heart_pulse",  "color": "warm",      "intensity": 0.60,
                      "spotlight": True},
        "prechorus": {"effect": "tension_build","color": "secondary", "intensity": 0.82,
                      "expectation_break": True},
        "chorus":    {"effect": "release_burst","color": "peak",      "intensity": 1.00,
                      "spatial": "explosion"},
        "climax":    {"effect": "release_burst","color": "peak",      "intensity": 1.00,
                      "spatial": "explosion"},
        "bridge":    {"effect": "twinkle",      "color": "dreamy",    "intensity": 0.50},
        "outro":     {"effect": "slow_pulse",   "color": "love",      "intensity": 0.32},
    }

    # bass_track: demucs 있으면 더 빠른 반응
    bass_source = "demucs_bass" if a.get("has_stems") else "stft_band"
    bass_smooth = 0.05 if a.get("has_stems") else 0.10

    analysis_meta = {
        "beat_source":     a.get("beat_source", "unknown"),
        "bpm_confidence":  a.get("bpm_confidence", 0.0),
        "kfa":             a.get("kfa", 0.0),
        "has_stems":       a.get("has_stems", False),
        "n_beats":         len(a.get("beat_times", [])),
        "n_downbeats":     len(a.get("downbeat_times", [])),
        "n_kicks":         len(a.get("kick_times", [])),
        "chroma_entropy":  a.get("chroma_entropy", 0.0),
        "dynamic_range":   a.get("dynamic_range", 0.0),
        "danceability":    a.get("danceability", 0.0),
    }
    if a.get("fallback_reason"):
        analysis_meta["fallback_reason"] = a["fallback_reason"]

    return {
        "metadata": {
            "title": title, "artist": artist,
            "bpm": bpm, "key": a["key"],
            "time_sig": "4/4", "duration": dur,
            "genre": a["genre"], "mood": a["mood"],
            "archetype": a["archetype"],
            "analysis_meta": analysis_meta,
        },
        "palette": palette,
        "global_mood": {
            "temperature": a["temperature"],
            "intensity":   intensity,
            "contrast":    contrast,
        },
        "tempo_mode": {
            "auto": True,
            "override": {"bars_per_change": bpc, "smooth": smooth, "hz_hi": hz_hi},
        },
        "motifs": _build_motifs(),
        "beat_reactive": _build_beat_reactive(a),
        "bass_track": {
            "follow":   True,
            "smooth":   bass_smooth,
            "freq_max": 200,
            "min_val":  0.30,
            "max_val":  1.00,
            "source":   bass_source,
        },
        "color_cycle":      color_cycle,
        "spatial":          _build_spatial(),
        "section_defaults": section_defaults,
        "global_arc": {
            "tension_curve": tension_curve,
            "tension_rules": [
                {"above": 0.80, "apply": "tension_build"},
                {"below": 0.25, "apply": "breath"},
            ],
        },
        "timeline":  timeline,
        "bookend":   bookend,
        "lyric_map": {
            "enabled": True, "source": "srt",
            "emotion_color": EMOTION_COLOR,
        },
    }


# ══════════════════════════════════════════════════════════════════
# 6. Lyric merge
# ══════════════════════════════════════════════════════════════════

def merge_lyric(mlml_dict: dict, lyric_analysis: dict,
                include_text: bool = False) -> dict:
    """Merge lyric-derived cues into an MLML script.

    include_text=False (default) keeps only the emotion label and timing.
    Raw lyric lines are usually copyrighted, so they are omitted unless
    explicitly requested; scripts produced with the default are safe to
    redistribute.
    """
    mlml = copy.deepcopy(mlml_dict)
    la   = lyric_analysis

    manual_entries = []
    for it in la["manual_map"]:
        if not it["color"]:
            continue
        entry = {"time": it["time"], "color": it["color"],
                 "brightness": it["brightness"], "duration": it["duration"]}
        if it.get("emotion"):
            entry["emotion"] = it["emotion"]
        if include_text:
            entry["text"] = it["text"]
        manual_entries.append(entry)
    mlml["lyric_map"].update({
        "enabled":       True,
        "source":        "srt",
        "emotion_color": EMOTION_COLOR,
    })
    if manual_entries:
        mlml["lyric_map"]["manual"] = manual_entries

    dominant = la["dominant_emotion"]
    if dominant:
        mlml["global_mood"]["temperature"] = TEMP_MAP.get(dominant, "warm")
        if dominant in EMOTION_COLOR:
            mlml["palette"]["love"] = EMOTION_COLOR[dominant]

    existing = {round(ev["t"], 0) for ev in mlml["timeline"]}
    for item in la["manual_map"]:
        if item["emotion"] in ("excited", "happy", "powerful") and item["brightness"]:
            t = item["time"]
            if round(t, 0) not in existing:
                mlml["timeline"].append({
                    "t": t, "group": 0,
                    "color": dominant or "happy",
                    "effect": "flash_all",
                    "intensity": 0.88,
                    "note": f"lyric emotion: {item['emotion']}",
                })
                existing.add(round(t, 0))

    mlml["timeline"].sort(key=lambda x: (x["t"], x.get("group", 0)))
    return mlml


# ══════════════════════════════════════════════════════════════════
# 7. Optional LLM refinement
# ══════════════════════════════════════════════════════════════════

# The refinement prompt is written in Korean because the reference corpus is
# Korean-language pop. Translating it will change LLM output; the deterministic
# path (--no-llm) is unaffected.
SYSTEM_PROMPT = """당신은 MLML(Music-to-Light Markup Language) v1.3 전문가입니다.
demucs 소스 분리, madmom 다운비트 추적, librosa 보조 특징이 통합된 고품질 분석 결과가 주어집니다.

핵심 규칙:
1. timeline.t: float(초), group: 0=전체 1=좌/A 2=우/B 3=킥 레이어
2. effect 허용값: breath|slow_pulse|heart_pulse|tension_build|release_burst|
   fast_strobe|double_blink|dim_glow|fade_inout|flicker|rainbow|wave_lr|wave_fb|
   wave_rl|color_sweep|call_and_response|pitch_track|solid|flash_all|sparkle|
   chase|color_wipe|bounce|twinkle|beat_flash|ripple|shimmer
3. color: palette 키 이름 또는 {hue:0~360, sat:0~1, val:0~1}
4. intensity: 0.0~1.0
5. fast_strobe 사용 시 hz(≤12)와 duration(≤4.0) 명시 필수
6. bass_track.source가 demucs_bass이면 smooth를 0.05 유지
7. 반드시 유효한 YAML만 출력 (설명 텍스트, 마크다운 없음)

연출 원칙:
- palette의 다양한 색상 (complement, triad_a, analog_a 등) 적극 활용
- 같은 구간 반복 시 이펙트/색상 변형으로 단조로움 방지
- intro ≤ 0.35, verse ≤ 0.65, chorus = 1.0 intensity 원칙
- strobe는 chorus/climax 에서만, 구간당 1회, hz≤12, duration≤4s 제한
- 브릿지: dreamy/twinkle/shimmer 등 몽환 연출
- 다운비트 color_cycle 활용
- kfa < 0.8이면 beat_reactive.on_kick.strength를 0.85로 낮춤
- 사용자 요구사항(user_prompt)이 있으면 최우선 반영
"""


def _call_llm_common(mlml_dict, analysis, title, artist,
                     lyric_analysis, user_prompt, call_fn, label):
    summary = {k: analysis[k] for k in [
        "bpm", "bpm_confidence", "key", "duration", "genre", "mood",
        "archetype", "temperature", "energy_ratio", "danceability",
        "kfa", "has_stems", "sc_mean", "zcr_mean", "dynamic_range", "chroma_entropy",
    ]}
    summary["n_kicks"]     = len(analysis.get("kick_times", []))
    summary["n_beats"]     = len(analysis.get("beat_times", []))
    summary["n_downbeats"] = len(analysis.get("downbeat_times", []))
    summary["segments"]    = analysis["segments"]

    lyric_section = ""
    if lyric_analysis:
        sample = [
            {"time": it["time"], "text": it["text"], "emotion": it["emotion"]}
            for it in lyric_analysis["manual_map"] if it["emotion"]
        ][:12]
        lyric_section = f"""
## 가사 분석
```json
{json.dumps({"dominant": lyric_analysis["dominant_emotion"],
              "stats": {k: v for k, v in lyric_analysis["emotion_stats"].items() if v > 0},
              "sample": sample}, ensure_ascii=False, indent=2)}
```
지배 감정({lyric_analysis["dominant_emotion"]})을 palette/global_mood에 반영하세요.
"""
    user_section = f"\n## 사용자 요구사항 (최우선 반영)\n{user_prompt}\n" if user_prompt else ""

    base_yaml = yaml.dump(mlml_dict, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)
    prompt = f"""## 음악 분석
```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```
{lyric_section}{user_section}
## 기본 MLML
```yaml
{base_yaml}
```
위 MLML을 개선하여 완성된 MLML v1.3을 YAML 형식으로만 출력하세요.
- palette의 다양한 색상을 구간마다 다르게 활용하세요
- 구간별 반복 시 이펙트/색상을 반드시 변형하세요
- strobe는 chorus/climax에서만, 절제되게 (hz≤12, duration≤4s)"""

    print(f"  {label}: refining MLML...")
    try:
        raw = call_fn(prompt)
        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.split("\n")
                            if not l.strip().startswith("```"))
        refined = yaml.safe_load(raw)
        if isinstance(refined, dict) and "metadata" in refined:
            print(f"  {label}: refinement applied")
            return refined
        print(f"  ! {label}: could not parse response - keeping compiler output")
        return mlml_dict
    except Exception as e:
        print(f"  ! {label} error: {e}")
        return mlml_dict


def refine_with_claude(mlml_dict, analysis, title, artist,
                       lyric_analysis=None, user_prompt="") -> dict:
    try:
        import anthropic
    except ImportError:
        print("  ! anthropic not installed: pip install anthropic")
        return mlml_dict

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ! ANTHROPIC_API_KEY is not set")
        return mlml_dict

    client = anthropic.Anthropic(api_key=api_key)
    model  = os.environ.get("MLML_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    return _call_llm_common(
        mlml_dict, analysis, title, artist, lyric_analysis, user_prompt,
        call_fn=lambda p: client.messages.create(
            model=model, max_tokens=6000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": p}],
        ).content[0].text.strip(),
        label=f"Claude ({model})",
    )


def refine_with_gpt(mlml_dict, analysis, title, artist,
                    lyric_analysis=None, user_prompt="") -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        print("  ! openai not installed: pip install openai")
        return mlml_dict

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("  ! OPENAI_API_KEY is not set")
        return mlml_dict

    client = OpenAI(api_key=api_key)
    model  = os.environ.get("MLML_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return _call_llm_common(
        mlml_dict, analysis, title, artist, lyric_analysis, user_prompt,
        call_fn=lambda p: client.chat.completions.create(
            model=model, max_tokens=6000,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user",   "content": p}],
        ).choices[0].message.content.strip(),
        label=f"OpenAI ({model})",
    )


# ══════════════════════════════════════════════════════════════════
# 8. Serialisation (numpy -> native Python types)
# ══════════════════════════════════════════════════════════════════

class MLMLDumper(yaml.Dumper):
    pass


def _np_float_repr(d, v):
    fv = float(v)
    return d.represent_scalar("tag:yaml.org,2002:float",
                               f"{fv:.1f}" if fv == int(fv) else f"{fv:g}")


def _np_int_repr(d, v):
    return d.represent_scalar("tag:yaml.org,2002:int", str(int(v)))


MLMLDumper.add_representer(type(None),
    lambda d, _: d.represent_scalar("tag:yaml.org,2002:null", "null"))
MLMLDumper.add_representer(float,
    lambda d, v: d.represent_scalar("tag:yaml.org,2002:float",
        f"{v:.1f}" if v == int(v) else f"{v:g}"))
MLMLDumper.add_representer(int,
    lambda d, v: d.represent_scalar("tag:yaml.org,2002:int", str(v)))

for _t in [np.float16, np.float32, np.float64]:
    try:
        MLMLDumper.add_representer(_t, _np_float_repr)
    except Exception:
        pass
for _t in [np.int8, np.int16, np.int32, np.int64,
           np.uint8, np.uint16, np.uint32, np.uint64]:
    try:
        MLMLDumper.add_representer(_t, _np_int_repr)
    except Exception:
        pass
try:
    MLMLDumper.add_representer(np.floating, _np_float_repr)
    MLMLDumper.add_representer(np.integer,  _np_int_repr)
except Exception:
    pass
MLMLDumper.add_representer(np.ndarray,
    lambda d, v: d.represent_data(v.tolist()))


def _sanitize(obj):
    """재귀적으로 numpy 타입을 Python 기본 타입으로 변환"""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def save_mlml(mlml_dict: dict, path: str):
    clean = _sanitize(mlml_dict)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(clean, f, Dumper=MLMLDumper,
                  allow_unicode=True, default_flow_style=False,
                  sort_keys=False, indent=2)
    print(f"  written: {path}")


# ══════════════════════════════════════════════════════════════════
# 9. Entry point
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="MP3 (+ SRT) -> MLML v1.3 | demucs + madmom + librosa",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python mp3_to_mlml.py song.mp3
  python mp3_to_mlml.py song.mp3 --srt song.srt
  python mp3_to_mlml.py song.mp3 --no-demucs      # skip demucs (fast mode)
  python mp3_to_mlml.py song.mp3 --device cuda    # run demucs on GPU
  python mp3_to_mlml.py song.mp3 --llm claude     # Anthropic refinement
  python mp3_to_mlml.py song.mp3 --llm gpt        # OpenAI refinement
  python mp3_to_mlml.py song.mp3 --no-llm         # deterministic, reproducible
  python mp3_to_mlml.py song.mp3 --prompt "K-pop girl group, bright and airy"
  python mp3_to_mlml.py song.mp3 --save-analysis  # also dump analysis JSON

Pass --no-llm to reproduce a published script byte-for-byte; LLM
refinement is non-deterministic.
        """
    )
    parser.add_argument("mp3",                  help="input MP3 file")
    parser.add_argument("--srt",    default="", help="lyric SRT file")
    parser.add_argument("--title",  default="", help="song title (default: filename)")
    parser.add_argument("--artist", default="Unknown", help="artist name")
    parser.add_argument("--out",    default="", help="output .mlml path")
    parser.add_argument("--device", default="cpu",
                        help="demucs device (cpu|cuda|mps)")
    parser.add_argument("--no-demucs", action="store_true",
                        help="skip demucs source separation")
    parser.add_argument("--llm", default="claude", choices=["claude", "gpt", "none"],
                        help="LLM used for the optional refinement pass")
    parser.add_argument("--llm-model", default="",
                        help="override the LLM model name")
    parser.add_argument("--no-llm", action="store_true",
                        help="skip LLM refinement (deterministic output)")
    parser.add_argument("--prompt", default="", help="extra instruction for the LLM")
    parser.add_argument("--include-lyric-text", action="store_true",
                        help="embed raw lyric lines in lyric_map (off by default; "
                             "lyrics are usually copyrighted - do not redistribute)")
    parser.add_argument("--save-analysis", action="store_true",
                        help="also write the raw analysis as JSON")
    parser.add_argument("--quiet", action="store_true", help="reduce log output")
    args = parser.parse_args()

    if not os.path.exists(args.mp3):
        print(f"error: {args.mp3} not found")
        sys.exit(1)

    if args.llm_model:
        if args.llm == "gpt":
            os.environ["MLML_OPENAI_MODEL"] = args.llm_model
        else:
            os.environ["MLML_ANTHROPIC_MODEL"] = args.llm_model

    base  = os.path.splitext(args.mp3)[0]
    title = args.title or os.path.basename(base)
    out   = args.out   or f"{base}.mlml"

    print("=" * 65)
    print(" MP3 -> MLML v1.3   [demucs + madmom + librosa]")
    print("=" * 65)

    # -- Stage 0: lyrics ------------------------------------------------
    lyric_analysis = None
    srt_path = args.srt or (f"{base}.srt" if os.path.exists(f"{base}.srt") else "")
    if srt_path and os.path.exists(srt_path):
        print(f"\n[0/4] parsing SRT: {srt_path}")
        entries        = parse_srt(srt_path)
        lyric_analysis = analyze_lyrics(entries)
        print(f"  {lyric_analysis['n_lines']} lines | "
              f"dominant emotion: {lyric_analysis['dominant_emotion']}")
        stats = {k: round(v, 2) for k, v in lyric_analysis["emotion_stats"].items() if v > 0}
        print(f"  emotion scores: {stats}")
        if args.include_lyric_text:
            print("  ! --include-lyric-text: raw lyrics will be embedded in the output")
    else:
        print("\n[0/4] no SRT - skipped")

    # -- Stage 1: analysis ----------------------------------------------
    print("\n[1/4] audio analysis")
    analysis = analyze(
        args.mp3,
        use_demucs=not args.no_demucs,
        device=args.device,
        verbose=not args.quiet,
    )

    if args.save_analysis:
        def to_py(obj):
            if isinstance(obj, (np.floating, float)): return float(obj)
            if isinstance(obj, (np.integer, int)):    return int(obj)
            if isinstance(obj, np.ndarray):           return obj.tolist()
            return obj
        ap = f"{base}_analysis.json"
        with open(ap, "w") as f:
            json.dump(analysis, f, default=to_py, indent=2)
        print(f"  analysis written: {ap}")

    # -- Stage 2: compile ------------------------------------------------
    print("\n[2/4] compiling MLML")
    mlml = build_mlml(analysis, title, args.artist)
    if lyric_analysis:
        mlml = merge_lyric(mlml, lyric_analysis,
                           include_text=args.include_lyric_text)
        print(f"  lyric_map: {len(mlml['lyric_map'].get('manual', []))} cues")
    print(f"  timeline: {len(mlml['timeline'])} events | "
          f"sections: {len(analysis['segments'])}")
    print(f"  palette: {len(mlml['palette'])} colors | "
          f"stems: {'demucs' if analysis['has_stems'] else 'librosa fallback'}")

    # -- Stage 3: optional LLM refinement --------------------------------
    use_llm = not args.no_llm and args.llm != "none"
    if use_llm:
        print(f"\n[3/4] LLM refinement (--llm {args.llm})")
        print("  note: output is non-deterministic; use --no-llm to reproduce")
        if args.llm == "gpt":
            mlml = refine_with_gpt(
                mlml, analysis, title, args.artist, lyric_analysis, args.prompt)
        else:
            mlml = refine_with_claude(
                mlml, analysis, title, args.artist, lyric_analysis, args.prompt)
    else:
        print("\n[3/4] LLM refinement skipped (deterministic)")

    # -- Stage 4: write ---------------------------------------------------
    print("\n[4/4] writing output")
    save_mlml(mlml, out)

    meta = mlml["metadata"]
    am   = meta.get("analysis_meta", {})
    n_strobe = sum(1 for ev in mlml["timeline"]
                   if ev.get("effect") == "fast_strobe")
    beat_src = am.get("beat_source", "unknown")
    if am.get("fallback_reason"):
        beat_src += f"  ({am['fallback_reason']})"

    print(f"""
---------------------------------------------------------------
 done: {out}
---------------------------------------------------------------
 title:          {meta["title"]}
 artist:         {meta["artist"]}
 BPM:            {meta["bpm"]}  (confidence {am.get("bpm_confidence", "?")})
 key:            {meta["key"]}
 duration:       {meta["duration"]}s
 genre / mood:   {meta["genre"]} / {meta["mood"]}
 beat source:    {beat_src}
 stems:          {"demucs" if am.get("has_stems") else "librosa fallback"}
 beats/downbeats:{am.get("n_beats", "?")} / {am.get("n_downbeats", "?")}
 kicks:          {am.get("n_kicks", "?")}  KFA={am.get("kfa", "?")}
 strobe:         {"enabled (BPM>=128, high energy)" if meta["bpm"] >= 128 else "disabled (BPM<128)"}
 sections:       {len(analysis["segments"])}
 events:         {len(mlml["timeline"])} (strobe: {n_strobe})
 palette:        {len(mlml["palette"])} colors
 lyric text:     {"embedded" if args.include_lyric_text else "excluded"}
 reproducible:   {"yes (--no-llm)" if not use_llm else "no (LLM refinement used)"}
---------------------------------------------------------------
 play: python mlml_player.py {out} {args.mp3}
---------------------------------------------------------------
""")


if __name__ == "__main__":
    main()
