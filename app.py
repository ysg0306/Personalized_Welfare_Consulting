from dotenv import load_dotenv
load_dotenv()  # .env 파일에서 환경 변수를 읽어옵니다.

import os
import streamlit as st
import time
import pandas as pd
from tts_service import generate_policy_tts

# DB 및 AI, LLM 모듈 불러오기
try:
    from db_manager import get_filtered_policies
    from matching_recommend import make_score
    from llm_service import generate_policy_summary          # 공고문 3줄 요약 LLM
    from llm_service_profile import generate_policy_summary as generate_user_profile_summary  # 사용자 프로필 요약 LLM
except ImportError as e:
    st.error(f"필요한 라이브러리/파일을 불러오는 중 오류가 발생했습니다: {e}")

st.set_page_config(
    page_title="맞춤형 복지 컨설팅 서비스",
    layout="wide"
)

st.markdown(
    """
    <style>
        .stApp {
            background: #f4f6f9;
            color: #2c3e50;
        }
        .stButton>button {
            background-color: #5b7a9c;
            color: #ffffff;
            border-radius: 8px;
            border: none;
            font-weight: 600;
        }
        .stButton>button:hover {
            background-color: #415b77;
            border: none;
            color: #ffffff;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
            color: #2c3e50;
        }
        .stProgress > div > div > div > div {
            background-color: #8fa9c4;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("복지 혜택 지능형 컨설팅")
st.subheader("나에게 꼭 맞는 숨은 정부·지자체·대학 혜택을 찾아드립니다.")
st.markdown("---")

# 1. 사용자 정보 입력받기
st.sidebar.header("맞춤 정보 입력")
user_name = st.sidebar.text_input("이름을 입력하세요", value="")
user_age = st.sidebar.slider("나이 (만)", 19, 65, 23)
user_income = st.sidebar.slider("소득 분위 (1~10분위)", 1, 10, 5)

user_region = st.sidebar.selectbox(
    "거주 지역",
    [
        "전국 (공통)", 
        "서울특별시", "부산광역시", "대구광역시", "인천광역시", 
        "광주광역시", "대전광역시", "울산광역시", "세종특별자치시", 
        "경기도", "강원특별자치도", "충청북도", "충청남도", 
        "전북특별자치도", "전라남도", "경상북도", "경상남도", "제주특별자치도"
    ]
)
is_student = st.sidebar.checkbox("대학생 여부", value=True)

# 메인 화면 상단 자유 입력 텍스트
user_text_input = st.text_area(
    "💡 필요한 혜택이나 현재 상황을 자유롭게 입력해 주세요 (선택)", 
    placeholder="예: 자취 중이라 월세 지원이 필요해요. 취업 준비 관련 장학금도 궁금합니다.",
    height=100
).strip()

search_btn = st.sidebar.button("맞춤 혜택 조회하기")

# 2. 버튼 클릭 시 데이터 처리 및 LLM 계산
if search_btn:
    display_name = user_name if user_name else "회원"
    user_profile = {
        "user_name": display_name,
        "user_age": user_age,
        "user_income": user_income,
        "user_region": user_region,
        "is_student": is_student,
        "user_grade": 3,
        "user_text": user_text_input
    }

    with st.spinner("DB 조회 및 AI 추천, LLM 요약 결과를 생성하고 있습니다..."):
        # 프로필 요약
        profile_raw_text = f"이름: {display_name}, 나이: {user_age}세, 거주지: {user_region}, 대학생 여부: {is_student}, 추가 정보: {user_text_input}"
        try:
            profile_summary_list = generate_user_profile_summary(profile_raw_text)
        except Exception:
            profile_summary_list = [f"{user_region}에 거주 중인 {user_age}세 사용자 프로필입니다."]

        # DB 필터링 및 스코어링
        filtered_raw = get_filtered_policies(user_profile)
        if not filtered_raw:
            recommendations = []
        else:
            policy_df = pd.DataFrame(filtered_raw)
            recommendations = make_score(user_profile, policy_df, top_k=3)
            if isinstance(recommendations, pd.DataFrame):
                recommendations = recommendations.to_dict(orient='records')

            # LLM 3줄 요약
            for policy in recommendations:
                original_text = (
                    policy.get('original_content') or policy.get('content') or 
                    policy.get('description') or policy.get('details') or ''
                )
                if original_text and len(str(original_text).strip()) > 20:
                    try:
                        policy['summary'] = generate_policy_summary(str(original_text))
                        time.sleep(0.3)
                    except Exception:
                        clean_text = str(original_text).strip()
                        policy['summary'] = [
                            clean_text[:40] + "..." if len(clean_text) > 40 else clean_text,
                            "자세한 신청 자격 및 서류는 상세 공고를 참고하세요.",
                            "관련 문의는 해당 주관 기관을 통해 확인하실 수 있습니다."
                        ]
                else:
                    policy['summary'] = [
                        f"지원 대상: {policy.get('target', '해당 조건 충족자')}",
                        f"혜택 내용: {policy.get('title', '상세 공고 참고')}",
                        "신청 방법 및 기간은 기관 홈페이지를 확인해 주세요."
                    ]

        # 결과를 세션에 저장
        st.session_state['has_searched'] = True
        st.session_state['display_name'] = display_name
        st.session_state['profile_summary_list'] = profile_summary_list
        st.session_state['recommendations'] = recommendations
        st.session_state['user_text_input'] = user_text_input

if st.session_state.get('has_searched', False):
    display_name = st.session_state.get('display_name', '회원')
    profile_summary_list = st.session_state.get('profile_summary_list', [])
    recommendations = st.session_state.get('recommendations', [])
    user_text_input = st.session_state.get('user_text_input', '')

    st.write(f"###  {display_name}님을 위한 맞춤형 추천 리포트")
    st.info("💡 **AI 프로필 진단**\n\n" + "\n".join([f"• {line}" for line in profile_summary_list]))

    def render_policy_card(policy, idx, prefix):
        title = policy.get('title') or policy.get('policy_name') or '복지 혜택'
        
        raw_score = policy.get('score', 0) or 0
        try:
            raw_score = float(raw_score)
            score = int(raw_score * 100) if 0 < raw_score <= 1.0 else int(raw_score)
        except (ValueError, TypeError):
            score = 0
        
       # 추천 이유가 없거나 기본 문구일 때 점수/순위에 따라 다채롭게 생성
        default_reason = '사용자 프로필 및 입력하신 고민 내용과 가장 잘 일치하는 혜택입니다.'
        current_reason = policy.get('reason')

        if not current_reason or current_reason == default_reason:
            if idx == 0:
                reason = f"입력하신 프로필과 고민 내용({user_text_input if user_text_input else '조건'})에 가장 높은 적합도를 보인 혜택입니다."
            elif idx == 1:
                reason = "사용자의 거주 지역 및 연령 조건에 잘 부합하며 지원 가능성이 높은 혜택입니다."
            else:
                reason = "추가적으로 지원 자격 조건이 일치하여 함께 검토해 볼 만한 추천 복지입니다."
        else:
            reason = current_reason
        
        summary = policy.get('summary', ['세부 내용은 상세 페이지를 확인하세요.'])
        if isinstance(summary, str):
            summary = [summary]

        st.markdown(
            f"""
            <div style='background:#ffffff; border:1px solid #dbe3eb; border-top: 5px solid #8fa9c4; border-radius:12px; padding:22px; margin-bottom:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                <div style='font-size:21px; font-weight:700; color:#2c3e50; margin-bottom:12px;'>{title}</div>
                <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; background:#f0f4f8; padding:8px 12px; border-radius:8px;'>
                    <div style='color:#708090; font-weight:500;'>매칭 적합도</div>
                    <div style='font-size:22px; font-weight:700; color:#4a7496;'>{score}점</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(max(score, 0) / 100.0, 1.0))
        st.markdown(
            f"""
            <div style='background:#ffffff; border-left: 1px solid #dbe3eb; border-right: 1px solid #dbe3eb; border-bottom: 1px solid #dbe3eb; border-radius: 0 0 12px 12px; padding: 22px; margin-top: -30px; margin-bottom: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                <div style='color:#475569; margin-bottom:14px; font-size:15px; line-height:1.5;'><b>추천 이유:</b> {reason}</div>
                <div style='color:#5b7a9c; font-weight:700; margin-bottom:8px; font-size:15px;'>📋 핵심 요약 (AI 3줄 요약)</div>
                <ul style='margin:0; padding-left:18px; color:#475569; font-size:14px; line-height:1.6;'>
                    {''.join(f"<li style='margin-bottom:6px;'>{line}</li>" for line in summary)}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # 각 카드마다 고유한 policy_id 가져오기 (없으면 index 활용)
        policy_id = str(policy.get('id') or policy.get('policy_id') or f"policy_{prefix}_{idx}")
        
        # 버튼 눌렀을 때 동작
        if st.button("🔊 음성 안내 듣기", key=f"tts_btn_{prefix}_{idx}"):
            with st.spinner("🔊 AI가 음성을 생성하는 중입니다..."):
                try:
                    # tts_service.py 함수 실행
                    audio_path = generate_policy_tts(summary, policy_id)
                    
                    # 생성된 MP3 파일이 존재하면 플레이어로 재생
                    if os.path.exists(audio_path):
                        st.session_state[f"audio_{prefix}_{idx}"] = audio_path
                        st.toast("🔊 음성 안내 파일이 생성되었습니다!", icon="✅")
                    else:
                        st.error("음성 파일을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"음성 생성 실패: {e}")

        # 오디오 파일이 이미 생성되어 있다면 플레이어 유지
        saved_audio = st.session_state.get(f"audio_{prefix}_{idx}")
        if saved_audio and os.path.exists(saved_audio):
            st.audio(saved_audio, format="audio/mp3")

    tab1, tab2, tab3 = st.tabs(["✨ 전체 추천", "🏛️ 정부/지자체 혜택", "🏫 대학 혜택"])
    
    with tab1:
        if recommendations:
            col1, col2 = st.columns(2)
            for i, policy in enumerate(recommendations):
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    render_policy_card(policy, i, "all")
        else:
            st.info("추천할 혜택이 없습니다.")

    with tab2:
        gov_policies = [p for p in recommendations if p.get('category', 'government') == 'government']
        if gov_policies:
            col1, col2 = st.columns(2)
            for i, policy in enumerate(gov_policies):
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    render_policy_card(policy, i, "gov")
        else:
            st.info("조건에 맞는 정부/지자체 혜택이 없습니다.")

    with tab3:
        univ_policies = [p for p in recommendations if p.get('category') == 'univ']
        if univ_policies:
            col1, col2 = st.columns(2)
            for i, policy in enumerate(univ_policies):
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    render_policy_card(policy, i, "univ")
        else:
            st.info("조건에 맞는 대학 혜택이 없습니다.")

else:
    st.info("왼쪽 사이드바에서 정보를 입력한 뒤 '맞춤 혜택 조회하기' 버튼을 눌러주세요.")