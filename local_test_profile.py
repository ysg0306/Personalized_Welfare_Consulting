import os
from dotenv import load_dotenv
from llm_service_profile import generate_policy_summary
from tts_service import generate_policy_tts

# 테스트용 인데 이거 수정해서 프론트 엔드에 쓰면 될듯
# 1. .env 파일에 적어둔 API 키들을 시스템 환경변수로 가져옵니다.
load_dotenv()

# 테스트용 공고문
test_notice = """
    "user_name": "홍길동"
    "user_age": 22
    "user_income": 6
    "user_region": "경기도"
    "is_student": Ture

취업을 하기 위해 자격증을 따고 싶어 하지만 돈이 부족해서 자격증 관련 제도 정보를 원해 

"""

def run_integration_test():
    print("파이썬 연동 테스트를 시작합니다! (Groq 전용 버전)")
    print("--------------------------------------------------")
    
    # .env 파일에 입력한 Groq API 키가 제대로 읽히는지 확인합니다.
    groq_key = os.getenv("GROQ_API_KEY")
    print("Groq API 키 읽기 성공 여부:", bool(groq_key))
    print("--------------------------------------------------")
    
    # API 제공자를 그록(groq)으로 고정합니다.
    api_provider = "groq"
    
    print("1단계: AI(Groq)를 통해 프로필 요약 중입니다...")
    try:
        # llm_service에서 요약 함수 호출 (Groq 사용)
        summary_list = generate_policy_summary(test_notice, provider=api_provider)
        
        print("\n[프로필 2줄 요약 결과 수신 완료]")
        for i, line in enumerate(summary_list):
            print(f"  {i+1}번째 줄: {line}")
        print("--------------------------------------------------")
        
        
        
    except Exception as error:
        print("\n[테스트 중 에러 발생] 아래 에러 원인을 확인해 주세요:")
        print(error)

if __name__ == "__main__":
    run_integration_test()
