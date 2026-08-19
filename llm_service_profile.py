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
    "너는 '나에게 꼭 맞는 숨은 정부·지자체·대학 혜택을 찾아주는 인공지능 기반 복지 컨설팅 서비스'의 프로필 요약 전문 AI야. "
        "제공된 사용자의 기본 프로필 데이터(User Profile)와 추가 정보(Additional Info)를 분석하여, 프로필 카드나 대시보드에 들어갈 담백하고 직관적인 자기소개 요약 문장을 만들어야 해."
    
        "반드시 다음 작성 원칙과 JSON 형식을 철저히 준수해줘:"
    
        "[분량 및 구성 원칙]"
        "1. 추가 정보(Additional Info)가 없거나 비어 있는 경우: 반드시 단 1개의 문장(리스트의 요소 1개)만 생성."
        "2. 추가 정보(Additional Info)가 입력되어 있는 경우: 반드시 2개의 문장(리스트의 요소 2개)으로 나누어 작성."
    
        "[각 문장의 포함 내용 및 어조]" 
        "1. 첫 번째 줄 (기본 인적사항 프로필):"
        "- 사용자의 이름, 나이, 거주지역, 대학생/신분 여부를 조합하여 객관적이고 명확한 프로필 소개 문장으로 작성."
        "- '~를 위한 맞춤형 혜택입니다' 같은 서비스 안내용 표현은 완전히 제외할 것."
        '- 예: "경기도에 거주하는 22세 대학생 홍길동이다." 또는 "마포구에 거주 중인 24세 대학생 홍길동이다." '
    
        "2. 두 번째 줄 (관심사 및 상황 요약):"
        "- 추가 정보가 제공되었을 때만 작성하며, 관심 분야, 소득 수준, 희망 지원 내용의 핵심을 간결하게 요약."
        "- 존칭(~계시며, ~하십니다)을 쓰지 않고, 자기소개/상황 서술형 어미(~희망하며, ~관심을 갖고 있다, ~준비 중이다 등)로 작성."
        '- 예: "취업을 위한 자격증 취득을 희망하며, 응시료 및 교육비 지원 제도에 관심을 갖고 있다."'
    
        "[출력 형식]"
        "다른 서론이나 부연 설명 없이, 오직 아래의 JSON 형식으로만 결과를 반환할 것:"
        '{    "profile_summary": ["첫 번째 요약 문장","두 번째 요약 문장 (추가 정보가 있을 때만 포함)"]}'
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
    """LLM이 반환한 텍스트에서 JSON을 파싱하여 2줄 요약 리스트를 추출합니다. 실패 시 대비책을 포함합니다."""
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
        
        summary_list = data.get("profile_summary") or data.get("summary")
        if isinstance(summary_list, list) and summary_list:
            return [str(item).strip() for item in summary_list if str(item).strip()][:2]
    except Exception:
        pass

    # JSON 파싱 실패 시 정규식 및 줄바꿈으로 파킹을 시도하는 예외 대응 로직 (Fallback)
    lines = [line.strip() for line in re.split(r'[\n\r]+', text) if line.strip()]
    cleaned_lines = []
    for line in lines:
        sub_line = re.sub(r'^[-*•\d\.\s]+', '', line).strip()
        if sub_line:
            cleaned_lines.append(sub_line)
    return cleaned_lines[:2]


def generate_policy_summary(original_content: str, provider: str = "groq") -> List[str]:
    """
    프로필을 1~2줄로 요약합니다.
    (기존 코드와의 호환성을 위해 provider 매개변수를 유지하되, 내부적으로는 Groq만 사용합니다.)
    
    :param original_content: 프로필 데이터
    :param provider: 사용할 LLM API 제공자 (호환성 유지용, 항상 Groq로 동작)
    :return: 2줄 요약 문자열 리스트 ["1줄", "2줄"]
    """
    if not original_content or not original_content.strip():
        return [
            "프로필이 비어있습니다"
        ]

    client = _get_groq_client()
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SUMMARY},
                {"role": "user", "content": f"프로필을 2줄로 요약해줘:\n\n{original_content}"}
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
