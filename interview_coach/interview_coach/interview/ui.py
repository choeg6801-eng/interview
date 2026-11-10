"""화면 꾸미기: CSS와 HTML 조각. 디자인은 남색 한 가지 + 흰 바탕입니다."""
import html
import re

from .fillers import MAYBE_FILLERS, SURE_FILLERS

NAVY = "#1b2b57"

CSS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{
  --navy:#1b2b57; --navy-700:#13203f; --navy-50:#eef1f8; --navy-100:#dde3f0;
  --line:#e3e7ee; --ink:#161b2b; --ink-2:#4a5368; --ink-3:#8a92a6;
  --good:#1f8a52; --good-bg:#e7f4ec; --mid:#b26a00; --mid-bg:#fdf3e2; --low:#c2412d; --low-bg:#fbeae7;
}
html, body, [class*="css"], .stApp, button, input, textarea, select {
  font-family: "Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif !important;
}
/* Streamlit 기본 장식 숨김 */
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none !important;}
section[data-testid="stSidebar"] {display:none;}
.block-container {max-width: 1180px; padding-top: 1.2rem; padding-bottom: 4rem;}
hr {border-color: var(--line) !important; margin: 0.6rem 0 1.2rem !important;}
/* 상단 메뉴·유형 버튼 */
[data-testid="stButtonGroup"] button {font-weight: 600;}
[data-testid="stMarkdownContainer"] h3 {font-weight: 700;}
/* 진행 상태 상자 */
[data-testid="stStatusWidget"], [data-testid="stExpander"] {border-radius: 10px;}
/* 0 높이 스크립트 칸이 틈을 만들지 않게 */
iframe[height="0"] {display:block; margin:0 !important;}
[data-testid="stElementContainer"]:has(> iframe[height="0"]),
[data-testid="element-container"]:has(> iframe[height="0"]) {display:none;}
h1, h2, h3 {letter-spacing: -0.02em;}

/* 버튼 */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 10px; min-height: 44px; font-weight: 600; border: 1px solid var(--line);
}
.stButton > button:hover, .stDownloadButton > button:hover {border-color: var(--navy-100); background: var(--navy-50); color: var(--ink);}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {background: var(--navy); border-color: var(--navy); color:#fff;}
.stButton > button[kind="primary"]:hover {background: var(--navy-700); color:#fff;}

/* 입력칸 */
.stTextInput input, .stTextArea textarea, .stNumberInput input {border-radius: 10px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 12px; border-color: var(--line); background:#fff;}

/* 상단 */
.brand {display:flex; align-items:center; gap:10px; font-weight:700; font-size:19px; color:var(--navy); padding-top:4px;}
.brand i {width:22px; height:22px; border-radius:6px; background:var(--navy); display:grid; place-items:center;}
.brand i::after {content:""; width:8px; height:8px; border:2px solid #fff; border-radius:50%;}
.status {font-size:13px; color:var(--ink-3); text-align:right; padding-top:10px;}
.status .dot {display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; vertical-align:1px;}

/* 단계: 버튼이 아니라 진행 표시 (테두리 없이, 선으로 이어서) */
.steps {display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin: 2px 0 4px; cursor:default; user-select:none;}
.step {display:flex; align-items:center; gap:7px; font-size:14px; color:var(--ink-3); white-space:nowrap;}
.step b {width:22px; height:22px; border-radius:50%; display:grid; place-items:center; font-size:12px;
         border:1.5px solid var(--navy-100); color:var(--ink-3); background:transparent;}
.step.done {color:var(--ink-2);}
.step.done b {background:var(--navy); border-color:var(--navy); color:#fff;}
.step.now {color:var(--navy); font-weight:700;}
.step.now b {border-color:var(--navy); color:var(--navy);}
.steps .line {width:28px; height:1.5px; background:var(--navy-100);}
.steps .line.done {background:var(--navy);}
.todo {font-size:14px; color:var(--ink-2); margin: 0 0 18px;}
.todo b {color:var(--navy);}

/* 질문 카드 */
.qcard {background:var(--navy); color:#fff; border-radius:16px; padding:24px 26px; display:grid; gap:16px; margin-bottom:14px;}
.qtop {display:flex; justify-content:space-between; align-items:center;}
.qtype {font-size:13px; font-weight:600; border:1px solid rgba(255,255,255,.35); border-radius:6px; padding:2px 10px;}
.qcount, .qlang {font-size:14px; color:#aeb9d6; font-variant-numeric:tabular-nums;}
.qtext {font-size:clamp(22px,2.6vw,29px); font-weight:700; line-height:1.45; letter-spacing:-0.02em; word-break:keep-all; margin:0;}
.qbar {height:4px; border-radius:2px; background:rgba(255,255,255,.18); overflow:hidden;}
.qbar i {display:block; height:100%; background:#fff; border-radius:2px;}

/* 질문 칸을 화면에 붙여 둠: 아래로 내려가도 질문이 보이게 (넓은 화면만) */
@media (min-width: 900px){
  div[data-testid="stColumn"]:has(.qcard), div[data-testid="column"]:has(.qcard) {
    position: sticky; top: 1rem; align-self: flex-start;
  }
}
/* 탭 */
.stTabs [data-baseweb="tab-list"] {gap: 4px;}
.stTabs [data-baseweb="tab"] {padding: 8px 12px;}
/* 접히는 칸 */
[data-testid="stExpander"] details {border-radius: 10px; border-color: var(--line); background:#fff;}
[data-testid="stExpander"] summary {font-weight: 600;}

/* 공통 조각 */
.label {font-size:13px; font-weight:600; color:var(--ink-3); letter-spacing:.02em;}
.pill {display:inline-flex; align-items:center; font-size:13px; font-weight:600; padding:3px 10px; border-radius:999px;}
.pill.good {background:var(--good-bg); color:var(--good);}
.pill.mid {background:var(--mid-bg); color:var(--mid);}
.pill.low {background:var(--low-bg); color:var(--low);}
.note {font-size:13px; color:var(--ink-3);}
.kpis {display:grid; grid-template-columns:repeat(3,1fr); border:1px solid var(--line); border-radius:10px; background:#fff;}
.kpi {padding:10px 12px;}
.kpi + .kpi {border-left:1px solid var(--line);}
.kpi .k {font-size:12px; color:var(--ink-3);}
.kpi .v {font-size:22px; font-weight:700; font-variant-numeric:tabular-nums;}
.camstate {display:flex; justify-content:space-between; align-items:center; font-size:14px; margin:4px 0 10px;}
.legend {display:flex; gap:12px; font-size:12px; color:var(--ink-3); flex-wrap:wrap; margin-top:8px;}
.legend span {display:flex; align-items:center; gap:5px;}
.legend span::before {content:""; width:10px; height:10px; border-radius:3px; border:2px solid var(--c);}

/* 결과 요약 */
.summary {display:grid; grid-template-columns:200px minmax(0,1fr) minmax(0,1fr); background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; margin-bottom:14px;}
.total {padding:22px; border-right:1px solid var(--line); display:grid; gap:6px; align-content:center;}
.total .num {font-size:54px; font-weight:800; letter-spacing:-0.04em; line-height:1; color:var(--navy); font-variant-numeric:tabular-nums;}
.total .num small {font-size:17px; font-weight:600; color:var(--ink-3); margin-left:2px;}
.bars {padding:18px 22px; display:grid; gap:10px; border-right:1px solid var(--line);}
.brow {display:grid; grid-template-columns:84px 1fr 30px; align-items:center; gap:10px; font-size:14px;}
.brow .n {color:var(--ink-2);}
.brow .t {height:6px; border-radius:3px; background:var(--navy-50); overflow:hidden;}
.brow .t i {display:block; height:100%; background:var(--navy); border-radius:3px;}
.brow .t i.low {background:var(--low);}
.brow .s {text-align:right; font-weight:700; font-variant-numeric:tabular-nums;}
.fix {padding:18px 22px; display:grid; gap:10px; align-content:start;}
.fix h4 {font-size:15px; margin:0; font-weight:700;}
.fix ol {margin:0; padding:0; list-style:none; display:grid; gap:10px; counter-reset:f;}
.fix li {counter-increment:f; display:grid; grid-template-columns:22px 1fr; gap:10px; font-size:14px; line-height:1.55;}
.fix li::before {content:counter(f); width:22px; height:22px; border-radius:50%; background:var(--navy-50); color:var(--navy);
                 font-size:12px; font-weight:700; display:grid; place-items:center;}
.crit {display:grid; gap:10px; margin:0;}
.crit div {display:grid; grid-template-columns:120px 1fr; gap:12px; font-size:15px;}
.crit dt {font-weight:600;}
.crit dd {margin:0; color:var(--ink-2);}
.followup {background:var(--navy-50); border-radius:10px; padding:12px 16px; font-size:15px; margin:14px 0 12px;}
.followup b {color:var(--navy);}
.stats {display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px;}
.stats.six {grid-template-columns:repeat(6,1fr);}
.stat {border:1px solid var(--line); border-radius:10px; padding:12px 14px; background:#fff;}
.stat .k {font-size:13px; color:var(--ink-3);}
.stat .v {font-size:24px; font-weight:700; font-variant-numeric:tabular-nums; letter-spacing:-0.02em;}
.transcript {font-size:16px; line-height:1.9; color:var(--ink-2);}
.transcript mark {background:var(--mid-bg); color:var(--mid); border-radius:4px; padding:0 3px;}
.better {font-size:16px; line-height:1.9;}
.better .blank {background:var(--navy-50); color:var(--navy); border-radius:4px; padding:1px 5px; font-weight:600;}
.weak h4 {font-size:15px; margin:0 0 6px;}
.wbar {display:grid; grid-template-columns:90px 1fr 34px; gap:10px; align-items:center; font-size:14px; margin-top:8px;}
.wbar .t {height:8px; border-radius:4px; background:var(--navy-50); overflow:hidden;}
.wbar .t i {display:block; height:100%; background:var(--navy);}
.wbar.weakest .t i {background:var(--low);}
.wbar .s {text-align:right; font-weight:700;}

.delta {font-size:13px; color:var(--ink-3); margin-top:2px;}
.delta b {font-variant-numeric:tabular-nums;}
.delta.up b {color:var(--good);}
.delta.down b {color:var(--low);}
.hint {font-size:15px; line-height:1.75; color:var(--ink-2);}

/* 녹화한 답변 */
.take {display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:4px;}
.take b {font-size:16px;}
.take .ok {display:inline-flex; align-items:center; gap:6px; font-size:13px; font-weight:600; color:var(--good);}
.take .ok::before {content:""; width:7px; height:7px; border-radius:50%; background:var(--good);}
[data-testid="stVideo"] video, .stVideo video {border-radius:10px; background:#20283c;}

@media (max-width: 900px){
  .summary {grid-template-columns:minmax(0,1fr);}
  .total, .bars {border-right:none; border-bottom:1px solid var(--line);}
  .stats, .stats.six {grid-template-columns:1fr 1fr;}
  .crit div {grid-template-columns:1fr; gap:2px;}
}
</style>
"""

# 빈 줄이 있으면 Streamlit(마크다운)이 그 뒤를 글자로 출력하므로, 빈 줄을 모두 없애고 <style>을 맨 앞에 둠
CSS = re.sub(r"\n\s*\n", "\n", CSS).strip()
_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">'
CSS = CSS.replace(_LINK, "").strip()
CSS = CSS.replace("<style>", "<style>\n@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');", 1)

LABELS = {
    "logic": "논리성", "specificity": "구체성", "job_fit": "직무 적합성",
    "delivery": "전달력", "voice": "목소리", "face": "시선·자세",
}

e = html.escape


def grade(score: int) -> tuple[str, str]:
    if score >= 80:
        return "좋음", "good"
    if score >= 65:
        return "보통", "mid"
    return "보완 필요", "low"


def steps_html(recorded: bool, evaluated: bool) -> str:
    """진행 단계 표시와 '지금 할 일' 한 줄 (누르는 버튼이 아님)."""
    done = [True, recorded, evaluated]
    names = ["질문 고르기", "답변 녹화", "평가 받기"]
    now = next((i for i, d in enumerate(done) if not d), None)
    parts = []
    for i, n in enumerate(names):
        if i:
            parts.append(f'<span class="line {"done" if done[i] else ""}"></span>')
        cls = "done" if done[i] else ("now" if i == now else "")
        mark = "✓" if done[i] else str(i + 1)
        parts.append(f'<div class="step {cls}"><b>{mark}</b>{n}</div>')
    todo = {
        1: "<b>지금 할 일</b> · 녹화 칸에서 카메라를 켜고 <b>녹화 시작</b>을 누르세요. 질문은 아래 카드에서 바꿀 수 있습니다.",
        2: "<b>지금 할 일</b> · 녹화 칸 아래 <b>이 답변 평가 받기</b>를 누르세요.",
        None: "<b>평가 완료</b> · 아래에서 결과를 보고, 다시 녹화하거나 다음 질문으로 넘어가세요.",
    }[now]
    return '<div class="steps" aria-label="진행 단계">' + "".join(parts) + f'</div><p class="todo">{todo}</p>'


def qcard_html(q: dict, pos: int, total: int, lang: str) -> str:
    pct = (pos + 1) / max(total, 1) * 100
    return f"""<div class="qcard">
  <div class="qtop"><span class="qtype">{e(q['type'])}</span><span class="qcount">{pos + 1} / {total}</span></div>
  <p class="qtext">{e(q['q'])}</p>
  <div class="qbar"><i style="width:{pct:.1f}%"></i></div>
  <span class="qlang">{'영어로 답변' if lang == 'en' else '한국어로 답변'}</span>
</div>"""


def summary_html(r: dict, prev: int | None = None) -> str:
    a = r["ai"]
    vals = {"logic": a["logic"], "specificity": a["specificity"], "job_fit": a["job_fit"],
            "delivery": a["delivery"], "voice": r["voice"]["score"], "face": r["face"]["score"]}
    present = {k: v for k, v in vals.items() if v is not None}
    weakest = min(present, key=present.get)
    g, cls = grade(r["total"])
    rows = []
    for k, v in vals.items():
        if v is None:
            rows.append(f'<div class="brow"><span class="n">{LABELS[k]}</span><span class="note">측정 안 함</span><span class="s">–</span></div>')
            continue
        low = " low" if k == weakest else ""
        rows.append(f'<div class="brow"><span class="n">{LABELS[k]}</span><span class="t"><i class="{low.strip()}" style="width:{v}%"></i></span><span class="s">{v}</span></div>')
    fixes = "".join(f"<li>{e(x)}</li>" for x in a["improvements"][:3])
    if prev is None:
        delta = '<span class="delta">이 질문 첫 평가</span>'
    else:
        d = r["total"] - prev
        cls = "up" if d > 0 else ("down" if d < 0 else "")
        sign = f"+{d}" if d > 0 else str(d)
        delta = f'<span class="delta {cls}">지난번 {prev}점 → <b>{sign}</b></span>'

    return f"""<div class="summary">
  <div class="total"><span class="label">종합 점수</span>
    <div class="num">{r['total']}<small>/100</small></div>
    <span class="pill {cls}" style="justify-self:start">{g} · {LABELS[weakest]} 보완</span>{delta}</div>
  <div class="bars">{''.join(rows)}</div>
  <div class="fix"><h4>다음 답변에서 먼저 고칠 것</h4><ol>{fixes}</ol></div>
</div>"""


def criteria_html(a: dict) -> str:
    items = [("답변 흐름", a["structure"]),
             (f"논리성 {a['logic']}", a["logic_comment"]),
             (f"구체성 {a['specificity']}", a["specificity_comment"]),
             (f"직무 적합성 {a['job_fit']}", a["job_fit_comment"]),
             (f"전달력 {a['delivery']}", a["delivery_comment"])]
    body = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in items)
    return f'<dl class="crit">{body}</dl>'


def followup_html(text: str) -> str:
    return f'<div class="followup"><b>이어서 나올 수 있는 질문</b> · {e(text)}</div>'


def stat_html(k: str, v: str, pill: tuple[str, str] | None = None) -> str:
    p = f'<div><span class="pill {pill[1]}">{e(pill[0])}</span></div>' if pill else ""
    return f'<div class="stat"><div class="k">{e(k)}</div><div class="v">{e(v)}</div>{p}</div>'


def highlight_fillers(text: str) -> str:
    def repl(m):
        w = m.group(0)
        if w.lower() in SURE_FILLERS or w.lower() in MAYBE_FILLERS:
            return f"<mark>{w}</mark>"
        return w
    return '<p class="transcript">' + re.sub(r"[가-힣]+|[A-Za-z']+", repl, e(text)) + "</p>"


def better_html(text: str) -> str:
    body = re.sub(r"\[([^\]]+)\]", r'<span class="blank">\1</span>', e(text))
    return f'<p class="better">{body}</p>'


def kpis_html(items: list[tuple[str, str]]) -> str:
    return '<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="k">{e(k)}</div><div class="v">{e(v)}</div></div>' for k, v in items
    ) + "</div>"
