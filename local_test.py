import os
from dotenv import load_dotenv
from llm_service import generate_policy_summary
from tts_service import generate_policy_tts

# 테스트용 인데 이거 수정해서 프론트 엔드에 쓰면 될듯
# 1. .env 파일에 적어둔 API 키들을 시스템 환경변수로 가져옵니다.
load_dotenv()

# 테스트용 공고문
test_notice = "동두천시 청년 전세자금 대출이자 지원 사업 대상자는 관내에 주민등록을 둔 만 19세 이상 39세 이하의 무주택 청년 가구주이며, 소득 기준은 기준 중위소득 180% 이하입니다. 혜택 내용으로는 대출 잔액의 1% 범위 내에서 연간 최대 100만 원까지 대출 이자를 지원받을 수 있습니다. 신청 기간은 2026년 9월 1일부터 9월 15일까지 청년 정책 플랫폼을 통해 접수할 수 있습니다."

def run_integration_test():
    print("파이썬 연동 테스트를 시작합니다! (Groq 전용 버전)")
    print("--------------------------------------------------")
    
    # .env 파일에 입력한 Groq API 키가 제대로 읽히는지 확인합니다.
    groq_key = os.getenv("GROQ_API_KEY")
    print("Groq API 키 읽기 성공 여부:", bool(groq_key))
    print("--------------------------------------------------")
    
    # API 제공자를 그록(groq)으로 고정합니다.
    api_provider = "groq"
    
    print("1단계: AI(Groq)를 통해 복잡한 공고문을 쉬운 3줄 요약으로 정제하는 중입니다...")
    try:
        # llm_service에서 요약 함수 호출 (Groq 사용)
        summary_list = generate_policy_summary(test_notice, provider=api_provider)
        
        print("\n[AI 3줄 요약 결과 수신 완료]")
        for i, line in enumerate(summary_list):
            print(f"  {i+1}번째 줄: {line}")
        print("--------------------------------------------------")
        
        print("2단계: 요약된 내용을 읽어주는 친절한 MP3 음성 파일을 생성하는 중입니다...")
        # tts_service에서 음성 생성 함수 호출
        audio_file_path = generate_policy_tts(summary_list, "dongducheon_youth_policy")
        
        print("\n[음성 파일 생성 완료]")
        print("파일 저장 경로:", audio_file_path)
        print("파일이 폴더에 실제로 존재합니까?:", os.path.exists(audio_file_path))
        print("--------------------------------------------------")
        print("축하합니다! Groq 기반 요약과 음성 생성이 완벽하게 연동되었습니다!")
        
    except Exception as error:
        print("\n[테스트 중 에러 발생] 아래 에러 원인을 확인해 주세요:")
        print(error)

if __name__ == "__main__":
    run_integration_test()
