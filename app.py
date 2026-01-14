import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# 디스코드 알림 함수
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception as e:
        st.error("전송 오류가 발생했습니다.")

st.title("🔮 익명 온라인 철학원")
st.info("비밀 보장! 작성해주신 내용은 운영자의 개인 알림창으로만 전송됩니다.")

with st.form("saju_form", clear_on_submit=True):
    nickname = st.text_input("닉네임")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    
    is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    birth_time = st.time_input("태어난 시간")
    concern = st.text_area("고민 내용", height=150)
    
    submitted = st.form_submit_button("상담 신청하기")

    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        else:
            final_time = "시간모름" if is_unknown_time else str(birth_time)
            
            # 보낼 메시지 모양
            message = f"""
**[🔮 새로운 상담 신청 도착!]**
--------------------------------
👤 **닉네임**: {nickname} ({gender})
🎂 **생일**: {birth_date}
⏰ **시간**: {final_time}

📜 **고민내용**:
{concern}
--------------------------------
"""
            send_discord_message(message)
            st.success("접수 완료! 꼼꼼히 보고 답변 드릴게요. 🍀")
