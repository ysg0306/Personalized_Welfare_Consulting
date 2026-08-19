import os
import json
import re
from typing import List, Dict, Any

try:
    from groq import Groq
except ImportError:
    Groq = None

DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT_SUMMARY = (
    "너는 복잡한 정부, 지자체, 대학교 복지 혜택 공고문을 대학생과 정보 취약계층(노년층, 다문화 가정 등)이 "
    "한눈에 이해할 수 있도록 아주 친절하고 명확하게 요약하는 배리어프리(Barrier-free) 전문 AI 컨설턴트야.\n\n"
    "다음 원칙을 반드시 지켜서 3줄 요약을 JSON 형식으로 작성해줘:\n"
    "1. 쉬운 단어 사용: 어려운 행정 전문 용어, 한자어, 복잡한 법률 어투는 버리고 누구나 이해할 수 있는 일상 언어로 바꾸어 작성해줘. "
    "(예: '수혜 대상자' -> '혜택을 받는 사람', '소득분위 편차' -> '가구 소득 수준')\n"
    "2. 구조적인 정보 배치:\n"
    "   - 첫 번째 줄: 지원 대상 (누가 신청할 수 있는지 구체적으로)\n"
    "   - 두 번째 줄: 혜택 내용 (무엇을 지원받을 수 있는지 금액이나 혜택 중심으로)\n"
    "   - 세 번째 줄: 신청 방법 및 기간 (언제 어떻게 신청하는지 간결하게)\n"
    "3. 종결 어미: 정보 취약계층이 읽고 들을 때 편안함을 느끼도록 부드럽고 정중한 어조(~입니다, ~받으세요 등)를 사용해줘.\n"
    "4. 분량 제한: 한 줄당 너무 길지 않게(공백 포함 30~50자 내외) 리스닝(TTS)에 최적화된 호흡으로 정리해줘.\n\n"
    "반드시 아래 JSON 형식으로만 응답해줘. 다른 텍스트는 절대 포함하지 마:\n"
    '{\n  "summary": [\n    "첫 번째 요약 문장",\n    "두 번째 요약 문장",\n    "세 번째 요약 문장"\n  ]\n}'
)

def _get_groq_client() -> "Groq":
    """Groq 클라이언트를 초기화하여 반환합니다."""
    if Groq is None:
        raise ImportError("groq 패키지가 설치되지 않았습니다. 'pip install groq'를 실행해 주세요.")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY 환경 변수가 설정되지 않았습니다.")
    return Groq(api_key=api_key)

def _parse_summary_json(text: str) -> List[str]:
    """LLM이 반환한 텍스트에서 JSON을 파싱하여 3줄 요약 리스트를 추출합니다. 실패 시 대비책을 포함합니다."""
    clean_text = text.strip()
    # 마크다운 코드 블록 기호 제거
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        data = json.loads(clean_text)
        if isinstance(data, dict) and "summary" in data and isinstance(data["summary"], list):
            res = [str(item) for item in data["summary"]]
            while len(res) < 3:
                res.append("상세 공고 내용을 확인해 주세요.")
            return res[:3]
    except Exception:
        pass

    # JSON 파싱 실패 시 정규식 및 줄바꿈으로 파킹을 시도하는 예외 대응 로직 (Fallback)
    lines = [line.strip() for line in re.split(r'[\n\r]+', text) if line.strip()]
    cleaned_lines = []
    for line in lines:
        sub_line = re.sub(r'^[-*•\d\.\s]+', '', line).strip()
        if sub_line:
            cleaned_lines.append(sub_line)
            
    while len(cleaned_lines) < 3:
        cleaned_lines.append("상세 정보를 확인해 주세요.")
    return cleaned_lines[:3]


def generate_policy_summary(original_content: str, provider: str = "groq") -> List[str]:
    """
    제공된 정책 원문(original_content)을 3줄로 배리어프리 요약합니다.
    (기존 코드와의 호환성을 위해 provider 매개변수를 유지하되, 내부적으로는 Groq만 사용합니다.)
    
    :param original_content: 복지 공고문 텍스트 원문
    :param provider: 사용할 LLM API 제공자 (호환성 유지용, 항상 Groq로 동작)
    :return: 3줄 요약 문자열 리스트 ["1줄", "2줄", "3줄"]
    """
    if not original_content or not original_content.strip():
        return [
            "제공된 공고문 내용이 비어 있습니다.",
            "신청 대상을 다시 확인해 주세요.",
            "해당 기관이나 학교에 직접 문의해 보시는 것을 추천합니다."
        ]

    client = _get_groq_client()
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SUMMARY},
                {"role": "user", "content": f"다음 복지 공고문을 3줄로 요약해줘:\n\n{original_content}"}
            ],
            model=DEFAULT_GROQ_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"}  # Groq JSON 모드 활성화
        )
        response_text = chat_completion.choices[0].message.content
        return _parse_summary_json(response_text)
    except Exception as e:
        print(f"[Groq Error] {e}")
        raise e


def policy_chatbot_response(original_content: str, chat_history: List[Dict[str, str]], user_question: str, provider: str = "groq") -> str:
    """
    해당 복지 공고(original_content)를 바탕으로 사용자가 던진 질문(user_question)에 답변합니다.
    (기존 코드와의 호환성을 위해 provider 매개변수를 유지하되, 내부적으로는 Groq만 사용합니다.)
    
    :param original_content: 복지 공고문 텍스트 원문
    :param chat_history: 이전 대화 내역 리스트 [{"role": "user"/"assistant", "content": "..."}]
    :param user_question: 사용자의 새로운 질문
    :param provider: 사용할 LLM API 제공자 (호환성 유지용, 항상 Groq로 동작)
    :return: 챗봇 답변 문자열
    """
    system_prompt = (
        "너는 사용자가 선택한 특정 복지 정책에 대해 친절하게 답변해주는 맞춤형 챗봇 도우미야.\n"
        "반드시 아래에 제공된 [선택된 복지 정책 원문]에 근거해서만 사실적으로 답변해야 해. "
        "절대로 지어내거나 추측해서 답하지 말고, 원문에 없는 내용이라면 '공고문에는 나와 있지 않으니 해당 주관 기관에 확인이 필요합니다'라고 솔직하고 친절하게 안내해줘.\n\n"
        "답변 어조는 부드럽고 다정하게 존댓말을 사용하고, 정보 취약계층을 배려해 문장을 너무 길고 복잡하게 쓰지 마.\n\n"
        f"[선택된 복지 정책 원문]\n{original_content}"
    )

    client = _get_groq_client()
    messages = [{"role": "system", "content": system_prompt}]
    for chat in chat_history:
        messages.append({"role": chat["role"], "content": chat["content"]})
    messages.append({"role": "user", "content": user_question})
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=DEFAULT_GROQ_MODEL,
            temperature=0.3,
            max_tokens=800
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"[Groq Chatbot Error] {e}")
        raise e
