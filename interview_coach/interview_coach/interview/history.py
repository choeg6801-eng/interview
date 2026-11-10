"""평가 기록을 내 컴퓨터(data/history.json)에 자동 저장하고 불러옵니다.

- 저장하는 것: 질문, 점수, 평가 내용, 음성 인식 결과, 말하기 지표, 저장한 영상 파일 위치
- 저장하지 않는 것: 영상 자체(영상은 '내 컴퓨터에 저장'을 눌렀을 때만 recordings 폴더에 남음), 메모
"""
import json

from .config import HISTORY_PATH

SKIP_KEYS = {"video", "memo"}


def _clean(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in SKIP_KEYS}


def load() -> list:
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save(records: list) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HISTORY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps([_clean(r) for r in records], ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(HISTORY_PATH)   # 쓰는 도중 꺼져도 기존 파일이 깨지지 않게


def clear() -> None:
    try:
        HISTORY_PATH.unlink()
    except FileNotFoundError:
        pass


def previous_total(records: list, rec: dict):
    """같은 질문을 이 기록보다 먼저 평가한 점수 (없으면 None)."""
    prev = None
    for r in records:
        if r is rec or (rec.get("id") and r.get("id") == rec.get("id")):
            break
        if r["question"]["q"] == rec["question"]["q"]:
            prev = r["total"]
    return prev
