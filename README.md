Personalized_Welfare_Consulting
나에게 꼭 맞는 숨은 정부·지자체·대학 혜택을 찾아주는 인공지능 기반 복지 컨설팅 서비스입니다.

---
팀원 및 역할 분담
* 신종현: 데이터 크롤링
* 김영준: AI 분석 및 매칭 
* 유승균: 서비스 인터페이스
* 신서원: 데이터베이스
* 김현서: 백엔드 및 웹 화면

> 개발 환경 (Python Version): `3.13.2`

---

실행 방법
이 프로젝트를 로컬 환경에서 실행하려면 아래 명령어를 순서대로 입력하세요.

1. 라이브러리 설치, 실행
```bash
pip install streamlit
```
```bash
streamlit run app.py
```

2. 에이전트 간 공동 데이터 규격
1) 사용자 프로필 데이터 규격(입력 데이터)
```python
user_profile = {
    "user_name": "",          # 문자열 (이름)
    "user_age": 0,               # 정수형 (만 나이)
    "user_income": 0,             # 정수형 (소득 분위, 1~10분위)
    "user_region": "",     # 문자열 (거주 지역 광역시/도 단위)
    "is_student": False           # 불리언 (대학생 여부)
}
```
2) 복지 정책 원본 데이터 규격
```python
policy_data = {
    "policy_id": "",    # 문자열 (고유 정책 식별 ID)
    "title": "", # 문자열 (정책 이름)
    "category": "",   # 문자열 (카테고리 분류)
    "target_age": [0,0],        # 리스트 (대상 연령대 [최소, 최대])
    "target_income": 0,            # 정수형 (대상 최대 소득분위 제한, 이하 조건)
    "target_region": "",      # 문자열 (대상 거주 지역 제한)
    "target_student": None,        # 불리언/None (대학생 제한 여부, 상관없으면 None)
    "original_content": "" # 문자열 (원본 상세 내용)
}
```
3) AI 추천 및 매칭 결과 데이터 규격
```python
# 여러 개의 추천 정책이 담긴 리스트 형태
recommended_policies = [
    {
        "policy_id": "",
        "title": "",
        "score": 0,              # 정수형 (AI가 계산한 매칭 적합도 점수, 0~100)
        "reason": "",            # 문자열 (매칭 추천 이유)
        "summary": [],           # 리스트 (LLM 에이전트가 요약한 핵심 내용 3줄)
        "tts_audio_path": ""     # 문자열 (TTS 에이전트가 생성한 음성 파일 경로)
    }
]
```
