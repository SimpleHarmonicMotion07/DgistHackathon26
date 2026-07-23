import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai

from streamlit_option_menu import option_menu

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="DGIST Hackathon", page_icon="🚀")

# 1. 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""


# 2. DB 연결 함수 (에러 방어 로직 추가)
def get_database():
    try:
        # secrets.toml의 정보를 바탕으로 연결 시도
        conn = st.connection("gsheets", type=GSheetsConnection)

        # worksheet 파라미터를 생략하면 기본적으로 첫 번째 시트를 가져옵니다 (Sheet1 / 시트1 오류 방지)
        users_db = conn.read(ttl=0)

        # 데이터프레임에 필수 컬럼이 있는지 확인 (초기 세팅 오류 방지)
        if "id" not in users_db.columns or "password" not in users_db.columns:
            st.error("🚨 구글 시트의 첫 번째 행에 'id', 'name', 'password' 헤더를 작성했는지 확인해주세요.")
            return conn, None

        return conn, users_db

    except Exception as e:
        st.error("🚨 구글 시트 인증/연결에 실패했습니다. 아래 에러 메시지를 확인하세요.")
        st.code(str(e))
        return None, None

# ... (위쪽의 DB 연결 및 로그인 로직은 그대로 유지) ...

# --- 1. 각각의 메뉴 화면을 담당할 함수들 ---

def show_home():
    st.title("🏠 메인 홈 화면")
    st.write("서비스에 오신 것을 환영합니다! 🎉")
    st.info("이곳에는 서비스의 핵심 가치를 설명하는 소개글, 최근 등록된 매칭 인원 요약, 혹은 공지사항 등을 배치하면 좋습니다.")

    # 예시 컴포넌트
    st.metric(label="현재 가입된 DGIST 학생", value="128명", delta="12명 증가")


def show_ugrp_search():
    st.title("🔬 UGRP 매칭 시스템")
    st.write("성공적인 UGRP를 위해, 나의 정보를 등록하고 원하는 팀원/리더를 찾아보세요!")

    # 1. 역할 선택
    role = st.radio("당신의 현재 포지션은 무엇인가요?", ["구성원 (팀을 찾는 중)", "리더 (팀원을 찾는 중)", "팀 (추가 인원 모집 중)"], horizontal=True)

    with st.form("ugrp_form"):
        st.subheader("👤 나의 특성 입력")
        col1, col2 = st.columns(2)
        with col1:
            my_name = st.text_input("이름")
            my_gender = st.selectbox("성별", ["남", "여"])
            my_track = st.selectbox("전공 트랙", ["물리", "화학", "생명", "뇌", "기계", "재료", "전자", "컴퓨터", "화공", "자율"])
        with col2:
            my_time = st.selectbox("주당 투자 가능 시간", ["0~5시간", "5~10시간", "10~15시간", "15시간 이상"])
            my_topic = st.text_input("희망 분야/주제 (구체적으로)")
        my_pr = st.text_area("기타 하고 싶은 말 (자기 PR)")

        st.write("---")

        st.subheader("🤝 선호하는 파트너/팀 조건")
        pref_gender = st.radio("선호 성별", ["남", "여", "상관없음"], horizontal=True)
        pref_headcount = st.multiselect("희망 인원 (복수 선택 가능)", ["3명", "4명", "5명", "6명"])
        pref_track = st.multiselect("선호 트랙 (복수 선택 가능)", ["물리", "화학", "생명", "뇌", "기계", "재료", "전자", "컴퓨터", "화공", "자율"])
        pref_time = st.selectbox("선호하는 주당 투자 시간", ["0~5시간", "5~10시간", "10~15시간", "15시간 이상", "상관없음"])

        submit_btn = st.form_submit_button("매칭 등록 및 탐색 시작")

        if submit_btn:
            # TODO: 여기에 st.connection을 이용해 UGRP_DB 시트에 데이터를 저장(append)하는 로직 추가!
            st.success("데이터가 성공적으로 등록되었습니다! 매칭 알고리즘을 시작합니다.")

@st.cache_data(show_spinner=False)
def get_ai_recommendation_cached(user_info_str, others_info_str, api_key):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    genai.configure(api_key=api_key)

    # 가장 안정적이고 속도가 빠른 플래시 모델 사용
    model = genai.GenerativeModel("gemini-3.5-flash")

    prompt = f"""
    당신은 기숙사 룸메이트 매칭 전문가 AI입니다.
    아래는 현재 로그인한 사용자의 프로필 및 선호 조건입니다:
    {user_info_str}

    아래는 데이터베이스에 등록된 다른 사용자들의 프로필 목록입니다:
    {others_info_str}

    조건:
    1. 로그인한 사용자의 '선호 조건(pref_...)'과 '나의 특성(my_...'을 종합적으로 고려하여 가장 잘 어울리는 상위 최대 5명을 선정해주세요.
    2. 만약 등록된 전체 인원이 5명 미만이라면 있는 만큼만 선정해주세요.
    3. 각 추천 사람별로 이름(my_name), 이메일/아이디(id), 주요 특징 요약, 그리고 추천 이유를 깔끔하게 정리해서 출력해주세요.
    """

    response = model.generate_content(prompt)
    return response.text

def show_roommate_search():
    st.title("🛏️ 기숙사 룸메이트 매칭 & AI 추천")
    st.info("나의 특성과 선호 조건을 입력하고 저장하거나, AI 매칭 추천을 받아보세요!")

    # 1. 구글 시트 연결 객체 생성
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 2. 로그인된 사용자 정보 가져오기
    current_id = st.session_state.get("id", st.session_state.get("username", "unknown_user"))
    current_name = st.session_state.get("name", st.session_state.get("username", "알수없음"))

    # 3. 기존에 DB에 저장해둔 내 데이터가 있다면 불러오기 (자동 채우기용)
    saved_data = {}
    try:
        existing_df = conn.read(worksheet="Roommate_DB", ttl=0)
        if existing_df is not None and not existing_df.empty and "id" in existing_df.columns:
            user_row = existing_df[existing_df["id"] == current_id]
            if not user_row.empty:
                saved_data = user_row.iloc[0].to_dict()
    except Exception:
        pass  # 데이터가 없거나 첫 실행 시 패스

    # 폼 생성: 입력 중 새로고침 방지
    with st.form("roommate_form"):

        # ---------------------------------------------------------
        # 1. 나의 특성 (My Characteristics)
        # ---------------------------------------------------------
        st.subheader("👤 나의 특성 입력")

        col1, col2 = st.columns(2)
        with col1:
            my_age = st.number_input("나이 (my_age)", min_value=18, max_value=30, value=int(saved_data.get("my_age", 20)))
            my_grade = st.number_input("학년 (my_grade)", min_value=1, max_value=4,
                                       value=int(saved_data.get("my_grade", 1)))
        with col2:
            default_gender_idx = 0 if saved_data.get("my_gender") == "남" else (
                1 if saved_data.get("my_gender") == "여" else 0)
            my_gender = st.selectbox("성별 (my_gender)", ["남", "여"], index=default_gender_idx)

            military_options = ["군필", "미필", "면제", "병역 의무 대상 아님"]
            m_val = saved_data.get("my_military", "미필")
            m_idx = military_options.index(m_val) if m_val in military_options else 0
            my_military = st.selectbox("병역 상태 (my_military)", military_options, index=m_idx)

        st.markdown("**생활 습관 및 패턴**")
        col3, col4 = st.columns(2)
        with col3:
            smoke_options = ["무", "유(전담)", "유(연초)"]
            s_val = saved_data.get("my_smoke", "무")
            s_idx = smoke_options.index(s_val) if s_val in smoke_options else 0
            my_smoke = st.selectbox("흡연 여부 (my_smoke)", smoke_options, index=s_idx)

            my_sleep_time = st.text_input("취침/기상 시간 (my_sleep_time)",
                                          value=str(saved_data.get("my_sleep_time", "01:30 ~ 08:00")))

            clean_options = ["한 달에 1번", "3주에 1번", "2주에 1번", "1주에 1번", "1주에 2번 이상"]
            c_val = saved_data.get("my_clean", "1주 1번")
            c_idx = clean_options.index(c_val) if c_val in clean_options else 1
            my_clean = st.selectbox("청소 주기 (my_clean)", clean_options, index=c_idx)

            my_inout_time = st.text_input("출입 시간 (my_inout_time)", value=str(saved_data.get("my_inout_time", "")))

            shower_options = ["아침", "점심", "저녁", "심야"]
            saved_shower = str(saved_data.get("my_shower_time", ""))
            default_showers = [sh.strip() for sh in saved_shower.split(",") if sh.strip() in shower_options]
            my_shower_time = st.multiselect("씻는 시간 (my_shower_time)", shower_options, default=default_showers)

        with col4:
            eat_options = ["전부 가능", "냄새 나는 건 안됨", "전부 안됨"]
            e_val = saved_data.get("my_eat", "전부 가능")
            e_idx = eat_options.index(e_val) if e_val in eat_options else 0
            my_eat = st.selectbox("방 안 음식 섭취 (my_eat)", eat_options, index=e_idx)

            drink_options = ["안마심", "일주일에 1번", "2~3회", "4회 이상"]
            d_val = saved_data.get("my_drink", "안마심")
            d_idx = drink_options.index(d_val) if d_val in drink_options else 0
            my_drink = st.selectbox("음주 여부 (my_drink)", drink_options, index=d_idx)

            my_room_freq = st.text_input("방에 얼마나 자주 있는지 (my_room_freq)", value=str(saved_data.get("my_room_freq", "")))
            my_home_freq = st.text_input("본가 얼마나 자주 가는지 (my_home_freq)", value=str(saved_data.get("my_home_freq", "")))
            my_ac_temp = st.number_input("에어컨 선호 온도 (my_ac_temp)", value=float(saved_data.get("my_ac_temp", 23)))

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
            my_earphone = st.selectbox("이어폰 사용 여부 (my_earphone)", ear_options, index=ear_idx)

            talk_options = ["안함", "가끔", "자주"]
            t_val = saved_data.get("my_talk_alone", "안함")
            t_idx = talk_options.index(t_val) if t_val in talk_options else 0
            my_talk_alone = st.selectbox("혼잣말 여부 (my_talk_alone)", talk_options, index=t_idx)

            fridge_options = ["무", "유"]
            f_val = saved_data.get("my_fridge", "무")
            f_idx = fridge_options.index(f_val) if f_val in fridge_options else 0
            my_fridge = st.selectbox("냉장고 여부 (my_fridge)", fridge_options, index=f_idx)

        with col6:
            snore_options = ["무", "유"]
            sn_val = saved_data.get("my_snore", "무")
            sn_idx = snore_options.index(sn_val) if sn_val in snore_options else 0
            my_snore = st.selectbox("코골이 여부 (my_snore)", snore_options, index=sn_idx)

            sens_options = ["어두움", "밝음"]
            sens_val = saved_data.get("my_sleep_sens", "어두움")
            sens_idx = sens_options.index(sens_val) if sens_val in sens_options else 0
            my_sleep_sens = st.selectbox("잠귀 (my_sleep_sens)", sens_options, index=sens_idx)

            alarm_options = ["바로 듣고 끔", "못들음"]
            al_val = saved_data.get("my_alarm", "바로 듣고 끔")
            al_idx = alarm_options.index(al_val) if al_val in alarm_options else 0
            my_alarm = st.selectbox("알람 소리 (my_alarm)", alarm_options, index=al_idx)

        st.markdown("**상세 정보**")
        my_hobby = st.text_input("취미 (my_hobby)", value=str(saved_data.get("my_hobby", "")))

        dh_yn_options = ["무", "유"]
        dh_val = saved_data.get("my_deep_hobby_yn", "무")
        dh_idx = dh_yn_options.index(dh_val) if dh_val in dh_yn_options else 0
        my_deep_hobby_yn = st.selectbox("딥한 취미 유/무 (my_deep_hobby_yn)", dh_yn_options, index=dh_idx)

        my_deep_hobby_desc = st.text_input("딥한 취미 상세 (있을 경우) (my_deep_hobby_desc)",
                                           value=str(saved_data.get("my_deep_hobby_desc", "")))

        dh_habit_options = ["무", "유"]
        dh_h_val = saved_data.get("my_drink_habit_yn", "무")
        dh_h_idx = dh_habit_options.index(dh_h_val) if dh_h_val in dh_habit_options else 0
        my_drink_habit_yn = st.selectbox("술버릇 여부 (my_drink_habit_yn)", dh_habit_options, index=dh_h_idx)

        my_drink_habit_desc = st.text_input("술버릇 상세 (있을 경우) (my_drink_habit_desc)",
                                            value=str(saved_data.get("my_drink_habit_desc", "")))
        my_pr = st.text_area("기타 사항 / 자기 PR (my_pr)", value=str(saved_data.get("my_pr", "")))

        st.markdown("---")

        # ---------------------------------------------------------
        # 2. 선호하는 특성 (Preference)
        # ---------------------------------------------------------
        st.subheader("🤝 선호하는 룸메이트 조건")

        col7, col8 = st.columns(2)
        with col7:
            pre_age = st.text_input("선호 나이 (pre_age)", value=str(saved_data.get("pre_age", "")))
            pref_grade_ = st.text_input("선호 학년 (pref_grade_)", value=str(saved_data.get("pref_grade_", "")))

            pref_mil_options = ["상관없음", "군필", "미필", "면제", "병역 의무 대상 아님"]
            p_m_val = saved_data.get("pref_military", "상관없음")
            p_m_idx = pref_mil_options.index(p_m_val) if p_m_val in pref_mil_options else 0
            pref_military = st.selectbox("선호 병역 상태 (pref_military)", pref_mil_options, index=p_m_idx)

            pref_smoke_options = ["상관없음", "무", "유(전담)", "유(연초)"]
            p_s_val = saved_data.get("pref_smoke", "상관없음")
            p_s_idx = pref_smoke_options.index(p_s_val) if p_s_val in pref_smoke_options else 0
            pref_smoke = st.selectbox("선호 흡연 여부 (pref_smoke)", pref_smoke_options, index=p_s_idx)

            pref_clean_options = ["상관없음", "한 달에 1번", "3주에 1번", "2주에 1번", "1주에 1번", "1주에 2번 이상"]
            p_c_val = saved_data.get("pref_clean", "상관없음")
            p_c_idx = pref_clean_options.index(p_c_val) if p_c_val in pref_clean_options else 0
            pref_clean = st.selectbox("선호 청소 주기 (pref_clean)", pref_clean_options, index=p_c_idx)

            pref_inout_time = st.text_input("선호 출입 시간 (pref_inout_time)",
                                            value=str(saved_data.get("pref_inout_time", "")))
            pref_shower_time = st.text_input("선호 씻는 시간 (pref_shower_time)",
                                             value=str(saved_data.get("pref_shower_time", "")))
            pref_room_freq = st.text_input("선호 방 체류 빈도 (pref_room_freq)",
                                           value=str(saved_data.get("pref_room_freq", "")))

        with col8:
            pref_eat_options = ["상관없음", "전부 가능", "냄새 나는 건 안됨", "전부 안됨"]
            p_e_val = saved_data.get("pref_eat", "상관없음")
            p_e_idx = pref_eat_options.index(p_e_val) if p_e_val in pref_eat_options else 0
            pref_eat = st.selectbox("선호 방 안 음식 섭취 (pref_eat)", pref_eat_options, index=p_e_idx)

            pref_drink_options = ["상관없음", "안마심", "일주일에 1번", "2~3회", "4회 이상"]
            p_d_val = saved_data.get("pref_drink", "상관없음")
            p_d_idx = pref_drink_options.index(p_d_val) if p_d_val in pref_drink_options else 0
            pref_drink = st.selectbox("선호 음주 여부 (pref_drink)", pref_drink_options, index=p_d_idx)

            pref_sleep_time = st.text_input("선호 취침 및 기상 시간 (pref_sleep_time)",
                                            value=str(saved_data.get("pref_sleep_time", "")))
            pref_home_freq = st.text_input("선호 본가 방문 빈도 (pref_home_freq)",
                                           value=str(saved_data.get("pref_home_freq", "")))
            pref_ac_temp = st.text_input("선호 에어컨 온도 (pref_ac_temp)", value=str(saved_data.get("pref_ac_temp", "")))

            pref_fridge_options = ["상관없음", "무", "유"]
            p_f_val = saved_data.get("pref_fridge", "상관없음")
            p_f_idx = pref_fridge_options.index(p_f_val) if p_f_val in pref_fridge_options else 0
            pref_fridge = st.selectbox("선호 냉장고 여부 (pref_fridge)", pref_fridge_options, index=p_f_idx)

        st.markdown("**소음 및 상세 선호 조건**")
        col9, col10 = st.columns(2)
        with col9:
            pref_game_options = ["상관없음", "무", "유"]
            p_g_val = saved_data.get("pref_game", "상관없음")
            p_g_idx = pref_game_options.index(p_g_val) if p_g_val in pref_game_options else 0
            pref_game = st.selectbox("선호 게임 여부 (pref_game)", pref_game_options, index=p_g_idx)

            pref_ear_options = ["상관없음", "항상 사용", "자주 사용", "상황에 따라 사용", "거의 사용하지 않음"]
            p_ear_val = saved_data.get("pref_earphone", "상관없음")
            p_ear_idx = pref_ear_options.index(p_ear_val) if p_ear_val in pref_ear_options else 0
            pref_earphone = st.selectbox("선호 이어폰 사용 여부 (pref_earphone)", pref_ear_options, index=p_ear_idx)

            pref_talk_options = ["상관없음", "안함", "가끔", "자주"]
            p_t_val = saved_data.get("pref_talk_alone", "상관없음")
            p_t_idx = pref_talk_options.index(p_t_val) if p_t_val in pref_talk_options else 0
            pref_talk_alone = st.selectbox("선호 혼잣말 여부 (pref_talk_alone)", pref_talk_options, index=p_t_idx)

            pref_snore_options = ["상관없음", "무", "유"]
            p_sn_val = saved_data.get("pref_snore", "상관없음")
            p_sn_idx = pref_snore_options.index(p_sn_val) if p_sn_val in pref_snore_options else 0
            pref_snore = st.selectbox("선호 코골이 여부 (pref_snore)", pref_snore_options, index=p_sn_idx)

        with col10:
            pref_sens_options = ["상관없음", "어두움", "밝음"]
            p_sens_val = saved_data.get("pref_sleep_sens", "상관없음")
            p_sens_idx = pref_sens_options.index(p_sens_val) if p_sens_val in pref_sens_options else 0
            pref_sleep_sens = st.selectbox("선호 잠귀 (pref_sleep_sens)", pref_sens_options, index=p_sens_idx)

            pref_alarm_options = ["상관없음", "바로 듣고 끔", "못들음"]
            p_al_val = saved_data.get("pref_alarm", "상관없음")
            p_al_idx = pref_alarm_options.index(p_al_val) if p_al_val in pref_alarm_options else 0
            pref_alarm = st.selectbox("선호 알람 소리 (pref_alarm)", pref_alarm_options, index=p_al_idx)

            pref_dh_options = ["상관없음", "무", "유"]
            p_dh_val = saved_data.get("pref_deep_hobby_yn", "상관없음")
            p_dh_idx = pref_dh_options.index(p_dh_val) if p_dh_val in pref_dh_options else 0
            pref_deep_hobby_yn = st.selectbox("선호 딥한 취미 유/무 (pref_deep_hobby_yn)", pref_dh_options, index=p_dh_idx)

            pref_dh_hab_options = ["상관없음", "무", "유"]
            p_dhh_val = saved_data.get("pref_drink_habit_yn", "상관없음")
            p_dhh_idx = pref_dh_hab_options.index(p_dhh_val) if p_dhh_val in pref_dh_hab_options else 0
            pref_drink_habit_yn = st.selectbox("선호 술버릇 여부 (pref_drink_habit_yn)", pref_dh_hab_options, index=p_dhh_idx)

        pref_hobby = st.text_input("선호 취미 (pref_hobby)", value=str(saved_data.get("pref_hobby", "")))
        pref_deep_hobby_desc = st.text_input("선호 딥한 취미 상세 (pref_deep_hobby_desc)",
                                             value=str(saved_data.get("pref_deep_hobby_desc", "")))
        pref_drink_habit_desc = st.text_input("선호 술버릇 상세 (pref_drink_habit_desc)",
                                              value=str(saved_data.get("pref_drink_habit_desc", "")))

        # 버튼 영역 레이아웃 (저장 버튼 + 조회 버튼)
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("💾 매칭 조건 저장하기", use_container_width=True)
        with btn_col2:
            matched_clicked = st.form_submit_button("🔍 룸메이트 추천받기 (AI)", use_container_width=True)

        # 공통 데이터 딕셔너리 생성 함수
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
                "my_name": current_name,
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
                "pref_ac_temp": pref_ac_temp
            }

        # 1. 저장하기 버튼 클릭 시
        if submitted:
            try:
                new_data = create_new_data()
                existing_data = conn.read(worksheet="Roommate_DB", ttl=0)

                if existing_data is None or existing_data.empty:
                    updated_df = pd.DataFrame([new_data])
                else:
                    if "id" in existing_data.columns and current_id in existing_data["id"].values:
                        existing_data = existing_data[existing_data["id"] != current_id]
                    updated_df = pd.concat([existing_data, pd.DataFrame([new_data])], ignore_index=True)

                conn.update(worksheet="Roommate_DB", data=updated_df)
                st.success("🎉 성공적으로 정보가 저장되었습니다!")
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

        # 2. AI 추천받기 버튼 클릭 시
        if matched_clicked:
            try:
                # 1. 먼저 데이터를 시트에 자동 저장
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

                # 2. 본인을 제외한 다른 사용자 필터링
                other_users_df = updated_df[updated_df["id"] != current_id]

                # 3. 인원 체크 (5명 미만인 경우)
                if other_users_df.empty or len(other_users_df) < 1:
                    st.warning("비어있습니다 (매칭 가능한 다른 사용자가 충분하지 않습니다)")
                else:
                    api_key = st.secrets.get("GEMINI_API_KEY", "")
                    if not api_key:
                        st.error("Gemini API 키가 secrets.toml에 설정되어 있지 않습니다.")
                    else:
                        # 데이터 프레임을 텍스트로 변환
                        user_info_str = str(new_data)
                        others_info_str = other_users_df.to_string()

                        with st.spinner("🤖 Gemini AI가 최적의 룸메이트를 분석 중입니다..."):
                            # 캐시된 함수를 호출하여 429 에러 방지
                            result_text = get_ai_recommendation_cached(
                                user_info_str, others_info_str, api_key
                            )

                        st.markdown("### 🏆 AI 맞춤 룸메이트 추천 결과 (Top 5)")
                        st.write(result_text)

            except Exception as e:
                st.error(f"추천 처리 중 오류가 발생했습니다: {e}")


# --- 2. 메인 페이지 (메뉴 네비게이션) ---

def main_page():
    # 1. 앱을 처음 켰을 때 기본 페이지를 'home'으로 설정
    if 'page' not in st.session_state:
        st.session_state.page = 'home'

    # 사이드바(화면 왼쪽)에 메뉴 구성
    with st.sidebar:
        # 안전한 호출을 위해 .get() 사용 권장
        username = st.session_state.get('username', '사용자')
        st.title(f"반갑습니다,\n**{username}**님! 👋")
        st.write("---")

        st.subheader("📌 메뉴 이동")

        # 2. 버튼 클릭 시 세션 상태(st.session_state.page) 값 변경
        if st.button("🏠 홈 화면", use_container_width=True):
            st.session_state.page = 'home'

        if st.button("🔬 UGRP 인원 탐색", use_container_width=True):
            st.session_state.page = 'ugrp'

        if st.button("🛏️ 기숙사 룸메이트 탐색", use_container_width=True):
            st.session_state.page = 'roommate'

        st.write("---")

        # 로그아웃 버튼
        if st.button("로그아웃", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()

    # 3. 변경된 세션 상태 값에 따라 알맞은 화면 함수를 호출 (라우팅)
    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'ugrp':
        show_ugrp_search()
    elif st.session_state.page == 'roommate':
        show_roommate_search()


# ... (아래쪽의 login_page() 및 앱 라우팅 로직은 그대로 유지) ...

# 4. 로그인 / 회원가입 화면
def login_page():
    st.title("🔐 서비스 로그인")

    # DB 데이터 불러오기 시도
    conn, users_db = get_database()

    # DB 연결에 실패했으면 아래 로직 실행 중단
    if users_db is None:
        st.warning("데이터베이스가 연결되지 않아 로그인 기능을 사용할 수 없습니다.")
        return

    tab_login, tab_signup = st.tabs(["로그인", "회원가입"])

    # --- 로그인 로직 ---
    with tab_login:
        st.subheader("로그인")
        login_id = st.text_input("아이디 (이메일)", key="login_id")
        login_pw = st.text_input("비밀번호", type="password", key="login_pw")

        if st.button("로그인", key="login_btn"):
            if login_id in users_db["id"].values:
                # 유저 정보 추출
                user_info = users_db[users_db["id"] == login_id].iloc[0]

                # DB의 비밀번호에서 무의미한 .0을 제거하고 양옆 공백을 없앰
                db_pw = str(user_info["password"]).replace(".0", "").strip()
                input_pw = str(login_pw).strip()

                if db_pw == input_pw:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = str(user_info["name"])
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
            else:
                st.error("존재하지 않는 아이디입니다.")

    # --- 회원가입 로직 ---
    with tab_signup:
        st.subheader("새로운 계정 만들기")
        signup_id = st.text_input("새 아이디 (이메일)", key="signup_id")
        signup_name = st.text_input("이름 (닉네임)", key="signup_name")
        signup_pw = st.text_input("새 비밀번호", type="password", key="signup_pw")
        signup_pw_check = st.text_input("비밀번호 확인", type="password", key="signup_pw_check")

        if st.button("회원가입", key="signup_btn"):
            if signup_pw != signup_pw_check:
                st.warning("비밀번호가 일치하지 않습니다.")
            elif not signup_id or not signup_pw or not signup_name:
                st.warning("모든 정보를 입력해주세요.")
            elif signup_id in users_db["id"].values:
                st.error("이미 존재하는 아이디입니다.")
            else:
                try:
                    # 새 유저 데이터 생성
                    new_user = pd.DataFrame(
                        [{"id": signup_id, "name": signup_name, "password": signup_pw}]
                    )

                    # 기존 DB에 결합 후 구글 시트 업데이트
                    updated_db = pd.concat([users_db, new_user], ignore_index=True)
                    conn.update(data=updated_db)

                    st.success(f"{signup_name}님, 회원가입이 완료되었습니다! 로그인 탭에서 로그인해주세요.")
                except Exception as e:
                    st.error(f"회원가입 처리 중 오류가 발생했습니다: {e}")




# 5. 앱 라우팅
if st.session_state["logged_in"]:
    main_page()
else:
    login_page()