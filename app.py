import re
import google.generativeai as genai
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="DGIST Hackathon", page_icon="🚀", layout="wide")

# 1. 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "id" not in st.session_state:
    st.session_state["id"] = ""
if "page" not in st.session_state:
    st.session_state.page = "home"
if "match_type" not in st.session_state:
    st.session_state.match_type = "roommate"
if "ai_cards_data" not in st.session_state:
    st.session_state.ai_cards_data = []
if "ai_raw_text" not in st.session_state:
    st.session_state.ai_raw_text = ""


# 2. DB 연결 함수
def get_database():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        users_db = conn.read(ttl=0)
        if "id" not in users_db.columns or "password" not in users_db.columns:
            st.error(
                "🚨 구글 시트의 첫 번째 행에 'id', 'name', 'password' 헤더를 작성했는지"
                " 확인해주세요."
            )
            return conn, None
        return conn, users_db
    except Exception as e:
        st.error("🚨 구글 시트 인증/연결에 실패했습니다.")
        st.code(str(e))
        return None, None


# --- 하이엔드 디자인 및 다이얼로그 팝업 전용 CSS ---
theme_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Outfit:wght@500;700;900&family=Noto+Sans+KR:wght@300;400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Noto Sans KR', sans-serif;
    }

    .dgist-logo {
        font-family: 'Outfit', sans-serif;
        font-size: 3.8rem;
        font-weight: 900;
        color: #1E293B;
        letter-spacing: -1px;
        line-height: 1.1;
        margin-bottom: 0.2rem;
    }
    .dgist-logo span { color: #3D6098; }

    .sub-brand-tag {
        font-size: 0.85rem;
        letter-spacing: 4px;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 1.8rem;
    }

    .chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 1.5rem 0 2.2rem 0;
    }
    .chip {
        background-color: #F1F5F9;
        border: 1.5px solid #CBD5E1;
        padding: 0.5rem 1.2rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #475569;
    }
    .chip-active {
        background-color: #3D6098;
        border: 1.5px solid #3D6098;
        color: #FFFFFF;
    }

    /* 결과 카드 디자인 (5개 병렬 배치용) */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        background-color: #F8FAFC !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 20px !important;
        padding: 1.2rem 1rem 1.2rem 1rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 25px !important;
        height: 3.2em;
        background-color: #3D6098 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
    }
    div.stButton > button:hover {
        background-color: #2F4A75 !important;
        color: #FFFFFF !important;
    }
</style>
"""


# --- 1. 홈 화면 ---
def show_home():
    st.markdown(theme_css, unsafe_allow_html=True)
    st.markdown(
        "<div class='dgist-logo'>dgist<span>.</span>match</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='sub-brand-tag'>Campus Life & Research Matching</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
      <div class='chip-container'>
          <div class='chip chip-active'>DGIST Official</div>
          <div class='chip'>Smart Matching</div>
          <div class='chip'>Roommate Service</div>
          <div class='chip'>AI Analytics</div>
      </div>
      """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(
            """
            <div style='font-size: 1.4rem; font-weight: 800; color: #1E293B; margin-bottom: 0.5rem;'>🏠 룸메이트 매칭</div>
            <div style='color: #64748B; font-size: 0.92rem; line-height: 1.6; margin-bottom: 1.5rem;'>
                생활관 취침 시간, 수면 습관, 청소 스타일 데이터를 분석하여 나에게 가장 어울리는 동반자를 찾습니다.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("ROOMMATE START ➔", key="btn_home_roommate"):
            st.session_state.match_type = "roommate"
            st.session_state.page = "roommate"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div style='font-size: 1.4rem; font-weight: 800; color: #1E293B; margin-bottom: 0.5rem;'>🔬 UGRP 연구팀 구성</div>
            <div style='color: #64748B; font-size: 0.92rem; line-height: 1.6; margin-bottom: 1.5rem;'>
                희망 연구 트랙과 본인의 주 역량을 분석하여 최적의 연구 시너지를 맞춰드립니다.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("UGRP TEAM START ➔", key="btn_home_ugrp"):
            st.session_state.match_type = "ugrp"
            st.session_state.page = "ugrp"
            st.rerun()


# --- 2. UGRP 탐색 화면 ---
def show_ugrp_search():
    st.markdown(theme_css, unsafe_allow_html=True)
    st.title("🔬 UGRP 매칭 시스템")
    st.write(
        "성공적인 UGRP를 위해, 나의 정보를 등록하고 원하는 팀원/리더를"
        " 찾아보세요!"
    )
    if st.button("← 홈으로 돌아가기"):
        st.session_state.page = "home"
        st.rerun()


# --- 3. 룸메이트 입력 및 AI 추천 화면 ---
@st.cache_data(show_spinner=False)
def get_ai_recommendation_cached(user_info_str, others_info_str, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    prompt = f"""
    당신은 기숙사 룸메이트 매칭 전문가 AI입니다.
    아래는 현재 로그인한 사용자의 프로필 및 선호 조건입니다:
    {user_info_str}

    아래는 데이터베이스에 등록된 다른 사용자들의 프로필 목록입니다:
    {others_info_str}

    조건:
    1. 로그인한 사용자의 '선호 조건'과 '나의 특성'을 종합적으로 고려하여 가장 잘 어울리는 상위 5명을 선정해주세요. 무조건 5명입니다.
    2. 각 추천 사람별 출력 포맷은 반드시 아래와 같이 한 줄씩 작성해주세요:
    [이름] [이메일/아이디] [추천 이유 요약]
    예시: 삼건우 shin_kunwoo@university.ac.kr 흡연하지 않고 음주 습관이 없으며 패턴이 잘 부합합니다.
    """
    response = model.generate_content(prompt)
    return response.text


def show_roommate_search():
    st.markdown(theme_css, unsafe_allow_html=True)
    st.title("🛏️ 기숙사 룸메이트 매칭 & AI 추천")
    st.info(
        "나의 특성과 선호 조건을 입력하고 저장하거나, AI 매칭 추천을 받아보세요!"
    )

    conn = st.connection("gsheets", type=GSheetsConnection)
    current_id = st.session_state.get("id", "unknown_user")
    current_name = st.session_state.get("username", "알수없음")

    saved_data = {}
    try:
        existing_df = conn.read(worksheet="Roommate_DB", ttl=0)
        if (
                existing_df is not None
                and not existing_df.empty
                and "id" in existing_df.columns
        ):
            user_row = existing_df[existing_df["id"] == current_id]
            if not user_row.empty:
                saved_data = user_row.iloc[0].to_dict()
    except Exception:
        pass

    with st.form("roommate_form"):
        st.subheader("👤 나의 특성 입력")

        col1, col2 = st.columns(2)
        with col1:
            my_age = st.number_input(
                "나이 (my_age)",
                min_value=18,
                max_value=30,
                value=int(saved_data.get("my_age", 20)),
            )
            my_grade = st.number_input(
                "학년 (my_grade)",
                min_value=1,
                max_value=4,
                value=int(saved_data.get("my_grade", 1)),
            )
        with col2:
            default_gender_idx = (
                0
                if saved_data.get("my_gender") == "남"
                else (1 if saved_data.get("my_gender") == "여" else 0)
            )
            my_gender = st.selectbox(
                "성별 (my_gender)", ["남", "여"], index=default_gender_idx
            )

            military_options = ["군필", "미필", "면제", "병역 의무 대상 아님"]
            m_val = saved_data.get("my_military", "미필")
            m_idx = military_options.index(m_val) if m_val in military_options else 0
            my_military = st.selectbox(
                "병역 상태 (my_military)", military_options, index=m_idx
            )

        st.markdown("**생활 습관 및 패턴**")
        col3, col4 = st.columns(2)
        with col3:
            smoke_options = ["무", "유(전담)", "유(연초)"]
            s_val = saved_data.get("my_smoke", "무")
            s_idx = smoke_options.index(s_val) if s_val in smoke_options else 0
            my_smoke = st.selectbox("흡연 여부 (my_smoke)", smoke_options, index=s_idx)

            my_sleep_time = st.text_input(
                "취침/기상 시간 (my_sleep_time)",
                value=str(saved_data.get("my_sleep_time", "01:30 ~ 08:00")),
            )

            clean_options = [
                "한 달에 1번",
                "3주에 1번",
                "2주에 1번",
                "1주에 1번",
                "1주에 2번 이상",
            ]
            c_val = saved_data.get("my_clean", "1주 1번")
            c_idx = clean_options.index(c_val) if c_val in clean_options else 1
            my_clean = st.selectbox("청소 주기 (my_clean)", clean_options, index=c_idx)

            my_inout_time = st.text_input(
                "출입 시간 (my_inout_time)", value=str(saved_data.get("my_inout_time", ""))
            )

            shower_options = ["아침", "점심", "저녁", "심야"]
            saved_shower = str(saved_data.get("my_shower_time", ""))
            default_showers = [
                sh.strip()
                for sh in saved_shower.split(",")
                if sh.strip() in shower_options
            ]
            my_shower_time = st.multiselect(
                "씻는 시간 (my_shower_time)", shower_options, default=default_showers
            )

        with col4:
            eat_options = ["전부 가능", "냄새 나는 건 안됨", "전부 안됨"]
            e_val = saved_data.get("my_eat", "전부 가능")
            e_idx = eat_options.index(e_val) if e_val in eat_options else 0
            my_eat = st.selectbox("방 안 음식 섭취 (my_eat)", eat_options, index=e_idx)

            drink_options = ["안마심", "일주일에 1번", "2~3회", "4회 이상"]
            d_val = saved_data.get("my_drink", "안마심")
            d_idx = drink_options.index(d_val) if d_val in drink_options else 0
            my_drink = st.selectbox("음주 여부 (my_drink)", drink_options, index=d_idx)

            my_room_freq = st.text_input(
                "방에 얼마나 자주 있는지 (my_room_freq)",
                value=str(saved_data.get("my_room_freq", "")),
            )
            my_home_freq = st.text_input(
                "본가 얼마나 자주 가는지 (my_home_freq)",
                value=str(saved_data.get("my_home_freq", "")),
            )
            my_ac_temp = st.number_input(
                "에어컨 선호 온도 (my_ac_temp)",
                value=float(saved_data.get("my_ac_temp", 23)),
            )

        st.markdown("**소음 및 기타 특성**")
        col5, col6 = st.columns(2)
        with col5:
            game_options = ["무", "유 (키보드/디코 등)"]
            g_val = saved_data.get("my_game", "무")
            g_idx = game_options.index(g_val) if g_val in game_options else 0
            my_game = st.selectbox("게임 여부 (my_game)", game_options, index=g_idx)

            ear_options = ["항상 사용", "자주 사용", "상황에 따라 사용", "거의 사용하지 않음"]
            ear_val = saved_data.get("my_earphone", "항상 사용")
            ear_idx = ear_options.index(ear_val) if ear_val in ear_options else 0
            my_earphone = st.selectbox(
                "이어폰 사용 여부 (my_earphone)", ear_options, index=ear_idx
            )

            talk_options = ["안함", "가끔", "자주"]
            t_val = saved_data.get("my_talk_alone", "안함")
            t_idx = talk_options.index(t_val) if t_val in talk_options else 0
            my_talk_alone = st.selectbox(
                "혼잣말 여부 (my_talk_alone)", talk_options, index=t_idx
            )

            fridge_options = ["무", "유"]
            f_val = saved_data.get("my_fridge", "무")
            f_idx = fridge_options.index(f_val) if f_val in fridge_options else 0
            my_fridge = st.selectbox(
                "냉장고 여부 (my_fridge)", fridge_options, index=f_idx
            )

        with col6:
            snore_options = ["무", "유"]
            sn_val = saved_data.get("my_snore", "무")
            sn_idx = snore_options.index(sn_val) if sn_val in snore_options else 0
            my_snore = st.selectbox(
                "코골이 여부 (my_snore)", snore_options, index=sn_idx
            )

            sens_options = ["어두움", "밝음"]
            sens_val = saved_data.get("my_sleep_sens", "어두움")
            sens_idx = sens_options.index(sens_val) if sens_val in sens_options else 0
            my_sleep_sens = st.selectbox(
                "잠귀 (my_sleep_sens)", sens_options, index=sens_idx
            )

            alarm_options = ["바로 듣고 끔", "못들음"]
            al_val = saved_data.get("my_alarm", "바로 듣고 끔")
            al_idx = alarm_options.index(al_val) if al_val in alarm_options else 0
            my_alarm = st.selectbox("알람 소리 (my_alarm)", alarm_options, index=al_idx)

        st.markdown("**상세 정보**")
        my_hobby = st.text_input(
            "취미 (my_hobby)", value=str(saved_data.get("my_hobby", ""))
        )

        dh_yn_options = ["무", "유"]
        dh_val = saved_data.get("my_deep_hobby_yn", "무")
        dh_idx = dh_yn_options.index(dh_val) if dh_val in dh_yn_options else 0
        my_deep_hobby_yn = st.selectbox(
            "딥한 취미 유/무 (my_deep_hobby_yn)", dh_yn_options, index=dh_idx
        )

        my_deep_hobby_desc = st.text_input(
            "딥한 취미 상세 (있을 경우) (my_deep_hobby_desc)",
            value=str(saved_data.get("my_deep_hobby_desc", "")),
        )

        dh_habit_options = ["무", "유"]
        dh_h_val = saved_data.get("my_drink_habit_yn", "무")
        dh_h_idx = (
            dh_habit_options.index(dh_h_val) if dh_h_val in dh_habit_options else 0
        )
        my_drink_habit_yn = st.selectbox(
            "술버릇 여부 (my_drink_habit_yn)", dh_habit_options, index=dh_h_idx
        )

        my_drink_habit_desc = st.text_input(
            "술버릇 상세 (있을 경우) (my_drink_habit_desc)",
            value=str(saved_data.get("my_drink_habit_desc", "")),
        )
        my_pr = st.text_area(
            "기타 사항 / 자기 PR (my_pr)", value=str(saved_data.get("my_pr", ""))
        )

        st.markdown("---")
        st.subheader("🤝 선호하는 룸메이트 조건")

        col7, col8 = st.columns(2)
        with col7:
            pre_age = st.text_input(
                "선호 나이 (pre_age)", value=str(saved_data.get("pre_age", ""))
            )
            pref_grade_ = st.text_input(
                "선호 학년 (pref_grade_)", value=str(saved_data.get("pref_grade_", ""))
            )

            pref_mil_options = ["상관없음", "군필", "미필", "면제", "병역 의무 대상 아님"]
            p_m_val = saved_data.get("pref_military", "상관없음")
            p_m_idx = (
                pref_mil_options.index(p_m_val)
                if p_m_val in pref_mil_options
                else 0
            )
            pref_military = st.selectbox(
                "선호 병역 상태 (pref_military)", pref_mil_options, index=p_m_idx
            )

            pref_smoke_options = ["상관없음", "무", "유(전담)", "유(연초)"]
            p_s_val = saved_data.get("pref_smoke", "상관없음")
            p_s_idx = (
                pref_smoke_options.index(p_s_val)
                if p_s_val in pref_smoke_options
                else 0
            )
            pref_smoke = st.selectbox(
                "선호 흡연 여부 (pref_smoke)", pref_smoke_options, index=p_s_idx
            )

            pref_clean_options = [
                "상관없음",
                "한 달에 1번",
                "3주에 1번",
                "2주에 1번",
                "1주에 1번",
                "1주에 2번 이상",
            ]
            p_c_val = saved_data.get("pref_clean", "상관없음")
            p_c_idx = (
                pref_clean_options.index(p_c_val)
                if p_c_val in pref_clean_options
                else 0
            )
            pref_clean = st.selectbox(
                "선호 청소 주기 (pref_clean)", pref_clean_options, index=p_c_idx
            )

            pref_inout_time = st.text_input(
                "선호 출입 시간 (pref_inout_time)",
                value=str(saved_data.get("pref_inout_time", "")),
            )
            pref_shower_time = st.text_input(
                "선호 씻는 시간 (pref_shower_time)",
                value=str(saved_data.get("pref_shower_time", "")),
            )
            pref_room_freq = st.text_input(
                "선호 방 체류 빈도 (pref_room_freq)",
                value=str(saved_data.get("pref_room_freq", "")),
            )

        with col8:
            pref_eat_options = ["상관없음", "전부 가능", "냄새 나는 건 안됨", "전부 안됨"]
            p_e_val = saved_data.get("pref_eat", "상관없음")
            p_e_idx = pref_eat_options.index(p_e_val) if p_e_val in pref_eat_options else 0
            pref_eat = st.selectbox(
                "선호 방 안 음식 섭취 (pref_eat)", pref_eat_options, index=p_e_idx
            )

            pref_drink_options = ["상관없음", "안마심", "일주일에 1번", "2~3회", "4회 이상"]
            p_d_val = saved_data.get("pref_drink", "상관없음")
            p_d_idx = (
                pref_drink_options.index(p_d_val)
                if p_d_val in pref_drink_options
                else 0
            )
            pref_drink = st.selectbox(
                "선호 음주 여부 (pref_drink)", pref_drink_options, index=p_d_idx
            )

            pref_sleep_time = st.text_input(
                "선호 취침 및 기상 시간 (pref_sleep_time)",
                value=str(saved_data.get("pref_sleep_time", "")),
            )
            pref_home_freq = st.text_input(
                "선호 본가 방문 빈도 (pref_home_freq)",
                value=str(saved_data.get("pref_home_freq", "")),
            )
            pref_ac_temp = st.text_input(
                "선호 에어컨 온도 (pref_ac_temp)",
                value=str(saved_data.get("pref_ac_temp", "")),
            )

            pref_fridge_options = ["상관없음", "무", "유"]
            p_f_val = saved_data.get("pref_fridge", "상관없음")
            p_f_idx = (
                pref_fridge_options.index(p_f_val)
                if p_f_val in pref_fridge_options
                else 0
            )
            pref_fridge = st.selectbox(
                "선호 냉장고 여부 (pref_fridge)", pref_fridge_options, index=p_f_idx
            )

        st.markdown("**소음 및 상세 선호 조건**")
        col9, col10 = st.columns(2)
        with col9:
            pref_game_options = ["상관없음", "무", "유"]
            p_g_val = saved_data.get("pref_game", "상관없음")
            p_g_idx = (
                pref_game_options.index(p_g_val)
                if p_g_val in pref_game_options
                else 0
            )
            pref_game = st.selectbox(
                "선호 게임 여부 (pref_game)", pref_game_options, index=p_g_idx
            )

            pref_ear_options = [
                "상관없음",
                "항상 사용",
                "자주 사용",
                "상황에 따라 사용",
                "거의 사용하지 않음",
            ]
            p_ear_val = saved_data.get("pref_earphone", "상관없음")
            p_ear_idx = (
                pref_ear_options.index(p_ear_val)
                if p_ear_val in pref_ear_options
                else 0
            )
            pref_earphone = st.selectbox(
                "선호 이어폰 사용 여부 (pref_earphone)", pref_ear_options, index=p_ear_idx
            )

            pref_talk_options = ["상관없음", "안함", "가끔", "자주"]
            p_t_val = saved_data.get("pref_talk_alone", "상관없음")
            p_t_idx = (
                pref_talk_options.index(p_t_val)
                if p_t_val in pref_talk_options
                else 0
            )
            pref_talk_alone = st.selectbox(
                "선호 혼잣말 여부 (pref_talk_alone)", pref_talk_options, index=p_t_idx
            )

            pref_snore_options = ["상관없음", "무", "유"]
            p_sn_val = saved_data.get("pref_snore", "상관없음")
            p_sn_idx = (
                pref_snore_options.index(p_sn_val)
                if p_sn_val in pref_snore_options
                else 0
            )
            pref_snore = st.selectbox(
                "선호 코골이 여부 (pref_snore)", pref_snore_options, index=p_sn_idx
            )

        with col10:
            pref_sens_options = ["상관없음", "어두움", "밝음"]
            p_sens_val = saved_data.get("pref_sleep_sens", "상관없음")
            p_sens_idx = (
                pref_sens_options.index(p_sens_val)
                if p_sens_val in pref_sens_options
                else 0
            )
            pref_sleep_sens = st.selectbox(
                "선호 잠귀 (pref_sleep_sens)", pref_sens_options, index=p_sens_idx
            )

            pref_alarm_options = ["상관없음", "바로 듣고 끔", "못들음"]
            p_al_val = saved_data.get("pref_alarm", "상관없음")
            p_al_idx = (
                pref_alarm_options.index(p_al_val)
                if p_al_val in pref_alarm_options
                else 0
            )
            pref_alarm = st.selectbox(
                "선호 알람 소리 (pref_alarm)", pref_alarm_options, index=p_al_idx
            )

            pref_dh_options = ["상관없음", "무", "유"]
            p_dh_val = saved_data.get("pref_deep_hobby_yn", "상관없음")
            p_dh_idx = (
                pref_dh_options.index(p_dh_val) if p_dh_val in pref_dh_options else 0
            )
            pref_deep_hobby_yn = st.selectbox(
                "선호 딥한 취미 유/무 (pref_deep_hobby_yn)",
                pref_dh_options,
                index=p_dh_idx,
            )

            pref_dh_hab_options = ["상관없음", "무", "유"]
            p_dhh_val = saved_data.get("pref_drink_habit_yn", "상관없음")
            p_dhh_idx = (
                pref_dh_hab_options.index(p_dhh_val)
                if p_dhh_val in pref_dh_hab_options
                else 0
            )
            pref_drink_habit_yn = st.selectbox(
                "선호 술버릇 여부 (pref_drink_habit_yn)",
                pref_dh_hab_options,
                index=p_dhh_idx,
            )

        pref_hobby = st.text_input(
            "선호 취미 (pref_hobby)", value=str(saved_data.get("pref_hobby", ""))
        )
        pref_deep_hobby_desc = st.text_input(
            "선호 딥한 취미 상세 (pref_deep_hobby_desc)",
            value=str(saved_data.get("pref_deep_hobby_desc", "")),
        )
        pref_drink_habit_desc = st.text_input(
            "선호 술버릇 상세 (pref_drink_habit_desc)",
            value=str(saved_data.get("pref_drink_habit_desc", "")),
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button(
                "💾 매칭 조건 저장하기", use_container_width=True
            )
        with btn_col2:
            matched_clicked = st.form_submit_button(
                "🔍 룸메이트 추천받기 (AI)", use_container_width=True
            )

        def create_new_data():
            return {
                "id": current_id,
                "my_gender": my_gender,
                "my_smoke": my_smoke,
                "my_sleep_time": my_sleep_time,
                "my_military": my_military,
                "my_clean": my_clean,
                "my_game": my_game,
                "my_earphone": my_earphone,
                "my_talk_alone": my_talk_alone,
                "my_snore": my_snore,
                "my_sleep_sens": my_sleep_sens,
                "my_alarm": my_alarm,
                "my_inout_time": my_inout_time,
                "my_shower_time": ", ".join(my_shower_time),
                "my_deep_hobby_yn": my_deep_hobby_yn,
                "my_eat": my_eat,
                "my_drink": my_drink,
                "my_drink_habit_yn": my_drink_habit_yn,
                "my_fridge": my_fridge,
                "my_name": current_name,  # 시트 첫 번째 페이지 로그인 정보에서 가져온 정확한 이름!
                "my_age": my_age,
                "my_grade": my_grade,
                "my_hobby": my_hobby,
                "my_deep_hobby_desc": my_deep_hobby_desc,
                "my_drink_habit_desc": my_drink_habit_desc,
                "my_room_freq": my_room_freq,
                "my_home_freq": my_home_freq,
                "my_ac_temp": my_ac_temp,
                "my_pr": my_pr,
                "pref_smoke": pref_smoke,
                "pref_sleep_time": pref_sleep_time,
                "pref_military": pref_military,
                "pref_clean": pref_clean,
                "pref_game": pref_game,
                "pref_earphone": pref_earphone,
                "pref_talk_alone": pref_talk_alone,
                "pref_snore": pref_snore,
                "pref_sleep_sens": pref_sleep_sens,
                "pref_alarm": pref_alarm,
                "pref_inout_time": pref_inout_time,
                "pref_shower_time": pref_shower_time,
                "pref_deep_hobby_yn": pref_deep_hobby_yn,
                "pref_eat": pref_eat,
                "pref_drink": pref_drink,
                "pref_drink_habit_yn": pref_drink_habit_yn,
                "pref_fridge": pref_fridge,
                "pre_age": pre_age,
                "pref_grade_": pref_grade_,
                "pref_hobby": pref_hobby,
                "pref_deep_hobby_desc": pref_deep_hobby_desc,
                "pref_drink_habit_desc": pref_drink_habit_desc,
                "pref_room_freq": pref_room_freq,
                "pref_home_freq": pref_home_freq,
                "pref_ac_temp": pref_ac_temp,
            }

        if submitted:
            try:
                new_data = create_new_data()
                existing_data = conn.read(worksheet="Roommate_DB", ttl=0)
                if existing_data is None or existing_data.empty:
                    updated_df = pd.DataFrame([new_data])
                else:
                    if (
                            "id" in existing_data.columns
                            and current_id in existing_data["id"].values
                    ):
                        existing_data = existing_data[existing_data["id"] != current_id]
                    updated_df = pd.concat(
                        [existing_data, pd.DataFrame([new_data])], ignore_index=True
                    )
                conn.update(worksheet="Roommate_DB", data=updated_df)
                st.success("🎉 성공적으로 정보가 저장되었습니다!")
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

        if matched_clicked:
            try:
                new_data = create_new_data()
                existing_data = conn.read(worksheet="Roommate_DB", ttl=0)
                if existing_data is None or existing_data.empty:
                    updated_df = pd.DataFrame([new_data])
                else:
                    if (
                            "id" in existing_data.columns
                            and current_id in existing_data["id"].values
                    ):
                        existing_data = existing_data[existing_data["id"] != current_id]
                    updated_df = pd.concat(
                        [existing_data, pd.DataFrame([new_data])], ignore_index=True
                    )
                conn.update(worksheet="Roommate_DB", data=updated_df)

                other_users_df = updated_df[updated_df["id"] != current_id]
                if other_users_df.empty or len(other_users_df) < 1:
                    st.warning(
                        "비어있습니다 (매칭 가능한 다른 사용자가 충분하지 않습니다)"
                    )
                else:
                    api_key = st.secrets.get("GEMINI_API_KEY", "")
                    if not api_key:
                        st.error("Gemini API 키가 secrets.toml에 설정되어 있지 않습니다.")
                    else:
                        with st.spinner("🤖 Gemini AI가 최적의 룸메이트를 분석 중입니다..."):
                            # AI 추천 함수 호출 (요청하신 대로 [이름] [이메일] [추천이유] 포맷 적용)
                            result_text = get_ai_recommendation_cached(
                                str(new_data), other_users_df.to_string(), api_key
                            )

                        st.session_state.ai_raw_text = result_text

                        parsed_cards = []
                        lines = result_text.strip().split("\n")

                        for i, line in enumerate(lines[:5]):
                            parts = line.split(" ", 2)
                            candidate_name = parts[0] if len(parts) >= 0 else f"후보 {i + 1}"
                            matched_row = other_users_df[
                                other_users_df["my_name"]
                                .astype(str)
                                .str.contains(candidate_name, na=False)
                            ]
                            user_details = (
                                matched_row.iloc[0].to_dict()
                                if not matched_row.empty
                                else {}
                            )

                            if len(parts) >= 3:
                                parsed_cards.append({
                                    "name": parts[0],
                                    "email": parts[1],
                                    "desc": parts[2],
                                    "details": user_details,
                                })
                            else:
                                parsed_cards.append({
                                    "name": f"후보 {i + 1}",
                                    "email": "contact@university.ac.kr",
                                    "desc": line,
                                    "details": user_details,
                                })

                        st.session_state.ai_cards_data = parsed_cards
                        st.session_state.page = "result"
                        st.rerun()

            except Exception as e:
                st.error(f"추천 처리 중 오류가 발생했습니다: {e}")

    if st.button("← 홈으로 돌아가기"):
        st.session_state.page = "home"
        st.rerun()


# --- 세부정보 팝업 다이얼로그 함수 ---
@st.dialog("📋 후보 세부 프로필 및 자기소개")
def show_detail_dialog(c):
    st.subheader(f"👤 {c['name']} 님의 상세 정보")
    st.write(f"📧 **이메일(ID):** {c['email']}")
    st.write("---")

    details = c.get("details", {})
    if details:
        st.markdown("### 🔹 라이프스타일 및 특성")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write(f"- **나이:** {details.get('my_age', '정보 없음')}")
            st.write(f"- **학년:** {details.get('my_grade', '정보 없음')}")
            st.write(f"- **성별:** {details.get('my_gender', '정보 없음')}")
            st.write(f"- **병역 상태:** {details.get('my_military', '정보 없음')}")
            st.write(f"- **흡연 여부:** {details.get('my_smoke', '정보 없음')}")
            st.write(f"- **취침/기상:** {details.get('my_sleep_time', '정보 없음')}")
        with col_d2:
            st.write(f"- **청소 주기:** {details.get('my_clean', '정보 없음')}")
            st.write(f"- **방 안 음식:** {details.get('my_eat', '정보 없음')}")
            st.write(f"- **음주 여부:** {details.get('my_drink', '정보 없음')}")
            st.write(f"- **에어컨 온도:** {details.get('my_ac_temp', '정보 없음')}℃")
            st.write(f"- **취미:** {details.get('my_hobby', '정보 없음')}")

        st.markdown("### 📝 자기 PR 및 기타 사항")
        st.info(
            details.get("my_pr", "작성된 자기 PR 내용이 없습니다.")
            if details.get("my_pr")
            else "작성된 자기 PR 내용이 없습니다."
        )
    else:
        st.info("해당 사용자의 상세 설문 데이터가 데이터베이스에 없습니다.")

    if st.button("닫기", use_container_width=True):
        st.rerun()


# --- 4. 추천 결과 화면 ---
def show_result():
    st.markdown(theme_css, unsafe_allow_html=True)
    st.markdown(
        "<div class='dgist-logo'>match<span>.</span>result</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h2 style='color:#1E293B; font-weight:800;"
        f" margin-top:0.5rem;'>{st.session_state.get('username', '사용자')}님을"
        " 위한 AI 룸메이트 추천 리스트</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#64748B; margin-bottom: 2rem;'>Gemini AI가 라이프스타일과"
        " 선호 조건을 분석하여 선정한 상위 5개 프로필입니다.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("✨ Gemini AI 심층 분석 리포트 전체 보기", expanded=False):
        st.write(st.session_state.ai_raw_text)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    cards = st.session_state.ai_cards_data
    if not cards:
        st.warning("표시할 추천 데이터가 없습니다. 다시 시도해 주세요.")
    else:
        cols = st.columns(5, gap="small")
        for idx, c in enumerate(cards):
            if idx < len(cols):
                with cols[idx]:
                    st.markdown(
                        f"""
                        <div style='font-size: 1.15rem; font-weight: 800; color: #1E293B; margin-bottom: 0.2rem;'>{c['name']}</div>
                        <div style='color: #3D6098; font-size: 0.72rem; font-weight: 700; margin-bottom: 0.8rem; word-break: break-all;'>{c['email']}</div>
                        <div style='color: #475569; font-size: 0.82rem; line-height: 1.4; margin-bottom: 1rem; min-height: 5.2em;'>"{c['desc']}"</div>
                    """,
                        unsafe_allow_html=True,
                    )
                    if st.button("세부정보 보기", key=f"detail_btn_{idx}"):
                        show_detail_dialog(c)

    st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("← 룸메이트 조건 입력 화면으로"):
            st.session_state.page = "roommate"
            st.rerun()
    with col_b2:
        if st.button("🏠 메인 홈으로 돌아가기"):
            st.session_state.page = "home"
            st.rerun()


# --- 5. 메인 네비게이션 및 로그인 분기 ---
def main_page():
    with st.sidebar:
        username = st.session_state.get("username", "사용자")
        st.title(f"반갑습니다,\n**{username}**님! 👋")
        st.write("---")
        st.subheader("📌 메뉴 이동")

        if st.button("🏠 홈 화면", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
        if st.button("🔬 UGRP 인원 탐색", use_container_width=True):
            st.session_state.page = "ugrp"
            st.rerun()
        if st.button("🛏️ 기숙사 룸메이트 탐색", use_container_width=True):
            st.session_state.page = "roommate"
            st.rerun()

        st.write("---")
        if st.button("로그아웃", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["id"] = ""
            st.rerun()

    if st.session_state.page == "home":
        show_home()
    elif st.session_state.page == "ugrp":
        show_ugrp_search()
    elif st.session_state.page == "roommate":
        show_roommate_search()
    elif st.session_state.page == "result":
        show_result()


def login_page():
    st.title("🔐 서비스 로그인")
    conn, users_db = get_database()
    if users_db is None:
        st.warning("데이터베이스가 연결되지 않았습니다.")
        return

    tab_login, tab_signup = st.tabs(["로그인", "회원가입"])
    with tab_login:
        st.subheader("로그인")
        login_id = st.text_input("아이디 (이메일)", key="login_id")
        login_pw = st.text_input("비밀번호", type="password", key="login_pw")

        if st.button("로그인", key="login_btn"):
            if login_id in users_db["id"].values:
                user_info = users_db[users_db["id"] == login_id].iloc[0]
                db_pw = str(user_info["password"]).replace(".0", "").strip()
                if db_pw == str(login_pw).strip():
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = str(user_info["name"])  # 이름 저장!
                    st.session_state["id"] = login_id  # 이메일 저장!
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
            else:
                st.error("존재하지 않는 아이디입니다.")

    with tab_signup:
        st.subheader("새로운 계정 만들기")
        signup_id = st.text_input("새 아이디 (이메일)", key="signup_id")
        signup_name = st.text_input("이름 (닉네임)", key="signup_name")
        signup_pw = st.text_input("새 비밀번호", type="password", key="signup_pw")
        signup_pw_check = st.text_input(
            "비밀번호 확인", type="password", key="signup_pw_check"
        )

        if st.button("회원가입", key="signup_btn"):
            if signup_pw != signup_pw_check:
                st.warning("비밀번호가 일치하지 않습니다.")
            elif not signup_id or not signup_pw or not signup_name:
                st.warning("모든 정보를 입력해주세요.")
            elif signup_id in users_db["id"].values:
                st.error("이미 존재하는 아이디입니다.")
            else:
                try:
                    new_user = pd.DataFrame(
                        [{"id": signup_id, "name": signup_name, "password": signup_pw}]
                    )
                    updated_db = pd.concat([users_db, new_user], ignore_index=True)
                    conn.update(data=updated_db)
                    st.success("회원가입 완료! 로그인 탭에서 로그인해주세요.")
                except Exception as e:
                    st.error(f"오류 발생: {e}")


# 앱 실행 분기
if st.session_state["logged_in"]:
    main_page()
else:
    login_page()