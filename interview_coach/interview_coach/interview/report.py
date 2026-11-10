"""점수 합산과 리포트(마크다운) 만들기."""
from datetime import datetime

from .config import EN_WORDS_PER_MIN, KO_SYLLABLES_PER_MIN


def rate_comment(rate: float, lang: str) -> tuple[str, int]:
    lo, hi = KO_SYLLABLES_PER_MIN if lang == "ko" else EN_WORDS_PER_MIN
    unit = "음절/분" if lang == "ko" else "단어/분"
    if rate < lo * 0.85:
        return f"{rate:.0f}{unit} · 느린 편 (참고 범위 {lo}~{hi})", 70
    if rate < lo:
        return f"{rate:.0f}{unit} · 약간 느림 (참고 범위 {lo}~{hi})", 85
    if rate <= hi:
        return f"{rate:.0f}{unit} · 적당함 (참고 범위 {lo}~{hi})", 100
    if rate <= hi * 1.15:
        return f"{rate:.0f}{unit} · 약간 빠름 (참고 범위 {lo}~{hi})", 85
    return f"{rate:.0f}{unit} · 빠른 편 (참고 범위 {lo}~{hi})", 70


def filler_score(fillers: dict, minutes: float) -> tuple[int, float]:
    weighted = fillers["sure_total"] + 0.5 * fillers["maybe_total"]
    per_min = weighted / max(minutes, 0.25)
    if per_min <= 2:
        return 100, per_min
    if per_min <= 4:
        return 85, per_min
    if per_min <= 7:
        return 70, per_min
    return 55, per_min


def total_score(ai: dict, voice: dict, face: dict) -> int:
    """종합 = 내용(AI 논리·구체성·직무) 60% + 전달(AI 전달력·목소리) 25% + 태도(카메라) 15%.
    카메라를 안 쓰면 태도 비중을 내용·전달에 나눠 줍니다."""
    content = (ai["logic"] + ai["specificity"] + ai["job_fit"]) / 3
    delivery = (ai["delivery"] + voice["score"]) / 2
    if face.get("score") is None:
        return round(content * 0.7 + delivery * 0.3)
    return round(content * 0.6 + delivery * 0.25 + face["score"] * 0.15)


def build_markdown(records: list, context: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# 면접 연습 리포트", "", f"- 작성: {now}", f"- 지원 정보: {context}",
             f"- 연습한 질문: {len(records)}개", ""]
    if records:
        avg = round(sum(r["total"] for r in records) / len(records))
        lines += [f"## 평균 종합 점수: {avg}점", ""]
        lines += ["| # | 유형 | 질문 | 종합 | 논리 | 구체 | 직무 | 전달 | 목소리 | 태도 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(records, 1):
            a = r["ai"]
            face = r["face"].get("score")
            lines.append(
                f"| {i} | {r['question']['type']} | {r['question']['q']} | {r['total']} | "
                f"{a['logic']} | {a['specificity']} | {a['job_fit']} | {a['delivery']} | "
                f"{r['voice']['score']} | {face if face is not None else '-'} |"
            )
        lines.append("")
    for i, r in enumerate(records, 1):
        a = r["ai"]
        lines += [
            f"## {i}. {r['question']['q']}", "",
            f"**종합 {r['total']}점** · {r['time']}", "",
            "### 내 답변 (음성 인식)", "", r["transcript"] or "(인식된 내용 없음)", "",
            "### 말하기 측정",
            f"- 말하기 속도: {r['rate_text']}",
            f"- 습관어: 확실 {r['fillers']['sure_total']}회 {r['fillers']['sure']}, "
            f"의심 {r['fillers']['maybe_total']}회 {r['fillers']['maybe']}",
            f"- 침묵: {r['audio']['pause_count']}회, 가장 긴 침묵 {r['audio']['longest_pause_sec']}초",
            f"- 목소리: {r['voice']['tone']} · " + " / ".join(r["voice"]["notes"]),
        ]
        if r["face"].get("score") is not None:
            lines.append("- 카메라 태도: " + " / ".join(r["face"]["notes"]))
        lines += [
            "", "### 평가",
            f"- 논리성 {a['logic']}: {a['logic_comment']}",
            f"- 구체성 {a['specificity']}: {a['specificity_comment']}",
            f"- 직무 적합성 {a['job_fit']}: {a['job_fit_comment']}",
            f"- 전달력 {a['delivery']}: {a['delivery_comment']}",
            f"- 답변 흐름: {a['structure']}", "",
            "**잘한 점**", *[f"- {s}" for s in a["strengths"]], "",
            "**고칠 점**", *[f"- {s}" for s in a["improvements"]], "",
            "**개선 답변 예시**", "", a["better_answer"], "",
            f"**예상 꼬리 질문:** {a['follow_up_question']}", "",
        ]
        if r.get("memo"):
            lines += ["**내 메모**", "", r["memo"], ""]
    lines += ["---", "목소리 자신감·태도 점수는 연습용 경험 규칙으로 계산한 참고값입니다."]
    return "\n".join(lines)
