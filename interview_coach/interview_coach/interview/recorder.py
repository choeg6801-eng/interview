"""브라우저 녹화 부품(components/recorder/index.html)을 Streamlit 에 연결합니다.

부품이 하는 일 (모두 사용자의 브라우저 안에서)
- 카메라·마이크 켜기, 3초 카운트다운, 시간 제한 녹화
- MediaPipe 로 시선·표정 분석 (영상은 밖으로 보내지 않음)
- 녹화가 끝나면 영상(webm)·목소리(wav)·시선 지표를 파이썬으로 넘김
"""
import base64
from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "recorder"
_component = components.declare_component("interview_recorder", path=str(_DIR))


def recorder(seconds: int, token: str, question: str = "", key: str = "interview-recorder"):
    """녹화가 끝날 때마다 새 값을 돌려줍니다. 값이 없으면 None."""
    return _component(seconds=seconds, token=token, question=question, key=key, default=None)


def decode(value: dict) -> dict:
    return {
        "id": value["id"],
        "token": value.get("token", ""),
        "mime": value.get("mime") or "video/webm",
        "video": base64.b64decode(value.get("video_b64", "")),
        "wav": base64.b64decode(value.get("wav_b64", "")),
        "duration": value.get("duration", 0),
        "face": value.get("face") or {},
    }
