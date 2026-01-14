import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# ---------------------------------------------------------
# [핵심] 사주팔자 계산 로직 (여기가 진짜입니다!)
# ---------------------------------------------------------
class SajuCalculator:
    def __init__(self):
        self.gan = list("갑을병정무기경신임계")
        self.ji = list("자축인묘진사오미신유술해")
        self.gan_colors = {"갑": "목(초록)", "을": "목(초록)", "병": "화(빨강)", "정": "화(빨강)", 
                           "무": "토(노랑)", "기": "토(노랑)", "경": "금(흰색)", "신": "금(흰색)", 
                           "임": "수(검정)", "계": "수(검정)"}
        self.ji_colors = {"인": "목", "묘": "목", "사": "화", "오": "화", 
                          "진": "토", "술": "토", "축": "토", "미": "토", 
                          "신": "금", "유": "금", "해": "수", "자": "수"}
        
    def get_60ganji(self, index):
        return self.gan[index % 10] + self.ji[index % 12]

    # 1. 연주 (태어난 해)
    def get_year_pillar(self, year):
        # 1984년이 갑자년(0번) 기준
        idx = (year - 1984) % 60
        return self.get_60ganji(idx)

    # 2. 일주 (태어난 날) - 가장 중요!
    def get_day_pillar(self, date_obj):
        # 1900년 1월 1일은 '갑술일(10번)' 입니다. 기준점 잡기.
        base_date = datetime(1900, 1, 1)
        days_diff = (date_obj - base_date).days
        idx = (10 + days_diff) % 60 
        return self.get_60ganji(idx)

    # 3. 시주 (태어난 시간)
    def get_time_pillar(self, day_gan, hour):
        # 시간 지지 찾기 (자시, 축시...)
        # 23:30~01:29 = 자시 (0번)
        time_idx = (hour + 1) // 2 % 12
        time_ji = self.ji[time_idx]
        
        # 시간 천간 찾기 (일간에 따라 달라짐 - 시두법)
        day_gan_idx = self.gan.index(day_gan)
        start_gan_idx = (day_gan_idx % 5) * 2
        time_gan = self.gan[(start_gan_idx + time_idx) % 10]
        
        return time_gan + time_ji

    # 4. 오행 점수 합산 (글자 4~6개 분석)
    def calculate_elements(self, pillars):
        scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        
        # 모든 글자(천간, 지지)를 분해해서 점수 매기기
        all_chars = "".join(pillars) # 예: "갑자병인..."
        
        for char in all_chars:
            # 천간 색상에서 오행 찾기
            if char in self.gan_colors:
                elem = self.gan_colors[char].split("(")[0]
                scores[elem] += 10
            # 지지 색상에서 오행 찾기
            elif char in self.ji_colors:
                elem = self.ji_colors[char]
                scores[elem] += 10
                
        return scores

# ---------------------------------------------------------
# [기능] 디스코드 알림
# ---------------------------------------------------------
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception:
        pass

# ---------------------------------------------------------
# [기능] 예쁜 차트
# ---------------------------------------------------------
def draw_pretty_chart(scores):
    df = pd.DataFrame(list(scores.items()), columns=["오행", "점수"])
    domain = ["목", "화", "토", "금", "수"]
    range_ = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    
    chart = alt.Chart(df).mark_bar(cornerRadius=10).encode(
        x=alt.X('오행', sort=None),
        y='점수',
        color=alt.Color('오행', scale=alt.Scale(domain=domain, range=range_), legend=None),
        tooltip=['오행', '점수']
    ).properties(height=250).configure_axis(grid=False).configure_view(strokeWidth=0)
    return chart

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 온라인 철학원")
st.markdown("##### 당신의 '일주(타고난 기운)'를 분석해드립니다.")
st.caption("정확한 생년월일시를 입력하면 오행 분포를 계산해 드려요!")

calc = SajuCalculator() # 계산기 준비

with st.form("saju_form", clear_on_submit=False):
    nickname = st.text_input("닉네임", placeholder="예: 도깨비")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    
    # 날짜 시간 입력
    col1, col2 = st.columns(2)
    with col1:
        birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    with col2:
        birth_time = st.time_input("태어난 시간")
    is_unknown_time = st.checkbox("태어난 시간을 몰라요 (체크 시 시간 제외하고 분석)")
    
    concern = st.text_area("고민 내용", height=150)
    contact = st.text_input("답변 받을 이메일", placeholder="답변 받을 연락처")
    
    submitted = st.form_submit_button("내 일주 확인하고 상담받기")

    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        elif not nickname:
            st.error("닉네임을 적어주세요!")
        else:
            # 1. 사주 글자 뽑아내기
            year_pillar = calc.get_year_pillar(birth_date.year) # 연주
            day_pillar = calc.get_day_pillar(datetime.combine(birth_date, birth_time)) # 일주 (핵심)
            
            if not is_unknown_time:
                # 일간(Day Stem)을 기준으로 시주 계산
                day_gan = day_pillar[0] 
                time_pillar = calc.get_time_pillar(day_gan, birth_time.hour)
                pillars = [year_pillar, day_pillar, time_pillar]
                result_text = f"연주: {year_pillar} / **일주: {day_pillar}** / 시주: {time_pillar}"
            else:
                pillars = [year_pillar, day_pillar]
                result_text = f"연주: {year_pillar} / **일주: {day_pillar}**"

            # 2. 오행 점수 계산
            scores = calc.calculate_elements(pillars)
            
            # 3. 디스코드 전송
            final_contact = contact if contact else "블로그 게시 희망"
            msg = f"""
**[🔮 정밀 상담 신청란입니다. 고민을 적어주세요.]**
👤 {nickname} ({gender})
📅 {birth_date} {str(birth_time)[:5]}
🔖 **사주결과**: {result_text}
📧 {final_contact}

📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            # 4. 결과 화면
            st.success(f"✅ 접수되었습니다! {nickname}님은 **'{day_pillar}'** 이시군요!")
            st.info(f"당신의 사주 구성: {result_text}")
            
            st.markdown("---")
            st.write("📊 **당신의 오행 에너지 분포** (연/일/시 종합)")
            chart = draw_pretty_chart(scores)
            st.altair_chart(chart, use_container_width=True)
            
            # 일주에 대한 간단 코멘트 (재미 요소)
            st.markdown(f"""
            > **Tip:** 당신은 **'{day_pillar[0]}({calc.gan_colors[day_pillar[0]]})'**의 기운을 타고난 **'{day_pillar}'** 입니다. 
            운영자가 이 정보를 바탕으로 더 깊이 있는 풀이를 보내드릴게요! 🍀
            """)

