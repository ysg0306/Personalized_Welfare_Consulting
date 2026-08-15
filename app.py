import streamlit as st
import time
import pandas as pd

#DB 및 AI 모듈 불러오기
try:
    from db_manager import get_filtered_policies
    from matching_recommend import make_score
except ImportError:
    st.error("db_manager.py 또는 matching_recommend.py 파일이 같은 폴더에 있는지 확인해주세요!")

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

search_btn = st.sidebar.button("맞춤 혜택 조회하기")

# 버튼을 눌렀을 때 실제 DB 및 AI 작동
if search_btn:
    display_name = user_name if user_name else "회원"
    st.write(f"###  {display_name}님을 위한 맞춤형 추천 리포트")
    
    with st.spinner("DB 조회 및 AI 추천 결과를 계산하고 있습니다..."):
        # 1. 사용자 프로필 딕셔너리 생성
        user_profile = {
            "user_age": user_age,
            "user_income": user_income,
            "user_region": user_region,
            "is_student": is_student,
            "user_grade": 3  # 기본값
        }
        
        # 2. 1차 필터링
        filtered_raw = get_filtered_policies(user_profile)
        
        
        if not filtered_raw:
            st.warning("조건에 맞는 복지 혜택이 없습니다.")
            recommendations = []
        else:
            # 3. 유사도 계산 상위 3개 추천
            policy_df = pd.DataFrame(filtered_raw)
            recommendations = make_score(user_profile, policy_df, top_k=3)
            
            # DataFrame 형태면 리스트(dict) 형태로 변환
            if isinstance(recommendations, pd.DataFrame):
                recommendations = recommendations.to_dict(orient='records')

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["✨ 전체 추천", "🏛️ 정부/지자체 혜택", "🏫 대학 혜택"])
    
    # 공통 추천 카드 출력 함수
    def render_policy_card(policy, idx, prefix):
        title = policy.get('title', policy.get('policy_name', '복지 혜택'))
        score = policy.get('score', 80)
        reason = policy.get('reason', '사용자 프로필과 매칭되는 혜택입니다.')
        
        # summary가 리스트가 아닐 경우 처리
        summary = policy.get('summary', ['세부 내용은 상세 페이지를 확인하세요.'])
        if isinstance(summary, str):
            summary = [summary]

        st.markdown(
            f"""
            <div style='background:#ffffff; border:1px solid #dbe3eb; border-top: 5px solid #8fa9c4; border-radius:12px; padding:22px; margin-bottom:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                <div style='font-size:21px; font-weight:700; color:#2c3e50; margin-bottom:12px;'>{title}</div>
                <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; background:#f0f4f8; padding:8px 12px; border-radius:8px;'>
                    <div style='color:#708090; font-weight:500;'>매칭 적합도</div>
                    <div style='font-size:22px; font-weight:700; color:#4a7496;'>{int(score)}점</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(int(score) / 100.0, 1.0))
        st.markdown(
            f"""
            <div style='background:#ffffff; border-left: 1px solid #dbe3eb; border-right: 1px solid #dbe3eb; border-bottom: 1px solid #dbe3eb; border-radius: 0 0 12px 12px; padding: 22px; margin-top: -30px; margin-bottom: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                <div style='color:#475569; margin-bottom:14px; font-size:15px; line-height:1.5;'><b>추천 이유:</b> {reason}</div>
                <div style='color:#5b7a9c; font-weight:700; margin-bottom:8px; font-size:15px;'>📋 핵심 요약</div>
                <ul style='margin:0; padding-left:18px; color:#475569; font-size:14px; line-height:1.6;'>
                    {''.join(f"<li style='margin-bottom:6px;'>{line}</li>" for line in summary)}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔊 음성 안내 듣기", key=f"tts_{prefix}_{idx}"):
            st.success("음성 안내를 준비 중입니다. (추후 연동 예정)")

    # 탭 1: 전체 추천
    with tab1:
        if recommendations:
            col1, col2 = st.columns(2)
            for i, policy in enumerate(recommendations):
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    render_policy_card(policy, i, "all")
        else:
            st.info("추천할 혜택이 없습니다.")

    # 탭 2: 정부/지자체
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

    # 탭 3: 대학 혜택
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