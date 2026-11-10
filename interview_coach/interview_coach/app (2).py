"""면접 연습실 (Streamlit)

실행: streamlit run app.py
"""
import hashlib
import random
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from interview import config, history, ui
from interview.audio_metrics import analyze, speech_rate, voice_confidence
from interview.fillers import count_fillers, count_units
from interview.face_score import face_score
from interview.questions import DEFAULT_QUESTIONS, answer_language
from interview.recorder import decode, recorder
from interview.report import build_markdown, filler_score, rate_comment, total_score

st.set_page_config(page_title="면접 연습실", layout="wide", initial_sidebar_state="collapsed")
st.markdown(ui.CSS, unsafe_allow_html=True)

# ---------------- 상태 ----------------
ss = st.session_state
ss.setdefault("questions", [dict(q) for q in DEFAULT_QUESTIONS])
ss.setdefault("filter", "전체")
ss.setdefault("order", list(range(len(ss.questions))))
ss.setdefault("idx", 0)
ss.setdefault("memos", {})          # 화면에만 보관 (파일 저장 안 함)
if "records" not in ss:              # 앱을 켤 때 지난 평가 기록 불러오기
    ss.records = history.load()
    ss.results = {r["question"]["q"]: r for r in ss.records}   # 질문별 마지막 평가
ss.setdefault("results", {})
ss.setdefault("context", "해외영업 신입 (동남아)")
ss.setdefault("real_qs", None)
ss.setdefault("gen_qs", None)
ss.setdefault("page", "연습")
ss.setdefault("recordings", {})    # 질문별 마지막 녹화 (화면에만 보관)
ss.setdefault("local_results", {})  # API 키 없이 한 기본 평가 (화면에만 보관)

TYPE_ORDER = ["인성", "직무", "영어"]


def rebuild_order():
    f = ss.filter
    ss.order = [i for i, q in enumerate(ss.questions) if f == "전체" or q["type"] == f]
    ss.idx = 0


def current_q():
    if not ss.order:
        return None
    return ss.questions[ss.order[ss.idx % len(ss.order)]]


def key_of(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


# ---------------- 상단 ----------------
top_l, top_m, top_r = st.columns([1.3, 2.6, 1.3], vertical_alignment="center")
top_l.markdown('<div class="brand"><i></i>면접 연습실</div>', unsafe_allow_html=True)
def _keep_selection(key: str, fallback_key: str):
    """같은 버튼을 다시 눌러 선택이 풀리면 직전 선택으로 되돌림."""
    if ss.get(key) is None:
        ss[key] = ss.get(fallback_key)
    ss[fallback_key] = ss[key]


ss.setdefault("_page_last", "연습")
with top_m:
    page = st.segmented_control("메뉴", ["연습", "맞춤 질문", "기록"], key="page",
                                label_visibility="collapsed",
                                on_change=_keep_selection, args=("page", "_page_last"))
    page = page or ss["_page_last"]


def scroll_to(anchor_id: str):
    """화면을 해당 위치로 부드럽게 옮김 (녹화 직후 평가 버튼, 평가 직후 결과)."""
    components.html(
        f"<script>setTimeout(()=>{{const el=window.parent.document.getElementById('{anchor_id}');"
        f"if(el)el.scrollIntoView({{behavior:'smooth',block:'center'}});}},350);</script>",
        height=0,
    )
if config.has_api_key():
    top_r.markdown('<div class="status"><span class="dot" style="background:#1f8a52"></span>API 키 입력됨</div>',
                   unsafe_allow_html=True)
    from interview import llm
else:
    top_r.markdown('<div class="status"><span class="dot" style="background:#b26a00"></span>기본 평가 모드</div>',
                   unsafe_allow_html=True)
st.divider()


# ================= 연습 =================
def page_practice():
    if not config.has_api_key():
        st.info("기본 평가 모드입니다. 목소리(멈춤·억양·음량)와 시선·자세를 평가합니다. "
                "답변 내용 평가(논리성·구체성 등)는 OpenAI API 키를 연결하면 함께 나옵니다.")

    q = current_q()
    qkey = q["q"] if q else ""
    token = key_of(qkey)
    take = ss.recordings.get(token)
    result = ss.results.get(qkey)
    local = ss.local_results.get(qkey)
    evaluated = bool(take and ((result and result.get("rec_id") == take["id"])
                               or (local and local.get("rec_id") == take["id"])))
    st.markdown(ui.steps_html(bool(take), evaluated), unsafe_allow_html=True)

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        present = [t for t in TYPE_ORDER if any(x["type"] == t for x in ss.questions)]
        present += sorted({x["type"] for x in ss.questions} - set(TYPE_ORDER))
        opts = ["전체"] + present
        counts = {t: (len(ss.questions) if t == "전체" else sum(x["type"] == t for x in ss.questions)) for t in opts}
        if ss.filter not in opts:
            ss.filter = "전체"
            rebuild_order()
        fkey = f"filter_ctrl_{len(ss.questions)}"

        def _on_filter():
            if ss.get(fkey) is None:          # 같은 버튼을 다시 눌러 선택이 풀린 경우
                ss[fkey] = ss.filter
            else:
                ss.filter = ss[fkey]
                rebuild_order()

        st.segmented_control("질문 유형", opts, default=ss.filter,
                             format_func=lambda t: f"{t} {counts[t]}", label_visibility="collapsed",
                             key=fkey, on_change=_on_filter)
        q = current_q()
        qkey = q["q"] if q else ""
        if q is None:
            st.info("이 유형에 질문이 없습니다.")
            return

        n = len(ss.order)
        lang = answer_language(q)
        st.markdown(ui.qcard_html(q, ss.idx, n, lang), unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        if c1.button("이전", use_container_width=True):
            ss.idx = (ss.idx - 1) % n
            st.rerun()
        if c2.button("섞기", use_container_width=True):
            random.shuffle(ss.order)
            ss.idx = 0
            st.rerun()
        if c3.button("다음", use_container_width=True, type="primary"):
            ss.idx = (ss.idx + 1) % n
            st.rerun()

        if q.get("hint"):
            with st.expander("답변 방향 보기 (막힐 때만 펼치세요)"):
                st.markdown(f'<div class="hint">{ui.e(q["hint"])}</div>', unsafe_allow_html=True)

        with st.expander("메모" + (" · 적어 둔 내용 있음" if ss.memos.get(qkey) else ""),
                         expanded=bool(ss.memos.get(qkey))):
            memo = st.text_area("메모", value=ss.memos.get(qkey, ""), height=100,
                                placeholder="말하고 싶은 핵심을 짧게 적어 두세요",
                                label_visibility="collapsed", key=f"memo_{token}")
            st.markdown('<div class="note">이 화면에만 남고, 파일로 저장하지 않습니다.</div>', unsafe_allow_html=True)
        ss.memos[qkey] = memo

        if not take:
            with st.expander("카메라 없이 목소리만 녹음하기"):
                audio = st.audio_input("목소리 녹음", key=f"audio_{token}", label_visibility="collapsed") \
                    if hasattr(st, "audio_input") else None
                uploaded = st.file_uploader("또는 WAV 파일 올리기", type=["wav"], key=f"up_{token}")
                source = audio or uploaded
                if st.button("이 녹음 평가 받기", type="primary", use_container_width=True,
                             disabled=source is None, key=f"eval_audio_{token}"):
                    run_analysis(q, source.getvalue(), memo, None)

    with right:
        value = recorder(seconds=config.ANSWER_SECONDS, token=token, question=qkey)
        if value and value.get("id") != ss.get("_last_take"):
            ss["_last_take"] = value["id"]
            rec = decode(value)
            rec["time"] = datetime.now().strftime("%H:%M")
            ss.recordings[rec["token"] or token] = rec
            ss["_scroll"] = "take-anchor"
            st.rerun()

        if take:   # 녹화 칸 바로 아래: 다시 보기는 녹화 칸 안에서, 여기서는 평가·저장
            with st.container(border=True):
                st.markdown('<div id="take-anchor"></div>', unsafe_allow_html=True)
                status = '<span class="ok">평가 완료</span>' if evaluated else \
                    f'<span class="note">{take["duration"]:.0f}초 · {take["time"]}</span>'
                st.markdown(f'<div class="take"><b>녹화한 답변</b>{status}</div>', unsafe_allow_html=True)
                b1, b2 = st.columns([1.4, 1])
                label = "다시 평가 받기" if evaluated else "이 답변 평가 받기"
                if b1.button(label, type="primary", use_container_width=True, key=f"eval_{take['id']}"):
                    run_analysis(q, take["wav"], memo, take)
                if take.get("saved"):
                    b2.button("저장됨", use_container_width=True, disabled=True, key=f"saved_{take['id']}")
                elif b2.button("내 컴퓨터에 저장", use_container_width=True, key=f"save_{take['id']}"):
                    save_take(q, take)
                    st.rerun()
                if take.get("saved"):
                    st.markdown(f'<div class="note">저장 위치: {ui.e(take["saved"])}</div>', unsafe_allow_html=True)
                if result and not evaluated:
                    st.markdown('<div class="note">새로 녹화한 답변은 아직 평가하지 않았습니다. 아래 결과는 이전 답변 기준입니다.</div>',
                                unsafe_allow_html=True)
                with st.expander("영상 다시 보기"):
                    st.video(take["video"], format=take["mime"])
                    st.markdown('<div class="note">면접관이 보는 방향(좌우 반전 없음)으로 나옵니다.</div>',
                                unsafe_allow_html=True)

    if local and (not result or local["at"] > result.get("at", "")):
        st.markdown("<div style='height:18px'></div><div id='result-anchor'></div>", unsafe_allow_html=True)
        show_local_result(local)
    elif result:
        st.markdown("<div style='height:18px'></div><div id='result-anchor'></div>", unsafe_allow_html=True)
        show_result(result, heading=True)

    if ss.get("_scroll"):
        scroll_to(ss.pop("_scroll"))


def save_take(q, take):
    config.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    ext = "mp4" if "mp4" in take["mime"] else "webm"
    name = f"{datetime.now():%Y%m%d_%H%M%S}_{q['type']}.{ext}"
    path = config.RECORDINGS_DIR / name
    path.write_bytes(take["video"])
    take["saved"] = str(path)
    for r in ss.records:
        if r.get("rec_id") == take["id"]:
            r["saved"] = str(path)
    history.save(ss.records)


# ---------- 평가 ----------
def run_local(q, wav_bytes, take):
    """API 키 없이 할 수 있는 평가: 목소리(녹음 파일)와 시선·자세(녹화 중 측정)."""
    try:
        audio = analyze(wav_bytes)
    except Exception as e:
        st.error(f"평가하지 못했습니다: {e}")
        return
    voice = voice_confidence(audio)
    face_raw = (take or {}).get("face") or {}
    face = face_score(face_raw)
    parts = [voice["score"]] + ([face["score"]] if face["score"] is not None else [])
    ss.local_results[q["q"]] = {
        "at": datetime.now().strftime("%Y%m%d%H%M%S"), "time": datetime.now().strftime("%H:%M"),
        "question": q, "audio": audio, "voice": voice, "face_raw": face_raw, "face": face,
        "total": round(sum(parts) / len(parts)), "rec_id": take["id"] if take else None,
    }
    ss["_scroll"] = "result-anchor"
    st.rerun()


def show_local_result(r):
    au, v, fc = r["audio"], r["voice"], r["face"]
    st.markdown(f"#### 기본 평가 결과 <span class='note' style='font-weight:400'>· {ui.e(r['question']['q'])} · {r['time']}</span>",
                unsafe_allow_html=True)
    g, cls = ui.grade(r["total"])
    rows = [("목소리", v["score"]), ("시선·자세", fc["score"])]
    bars = "".join(
        f'<div class="brow"><span class="n">{n}</span>'
        + (f'<span class="t"><i style="width:{x}%"></i></span><span class="s">{x}</span>' if x is not None
           else '<span class="note">측정 안 함</span><span class="s">–</span>')
        + "</div>" for n, x in rows)
    notes = "".join(f"<li>{ui.e(x)}</li>" for x in (v["notes"] + (fc["notes"] if fc["score"] is not None else []))[:3])
    st.markdown(f"""<div class="summary">
  <div class="total"><span class="label">기본 점수</span><div class="num">{r['total']}<small>/100</small></div>
    <span class="pill {cls}" style="justify-self:start">{g}</span>
    <span class="delta">목소리·시선 기준</span></div>
  <div class="bars">{bars}</div>
  <div class="fix"><h4>다음 답변에서 먼저 고칠 것</h4><ol>{notes}</ol></div></div>""", unsafe_allow_html=True)
    st.markdown(
        '<div class="stats">'
        + ui.stat_html("답변 길이", f"{au['speak_span_sec']:.0f}초")
        + ui.stat_html("0.7초 넘게 멈춤", f"{au['pause_count']}번")
        + ui.stat_html("가장 긴 멈춤", f"{au['longest_pause_sec']}초")
        + ui.stat_html("목소리 톤", v["tone"])
        + "</div>", unsafe_allow_html=True)
    if fc["score"] is not None:
        fr = r["face_raw"]
        st.markdown(f"- 카메라: 정면 응시 {fr['front_rate']:.0%}, 웃는 표정 {fr['smile_rate']:.0%}, "
                    f"눈 깜빡임 분당 {fr['blinks_per_min']:.0f}번")
    st.markdown('<div class="note">답변 내용(논리성·구체성·직무 적합성)과 습관어·말 빠르기 평가는 OpenAI API 키를 연결하면 함께 나옵니다. '
                '목소리·시선 점수는 같은 환경에서 내 기록끼리 비교하는 참고값입니다.</div>', unsafe_allow_html=True)


def run_analysis(q, wav_bytes, memo, take):
    if not config.has_api_key():
        run_local(q, wav_bytes, take)
        return
    lang = answer_language(q)
    face_raw = (take or {}).get("face") or {}
    with st.status("답변을 살펴보고 있습니다", expanded=True) as status:
        try:
            st.write("목소리 크기와 멈춤을 재는 중")
            audio = analyze(wav_bytes)
            voice = voice_confidence(audio)

            st.write("녹음을 글자로 옮기는 중")
            transcript = llm.transcribe(wav_bytes, lang)
            if not transcript:
                status.update(label="말소리가 잡히지 않았습니다. 다시 녹음해 주세요.", state="error")
                return

            fillers = count_fillers(transcript)
            rate = speech_rate(count_units(transcript, lang), audio, lang)
            rate_text, rate_pts = rate_comment(rate, lang)
            f_pts, f_per_min = filler_score(fillers, audio["speak_span_sec"] / 60)
            face = face_score(face_raw)

            st.write("답변 내용을 평가하는 중")
            metrics = {
                "말하기 속도": rate_text,
                "말하기 속도 점수": rate_pts,
                "습관어(확실)": fillers["sure"],
                "습관어(의심, 문맥 판단 필요)": fillers["maybe"],
                "분당 습관어": round(f_per_min, 1),
                "습관어 점수": f_pts,
                "침묵 횟수(0.7초 이상)": audio["pause_count"],
                "가장 긴 침묵(초)": audio["longest_pause_sec"],
                "답변 길이(초)": audio["speak_span_sec"],
                "목소리 자신감 추정": voice,
                "시선·표정 측정": face_raw or "측정 안 함",
            }
            ai = llm.evaluate(q, transcript, metrics, ss.context)
            total = total_score(ai, voice, face)
        except Exception as e:
            status.update(label=f"평가하지 못했습니다: {e}", state="error")
            return
        status.update(label="평가가 끝났습니다", state="complete", expanded=False)

    rec = {
        "id": uuid.uuid4().hex[:12],
        "at": datetime.now().strftime("%Y%m%d%H%M%S"),
        "time": datetime.now().strftime("%m/%d %H:%M"),
        "question": q, "lang": lang, "transcript": transcript,
        "audio": audio, "voice": voice, "fillers": fillers,
        "rate": rate, "rate_text": rate_text, "rate_pts": rate_pts,
        "filler_pts": f_pts, "filler_per_min": f_per_min,
        "face_raw": face_raw, "face": face, "ai": ai, "total": total, "memo": memo,
        "rec_id": take["id"] if take else None,
        "video": take["video"] if take else None, "mime": take["mime"] if take else None,
        "saved": take.get("saved") if take else None,
    }
    ss.results[q["q"]] = rec
    ss.records.append(rec)
    ss["_scroll"] = "result-anchor"
    try:
        history.save(ss.records)
    except OSError as e:
        st.toast(f"기록 파일에 저장하지 못했습니다: {e}")
    st.rerun()


def show_result(r, heading=False):
    a = r["ai"]
    if heading:
        st.markdown(f"#### 평가 결과 <span class='note' style='font-weight:400'>· {ui.e(r['question']['q'])} · {r['time']}</span>",
                    unsafe_allow_html=True)
    st.markdown(ui.summary_html(r, history.previous_total(ss.records, r)), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["항목별 평가", "말하기 습관", "내 답변", "다듬은 답변"])
    with t1:
        st.markdown(ui.criteria_html(a), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown("<span class='label'>잘한 점</span>", unsafe_allow_html=True)
        c1.markdown("\n".join(f"- {s}" for s in a["strengths"]))
        c2.markdown("<span class='label'>아쉬운 점</span>", unsafe_allow_html=True)
        c2.markdown("\n".join(f"- {s}" for s in a["improvements"]))
        st.markdown(ui.followup_html(a["follow_up_question"]), unsafe_allow_html=True)
    with t2:
        au, fl = r["audio"], r["fillers"]
        _, rate_cls = {100: ("", "good"), 85: ("", "mid"), 70: ("", "low")}[r["rate_pts"]]
        rate_word = r["rate_text"].split("·")[1].split("(")[0].strip()
        filler_n = fl["sure_total"] + fl["maybe_total"]
        f_cls = "good" if r["filler_pts"] >= 85 else ("mid" if r["filler_pts"] >= 70 else "low")
        p_cls = "good" if au["pause_count"] <= 2 else ("mid" if au["pause_count"] <= 4 else "low")
        tone = r["voice"]["tone"]
        t_cls = "good" if tone == "적당함" else "mid"
        unit = "음절/분" if r["lang"] == "ko" else "단어/분"
        st.markdown(
            '<div class="stats">'
            + ui.stat_html(f"말 빠르기 ({unit})", f"{r['rate']:.0f}", (rate_word, rate_cls))
            + ui.stat_html("습관어", f"{filler_n}번", ("적음" if f_cls == "good" else "조금 많음" if f_cls == "mid" else "많음", f_cls))
            + ui.stat_html("0.7초 넘게 멈춤", f"{au['pause_count']}번", ("괜찮음" if p_cls == "good" else "조금 많음" if p_cls == "mid" else "많음", p_cls))
            + ui.stat_html("목소리 톤", tone, (f"자신감 {r['voice']['score']}", t_cls))
            + "</div>",
            unsafe_allow_html=True,
        )
        lines = [f"말 빠르기: {r['rate_text']}",
                 f"습관어: 확실 {fl['sure'] or '없음'} · 문맥상 애매 {fl['maybe'] or '없음'}",
                 f"애매한 말 확인: {a['filler_judgement']}",
                 f"가장 길게 멈춘 시간 {au['longest_pause_sec']}초, 2초 넘게 멈춤 {au['long_pause_count']}번"]
        lines += r["voice"]["notes"]
        if r["face"]["score"] is not None:
            fr = r["face_raw"]
            lines.append(f"카메라: 정면 응시 {fr['front_rate']:.0%}, 웃는 표정 {fr['smile_rate']:.0%}, "
                         f"눈 깜빡임 분당 {fr['blinks_per_min']:.0f}번")
            lines += r["face"]["notes"]
        st.markdown("\n".join(f"- {x}" for x in lines))
        st.markdown('<div class="note">녹음을 글자로 바꿀 때 "음, 어"가 빠지는 경우가 있어 실제보다 적게 잡힐 수 있습니다. '
                    '목소리와 시선 점수는 같은 환경에서 내 기록끼리 비교하는 참고값입니다.</div>',
                    unsafe_allow_html=True)
    with t3:
        st.markdown(ui.highlight_fillers(r["transcript"]), unsafe_allow_html=True)
        st.markdown('<div class="note">표시된 부분이 습관어로 의심되는 말입니다.</div>', unsafe_allow_html=True)
        if r.get("memo"):
            st.markdown("<span class='label'>내 메모</span>", unsafe_allow_html=True)
            st.write(r["memo"])
    with t4:
        st.markdown(ui.better_html(a["better_answer"]), unsafe_allow_html=True)
        st.markdown('<div class="note">파란 칸은 본인 경험으로 채우세요. 말하지 않은 경험을 지어 넣지 않도록 비워 두었습니다.</div>',
                    unsafe_allow_html=True)


# ================= 맞춤 질문 =================
def page_custom():
    st.markdown("### 맞춤 질문")
    st.markdown('<div class="note" style="font-size:15px;margin-bottom:12px">지원하는 회사와 직무를 넣으면 실제 후기에 나온 질문을 찾고, '
                '예상 질문을 만들어 연습 목록에 넣습니다.</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.5], gap="large")

    with left:
        with st.form("info", border=True):
            company = st.text_input("회사", placeholder="예: OO상사")
            c1, c2 = st.columns(2)
            job = c1.text_input("직무", value="해외영업 신입")
            region = c2.text_input("담당 지역", value="동남아")
            jd = st.text_area("채용 공고 (선택)", height=110, placeholder="공고의 주요 업무, 자격 요건을 붙여 넣으세요")
            bg = st.text_area("내 경험 요약 (선택)", height=90, placeholder="경험을 넣으면 그 경험을 파고드는 질문도 만듭니다",
                              help="연락처 같은 개인 정보는 넣지 마세요.")
            st.markdown("<span class='label'>만들 질문 수</span>", unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            n_in = k1.number_input("인성", 0, 15, 5)
            n_job = k2.number_input("직무", 0, 15, 8)
            n_en = k3.number_input("영어", 0, 10, 3)
            do_collect = st.form_submit_button("실제 면접 질문 찾기", use_container_width=True)
            do_gen = st.form_submit_button("예상 질문 만들기", type="primary", use_container_width=True)

    with right:
        if (do_collect or do_gen) and not config.has_api_key():
            st.error("`.env` 파일에 OpenAI API 키가 있어야 합니다.")
        elif (do_collect or do_gen) and not company.strip():
            st.warning("회사 이름을 입력해 주세요.")
        else:
            if do_collect or do_gen:
                ss.context = f"{company} · {job} · {region}"
            if do_collect:
                with st.spinner("면접 후기를 찾고 있습니다. 30초~1분 걸립니다."):
                    try:
                        ss.real_qs = llm.collect_real_questions(company, job)
                    except Exception as e:
                        st.error(f"찾지 못했습니다: {e}")
            if do_gen:
                with st.spinner("예상 질문을 만들고 있습니다."):
                    try:
                        real = (ss.real_qs or {}).get("questions", [])
                        ss.gen_qs = llm.generate_questions(company, job, region, jd, bg, real,
                                                           {"인성": n_in, "직무": n_job, "영어": n_en})
                    except Exception as e:
                        st.error(f"만들지 못했습니다: {e}")

        if ss.real_qs is None and not ss.gen_qs:
            with st.container(border=True):
                st.markdown("**아직 찾은 질문이 없습니다**")
                st.markdown('<div class="note">회사와 직무를 넣고 "실제 면접 질문 찾기"를 누르면 공개된 면접 후기에서 '
                            '질문을 찾습니다. 그다음 "예상 질문 만들기"를 누르면 찾은 질문을 참고해 예상 질문을 만듭니다.</div>',
                            unsafe_allow_html=True)

        if ss.real_qs is not None:
            with st.container(border=True):
                qs = ss.real_qs["questions"]
                st.markdown(f"**실제 면접 후기 질문** <span class='label' style='float:right'>출처 {len(ss.real_qs['citations'])}곳</span>",
                            unsafe_allow_html=True)
                if not qs:
                    st.markdown('<div class="note">출처가 확인되는 질문을 찾지 못했습니다. 면접 후기 사이트는 로그인이 필요한 곳이 많아 '
                                '검색되지 않을 수 있습니다. 예상 질문 만들기를 이용해 주세요.</div>', unsafe_allow_html=True)
                sel_real = []
                for i, item in enumerate(qs):
                    text = item.get("question", "")
                    if st.checkbox(text, key=f"real_{i}", value=True):
                        sel_real.append(text)
                    src = item.get("source_url", "")
                    extra = " · ".join(x for x in [item.get("year", ""), item.get("note", "")] if x)
                    st.caption(f"출처: [{item.get('source_title') or src}]({src})" + (f" · {extra}" if extra else ""))
                if ss.real_qs["citations"]:
                    with st.expander("검색에 쓰인 출처 전체"):
                        for c in ss.real_qs["citations"]:
                            st.markdown(f"- [{c['title']}]({c['url']})")
                st.markdown('<div class="note">검색으로 모은 내용이라 틀릴 수 있습니다. 출처를 열어 확인하세요.</div>',
                            unsafe_allow_html=True)
                if sel_real and st.button("선택한 질문 연습 목록에 넣기"):
                    for s in sel_real:
                        add_question({"type": "영어" if s.startswith("영어로") else "직무", "q": s})
                    st.success(f"{len(sel_real)}개를 연습 목록에 넣었습니다.")

        if ss.gen_qs:
            with st.container(border=True):
                sel = []
                st.markdown("**예상 질문**")
                for i, item in enumerate(ss.gen_qs):
                    if st.checkbox(f"[{item['type']}] {item['q']}", key=f"gen_{i}", value=True):
                        sel.append(item)
                    st.caption(item["why"])
                c1, c2 = st.columns(2)
                if c1.button("연습 목록에 추가", type="primary", use_container_width=True):
                    for it in sel:
                        add_question({"type": it["type"], "q": it["q"], "hint": it.get("hint", "")})
                    st.success(f"{len(sel)}개를 추가했습니다. 위 메뉴에서 '연습'으로 가세요.")
                if c2.button("이 질문으로만 연습하기", use_container_width=True):
                    ss.questions = [{"type": it["type"], "q": it["q"], "hint": it.get("hint", "")} for it in sel]
                    ss.filter = "전체"
                    rebuild_order()
                    st.success("연습 목록을 바꿨습니다. 위 메뉴에서 '연습'으로 가세요.")

        st.markdown(f'<div class="note" style="margin-top:8px">지금 연습 목록: {len(ss.questions)}개</div>',
                    unsafe_allow_html=True)
        if st.button("기본 질문 20개로 되돌리기"):
            ss.questions = [dict(q) for q in DEFAULT_QUESTIONS]
            ss.filter = "전체"
            rebuild_order()
            st.success("기본 질문으로 되돌렸습니다.")


def add_question(q):
    if all(x["q"] != q["q"] for x in ss.questions):
        ss.questions.append(q)
    ss.filter = "전체"
    rebuild_order()


# ================= 기록 =================
def page_report():
    recs = ss.records
    h1, h2 = st.columns([3, 1.4], vertical_alignment="bottom")
    h1.markdown("### 연습 기록")
    if not recs:
        with st.container(border=True):
            st.markdown("**아직 기록이 없습니다**")
            st.markdown('<div class="note">연습 화면에서 답변을 녹화하고 평가를 받으면 여기에 점수가 쌓입니다. '
                        '점수와 평가 내용은 내 컴퓨터에 자동 저장되어, 프로그램을 껐다 켜도 남아 있습니다.</div>',
                        unsafe_allow_html=True)
        return
    h1.markdown(f'<div class="note" style="font-size:15px">지금까지 {len(recs)}개 답변을 평가했습니다. '
                f'기록은 자동 저장됩니다 (영상과 메모 제외).</div>', unsafe_allow_html=True)
    with h2:
        b1, b2 = st.columns(2)
        b1.download_button("내려받기", build_markdown(recs, ss.context),
                           file_name="면접연습_기록.md", mime="text/markdown", use_container_width=True)
        if b2.button("지우기", use_container_width=True):
            ss["_confirm_clear"] = True
    if ss.get("_confirm_clear"):
        with st.container(border=True):
            st.markdown("**평가 기록을 모두 지울까요?** 점수와 평가 내용이 사라지고 되돌릴 수 없습니다. "
                        "저장해 둔 영상 파일(recordings 폴더)은 지워지지 않습니다.")
            c1, c2, _ = st.columns([1, 1, 2])
            if c1.button("모두 지우기", type="primary", use_container_width=True):
                ss.records, ss.results = [], {}
                history.clear()
                ss["_confirm_clear"] = False
                st.rerun()
            if c2.button("취소", use_container_width=True):
                ss["_confirm_clear"] = False
                st.rerun()

    avg = lambda f: round(sum(f(r) for r in recs) / len(recs))
    keys = {"logic": "논리성", "specificity": "구체성", "job_fit": "직무 적합성", "delivery": "전달력"}
    avgs = {k: avg(lambda r, k=k: r["ai"][k]) for k in keys}
    weakest = min(avgs, key=avgs.get)
    cards = [("평균 종합", avg(lambda r: r["total"]))] + [(keys[k], avgs[k]) for k in keys] + \
            [("목소리", avg(lambda r: r["voice"]["score"]))]
    st.markdown(
        '<div class="stats six">'
        + "".join(ui.stat_html(k, str(v)) for k, v in cards) + "</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.4, 1], gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown("**종합 점수 흐름**")
            st.line_chart(pd.DataFrame({"종합": [r["total"] for r in recs]},
                                       index=pd.Index(range(1, len(recs) + 1), name="회")),
                          height=220, color="#1b2b57")
    with c2:
        with st.container(border=True):
            bars = "".join(
                f'<div class="wbar {"weakest" if k == weakest else ""}"><span>{keys[k]}</span>'
                f'<span class="t"><i style="width:{v}%"></i></span><span class="s">{v}</span></div>'
                for k, v in avgs.items())
            st.markdown(f'<div class="weak"><h4>가장 약한 항목은 {keys[weakest]}</h4>'
                        f'<div class="note" style="font-size:14px">다음 연습에서는 이 부분을 먼저 신경 써 보세요.</div>{bars}</div>',
                        unsafe_allow_html=True)

    def change(r):
        prev = history.previous_total(recs, r)
        return None if prev is None else r["total"] - prev

    df = pd.DataFrame([{
        "회": i, "날짜": r["time"], "유형": r["question"]["type"], "질문": r["question"]["q"], "종합": r["total"],
        "지난번 대비": change(r),
        "논리": r["ai"]["logic"], "구체": r["ai"]["specificity"], "직무": r["ai"]["job_fit"],
        "전달": r["ai"]["delivery"], "목소리": r["voice"]["score"], "시선": r["face"]["score"],
        "습관어": r["fillers"]["sure_total"] + r["fillers"]["maybe_total"],
    } for i, r in enumerate(recs, 1)])
    st.dataframe(df, hide_index=True, use_container_width=True,
                 column_config={"질문": st.column_config.TextColumn(width="large"),
                                "지난번 대비": st.column_config.NumberColumn(format="%+d", help="같은 질문의 직전 평가와 비교한 종합 점수 변화")})

    for i, r in enumerate(recs, 1):
        with st.expander(f"{i}회 · {r['time']} · {r['question']['q']} · {r['total']}점"):
            if r.get("video"):
                st.video(r["video"], format=r["mime"])
            elif r.get("saved") and Path(r["saved"]).exists():
                st.video(r["saved"])
            elif r.get("rec_id"):
                st.markdown('<div class="note">영상은 저장하지 않아 다시 볼 수 없습니다.</div>', unsafe_allow_html=True)
            show_result(r)


if page == "연습":
    page_practice()
elif page == "맞춤 질문":
    page_custom()
else:
    page_report()
