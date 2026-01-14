import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="익명 철학원", page_icon="🔮")

# ---------------------------------------------------------
# [나만의 일주 해석 사전]
# ---------------------------------------------------------
ilju_data = {
    "갑자": "큰 나무가 차가운 물 위에 떠 있는 형상. 지혜롭고 인정이 많으나 고독할 수 있음.",
    "을축": "언 땅에 핀 꽃. 끈기가 강하고 생활력이 좋으나 속마음을 잘 드러내지 않음.",
    # ... 필요한 만큼 채우세요 ...
}
default_desc = "아직 설명이 업데이트되지 않았습니다. 운영자가 직접 풀이해 드릴게요!"

# ---------------------------------------------------------
# [핵심] 사주팔자 계산 & 점수 로직 (고급)
# ---------------------------------------------------------
class SajuCalculator:
    def __init__(self):
        self.gan = list("갑을병정무기경신임계")
        self.ji = list("자축인묘진사오미신유술해")
        self.month_ji = list("인묘진사오미신유술해자축")
        
        # 오행 매핑
        self.gan_elements = {
            "갑": "목", "을": "목", "병": "화", "정": "화", "무": "토", "기": "토", 
            "경": "금", "신": "금", "임": "수", "계": "수"
        }
        self.ji_elements = {
            "인": "목", "묘": "목", "사": "화", "오": "화", "진": "토", "술": "토", 
            "축": "토", "미": "토", "신": "금", "유": "금", "해": "수", "자": "수"
        }
        
        # 오행 상생상극 (키가 값을 생함: 목생화)
        self.saeng = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
        # (키가 값을 극함: 목극토)
        self.geuk = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

    def get_60ganji(self, gan_idx, ji_idx):
        return self.gan[gan_idx % 10] + self.ji[ji_idx % 12]

    # ... (연주, 월주, 일주, 시주 계산 로직은 이전과 동일) ...
    def get_year_pillar(self, year):
        idx = (year - 1984) % 60
        return self.get_60ganji(idx % 10, idx % 12)

    def get_month_pillar(self, year_pillar, date_obj):
        year_gan = year_pillar[0]
        month = date_obj.month
        day = date_obj.day
        if day < 6:
            month -= 1
            if month == 0: month = 12
        saju_month_idx = (month - 2) % 12
        month_ji_char = self.month_ji[saju_month_idx]
        year_gan_idx = self.gan.index(year_gan)
        start_gan_idx = (year_gan_idx % 5) * 2 + 2
        month_gan_idx = (start_gan_idx + saju_month_idx) % 10
        return self.gan[month_gan_idx] + month_ji_char

    def get_day_pillar(self, date_obj):
        base_date = datetime(1900, 1, 1)
        days_diff = (date_obj - base_date).days
        idx = (10 + days_diff) % 60
        return self.get_60ganji(idx % 10, idx % 12)

    def get_time_pillar(self, day_pillar, hour):
        day_gan = day_pillar[0]
        time_idx = (hour + 1) // 2 % 12
        day_gan_idx = self.gan.index(day_gan)
        start_gan_idx = (day_gan_idx % 5) * 2
        time_gan_idx = (start_gan_idx + time_idx) % 10
        return self.gan[time_gan_idx] + self.ji[time_idx]

    # 🌟 [업그레이드] 위치별 가중치 점수 계산
    def calculate_weighted_scores(self, pillars):
        # pillars 순서: [연주, 월주, 일주, 시주] (각 2글자)
        # 위치별 점수표 (요청하신 기준)
        # 순서: [연간, 연지], [월간, 월지], [일간, 일지], [시간, 시지]
        weights = [
            [10, 7],   # 연주 (Stem, Branch)
            [17, 15],  # 월주
            [50, 20],  # 일주 (일간 50점!)
            [10, 5]    # 시주
        ]
        
        # 1. 일간의 오행 찾기 (기준점)
        day_gan = pillars[2][0] 
        my_element = self.gan_elements[day_gan]
        
        element_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        total_strength_score = 0 # 신강/신약 판별용 점수 (플러스/마이너스 합산)
        
        # 2. 8글자 전체 순회하며 점수 계산
        for i, pillar in enumerate(pillars): # 연/월/일/시
            for j, char in enumerate(pillar): # 간/지
                weight = weights[i][j] # 해당 위치의 점수 (예: 일간이면 50)
                
                # 글자의 오행 찾기
                if char in self.gan_elements:
                    elem = self.gan_elements[char]
                else:
                    elem = self.ji_elements[char]
                
                # [그래프용] 오행 세력 점수 (절대값 누적) -> "어떤 오행이 가장 센가?"
                element_scores[elem] += weight

                # [신강/신약 판별용] 내 편(+), 남의 편(-) 계산
                # 1. 나와 같은 오행 (비겁) -> 내 편 (+)
                if elem == my_element:
                    total_strength_score += weight
                # 2. 나를 생해주는 오행 (인성) -> 내 편 (+)
                elif self.saeng[elem] == my_element:
                    total_strength_score += weight
                # 3. 내가 생하는 오행 (식상) -> 힘빠짐 (-)
                elif self.saeng[my_element] == elem:
                    total_strength_score -= weight
                # 4. 내가 극하는 오행 (재성) -> 힘빠짐 (-)
                elif self.geuk[my_element] == elem:
                    total_strength_score -= weight
                # 5. 나를 극하는 오행 (관성) -> 힘빠짐 (-)
                elif self.geuk[elem] == my_element:
                    total_strength_score -= weight

        return element_scores, total_strength_score, my_element

# ---------------------------------------------------------
# [기능] 차트 & 알림
# ---------------------------------------------------------
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception: pass

def draw_pretty_chart(scores, my_element):
    df = pd.DataFrame(list(scores.items()), columns=["오행", "점수"])
    
    # 내 일간(기준)은 별도로 표시하거나 강조할 수 있음
    domain = ["목", "화", "토", "금", "수"]
    range_ = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    
    chart = alt.Chart(df).mark_bar(cornerRadius=10).encode(
        x=alt.X('오행', sort=None),
        y=alt.Y('점수', title='세력 점수'),
        color=alt.Color('오행', scale=alt.Scale(domain=domain, range=range_), legend=None),
        tooltip=['오행', '점수']
    ).properties(height=250).configure_axis(grid=False).configure_view(strokeWidth=0)
    
    return chart

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 정밀 사주풀이")
st.markdown("##### 사주 8글자의 위치별 세력을 정밀 분석합니다.")

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
    
    submitted = st.form_submit_button("정밀 분석 결과 보기")

    if submitted:
        if not concern:
            st.error("고민 내용을 적어주세요!")
        elif not nickname:
            st.error("닉네임을 적어주세요!")
        else:
            # 1. 사주 계산
            year_pillar = calc.get_year_pillar(birth_date.year)
            month_pillar = calc.get_month_pillar(year_pillar, birth_date)
            day_pillar = calc.get_day_pillar(datetime.combine(birth_date, birth_time))
            
            if not is_unknown_time:
                time_pillar = calc.get_time_pillar(day_pillar, birth_time.hour)
                pillars = [year_pillar, month_pillar, day_pillar, time_pillar]
                result_text = f"연주:{year_pillar} / 월주:**{month_pillar}** / 일주:**{day_pillar}** / 시주:{time_pillar}"
            else:
                pillars = [year_pillar, month_pillar, day_pillar, ["??", "??"]] # 시간 제외
                result_text = f"연주:{year_pillar} / 월주:**{month_pillar}** / 일주:**{day_pillar}**"

            # 2. 점수 계산 (여기가 핵심!)
            # element_scores: 오행별 세력 크기 (그래프용)
            # strength_score: 신강/신약 판별 점수 (+면 신강, -면 신약)
            element_scores, strength_score, my_elem = calc.calculate_weighted_scores(pillars)
            
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            # 신강/신약 텍스트 판별
            if strength_score > 20: power_desc = "매우 신강한 사주 (자존감과 주관이 아주 뚜렷함)"
            elif strength_score > 0: power_desc = "약간 신강한 사주 (주도적인 성향)"
            elif strength_score > -20: power_desc = "약간 신약한 사주 (주변과 조화를 중시)"
            else: power_desc = "매우 신약한 사주 (섬세하고 환경에 민감)"

            # 디스코드 전송
            final_contact = contact if contact else "블로그 게시 희망"
            msg = f"""
**[🔮 정밀 점수 상담]**
👤 {nickname} ({gender})
🔖 {result_text}
📊 신강/신약 점수: {strength_score} ({power_desc})
📧 {final_contact}
📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            # 결과 화면
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}일주'** 입니다.")
            st.info(f"사주 구성: {result_text}")
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="color:#333;">📜 {day_pillar}일주 성향</h4>
                <p>{my_interpretation}</p>
                <hr>
                <p><b>💡 에너지 분석:</b> {power_desc}</p>
                <p style='font-size:12px; color:gray;'>* 일간(50점)과 주변 글자의 생극제화를 수치로 계산한 결과입니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader(f"📊 {nickname}님의 오행 세력 그래프")
            st.caption(f"본인(일간)인 '{my_elem}'을 포함하여, 사주 내에서 각 오행이 차지하는 힘의 크기입니다.")
            chart = draw_pretty_chart(element_scores, my_elem)
            st.altair_chart(chart, use_container_width=True)
