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
        st.error(f"전송 오류: {e}")

# --- 화면 꾸미기 ---
st.title("🔮 익명 온라인 철학원")

# 안내문구 (여기를 잘 적어야 합니다!)
st.markdown("""
**생년월일시와 고민을 남겨주시면 명리학으로 풀이해 드립니다.**
1. **이메일**을 남기시면 메일로 답장을 보내드립니다. ✉️
2. 남기지 않으시면 **[운영자 블로그/인스타]**에 닉네임으로 답변이 올라갑니다.
""")
# (위 [운영자 블로그...] 부분에 님 블로그 주소를 적어두면 더 좋아요!)

with st.form("saju_form", clear_on_submit=True):
    # 기본 정보
    nickname = st.text_input("닉네임 (필수)", placeholder="예: 무지개")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    
    col1, col2 = st.columns(2)
    with col1:
        is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    with col2:
        birth_time = st.time_input("태어난 시간")
    
    # 고민 내용
    concern = st.text_area("고민 내용", height=150, placeholder="현재 상황과 가장 궁금한 점을 적어주세요.")
    
    # 📢 [추가됨] 연락받을 곳
    contact = st.text_input("답변 받을 이메일 (선택사항)", placeholder="입력하지 않으면 블로그에 답변이 게시됩니다.")
    
    submitted = st.form_submit_button("상담 신청하기")

    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        elif not nickname:
            st.error("닉네임을 적어주세요!")
        else:
            final_time = "시간모름" if is_unknown_time else str(birth_time)
            final_contact = contact if contact else "이메일 없음 (블로그 게시 요망)"
            
            # 디스코드에 보낼 메시지 (이메일 포함)
            message = f"""
**[🔮 상담 신청 도착!]**
--------------------------------
👤 **닉네임**: {nickname} ({gender})
🎂 **생일**: {birth_date} / {final_time}
📧 **연락처**: {final_contact}

📜 **고민내용**:
{concern}
--------------------------------
"""
            send_discord_message(message)
            st.success(f"접수 완료! {nickname}님, 곧 답변 드릴게요. 🍀")
