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
# [핵심] 사주팔자 계산기 (충 + 합 로직 탑재)
# ---------------------------------------------------------
class SajuCalculator:
    def __init__(self):
        self.gan = list("갑을병정무기경신임계")
        self.ji = list("자축인묘진사오미신유술해")
        self.month_ji = list("인묘진사오미신유술해자축")
        
        self.gan_elements = {
            "갑": "목", "을": "목", "병": "화", "정": "화", "무": "토", "기": "토", 
            "경": "금", "신": "금", "임": "수", "계": "수"
        }
        self.ji_elements = {
            "인": "목", "묘": "목", "사": "화", "오": "화", "진": "토", "술": "토", 
            "축": "토", "미": "토", "신": "금", "유": "금", "해": "수", "자": "수"
        }
        
        self.saeng = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
        self.geuk = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

        # 1. 충(Clash) 규칙
        self.chung_rules = {
            frozenset(["갑", "경"]): 8, frozenset(["을", "신"]): 5,
            frozenset(["병", "임"]): 8, frozenset(["정", "계"]): 5,
            frozenset(["무", "갑"]): 3, frozenset(["기", "계"]): 3
        }
        
        # 2. 합(Hap) 규칙 (사용자 정의 점수)
        # 키: 두 글자 세트, 값: {오행: 변화량, ...}
        self.hap_rules = {
            frozenset(["갑", "기"]): {"토": 8, "목": -5},
            frozenset(["을", "경"]): {"금": 8, "목": -5},
            frozenset(["병", "신"]): {"수": 5, "화": -3, "금": -3},
            frozenset(["정", "임"]): {"목": 5, "화": 3, "수": -3},
            frozenset(["무", "계"]): {"화": 5, "토": 3, "수": -3}
        }

    def get_60ganji(self, gan_idx, ji_idx):
        return self.gan[gan_idx % 10] + self.ji[ji_idx % 12]

    # ... (연,월,일,시주 계산 함수들은 기존과 동일) ...
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

    # 🌟 [최종 업그레이드] 충 + 합 반영 점수 계산
    def calculate_weighted_scores(self, pillars):
        base_weights = [[10, 7], [17, 15], [50, 20], [10, 5]]
        
        day_gan = pillars[2][0] 
        my_element = self.gan_elements[day_gan]
        
        element_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        total_strength_score = 0
        logs = [] # 충/합 발생 기록

        # 1. 기본 점수 계산 & 신강신약 1차 판별
        for i, pillar in enumerate(pillars):
            for j, char in enumerate(pillar):
                weight = base_weights[i][j]
                elem = self.gan_elements.get(char, self.ji_elements.get(char))
                
                element_scores[elem] += weight
                
                # 신강/신약 계산
                if elem == my_element: total_strength_score += weight
                elif self.saeng[elem] == my_element: total_strength_score += weight
                elif self.saeng[my_element] == elem: total_strength_score -= weight
                elif self.geuk[my_element] == elem: total_strength_score -= weight
                elif self.geuk[elem] == my_element: total_strength_score -= weight

        # 2. ⚡ 충(Clash) 반영
        for i, pillar in enumerate(pillars):
            if i != 2: # 일간 본인이 아닐 때
                char = pillar[0]
                pair = frozenset([day_gan, char])
                if pair in self.chung_rules:
                    penalty = self.chung_rules[pair]
                    element_scores[my_element] -= penalty
                    total_strength_score -= penalty
                    logs.append(f"💥 '{char}'와 충(Clash)! 내 기운 -{penalty}")

        # 3. 💖 합(Hap) 반영 (NEW!)
        # 천간 4글자 추출
        stems = [p[0] for p in pillars if p[0] != "?"]
        
        # 정의된 합 규칙을 하나씩 체크
        for pair, changes in self.hap_rules.items():
            # pair(두 글자)가 stems 리스트 안에 모두 들어있는지 확인
            if pair.issubset(set(stems)):
                pair_str = "+".join(pair)
                logs.append(f"💖 천간합({pair_str}) 성립!")
                
                for elem, score in changes.items():
                    # (1) 오행 점수 수정
                    element_scores[elem] += score
                    
                    # (2) 신강/신약 점수 재계산 (변화량에 따라)
                    # 점수가 추가(Positive)된 경우
                    if score > 0:
                        if elem == my_element or self.saeng[elem] == my_element:
                            total_strength_score += score # 내 편이 늘어남 -> 신강해짐
                        else:
                            total_strength_score -= score # 적군이 늘어남 -> 신약해짐
                    
                    # 점수가 감소(Negative)된 경우
                    else:
                        abs_score = abs(score)
                        if elem == my_element or self.saeng[elem] == my_element:
                            total_strength_score -= abs_score # 내 편이 줄어듦 -> 신약해짐
                        else:
                            total_strength_score += abs_score # 적군이 줄어듦 -> 신강해짐
                    
                    # 로그에 상세 내용 기록
                    sign = "+" if score > 0 else ""
                    logs.append(f"   -> {elem} {sign}{score}점")

        return element_scores, total_strength_score, my_element, logs

# ---------------------------------------------------------
# [기능] 차트 & 전송
# ---------------------------------------------------------
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception: pass

def draw_pretty_chart(scores, my_elem):
    df = pd.DataFrame(list(scores.items()), columns=["오행", "점수"])
    domain = ["목", "화", "토", "금", "수"]
    range_ = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    chart = alt.Chart(df).mark_bar(cornerRadius=10).encode(
        x=alt.X('오행', sort=None),
        y=alt.Y('점수', title='최종 세력 (충/합 반영)'),
        color=alt.Color('오행', scale=alt.Scale(domain=domain, range=range_), legend=None),
        tooltip=['오행', '점수']
    ).properties(height=250).configure_axis(grid=False).configure_view(strokeWidth=0)
    return chart

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 정밀 사주풀이")
st.markdown("##### [충]과 [합]의 상호작용까지 계산하는 완성형 만세력")

calc = SajuCalculator()

with st.form("saju_form", clear_on_submit=False):
    nickname = st.text_input("닉네임", placeholder="예: 도깨비")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    col1, col2 = st.columns(2)
    with col1: birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    with col2: birth_time = st.time_input("태어난 시간")
    is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    concern = st.text_area("고민 내용", height=150)
    contact = st.text_input("이메일 (선택)", placeholder="답변 받을 연락처")
    submitted = st.form_submit_button("최종 정밀 분석 보기")

    if submitted:
        if not concern: st.error("고민 내용을 적어주세요!")
        elif not nickname: st.error("닉네임을 적어주세요!")
        else:
            year_pillar = calc.get_year_pillar(birth_date.year)
            month_pillar = calc.get_month_pillar(year_pillar, birth_date)
            day_pillar = calc.get_day_pillar(datetime.combine(birth_date, birth_time))
            
            if not is_unknown_time:
                time_pillar = calc.get_time_pillar(day_pillar, birth_time.hour)
                pillars = [year_pillar, month_pillar, day_pillar, time_pillar]
                result_text = f"연주:{year_pillar} / 월주:**{month_pillar}** / 일주:**{day_pillar}** / 시주:{time_pillar}"
            else:
                pillars = [year_pillar, month_pillar, day_pillar, ["??", "??"]]
                result_text = f"연주:{year_pillar} / 월주:**{month_pillar}** / 일주:**{day_pillar}**"

            # 🌟 [계산] 충+합 반영
            element_scores, strength_score, my_elem, logs = calc.calculate_weighted_scores(pillars)
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            if strength_score > 20: power_desc = "매우 신강 (주관 뚜렷)"
            elif strength_score > 0: power_desc = "약간 신강 (주도적)"
            elif strength_score > -20: power_desc = "약간 신약 (조화 중시)"
            else: power_desc = "매우 신약 (환경 민감)"
            
            log_text = "\n".join(logs) if logs else "특이사항 없음"
            final_contact = contact if contact else "블로그 게시 희망"
            
            msg = f"""
**[🔮 최종 정밀 상담]**
👤 {nickname} ({gender})
🔖 {result_text}
📊 점수: {strength_score} ({power_desc})
📝 특이사항: {log_text}
📧 {final_contact}
📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}'** 입니다.")
            
            # 특이사항(충, 합) 보여주기
            if logs:
                st.warning(f"💡 **사주 내 화학반응(충/합) 발견!**\n\n" + "\n".join([f"- {log}" for log in logs]))
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="color:#333;">📜 {day_pillar}일주 분석</h4>
                <p>{my_interpretation}</p>
                <hr>
                <p><b>💡 최종 에너지 점수:</b> {strength_score}점 ({power_desc})</p>
                <p style='font-size:12px; color:gray;'>* 충(Clash)과 합(Hap)으로 인한 오행의 증감까지 모두 반영된 수치입니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader(f"📊 오행 세력 그래프")
            chart = draw_pretty_chart(element_scores, my_elem)
            st.altair_chart(chart, use_container_width=True)
