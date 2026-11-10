"""녹화 중 브라우저에서 잰 시선·표정 지표 → 0~100 태도 점수 (연습용 경험 규칙)."""


def face_score(s: dict) -> dict:
    if not s or s.get("frames", 0) < 30:
        return {"score": None, "notes": ["시선 분석 기록이 없어 시선·자세 점수는 내지 않았습니다."]}
    score, notes = 100.0, []
    if s["face_rate"] < 0.9:
        score -= 20
        notes.append("얼굴이 화면에서 자주 벗어났습니다. 카메라 위치를 고정하세요.")
    fr = s["front_rate"]
    if fr < 0.6:
        score -= 30
        notes.append(f"정면 응시가 {fr:.0%}입니다. 카메라 렌즈를 면접관 눈이라고 생각하세요.")
    elif fr < 0.8:
        score -= 12
        notes.append(f"정면 응시 {fr:.0%}. 생각할 때 시선이 자주 옆으로 갑니다.")
    if s["smile_rate"] < 0.05:
        score -= 8
        notes.append("표정 변화가 거의 없습니다. 첫인사와 마무리에 가볍게 웃어 보세요.")
    if s["blinks_per_min"] > 35:
        score -= 8
        notes.append("눈 깜빡임이 잦습니다. 긴장한 것처럼 보일 수 있습니다.")
    if s.get("head_sway_pct") is not None and s["head_sway_pct"] > 3:
        score -= 8
        notes.append("고개 움직임이 많습니다. 어깨를 펴고 고개를 고정해 보세요.")
    if not notes:
        notes.append("시선과 자세가 안정적입니다.")
    return {"score": int(max(0, round(score))), "notes": notes}
