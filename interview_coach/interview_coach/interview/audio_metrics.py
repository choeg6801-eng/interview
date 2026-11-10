"""녹음 파일(WAV)에서 말하기 지표를 계산합니다. numpy 만 사용합니다.

계산하는 것
- 말한 시간, 침묵(머뭇거림) 횟수와 비율
- 목소리 높낮이(억양) 변화, 음량과 음량 안정성, 뒤로 갈수록 작아지는지
- 위 값을 묶은 '목소리 자신감' 추정 점수

주의: 자신감 점수는 연구로 검증된 측정이 아니라 연습용 경험 규칙입니다.
마이크 거리·방 소음에 따라 값이 달라지므로 같은 환경에서 비교할 때 의미가 있습니다.
"""
import io
import wave

import numpy as np

FRAME_SEC = 0.03
HOP_SEC = 0.01
PAUSE_MIN_SEC = 0.7      # 이보다 긴 침묵을 '머뭇거림'으로 봄
LONG_PAUSE_SEC = 2.0     # 이보다 길면 '긴 침묵'


def read_wav(data: bytes):
    """WAV 바이트 → (모노 float32 배열, 샘플레이트)."""
    with wave.open(io.BytesIO(data), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        width = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    else:
        raise ValueError("지원하지 않는 WAV 형식입니다 (8/16/32비트 PCM만 지원).")
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def _downsample(x, sr, target=16000):
    factor = max(1, sr // target)
    if factor == 1:
        return x, sr
    n = len(x) // factor * factor
    return x[:n].reshape(-1, factor).mean(axis=1), sr // factor


def _frames(x, sr):
    flen = int(FRAME_SEC * sr)
    hop = int(HOP_SEC * sr)
    if len(x) < flen:
        x = np.pad(x, (0, flen - len(x)))
    n = 1 + (len(x) - flen) // hop
    idx = np.arange(flen)[None, :] + hop * np.arange(n)[:, None]
    return x[idx], hop


def _pitch(frame, sr, fmin=75, fmax=400):
    frame = frame - frame.mean()
    energy = np.dot(frame, frame)
    if energy <= 1e-8:
        return None
    ac = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
    lo, hi = int(sr / fmax), min(int(sr / fmin), len(ac) - 1)
    if hi <= lo:
        return None
    lag = lo + int(np.argmax(ac[lo:hi]))
    if ac[lag] / ac[0] < 0.45:      # 주기성이 약하면 무성음/소음으로 봄
        return None
    return sr / lag


def _segments(mask, hop_sec):
    """True 구간을 (시작, 끝) 초 목록으로."""
    segs, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            segs.append((start * hop_sec, i * hop_sec))
            start = None
    if start is not None:
        segs.append((start * hop_sec, len(mask) * hop_sec))
    merged = []
    for s, e in segs:   # 0.3초 미만 틈은 같은 말로 이어 붙임
        if merged and s - merged[-1][1] < 0.3:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return [(s, e) for s, e in merged if e - s >= 0.15]


def analyze(data: bytes) -> dict:
    x, sr = read_wav(data)
    x, sr = _downsample(x, sr)
    total_sec = len(x) / sr
    if total_sec < 1.0:
        raise ValueError("녹음이 1초보다 짧습니다. 다시 녹음해 주세요.")

    frames, hop = _frames(x, sr)
    hop_sec = hop / sr
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    floor = np.percentile(db, 10)
    peak = np.percentile(db, 98)
    thresh = max(floor + 10, peak - 30)
    voiced = db > thresh

    segs = _segments(voiced, hop_sec)
    if not segs:
        raise ValueError("목소리가 거의 잡히지 않았습니다. 마이크를 확인해 주세요.")

    speak_start, speak_end = segs[0][0], segs[-1][1]
    span = max(speak_end - speak_start, 1e-6)
    speech_sec = sum(e - s for s, e in segs)
    gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
    pauses = [g for g in gaps if g >= PAUSE_MIN_SEC]

    # 억양: 말한 프레임 일부에서 높낮이 추정
    voiced_idx = np.where(voiced)[0][::3]
    pitches = [p for p in (_pitch(frames[i], sr) for i in voiced_idx) if p]
    if len(pitches) >= 10:
        f = np.array(pitches)
        med = float(np.median(f))
        semis = 12 * np.log2(f / med)
        semis = semis[np.abs(semis) < 12]   # 옥타브 오검출 제거
        pitch_var = float(np.std(semis)) if len(semis) else 0.0
    else:
        med, pitch_var = None, None

    vdb = db[voiced]
    loud_std = float(np.std(vdb))
    third = max(1, len(vdb) // 3)
    fade = float(np.mean(vdb[:third]) - np.mean(vdb[-third:]))   # +면 끝으로 갈수록 작아짐

    return {
        "total_sec": round(total_sec, 1),
        "speak_span_sec": round(span, 1),
        "speech_sec": round(speech_sec, 1),
        "pause_count": len(pauses),
        "long_pause_count": sum(1 for g in pauses if g >= LONG_PAUSE_SEC),
        "longest_pause_sec": round(max(pauses), 1) if pauses else 0.0,
        "pause_ratio": round(sum(pauses) / span, 3),
        "pitch_median_hz": round(med, 1) if med else None,
        "pitch_variation_semitone": round(pitch_var, 2) if pitch_var is not None else None,
        "loudness_std_db": round(loud_std, 1),
        "fade_db": round(fade, 1),
    }


def voice_confidence(m: dict) -> dict:
    """음성 지표 → 0~100 자신감 추정 점수와 항목별 코멘트 (경험 규칙)."""
    score, notes = 100.0, []

    pv = m.get("pitch_variation_semitone")
    if pv is None:
        notes.append("목소리 높낮이를 충분히 측정하지 못했습니다.")
        tone = "측정 불가"
    elif pv < 1.5:
        score -= 15
        tone = "단조로움"
        notes.append("억양 변화가 적어 단조롭게 들릴 수 있습니다. 핵심 단어에 힘을 주세요.")
    elif pv > 5:
        score -= 10
        tone = "흔들림"
        notes.append("높낮이가 크게 흔들립니다. 긴장해서 목소리가 떨렸을 수 있습니다.")
    else:
        tone = "적당함"

    if m["loudness_std_db"] > 9:
        score -= 10
        notes.append("음량이 들쭉날쭉합니다. 문장 끝까지 같은 크기로 말해 보세요.")
    if m["fade_db"] > 4:
        score -= 15
        notes.append("뒤로 갈수록 목소리가 작아집니다. 마지막 문장을 또렷하게 마무리하세요.")
    if m["pause_ratio"] > 0.25:
        score -= 15
        notes.append("말 중간 침묵이 깁니다. 답변 순서를 미리 정해 두면 줄어듭니다.")
    elif m["pause_ratio"] > 0.15:
        score -= 7
    score -= min(15, m["long_pause_count"] * 5)
    if m["long_pause_count"]:
        notes.append(f"2초 넘는 침묵이 {m['long_pause_count']}번 있었습니다.")

    if not notes:
        notes.append("음량과 억양이 안정적입니다.")
    return {"score": int(max(0, min(100, round(score)))), "tone": tone, "notes": notes}


def speech_rate(units: int, m: dict, lang: str) -> float:
    """분당 음절(한국어) 또는 분당 단어(영어). 첫 말~마지막 말 사이 시간 기준."""
    minutes = max(m["speak_span_sec"], 1.0) / 60
    return round(units / minutes, 0)
