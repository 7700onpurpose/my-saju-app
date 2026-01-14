import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. 페이지 설정
st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# 2. 제목과 설명
st.title("🔮 익명 온라인 철학원")
st.write("생년월일시와 고민을 남겨주시면, 사주 명리를 바탕으로 답해드립니다.")
st.info("작성해주신 내용은 운영자만 볼 수 있으며, 절대 공개되지 않습니다.")

# 3. 입력 양식 만들기
with st.form("saju_form", clear_on_submit=True):
    # 입력받을 항목들
    nickname = st.text_input("닉네임 (익명)", placeholder="예: 길동이")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    
    # 태어난 시간 입력 (모르면 체크)
    is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    birth_time = st.time_input("태어난 시간")
    
    concern = st.text_area("고민 내용", height=150, placeholder="현재 상황과 가장 궁금한 점을 적어주세요.")
    
    # 제출 버튼
    submitted = st.form_submit_button("상담 신청하기")

    # 4. 버튼을 눌렀을 때 동작
    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        else:
            # 시간 처리
            final_time = "시간모름" if is_unknown_time else str(birth_time)
            
            # 저장할 데이터 뭉치기
            new_data = {
                "신청일시": [datetime.now().strftime("%Y-%m-%d %H:%M")],
                "닉네임": [nickname],
                "성별": [gender],
                "생년월일": [birth_date],
                "태어난시간": [final_time],
                "고민내용": [concern]
            }
            
            # 엑셀(CSV) 파일로 저장하는 마법
            df = pd.DataFrame(new_data)
            csv_file = 'saju_counseling.csv'
            
            if not os.path.exists(csv_file):
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            else:
                df.to_csv(csv_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            
            st.success(f"{nickname}님의 사연이 안전하게 접수되었습니다! 분석 후 연락드릴게요.")
            st.balloons() # 풍선 효과 팡팡