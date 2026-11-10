"""습관어(음, 어, um, uh 등) 검출.

- 확실한 습관어: 뜻 없이 시간을 끄는 소리 (음, 어, 아, um, uh ...)
- 의심 습관어: 정상 단어로도 쓰여서 문맥을 봐야 하는 말 (그, 저, 이제, 약간, like ...)
  → 의심 습관어는 점수에 반만 반영하고 따로 보여 줍니다.

주의: 음성 인식 모델은 습관어를 지우고 받아 적는 경향이 있습니다.
인식 프롬프트로 최대한 남기게 하지만 실제보다 적게 잡힐 수 있습니다.
"""
import re
from collections import Counter

SURE_FILLERS = {
    "음", "으음", "음음", "어", "어어", "으", "아", "에", "엄", "흠",
    "um", "umm", "uh", "uhh", "er", "erm", "ah", "eh", "hmm", "a",
}
MAYBE_FILLERS = {
    "그", "저", "뭐", "이제", "약간", "막", "그러니까", "그니까", "좀", "그냥",
    "like", "so", "basically", "actually",
}
MAYBE_PHRASES = ["you know", "i mean", "kind of", "sort of"]

TOKEN_RE = re.compile(r"[가-힣]+|[a-zA-Z']+")

# 음성 인식 모델에 주는 힌트: 습관어를 지우지 말고 들리는 대로 적게 함
TRANSCRIBE_PROMPT_KO = "음, 어, 그, 저, 이제, 약간... 습관어와 말 더듬음도 들리는 그대로 받아 적습니다."
TRANSCRIBE_PROMPT_EN = "Um, uh, er, ah, like, you know... Transcribe filler words and hesitations exactly as spoken."


def count_fillers(text: str) -> dict:
    lowered = text.lower()
    tokens = TOKEN_RE.findall(lowered)
    sure = Counter(t for t in tokens if t in SURE_FILLERS)
    maybe = Counter(t for t in tokens if t in MAYBE_FILLERS)
    for phrase in MAYBE_PHRASES:
        n = len(re.findall(r"\b" + re.escape(phrase) + r"\b", lowered))
        if n:
            maybe[phrase] += n
    return {
        "sure": dict(sure.most_common()),
        "maybe": dict(maybe.most_common()),
        "sure_total": sum(sure.values()),
        "maybe_total": sum(maybe.values()),
        "token_total": len(tokens),
    }


def count_units(text: str, lang: str) -> int:
    """말하기 속도 계산용 단위 수. 한국어는 음절(한글 글자 수), 영어는 단어 수."""
    if lang == "ko":
        return len(re.findall(r"[가-힣]", text))
    return len(re.findall(r"[a-zA-Z']+", text))
