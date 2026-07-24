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
    st.session_state.ai_raw_text = []
if "ugrp_ai_cards_data" not in st.session_state:
    st.session_state.ugrp_ai_cards_data = []
if "ugrp_ai_raw_text" not in st.session_state:
    st.session_state.ugrp_ai_raw_text = ""


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


# --- 2. UGRP 탐색 및 AI 추천 화면 ---
@st.cache_data(show_spinner=False)
def get_ugrp_ai_recommendation_cached(my_team_str, other_teams_str, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    prompt = f"""
    당신은 DGIST UGRP(Undergraduate Group Research Program) 연구팀 매칭 전문가 AI입니다.
    아래는 현재 로그인한 사용자의 '우리 팀' 정보 및 팀 PR입니다:
    {my_team_str}

    아래는 데이터베이스에 등록된 '다른 팀들'의 정보 목록입니다 (합병 시 총인원이 6명을 넘지 않는 팀들만 엄선됨):
    {other_teams_str}

    조건:
    1. 우리 팀의 연구 주제와 팀 PR, 다른 팀들의 연구 방향과 팀 PR을 종합적으로 비교하여 가장 연구 시너지가 잘 맞고 합병하기 좋은 상위 다른 팀(팀장 ID 기준)을 최대 5개 선정해주세요.
    2. 각 추천 팀별 출력 포맷은 반드시 아래와 같이 한 줄씩 작성해주세요:
    [팀장닉네임/이름] [팀장아이디/이메일] [추천 및 합병 시너지 이유 요약]
    예시: 홍길동 leader1@dgist.ac.kr AI 기반 헬스케어 주제가 일치하며 인원 합병 시 완벽한 시너지가 기대됩니다.
    정보를 전달하는 텍스트 이외의 텍스트들은 출력을 금지합니다.
    """
    response = model.generate_content(prompt)
    return response.text


def show_ugrp_search():
    st.title("🔬 DGIST UGRP 팀원 모집 및 AI 매칭 시스템")
    st.info("팀장 본인을 포함하여 함께 연구할 팀원들의 정보를 입력하고 저장하거나, 인원 제한(합산 최대 6명)을 만족하는 최적의 다른 연구팀을 AI로 추천받으세요!")

    try:
        conn, users_db = get_database()
        if users_db is None or users_db.empty:
            st.error("회원 데이터베이스를 불러올 수 없습니다.")
            return
        registered_emails = users_db["id"].astype(str).tolist()
    except Exception as e:
        st.error(f"구글 시트 연결 실패: {e}")
        return

    leader_id = st.session_state.get("id", "user@dgist.ac.kr")
    leader_name_default = st.session_state.get("username", "홍길동")

    track_options = ["물리", "화학", "생명", "뇌", "기계", "재료", "전자", "컴퓨터", "화공", "자율"]
    time_options = ["0~5시간", "5~10시간", "10~15시간", "15~20시간 이상"]
    gender_options = ["남", "여"]
    l_pg_options = ["남", "여", "상관없음"]

    saved_team_rows = []
    try:
        df_ugrp_existing = conn.read(worksheet="UGRP_DB", ttl=0)
        if df_ugrp_existing is not None and not df_ugrp_existing.empty and "id" in df_ugrp_existing.columns:
            my_team_df = df_ugrp_existing[df_ugrp_existing["id"] == leader_id]
            if not my_team_df.empty:
                saved_team_rows = my_team_df.sort_values(by="member_index").to_dict(orient="records")
    except Exception:
        pass

    default_num_members = max(0, len(saved_team_rows) - 1) if saved_team_rows else 1

    num_members = st.slider(
        "추가 팀원 수 선택 (본인 제외, 최대 4명)",
        min_value=0, max_value=4,
        value=default_num_members,
        step=1,
        key="num_members_slider"
    )

    with st.form("ugrp_form"):
        team_members_data = []

        leader_saved = saved_team_rows[0] if saved_team_rows and len(saved_team_rows) > 0 else {}

        st.markdown(f"### 👑 1번 멤버 (팀장 본인: {leader_name_default})")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            l_g_val = leader_saved.get("gender", "남")
            l_g_idx = gender_options.index(l_g_val) if l_g_val in gender_options else 0
            leader_gender = st.selectbox("성별", gender_options, index=l_g_idx, key="leader_gender")
        with col_l2:
            l_t_val = leader_saved.get("track", track_options[0])
            l_t_idx = track_options.index(l_t_val) if l_t_val in track_options else 0
            leader_track = st.selectbox("트랙", track_options, index=l_t_idx, key="leader_track")

        leader_topic = st.text_input("희망 연구 분야 및 주제 방향성", value=str(leader_saved.get("topic", "")),
                                     placeholder="예: AI 기반 헬스케어 데이터 분석", key="leader_topic")

        l_time_val = leader_saved.get("available_time", time_options[0])
        l_time_idx = time_options.index(l_time_val) if l_time_val in time_options else 0
        leader_time = st.selectbox("주당 투자 가능 시간", time_options, index=l_time_idx, key="leader_time")

        col_lp1, col_lp2 = st.columns(2)
        with col_lp1:
            l_pg_val = leader_saved.get("pref_gender", "상관없음")
            l_pg_idx = l_pg_options.index(l_pg_val) if l_pg_val in l_pg_options else 2
            leader_pref_gender = st.selectbox("선호하는 팀원 성별", l_pg_options, index=l_pg_idx, key="leader_pref_gender")
        with col_lp2:
            saved_l_tracks = str(leader_saved.get("preferred_tracks", "")).split(",")
            default_l_tracks = [t.strip() for t in saved_l_tracks if t.strip() in track_options]
            leader_pref_tracks = st.multiselect("선호하는 트랙 (복수 선택)", track_options, default=default_l_tracks,
                                                key="leader_pref_tracks")

        leader_pr = st.text_area("개인 자기 PR", value=str(leader_saved.get("pr", "")), placeholder="예: 팀장으로서 열심히 이끌겠습니다!",
                                 key="leader_pr")
        st.markdown("---")

        team_emails_input = []
        for i in range(num_members):
            st.markdown(f"### 👤 {i + 2}번 멤버 정보")
            member_saved = saved_team_rows[i + 1] if saved_team_rows and (i + 1) < len(saved_team_rows) else {}

            col_m1, col_m2, col_m3 = st.columns(3)

            with col_m1:
                m_email = st.text_input(f"팀원 이메일 (아이디)", value=str(member_saved.get("member_email", "")),
                                        placeholder=f"member{i + 1}@dgist.ac.kr", key=f"m_email_{i}")
                team_emails_input.append(m_email.strip())
            with col_m2:
                m_g_val = member_saved.get("gender", "남")
                m_g_idx = gender_options.index(m_g_val) if m_g_val in gender_options else 0
                m_gender = st.selectbox(f"성별", gender_options, index=m_g_idx, key=f"m_gender_{i}")
            with col_m3:
                m_t_val = member_saved.get("track", track_options[0])
                m_t_idx = track_options.index(m_t_val) if m_t_val in track_options else 0
                m_track = st.selectbox(f"트랙", track_options, index=m_t_idx, key=f"m_track_{i}")

            m_topic = st.text_input(f"희망 연구 분야 및 주제 방향성", value=str(member_saved.get("topic", "")),
                                    placeholder="관심 연구 방향", key=f"m_topic_{i}")

            m_time_val = member_saved.get("available_time", time_options[0])
            m_time_idx = time_options.index(m_time_val) if m_time_val in time_options else 0
            m_time = st.selectbox(f"주당 투자 가능 시간", time_options, index=m_time_idx, key=f"m_time_{i}")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                m_pg_val = member_saved.get("pref_gender", "상관없음")
                m_pg_idx = l_pg_options.index(m_pg_val) if m_pg_val in l_pg_options else 2
                m_pref_gender = st.selectbox(f"선호하는 팀원 성별", l_pg_options, index=m_pg_idx, key=f"m_pref_gender_{i}")
            with col_p2:
                saved_m_tracks = str(member_saved.get("preferred_tracks", "")).split(",")
                default_m_tracks = [t.strip() for t in saved_m_tracks if t.strip() in track_options]
                m_pref_tracks = st.multiselect(f"선호하는 트랙 (복수 선택)", track_options, default=default_m_tracks,
                                               key=f"m_pref_tracks_{i}")

            m_pr = st.text_area(f"개인 자기 PR", value=str(member_saved.get("pr", "")), placeholder="예: 코딩에 자신이 있습니다.",
                                key=f"m_pr_{i}")

            st.markdown("---")

            team_members_data.insert(i + 1, {
                "id": leader_id,
                "leader_name": leader_name_default,
                "member_index": i + 2,
                "member_email": m_email.strip(),
                "gender": m_gender,
                "track": m_track,
                "topic": m_topic,
                "available_time": m_time,
                "pref_gender": m_pref_gender,
                "preferred_tracks": ", ".join(m_pref_tracks),
                "pr": m_pr,
                "team_pr": ""
            })

        st.markdown("### 🏆 팀 전체 PR (팀 소개 및 각오)")
        is_team_pr_disabled = (num_members == 0)
        if is_team_pr_disabled:
            st.warning("⚠️ 추가 팀원이 0명이므로 팀 PR을 작성하실 수 없습니다.")

        default_team_pr = leader_saved.get("team_pr", "") if leader_saved else ""
        team_pr_input = st.text_area(
            "팀 PR (예: 열심히 하시는 분 오시면 좋겠습니다)",
            value=str(default_team_pr),
            placeholder="우리 팀과 함께 열정을 불태울 팀원을 기다립니다!",
            disabled=is_team_pr_disabled,
            key="team_pr_input"
        )

        team_members_data.insert(0, {
            "id": leader_id,
            "leader_name": leader_name_default,
            "member_index": 1,
            "member_email": leader_id,
            "gender": leader_gender,
            "track": leader_track,
            "topic": leader_topic,
            "available_time": leader_time,
            "pref_gender": leader_pref_gender,
            "preferred_tracks": ", ".join(leader_pref_tracks),
            "pr": leader_pr,
            "team_pr": "" if is_team_pr_disabled else team_pr_input
        })

        for data in team_members_data:
            data["team_pr"] = "" if is_team_pr_disabled else team_pr_input

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("💾 UGRP 팀 정보 저장하기", use_container_width=True)
        with btn_col2:
            ugrp_match_clicked = st.form_submit_button("🔍 UGRP 팀 추천받기 (AI)", use_container_width=True)

        def process_ugrp_save():
            has_empty_field = False
            for idx, member in enumerate(team_members_data):
                if idx > 0 and not member.get("member_email"):
                    has_empty_field = True
                    break
                if not member.get("topic") or not member.get("pr"):
                    has_empty_field = True
                    break

            if has_empty_field or (not is_team_pr_disabled and not team_pr_input.strip()):
                return "empty_error"

            invalid_emails = [email for email in team_emails_input if email and email not in registered_emails]
            if invalid_emails:
                return f"invalid_email:{', '.join(invalid_emails)}"

            already_in_other_team = []
            try:
                df_existing_check = conn.read(worksheet="UGRP_DB", ttl=0)
                if not df_existing_check.empty and "member_email" in df_existing_check.columns:
                    other_teams_df = df_existing_check[df_existing_check["id"] != leader_id]
                    taken_emails = other_teams_df["member_email"].astype(str).tolist()
                    for email in team_emails_input:
                        if email and email in taken_emails:
                            already_in_other_team.append(email)
            except:
                pass

            if already_in_other_team:
                return f"taken_email:{', '.join(already_in_other_team)}"

            try:
                df_new = pd.DataFrame(team_members_data)
                try:
                    df_existing = conn.read(worksheet="UGRP_DB", ttl=0)
                    if not df_existing.empty and "id" in df_existing.columns:
                        df_existing = df_existing[df_existing["id"] != leader_id]
                        df_final = pd.concat([df_existing, df_new], ignore_index=True)
                    else:
                        df_final = df_new
                except:
                    df_final = df_new

                conn.update(worksheet="UGRP_DB", data=df_final)
                return "success"
            except Exception as e:
                return f"db_error:{e}"

        if submitted:
            res = process_ugrp_save()
            if res == "empty_error":
                st.error("🚨 정해진 팀원 수만큼 모든 문항(이메일, 희망 주제, 자기 PR 등)을 빠짐없이 채워주세요!")
            elif res.startswith("invalid_email:"):
                st.error(f"🚨 시스템에 가입되지 않은 이메일입니다: {res.split(':')[1]}")
            elif res.startswith("taken_email:"):
                st.error(f"🚨 이미 다른 팀에 소속된 팀원입니다: {res.split(':')[1]}")
            elif res == "success":
                st.success("🎉 UGRP 팀 정보가 완벽하게 저장되었습니다!")
            else:
                st.error(f"저장 중 에러 발생: {res}")

        if ugrp_match_clicked:
            res = process_ugrp_save()
            if res != "success":
                st.error("🚨 AI 추천을 받으려면 먼저 팀 정보를 올바르게 작성하고 저장 조건(이메일 검증 및 빈칸 없음)을 만족해야 합니다!")
            else:
                try:
                    df_all_ugrp = conn.read(worksheet="UGRP_DB", ttl=0)
                    # 내 팀원들 행 제외하고 다른 팀장들 추출
                    other_teams_raw = df_all_ugrp[df_all_ugrp["id"] != leader_id]

                    if other_teams_raw.empty:
                        st.warning("현재 매칭을 구하고 있는 다른 UGRP 팀이 충분하지 않습니다.")
                    else:
                        # 팀별 인원수를 계산하여 합산 시 6명이 넘지 않는 팀들만 필터링
                        my_team_count = len(team_members_data)
                        valid_other_leader_ids = []

                        for oid, group in other_teams_raw.groupby("id"):
                            other_team_count = len(group)
                            if my_team_count + other_team_count <= 6:
                                valid_other_leader_ids.append(oid)

                        filtered_other_teams = other_teams_raw[other_teams_raw["id"].isin(valid_other_leader_ids)]

                        if filtered_other_teams.empty:
                            st.warning("합병 시 총인원이 6명 이하인 조건에 부합하는 다른 팀이 없습니다.")
                        else:
                            api_key = st.secrets.get("GEMINI_API_KEY", "")
                            if not api_key:
                                st.error("Gemini API 키가 secrets.toml에 설정되어 있지 않습니다.")
                            else:
                                with st.spinner("🤖 Gemini AI가 최적의 UGRP 연구 시너지 팀을 분석 중입니다..."):
                                    my_team_summary_str = f"우리 팀 인원: {my_team_count}명, 팀장: {leader_name_default}, 팀 PR: {team_pr_input}, 구성원 상세:\n" + pd.DataFrame(
                                        team_members_data).to_string()
                                    result_text = get_ugrp_ai_recommendation_cached(
                                        my_team_summary_str, filtered_other_teams.to_string(), api_key
                                    )

                                st.session_state.ugrp_ai_raw_text = result_text

                                parsed_cards = []
                                lines = result_text.strip().split("\n")

                                for i, line in enumerate(lines[:5]):
                                    parts = line.split(" ", 2)
                                    cand_name = parts[0] if len(parts) >= 0 else f"다른 팀 {i + 1}"

                                    # 해당 팀장의 데이터 그룹 추출
                                    matched_group = filtered_other_teams[
                                        filtered_other_teams["leader_name"].astype(str).str.contains(cand_name,
                                                                                                     na=False) |
                                        filtered_other_teams["id"].astype(str).str.contains(cand_name, na=False)
                                        ]
                                    if matched_group.empty:
                                        # 첫 번째 유효한 팀장 ID로 대체 시도
                                        unique_ids = filtered_other_teams["id"].unique()
                                        if i < len(unique_ids):
                                            matched_group = filtered_other_teams[
                                                filtered_other_teams["id"] == unique_ids[i]]

                                    team_details = matched_group.to_dict(
                                        orient="records") if not matched_group.empty else []
                                    team_leader_name = team_details[0].get("leader_name",
                                                                           "연구팀장") if team_details else "연구팀장"
                                    team_leader_email = team_details[0].get("id",
                                                                            "team@dgist.ac.kr") if team_details else "team@dgist.ac.kr"
                                    team_pr_desc = team_details[0].get("team_pr",
                                                                       "등록된 팀 PR이 없습니다.") if team_details else "등록된 팀 PR이 없습니다."

                                    if len(parts) >= 3:
                                        parsed_cards.append({
                                            "name": f"{team_leader_name} 팀",
                                            "email": team_leader_email,
                                            "desc": parts[2],
                                            "team_pr": team_pr_desc,
                                            "details": team_details,
                                        })
                                    else:
                                        parsed_cards.append({
                                            "name": f"연구팀 {i + 1}",
                                            "email": team_leader_email,
                                            "desc": line,
                                            "team_pr": team_pr_desc,
                                            "details": team_details,
                                        })

                                st.session_state.ugrp_ai_cards_data = parsed_cards
                                st.session_state.page = "ugrp_result"
                                st.rerun()

                except Exception as e:
                    st.error(f"UGRP 추천 처리 중 오류가 발생했습니다: {e}")

    if st.button("← 홈으로 돌아가기"):
        st.session_state.page = "home"
        st.rerun()


# --- UGRP 후보 세부정보 다이얼로그 팝업 함수 ---
@st.dialog("📋 UGRP 추천 연구팀 상세 프로필")
def show_ugrp_detail_dialog(c):
    st.subheader(f"🔬 {c['name']} 상세 정보")
    st.write(f"📧 **대표 팀장 이메일:** {c['email']}")
    st.markdown(f"🏆 **팀 전체 PR:** \"{c.get('team_pr', '정보 없음')}\"")
    st.write("---")

    details = c.get("details", [])
    if details:
        st.markdown("### 👥 팀원 구성 및 연구 성향")
        for idx, member in enumerate(details):
            with st.expander(f"👤 {idx + 1}번 멤버 ({member.get('member_email', '이메일 없음')})"):
                col_ud1, col_ud2 = st.columns(2)
                with col_ud1:
                    st.write(f"- **성별:** {member.get('gender', '정보 없음')}")
                    st.write(f"- **트랙:** {member.get('track', '정보 없음')}")
                    st.write(f"- **투자 시간:** {member.get('available_time', '정보 없음')}")
                with col_ud2:
                    st.write(f"- **희망 주제:** {member.get('topic', '정보 없음')}")
                    st.write(f"- **선호 성별:** {member.get('pref_gender', '정보 없음')}")
                    st.write(f"- **선호 트랙:** {member.get('preferred_tracks', '정보 없음')}")
                st.info(f"**개인 자기 PR:** {member.get('pr', '작성된 내용이 없습니다.')}")
    else:
        st.info("해당 팀의 상세 구성원 데이터가 없습니다.")

    if st.button("닫기", use_container_width=True, key="close_ugrp_dialog"):
        st.rerun()


# --- UGRP 추천 결과 화면 ---
def show_ugrp_result():
    st.markdown(theme_css, unsafe_allow_html=True)
    st.markdown(
        "<div class='dgist-logo'>ugrp<span>.</span>result</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h2 style='color:#1E293B; font-weight:800;"
        f" margin-top:0.5rem;'>{st.session_state.get('username', '사용자')}님의"
        " 팀을 위한 최적의 UGRP 연구팀 추천 리스트 (합산 최대 6명)</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#64748B; margin-bottom: 2rem;'>Gemini AI가 연구 주제 방향성과 팀 PR 시너지를 분석하여 선정한 상위 추천 연구팀 프로필입니다.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("✨ Gemini AI UGRP 심층 분석 리포트 전체 보기", expanded=False):
        st.write(st.session_state.get("ugrp_ai_raw_text", ""))

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    cards = st.session_state.get("ugrp_ai_cards_data", [])
    if not cards:
        st.warning("표시할 추천 UGRP 데이터가 없습니다. 다시 시도해 주세요.")
    else:
        cols = st.columns(len(cards) if len(cards) <= 5 else 5, gap="small")
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
                    if st.button("팀 세부정보 보기", key=f"ugrp_detail_btn_{idx}"):
                        show_ugrp_detail_dialog(c)

    st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("← UGRP 팀 입력 화면으로"):
            st.session_state.page = "ugrp"
            st.rerun()
    with col_b2:
        if st.button("🏠 메인 홈으로 돌아가기"):
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

    아래는 데이터베이스에 등록된 다른 사용자들의 프로필 목록입니다 (현재 '구함' 상태인 사용자들만 필터링됨):
    {others_info_str}

    조건:
    1. 로그인한 사용자의 '선호 조건'과 '나의 특성'을 종합적으로 고려하여 가장 잘 어울리는 상위 5명을 선정해주세요. 무조건 5명입니다.
    2. 각 추천 사람별 출력 포맷은 반드시 아래와 같이 한 줄씩 작성해주세요:
    [이름] [이메일/아이디] [추천 이유 요약]
    예시: 삼건우 shin_kunwoo@university.ac.kr 흡연하지 않고 음주 습관이 없으며 패턴이 잘 부합합니다.
    정보를 전달하는 텍스트 이외의 텍스트들은 출력을 금지합니다.
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
            current_status = st.session_state.get("matching_status", "구함")
            return {
                "id": current_id,
                "matching_status": current_status,
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
                # 1. 데이터를 시트에 자동 저장
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

                # 2. 다른 사용자 필터링 (구함 상태인 유저만)
                other_users_df = updated_df[updated_df["id"] != current_id]
                if "matching_status" in other_users_df.columns:
                    other_users_df = other_users_df[
                        other_users_df["matching_status"].astype(str) == "구함"
                        ]

                if other_users_df.empty or len(other_users_df) < 1:
                    st.warning(
                        "비어있습니다 (현재 매칭을 구하고 있는 다른 사용자가 충분하지 않습니다)"
                    )
                else:
                    api_key = st.secrets.get("GEMINI_API_KEY", "")
                    if not api_key:
                        st.error("Gemini API 키가 secrets.toml에 설정되어 있지 않습니다.")
                    else:
                        # 3. 프롬프트 밀림 방지를 위한 명확한 구조표(라벨 블록) 생성
                        others_info_list = []
                        for idx, row in other_users_df.iterrows():
                            row_str = (
                                f"- 이름: {row.get('my_name', '알수없음')} | "
                                f"이메일: {row.get('id', '')} | "
                                f"성별: {row.get('my_gender', '')} | "
                                f"흡연: {row.get('my_smoke', '')} | "
                                f"취침: {row.get('my_sleep_time', '')} | "
                                f"군필: {row.get('my_military', '')} | "
                                f"청소: {row.get('my_clean', '')} | "
                                f"자기PR: {row.get('my_pr', '')}"
                            )
                            others_info_list.append(row_str)
                        others_info_str = "\n".join(others_info_list)

                        user_info_str = str(new_data)

                        with st.spinner("🤖 Gemini AI가 최적의 룸메이트를 분석 중입니다..."):
                            result_text = get_ai_recommendation_cached(
                                user_info_str, others_info_str, api_key
                            )

                        st.session_state.ai_raw_text = result_text

                        # 4. 결과 파싱 및 데이터 맵핑 안정화
                        parsed_cards = []
                        lines = [line.strip() for line in result_text.strip().split("\n") if line.strip()]

                        for i, line in enumerate(lines[:5]):
                            # 정규식 패턴을 이용해 [이름] [이메일] [설명] 구조 안전하게 추출
                            match = re.match(r"^\[(.*?)\]\s*([\w\.-]+@[\w\.-]+\.\w+)\s+(.*)$", line)

                            if match:
                                c_name = match.group(1).strip()
                                c_email = match.group(2).strip()
                                c_desc = match.group(3).strip()
                            else:
                                # 포맷이 미세하게 다를 경우를 대비한 대체 분해
                                parts = line.split(" ", 2)
                                c_name = parts[0] if len(parts) > 0 else f"후보 {i + 1}"
                                c_email = parts[1] if len(parts) > 1 else "contact@university.ac.kr"
                                c_desc = parts[2] if len(parts) > 2 else line

                            # 이메일 혹은 이름으로 실제 데이터베이스 행 매칭
                            matched_row = other_users_df[
                                (other_users_df["id"].astype(str) == c_email) |
                                (other_users_df["my_name"].astype(str) == c_name)
                                ]

                            user_details = (
                                matched_row.iloc[0].to_dict()
                                if not matched_row.empty
                                else {}
                            )

                            parsed_cards.append({
                                "name": c_name,
                                "email": c_email,
                                "desc": c_desc,
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


# --- 5. 사이드바 토글 상태 변경 시 실시간 DB 반영 함수 ---
def update_matching_status_in_db():
    current_id = st.session_state.get("id", "")
    if not current_id:
        return

    new_status = st.session_state.get("matching_toggle_state", True)
    status_str = "구함" if new_status else "구함 완료"
    st.session_state["matching_status"] = status_str

    try:
        conn, _ = get_database()
        if conn is None:
            return
        existing_data = conn.read(worksheet="Roommate_DB", ttl=0)

        if (
                existing_data is not None
                and not existing_data.empty
                and "id" in existing_data.columns
        ):
            if "matching_status" not in existing_data.columns:
                existing_data["matching_status"] = "구함"
            existing_data["matching_status"] = existing_data[
                "matching_status"
            ].astype(str)

            if current_id in existing_data["id"].values:
                existing_data.loc[
                    existing_data["id"] == current_id, "matching_status"
                ] = status_str
                conn.update(worksheet="Roommate_DB", data=existing_data)
                if status_str == "구함":
                    st.sidebar.success("🟢 구함 상태로 변경되었습니다.")
                else:
                    st.sidebar.warning("🔴 구함 완료로 변경되었습니다.")
    except Exception as e:
        st.sidebar.error(f"상태 업데이트 실패: {e}")


# --- 6. 메인 네비게이션 및 로그인 분기 ---
def main_page():
    with st.sidebar:
        username = st.session_state.get("username", "사용자")
        st.title(f"반갑습니다,\n**{username}**님! 👋")
        st.write("---")

        st.subheader("💡 룸메이트 매칭 상태")
        st.toggle(
            "룸메이트 구하는 중",
            value=True,
            key="matching_toggle_state",
            on_change=update_matching_status_in_db,
            help=(
                "토글을 끄거나 켜면 즉시 구글 시트 DB에 반영되며, 다른 사람의 AI"
                " 추천 목록 반영 여부가 결정됩니다."
            ),
        )

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
    elif st.session_state.page == "ugrp_result":
        show_ugrp_result()
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
                    st.session_state["username"] = str(user_info["name"])
                    st.session_state["id"] = login_id
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