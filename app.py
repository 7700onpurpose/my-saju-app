import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# ---------------------------------------------------------
# [기능 1] 사주 맛보기 계산기 (연도 기준)
# ---------------------------------------------------------
def get_saju_info(year):
    # 천간 (하늘의 글자) - 색깔 결정
    stems = ["경(금/⚪)", "신(금/⚪)", "임(수/⚫)", "계(수/⚫)", "갑(목/🔵)", "을(목/🔵)", "병(화/🔴)", "정(화/🔴)", "무(토/🟡)", "기(토/🟡)"]
    # 지지 (땅의 글자) - 동물 결정
    branches = ["신(원숭이🐵)", "유(닭🐔)", "술(개🐶)", "해(돼지🐷)", "자(쥐🐭)", "축(소🐮)", "인(호랑이🐯)", "묘(토끼🐰)", "진(용🐲)", "사(뱀🐍)", "오(말🐴)", "미(양🐑)"]
    
    stem_idx = year % 10
    branch_idx = year % 12
    
    stem_char = stems[stem_idx]
    branch_char = branches[branch_idx]
    
    # 간단 오행 분석 (재미용 점수)
    # 실제 사주는 월/일/시 까지 봐야 하지만, 여기선 연도만으로 예시를 보여줍니다.
    # 랜덤이 아니라 실제 연도에 따른 고정값이므로 의미가 있습니다.
    elements_score = {"목(나무)": 10, "화(불)": 10, "토(땅)": 10, "금(쇠)": 10, "수(물)": 10}
    
    # 태어난 해의 기운을 더해줌
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
        pass # 에러 나도 조용히 넘어감 (사용자는 모르게)

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 온라인 철학원")

st.markdown("""
**생년월일시와 고민을 남겨주시면 명리학으로 풀이해 드립니다.** 입력하시면 **본인의 띠와 오행 그래프**를 즉시 확인하실 수 있어요!
""")

with st.form("saju_form", clear_on_submit=False): # 결과 보여주려고 False로 변경
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
            # 1. 사주 기본 정보 계산
            year = birth_date.year
            saju_name, scores = get_saju_info(year)
            
            # 2. 디스코드 전송
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
            
            # 3. 화면에 결과 보여주기 (뽕 차오르는 부분!)
            st.success(f"접수 완료! {nickname}님은 **'{saju_name}'** 이시군요!")
            st.markdown("---")
            st.subheader("📊 당신의 오행(에너지) 분포 맛보기")
            st.caption("※ 태어난 '해(Year)'를 기준으로 한 간단 분석입니다. 자세한 건 풀이에서 알려드릴게요!")
            
            # 그래프 그리기
            df = pd.DataFrame(list(scores.items()), columns=["오행", "점수"])
            st.bar_chart(df.set_index("오행"))
            
            st.info("더 깊은 내용은 운영자가 직접 풀이해서 알려드릴게요! 조금만 기다려주세요. 🍀")
