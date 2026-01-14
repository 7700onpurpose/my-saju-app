import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# ---------------------------------------------------------
# [나만의 일주 해석 사전] - 여기에 60개 내용을 채우세요!
# ---------------------------------------------------------
ilju_data = {
    "갑자": "큰 나무가 차가운 물 위에 떠 있는 형상. 지혜롭고 인정이 많으나 고독할 수 있음.",
    "을축": "언 땅에 핀 꽃. 끈기가 강하고 생활력이 좋으나 속마음을 잘 드러내지 않음.",
    # ... 계속 추가하세요 ...
}
default_desc = "아직 설명이 업데이트되지 않았습니다. 운영자가 직접 풀이해 드릴게요!"

# ---------------------------------------------------------
# [핵심] 사주팔자(4주 8자) 계산기
# ---------------------------------------------------------
class SajuCalculator:
    def __init__(self):
        self.gan = list("갑을병정무기경신임계")
        self.ji = list("자축인묘진사오미신유술해")
        # 월주 계산을 위한 지지 순서 (인월=1월 부터 시작)
        self.month_ji = list("인묘진사오미신유술해자축")
        
        self.gan_colors = {"갑": "목(초록)", "을": "목(초록)", "병": "화(빨강)", "정": "화(빨강)", 
                           "무": "토(노랑)", "기": "토(노랑)", "경": "금(흰색)", "신": "금(흰색)", 
                           "임": "수(검정)", "계": "수(검정)"}
        self.ji_colors = {"인": "목", "묘": "목", "사": "화", "오": "화", 
                          "진": "토", "술": "토", "축": "토", "미": "토", 
                          "신": "금", "유": "금", "해": "수", "자": "수"}

    def get_60ganji(self, gan_idx, ji_idx):
        return self.gan[gan_idx % 10] + self.ji[ji_idx % 12]

    # 1. 연주 (Year)
    def get_year_pillar(self, year):
        idx = (year - 1984) % 60
        gan_idx = idx % 10
        ji_idx = idx % 12
        return self.get_60ganji(gan_idx, ji_idx)

    # 2. 월주 (Month) - [추가됨!] 근사치 알고리즘 적용
    def get_month_pillar(self, year_pillar, date_obj):
        year_gan = year_pillar[0] # 연간 가져오기
        
        # 사주 명리학의 월은 양력 4~8일 사이 절기를 기준으로 바뀜.
        # 약식으로 '매월 6일'을 기준으로 월이 넘어간다고 계산 (오차 범위 내 근사치)
        month = date_obj.month
        day = date_obj.day
        
        # 6일 이전이면 전달의 기운을 받음
        if day < 6:
            month -= 1
            if month == 0: month = 12
        
        # 명리학에서는 '인(Tiger)'월이 1월(양력 2월)임.
        # month_ji 리스트 인덱스 맞추기 (2월 -> 인, 3월 -> 묘 ...)
        # 양력 2월(입춘)이 명리학의 1월
        saju_month_idx = (month - 2) % 12
        month_ji_char = self.month_ji[saju_month_idx]
        month_ji_idx = self.ji.index(month_ji_char)
        
        # 월간(Month Stem) 찾는 공식 (연두법)
        year_gan_idx = self.gan.index(year_gan)
        start_gan_idx = (year_gan_idx % 5) * 2 + 2 # 공식 보정값
        month_gan_idx = (start_gan_idx + saju_month_idx) % 10
        
        return self.gan[month_gan_idx] + month_ji_char

    # 3. 일주 (Day)
    def get_day_pillar(self, date_obj):
        base_date = datetime(1900, 1, 1)
        days_diff = (date_obj - base_date).days
        idx = (10 + days_diff) % 60
        return self.get_60ganji(idx % 10, idx % 12)

    # 4. 시주 (Time)
    def get_time_pillar(self, day_pillar, hour):
        day_gan = day_pillar[0]
        time_idx = (hour + 1) // 2 % 12
        day_gan_idx = self.gan.index(day_gan)
        start_gan_idx = (day_gan_idx % 5) * 2
        time_gan_idx = (start_gan_idx + time_idx) % 10
        return self.gan[time_gan_idx] + self.ji[time_idx]

    # 오행 점수 계산
    def calculate_elements(self, pillars):
        scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        all_chars = "".join(pillars)
        for char in all_chars:
            if char in self.gan_colors:
                elem = self.gan_colors[char].split("(")[0]
                scores[elem] += 10
            elif char in self.ji_colors:
                elem = self.ji_colors[char]
                scores[elem] += 10
        return scores

# ---------------------------------------------------------
# [기능] 디스코드 전송 & 차트
# ---------------------------------------------------------
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception: pass

def draw_pretty_chart(scores):
    df = pd.DataFrame(list(scores.items()), columns=["오행", "점수"])
    domain = ["목", "화", "토", "금", "수"]
    range_ = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    chart = alt.Chart(df).mark_bar(cornerRadius=10).encode(
        x=alt.X('오행', sort=None), y='점수',
        color=alt.Color('오행', scale=alt.Scale(domain=domain, range=range_), legend=None),
        tooltip=['오행', '점수']
    ).properties(height=250).configure_axis(grid=False).configure_view(strokeWidth=0)
    return chart

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 정밀 사주풀이")
st.markdown("##### 연월일시(사주팔자)를 모두 분석합니다.")

calc = SajuCalculator()

with st.form("saju_form", clear_on_submit=False):
    nickname = st.text_input("닉네임", placeholder="예: 도깨비")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    with col2:
        birth_time = st.time_input("태어난 시간")
    is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    
    concern = st.text_area("고민 내용", height=150)
    contact = st.text_input("이메일 (선택)", placeholder="답변 받을 연락처")
    
    submitted = st.form_submit_button("내 사주팔자 확인하기")

    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        elif not nickname:
            st.error("닉네임을 적어주세요!")
        else:
            # --- 사주 4기둥 계산 ---
            # 1. 연주
            year_pillar = calc.get_year_pillar(birth_date.year)
            
            # 2. 월주 (새로 추가됨!)
            month_pillar = calc.get_month_pillar(year_pillar, birth_date)
            
            # 3. 일주
            day_pillar = calc.get_day_pillar(datetime.combine(birth_date, birth_time))
            
            # 4. 시주
            if not is_unknown_time:
                time_pillar = calc.get_time_pillar(day_pillar, birth_time.hour)
                pillars = [year_pillar, month_pillar, day_pillar, time_pillar]
                result_text = f"연주:{year_pillar} / 월주:**{month_pillar}** / 일주:**{day_pillar}** / 시주:{time_pillar}"
            else:
                pillars = [year_pillar, month_pillar, day_pillar]
                result_text = f"연주:{year_pillar} / 월주:**{month_pillar}** / 일주:**{day_pillar}**"

            # 오행 점수
            scores = calc.calculate_elements(pillars)
            
            # 일주 해석 가져오기
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            # 디스코드 전송
            final_contact = contact if contact else "블로그 게시 희망"
            msg = f"""
**[🔮 4주 8자 완성 상담]**
👤 {nickname} ({gender})
📅 {birth_date}
🔖 {result_text}
📧 {final_contact}
📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            # 화면 출력
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}일주'** 입니다.")
            st.info(f"당신의 사주팔자: {result_text}")
            
            # 해석 박스
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="color:#333;">📜 {day_pillar}일주 성향 분석</h4>
                <p style="font-size:16px;">{my_interpretation}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("📊 **오행 에너지 분포 (연/월/일/시 종합)**")
            chart = draw_pretty_chart(scores)
            st.altair_chart(chart, use_container_width=True)
            
            st.caption("※ 월주는 절기일(보통 매월 4~8일)을 기준으로 하므로, 절기 당일에 태어나신 분은 실제 만세력과 약간의 차이가 있을 수 있습니다.")
