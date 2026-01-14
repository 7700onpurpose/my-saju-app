import streamlit as st
import requests
import pandas as pd
import altair as alt # 디자인 그래프 도구
from datetime import datetime

st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# ---------------------------------------------------------
# [기능 1] 사주 맛보기 계산기
# ---------------------------------------------------------
def get_saju_info(year):
    stems = ["경(금/⚪)", "신(금/⚪)", "임(수/⚫)", "계(수/⚫)", "갑(목/🔵)", "을(목/🔵)", "병(화/🔴)", "정(화/🔴)", "무(토/🟡)", "기(토/🟡)"]
    branches = ["신(원숭이🐵)", "유(닭🐔)", "술(개🐶)", "해(돼지🐷)", "자(쥐🐭)", "축(소🐮)", "인(호랑이🐯)", "묘(토끼🐰)", "진(용🐲)", "사(뱀🐍)", "오(말🐴)", "미(양🐑)"]
    
    stem_idx = year % 10
    branch_idx = year % 12
    
    stem_char = stems[stem_idx]
    branch_char = branches[branch_idx]
    
    # 오행 점수 (기본 10점 + 태어난 해의 기운 30점 보너스)
    elements_score = {"목(나무)": 10, "화(불)": 10, "토(땅)": 10, "금(쇠)": 10, "수(물)": 10}
    
    if "목" in stem_char: elements_score["목(나무)"] += 30
    elif "화" in stem_char: elements_score["화(불)"] += 30
    elif "토" in stem_char: elements_score["토(땅)"] += 30
    elif "금" in stem_char: elements_score["금(쇠)"] += 30
    elif "수" in stem_char: elements_score["수(물)"] += 30
    
    full_name = f"{stem_char[0]}{branch_char[0]}년생 ({branch_char.split('(')[1][:-1]})"
    return full_name, elements_score

# ---------------------------------------------------------
# [기능 2] 디스코드 알림
# ---------------------------------------------------------
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception as e:
        pass

# ---------------------------------------------------------
# [기능 3] 예쁜 그래프 그리기 함수 (새로 추가됨!)
# ---------------------------------------------------------
def draw_pretty_chart(scores):
    # 데이터 표 만들기
    df = pd.DataFrame(list(scores.items()), columns=["오행", "점수"])
    
    # 오행 색상 지정 (트렌디한 파스텔톤)
    # 목:초록, 화:빨강, 토:노랑, 금:회색, 수:남색
    domain = ["목(나무)", "화(불)", "토(땅)", "금(쇠)", "수(물)"]
    range_ = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    
    # 알테어 차트 생성
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
        x=alt.X('오행', sort=None, axis=alt.Axis(labelAngle=0)), # 글자 가로로
        y='점수',
        color=alt.Color('오행', scale=alt.Scale(domain=domain, range=range_), legend=None),
        tooltip=['오행', '점수'] # 마우스 올리면 숫자 보임
    ).properties(
        height=300 # 그래프 높이
    ).configure_axis(
        grid=False # 격자무늬 없애기 (깔끔하게)
    ).configure_view(
        strokeWidth=0 # 테두리 없애기
    )
    
    return chart

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 온라인 철학원")
st.markdown("### 당신의 이야기를 들려주세요.")
st.caption("생년월일시와 고민을 남겨주시면, 오행 분석 그래프와 함께 명리학으로 풀이해 드립니다.")

with st.form("saju_form", clear_on_submit=False):
    nickname = st.text_input("닉네임 (필수)", placeholder="예: 무지개")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    
    col1, col2 = st.columns(2)
    with col1:
        is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    with col2:
        birth_time = st.time_input("태어난 시간")
    
    concern = st.text_area("고민 내용", height=150, placeholder="가장 궁금한 점을 적어주세요.")
    contact = st.text_input("답변 받을 이메일 (선택)", placeholder="입력 시 메일로 답변, 미입력 시 블로그 게시")
    
    submitted = st.form_submit_button("상담 신청 및 내 사주 확인하기")

    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        elif not nickname:
            st.error("닉네임을 적어주세요!")
        else:
            # 1. 계산
            year = birth_date.year
            saju_name, scores = get_saju_info(year)
            
            # 2. 알림 전송
            final_time = "시간모름" if is_unknown_time else str(birth_time)
            final_contact = contact if contact else "블로그 게시 희망"
            
            msg = f"""
**[🔮 상담 신청 도착!]**
--------------------------------
👤 **닉네임**: {nickname} ({gender})
🗓 **사주**: {year}년생 -> **{saju_name}**
🎂 **생일**: {birth_date} / {final_time}
📧 **연락처**: {final_contact}

📜 **고민내용**:
{concern}
--------------------------------
"""
            send_discord_message(msg)
            
            # 3. 결과 화면 (디자인 업그레이드!)
            st.success(f"✅ 접수 완료! {nickname}님은 **'{saju_name}'** 이시군요!")
            
            st.markdown("---")
            st.markdown(f"#### 📊 {nickname}님의 오행 에너지")
            st.caption("나무(🌲), 불(🔥), 땅(⛰️), 쇠(💎), 물(🌊) 중 어떤 기운이 강할까요?")
            
            # 예쁜 차트 그리기
            chart = draw_pretty_chart(scores)
            st.altair_chart(chart, use_container_width=True)
            
            st.info("더 자세한 풀이는 운영자가 꼼꼼히 분석해서 곧 전달드릴게요! 🍀")
