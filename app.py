import streamlit as st
import time

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

dummy_policies = [
    {
        "title": "청년 기본소득 지원금",
        "score": 95,
        "category": "government",
        "summary": ["경기도 거주 만 19~24세 청년 대상", "분기별 25만 원(연 최대 100만 원) 지역화폐 지급", "신청 기간: 11월 중"],
        "reason": "사용자님의 나이(만 23세)와 경기도 거주 요건을 완벽하게 만족합니다!"
    },
    {
        "title": "대학생 국가 장학금 Ⅱ유형",
        "score": 88,
        "category": "univ",
        "summary": ["소득분위 8분위 이하 대학생 대상", "대학별 자체 기준에 따라 등록금 범위 내 지원", "학자금 지원구간 심사 완료 필요"],
        "reason": f"사용자님의 소득분위({user_income}분위) 및 대학생 조건에 부합하여 매칭률이 높습니다."
    }
]

if search_btn:
    display_name = user_name if user_name else "회원"
    st.write(f"###  {display_name}님을 위한 맞춤형 추천 리포트")
    
    with st.spinner("추천 결과를 정리하고 있습니다..."):
        time.sleep(1.5)
    
    tab1, tab2, tab3 = st.tabs(["✨ 전체 추천", "🏛️ 정부/지자체 혜택", "🏫 대학 혜택"])
    
    with tab1:
        col1, col2 = st.columns(2)
        for i, policy in enumerate(dummy_policies):
            target_col = col1 if i % 2 == 0 else col2
            with target_col:
                st.markdown(
                    f"""
                    <div style='background:#ffffff; border:1px solid #dbe3eb; border-top: 5px solid #8fa9c4; border-radius:12px; padding:22px; margin-bottom:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                        <div style='font-size:21px; font-weight:700; color:#2c3e50; margin-bottom:12px;'>{policy['title']}</div>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; background:#f0f4f8; padding:8px 12px; border-radius:8px;'>
                            <div style='color:#708090; font-weight:500;'>매칭 적합도</div>
                            <div style='font-size:22px; font-weight:700; color:#4a7496;'>{policy['score']}점</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(policy['score'] / 100)
                st.markdown(
                    f"""
                    <div style='background:#ffffff; border-left: 1px solid #dbe3eb; border-right: 1px solid #dbe3eb; border-bottom: 1px solid #dbe3eb; border-radius: 0 0 12px 12px; padding: 22px; margin-top: -30px; margin-bottom: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                        <div style='color:#475569; margin-bottom:14px; font-size:15px; line-height:1.5;'><b>추천 이유:</b> {policy['reason']}</div>
                        <div style='color:#5b7a9c; font-weight:700; margin-bottom:8px; font-size:15px;'>📋 핵심 요약</div>
                        <ul style='margin:0; padding-left:18px; color:#475569; font-size:14px; line-height:1.6;'>
                            {''.join(f"<li style='margin-bottom:6px;'>{line}</li>" for line in policy['summary'])}
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("🔊 음성 안내 듣기", key=f"tts_all_{i}"):
                    st.success("음성 안내를 준비 중입니다. (추후 연동 예정)")
                    
    with tab2:
        gov_policies = [p for p in dummy_policies if p['category'] == 'government']
        if gov_policies:
            col1, col2 = st.columns(2)
            for i, policy in enumerate(gov_policies):
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    st.markdown(
                        f"""
                        <div style='background:#ffffff; border:1px solid #dbe3eb; border-top: 5px solid #8fa9c4; border-radius:12px; padding:22px; margin-bottom:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                            <div style='font-size:21px; font-weight:700; color:#2c3e50; margin-bottom:12px;'>{policy['title']}</div>
                            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; background:#f0f4f8; padding:8px 12px; border-radius:8px;'>
                                <div style='color:#708090; font-weight:500;'>매칭 적합도</div>
                                <div style='font-size:22px; font-weight:700; color:#4a7496;'>{policy['score']}점</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.progress(policy['score'] / 100)
                    st.markdown(
                        f"""
                        <div style='background:#ffffff; border-left: 1px solid #dbe3eb; border-right: 1px solid #dbe3eb; border-bottom: 1px solid #dbe3eb; border-radius: 0 0 12px 12px; padding: 22px; margin-top: -30px; margin-bottom: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                            <div style='color:#475569; margin-bottom:14px; font-size:15px; line-height:1.5;'><b>추천 이유:</b> {policy['reason']}</div>
                            <div style='color:#5b7a9c; font-weight:700; margin-bottom:8px; font-size:15px;'>📋 핵심 요약</div>
                            <ul style='margin:0; padding-left:18px; color:#475569; font-size:14px; line-height:1.6;'>
                                {''.join(f"<li style='margin-bottom:6px;'>{line}</li>" for line in policy['summary'])}
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("🔊 음성 안내 듣기", key=f"tts_gov_{i}"):
                        st.success("음성 안내를 준비 중입니다. (추후 연동 예정)")
        else:
            st.info("조건에 맞는 정부/지자체 혜택이 없습니다.")

    with tab3:
        univ_policies = [p for p in dummy_policies if p['category'] == 'univ']
        if univ_policies:
            col1, col2 = st.columns(2)
            for i, policy in enumerate(univ_policies):
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    st.markdown(
                        f"""
                        <div style='background:#ffffff; border:1px solid #dbe3eb; border-top: 5px solid #8fa9c4; border-radius:12px; padding:22px; margin-bottom:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                            <div style='font-size:21px; font-weight:700; color:#2c3e50; margin-bottom:12px;'>{policy['title']}</div>
                            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; background:#f0f4f8; padding:8px 12px; border-radius:8px;'>
                                <div style='color:#708090; font-weight:500;'>매칭 적합도</div>
                                <div style='font-size:22px; font-weight:700; color:#4a7496;'>{policy['score']}점</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.progress(policy['score'] / 100)
                    st.markdown(
                        f"""
                        <div style='background:#ffffff; border-left: 1px solid #dbe3eb; border-right: 1px solid #dbe3eb; border-bottom: 1px solid #dbe3eb; border-radius: 0 0 12px 12px; padding: 22px; margin-top: -30px; margin-bottom: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                            <div style='color:#475569; margin-bottom:14px; font-size:15px; line-height:1.5;'><b>추천 이유:</b> {policy['reason']}</div>
                            <div style='color:#5b7a9c; font-weight:700; margin-bottom:8px; font-size:15px;'>📋 핵심 요약</div>
                            <ul style='margin:0; padding-left:18px; color:#475569; font-size:14px; line-height:1.6;'>
                                {''.join(f"<li style='margin-bottom:6px;'>{line}</li>" for line in policy['summary'])}
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("🔊 음성 안내 듣기", key=f"tts_univ_{i}"):
                        st.success("음성 안내를 준비 중입니다. (추후 연동 예정)")
        else:
            st.info("조건에 맞는 대학 혜택이 없습니다.")
else:
    st.info("왼쪽 사이드바에서 정보를 입력한 뒤 '맞춤 혜택 조회하기' 버튼을 눌러주세요.")