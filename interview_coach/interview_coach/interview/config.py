"""환경 변수(.env)와 기준값을 한곳에서 관리합니다."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# 평가·질문 생성용 모델 (2026-11 기준 OpenAI 문서에서 확인한 저가 모델)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.6-luna").strip()
# 음성 → 글자 변환 모델. whisper-1 은 2027-02-26 종료 예정이라 기본값은 gpt-transcribe
TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-transcribe").strip()

# 녹화 영상을 "저장" 버튼으로 남길 폴더
RECORDINGS_DIR = BASE_DIR / "recordings"
# 평가 기록 자동 저장 파일 (점수·평가 내용만, 영상과 메모는 저장 안 함)
HISTORY_PATH = BASE_DIR / "data" / "history.json"

# 말하기 속도 참고 범위 (검증된 표준이 아니라 연습용 기준값입니다. 필요하면 .env 에서 바꾸세요)
KO_SYLLABLES_PER_MIN = (
    int(os.getenv("KO_SPM_MIN", "260")),
    int(os.getenv("KO_SPM_MAX", "350")),
)
EN_WORDS_PER_MIN = (
    int(os.getenv("EN_WPM_MIN", "120")),
    int(os.getenv("EN_WPM_MAX", "160")),
)

ANSWER_SECONDS = 60
ANSWER_TIME_CHOICES = [60, 90, 120]


def has_api_key() -> bool:
    return bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("여기에")
