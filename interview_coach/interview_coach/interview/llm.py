"""OpenAI API 호출: 음성 인식, 답변 평가, 실제 면접 질문 수집, 예상 질문 생성."""
import io
import json
import re

from openai import OpenAI

from .config import LLM_MODEL, OPENAI_API_KEY, TRANSCRIBE_MODEL
from .fillers import TRANSCRIBE_PROMPT_EN, TRANSCRIBE_PROMPT_KO

_client = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ---------- 1) 음성 → 글자 ----------
def transcribe(wav_bytes: bytes, lang: str) -> str:
    f = io.BytesIO(wav_bytes)
    f.name = "answer.wav"
    prompt = TRANSCRIBE_PROMPT_EN if lang == "en" else TRANSCRIBE_PROMPT_KO
    kwargs = dict(model=TRANSCRIBE_MODEL, file=f, prompt=prompt, language=lang)
    try:
        res = client().audio.transcriptions.create(**kwargs)
    except Exception:
        # 일부 모델은 language 를 받지 않을 수 있어 한 번 빼고 다시 시도
        f.seek(0)
        kwargs.pop("language")
        res = client().audio.transcriptions.create(**kwargs)
    return getattr(res, "text", str(res)).strip()


# ---------- 2) 답변 평가 ----------
EVAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "logic": {"type": "integer", "description": "논리성 0~100"},
        "specificity": {"type": "integer", "description": "구체성 0~100"},
        "job_fit": {"type": "integer", "description": "직무 적합성 0~100"},
        "delivery": {"type": "integer", "description": "전달력 0~100 (말 속도·습관어·침묵 지표 반영)"},
        "logic_comment": {"type": "string"},
        "specificity_comment": {"type": "string"},
        "job_fit_comment": {"type": "string"},
        "delivery_comment": {"type": "string"},
        "structure": {"type": "string", "description": "답변 흐름 요약 (예: 결론→근거→사례)"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "improvements": {"type": "array", "items": {"type": "string"}},
        "filler_judgement": {"type": "string", "description": "의심 습관어가 실제 습관어인지 판단"},
        "better_answer": {"type": "string"},
        "follow_up_question": {"type": "string", "description": "면접관이 이어서 물을 만한 꼬리 질문"},
    },
    "required": [
        "logic", "specificity", "job_fit", "delivery",
        "logic_comment", "specificity_comment", "job_fit_comment", "delivery_comment",
        "structure", "strengths", "improvements", "filler_judgement",
        "better_answer", "follow_up_question",
    ],
}

EVAL_SYSTEM = """당신은 한국 기업의 해외영업 신입 채용 면접관이자 면접 코치입니다.
지원자의 답변(음성 인식 결과)과 말하기 측정값을 보고 객관적으로 평가합니다.

규칙
- 칭찬을 부풀리지 말고 근거를 들어 평가합니다. 점수는 엄격하게 매깁니다 (보통 수준 답변 = 60점 안팎).
- 논리성: 질문에 대한 결론이 먼저 나오는지, 근거와 사례가 순서 있게 이어지는지.
- 구체성: 숫자, 기간, 본인이 한 행동, 결과가 있는지. 추상적 표현만 있으면 감점.
- 직무 적합성: 해외영업(바이어 소통, 협상, 납기·결제·클레임 관리, 시장 이해)과 연결되는지.
- 전달력: 함께 주는 말 속도, 습관어 수, 침묵 지표를 반영합니다.
- 개선 답변 예시(better_answer)는 지원자가 실제로 말한 내용만 바탕으로 다시 구성합니다.
  지원자가 말하지 않은 경험·숫자·회사명은 절대 지어내지 말고 [여기에 본인 경험/숫자] 처럼 빈칸으로 둡니다.
- 영어 질문이면 better_answer 는 영어로, 나머지 설명은 모두 한국어로 씁니다.
- 음성 인식 결과에는 인식 오류가 있을 수 있으니 사소한 오탈자는 감점하지 않습니다."""


def evaluate(question: dict, transcript: str, metrics: dict, context: str = "") -> dict:
    user = {
        "질문 유형": question["type"],
        "질문": question["q"],
        "지원 정보": context or "해외영업 신입 (동남아)",
        "답변(음성 인식)": transcript,
        "말하기 측정값": metrics,
    }
    res = client().chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": EVAL_SYSTEM},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "interview_eval", "strict": True, "schema": EVAL_SCHEMA},
        },
    )
    data = json.loads(res.choices[0].message.content)
    for k in ("logic", "specificity", "job_fit", "delivery"):
        data[k] = int(max(0, min(100, data[k])))
    return data


# ---------- 3) 실제 면접 질문 수집 (웹 검색) ----------
COLLECT_PROMPT = """다음 회사·직무의 실제 면접 후기에 나온 질문을 웹에서 찾아 주세요.
회사: {company}
직무: {job}

규칙
- 공개된 면접 후기, 기사, 회사 채용 페이지 등에서 '실제로 나왔다'고 적힌 질문만 모읍니다.
- 출처에서 확인되지 않은 질문을 지어내지 마세요. 못 찾으면 빈 목록을 돌려주세요.
- 같은 회사의 다른 직무 질문이면 note 에 그렇게 적습니다.
- 질문은 한국어로 옮겨 적습니다.

반드시 아래 JSON 형식만 출력하세요 (설명 문장, 코드블록 표시 없이):
{{"questions": [{{"question": "...", "source_title": "...", "source_url": "https://...", "year": "알 수 없으면 빈 문자열", "note": "..."}}]}}"""


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"questions": []}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"questions": []}


def collect_real_questions(company: str, job: str) -> dict:
    """반환: {"questions": [...], "citations": [{"title","url"}], "raw": 원문}"""
    res = client().responses.create(
        model=LLM_MODEL,
        tools=[{"type": "web_search"}],
        input=COLLECT_PROMPT.format(company=company, job=job),
    )
    text = res.output_text or ""
    citations = []
    for item in res.output:
        if getattr(item, "type", "") != "message":
            continue
        for content in item.content:
            for ann in getattr(content, "annotations", []) or []:
                if getattr(ann, "type", "") == "url_citation":
                    citations.append({"title": ann.title, "url": ann.url})
    data = _extract_json(text)
    seen, uniq = set(), []
    for c in citations:
        if c["url"] not in seen:
            seen.add(c["url"])
            uniq.append(c)
    return {"questions": data.get("questions", []), "citations": uniq, "raw": text}


# ---------- 4) 예상 질문 생성 ----------
GEN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {"type": "string", "enum": ["인성", "직무", "영어"]},
                    "q": {"type": "string"},
                    "why": {"type": "string", "description": "이 질문이 나올 만한 이유"},
                    "hint": {"type": "string", "description": "답변 뼈대 (정답이 아닌 말하는 순서)"},
                },
                "required": ["type", "q", "why", "hint"],
            },
        }
    },
    "required": ["questions"],
}


def generate_questions(company: str, job: str, region: str, jd: str, background: str,
                       real_questions: list, counts: dict) -> list:
    sys = """당신은 한국 기업 해외영업 채용 면접관입니다. 지원 정보를 보고 실제 면접에서 나올 법한 예상 질문을 만듭니다.
- 회사·직무·지역·채용 공고 내용과 직접 연결된 구체적 질문을 우선합니다.
- 수집된 실제 면접 질문이 있으면 그 경향을 참고하되 똑같이 베끼지 않습니다.
- 지원자 배경이 있으면 그 경험을 파고드는 꼬리 질문도 넣습니다.
- 영어 유형 질문은 '영어로, ~해 보세요' 처럼 한국어로 적습니다.
- hint 에는 정답 대신 답변 뼈대(예: 결론 → 근거 → 경험 → 기여)를 1~2문장으로 씁니다.
  지원자의 경험이나 숫자를 지어내지 말고, 지식 질문이면 핵심 개념만 정확하게 적습니다.
- 모든 글은 한국어로 씁니다."""
    user = {
        "회사": company, "직무": job, "담당 지역": region,
        "채용 공고 내용": jd, "지원자 배경": background,
        "수집된 실제 면접 질문": [q.get("question") for q in real_questions],
        "만들 개수": counts,
    }
    res = client().chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "gen_questions", "strict": True, "schema": GEN_SCHEMA},
        },
    )
    return json.loads(res.choices[0].message.content)["questions"]
