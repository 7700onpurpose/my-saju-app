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
    "신사": "용광로 속의 보석. 예리하고 섬세하지만, 속으로는 뜨거운 열정(혹은 스트레스)을 품고 있음.",
    # ... 필요한 만큼 채우세요 ...
}
default_desc = "아직 설명이 업데이트되지 않았습니다. 업데이트를 기다려 주세요."

# ---------------------------------------------------------
# [핵심] 사주팔자 계산기
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

        self.chung_rules = {
            frozenset(["갑", "경"]): 8, frozenset(["을", "신"]): 5,
            frozenset(["병", "임"]): 8, frozenset(["정", "계"]): 5,
            frozenset(["무", "갑"]): 3, frozenset(["기", "계"]): 3
        }
        self.hap_rules = {
            frozenset(["갑", "기"]): {"토": 8, "목": -5},
            frozenset(["을", "경"]): {"금": 8, "목": -5},
            frozenset(["병", "신"]): {"수": 5, "화": -3, "금": -3},
            frozenset(["정", "임"]): {"목": 5, "화": 3, "수": -3},
            frozenset(["무", "계"]): {"화": 5, "토": 3, "수": -3}
        }
        self.jiji_chung_rules = [
            ({"자", "오"}, "수", "화", 7), ({"묘", "유"}, "목", "금", 5), ({"사", "해"}, "화", "수", 8)
        ]
        self.samhap_rules = {
            "목": {"members": {"해", "묘", "미"}, "name": "해묘미"},
            "화": {"members": {"인", "오", "술"}, "name": "인오술"},
            "금": {"members": {"사", "유", "축"}, "name": "사유축"},
            "수": {"members": {"신", "자", "진"}, "name": "신자진"}
        }
        self.banghap_rules = {
            "목": {"members": {"인", "묘", "진"}, "name": "인묘진"},
            "화": {"members": {"사", "오", "미"}, "name": "사오미"},
            "금": {"members": {"신", "유", "술"}, "name": "신유술"},
            "수": {"members": {"해", "자", "축"}, "name": "해자축"}
        }

    def get_60ganji(self, gan_idx, ji_idx): return self.gan[gan_idx % 10] + self.ji[ji_idx % 12]
    def get_year_pillar(self, year): return self.get_60ganji((year - 1984) % 60 % 10, (year - 1984) % 60 % 12)
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
        days_diff = (date_obj - datetime(1900, 1, 1)).days
        return self.get_60ganji((10 + days_diff) % 60 % 10, (10 + days_diff) % 60 % 12)
    def get_time_pillar(self, day_pillar, hour):
        day_gan = day_pillar[0]
        time_idx = (hour + 1) // 2 % 12
        day_gan_idx = self.gan.index(day_gan)
        start_gan_idx = (day_gan_idx % 5) * 2
        return self.gan[(start_gan_idx + time_idx) % 10] + self.ji[time_idx]

    def calculate_weighted_scores(self, pillars):
        base_weights = [[10, 7], [17, 15], [20, 20], [10, 5]]
        
        day_gan = pillars[2][0] 
        my_element = self.gan_elements[day_gan]
        
        element_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        jiji_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        total_strength_score = 0
        logs = [] 

        # Step 1: 기본 점수
        for i, pillar in enumerate(pillars):
            for j, char in enumerate(pillar):
                weight = base_weights[i][j]
                elem = self.gan_elements.get(char, self.ji_elements.get(char))
                element_scores[elem] += weight
                if j == 1: jiji_scores[elem] += weight
                
                if elem == my_element: total_strength_score += weight
                elif self.saeng[elem] == my_element: total_strength_score += weight
                elif self.saeng[my_element] == elem: total_strength_score -= weight
                elif self.geuk[my_element] == elem: total_strength_score -= weight
                elif self.geuk[elem] == my_element: total_strength_score -= weight

        # Step 2: 천간충
        for i, pillar in enumerate(pillars):
            if i != 2:
                pair = frozenset([day_gan, pillar[0]])
                if pair in self.chung_rules:
                    penalty = self.chung_rules[pair]
                    element_scores[my_element] -= penalty
                    total_strength_score -= penalty
                    logs.append(f"💥 천간충('{pillar[0]}')! 내 기운 -{penalty}")

        # Step 3: 천간합
        stems = [p[0] for p in pillars if p[0] != "?"]
        for pair, changes in self.hap_rules.items():
            if pair.issubset(set(stems)):
                for elem, score in changes.items():
                    element_scores[elem] += score
                    if score > 0:
                        if elem == my_element or self.saeng[elem] == my_element: total_strength_score += score
                        else: total_strength_score -= score
                logs.append(f"💖 천간합({'+'.join(pair)}) 성립!")

        # Step 4: 지지충
        branches = [p[1] for p in pillars if p[1] != "?"]
        branches_set = set(branches)
        for rule_set, e1, e2, sc in self.jiji_chung_rules:
            if rule_set.issubset(branches_set):
                w, l = (e1, e2) if jiji_scores[e1] >= jiji_scores[e2] else (e2, e1)
                element_scores[w] += sc
                element_scores[l] -= sc
                logs.append(f"⚔️ 지지충 승자:{w}(+{sc})")
                if w == my_element or self.saeng[w] == my_element: total_strength_score += sc
                else: total_strength_score -= sc
                if l == my_element or self.saeng[l] == my_element: total_strength_score -= sc
                else: total_strength_score += sc

        # Step 5: 삼합/방합
        for rules in [self.samhap_rules, self.banghap_rules]:
            for target, rule in rules.items():
                cnt = len(rule["members"].intersection(branches_set))
                add = 10 if cnt == 3 else (6 if cnt == 2 else 0)
                if add > 0:
                    element_scores[target] += add
                    logs.append(f"🌀 {rule['name']} +{add}")
                    if target == my_element or self.saeng[target] == my_element: total_strength_score += add
                    else: total_strength_score -= add

        # Step 6: 병존
        for seq in [stems, branches]:
            for k in range(len(seq)-1):
                if seq[k] == seq[k+1] and seq[k] != "?":
                    elem = self.gan_elements.get(seq[k], self.ji_elements.get(seq[k]))
                    element_scores[elem] += 10
                    logs.append(f"👯 병존({seq[k]}) +10")
                    if elem == my_element or self.saeng[elem] == my_element: total_strength_score += 10
                    else: total_strength_score -= 10

        # Step 7: Top 2 Battle
        sorted_scores = sorted(element_scores.items(), key=lambda x: x[1], reverse=True)
        top1_elem = sorted_scores[0][0]
        top2_elem = sorted_scores[1][0]
        battle_log = ""
        bonus = 10
        
        if self.geuk[top1_elem] == top2_elem:
            element_scores[top1_elem] += bonus
            element_scores[top2_elem] -= bonus
            battle_log = f"1위({top1_elem})가 2위({top2_elem})를 제압하여 격차 벌어짐"
        elif self.geuk[top2_elem] == top1_elem:
            element_scores[top2_elem] += bonus
            element_scores[top1_elem] -= bonus
            battle_log = f"2위({top2_elem})가 1위({top1_elem})를 맹렬히 공격! (하극상)"
            if top1_elem == my_element: total_strength_score -= bonus
            if top2_elem == my_element: total_strength_score += bonus
        elif self.saeng[top1_elem] == top2_elem:
            element_scores[top1_elem] -= 5
            element_scores[top2_elem] += 10
            battle_log = f"1위({top1_elem})가 2위({top2_elem})를 생하여 기운 설기됨"

        if battle_log: logs.append(f"🏆 **세력전쟁:** {battle_log}")

        return element_scores, total_strength_score, my_element, logs

# ---------------------------------------------------------
# [기능] 차트 (오류 수정됨: transform_filter 사용)
# ---------------------------------------------------------
def send_discord_message(msg):
    try:
        url = st.secrets["discord_url"]
        payload = {"content": msg}
        requests.post(url, json=payload)
    except Exception: pass

def draw_pie_chart(scores):
    # 1. 데이터 프레임 변환
    data = []
    for elem, score in scores.items():
        safe_score = max(0, score)
        data.append({"오행": elem, "점수": safe_score})
    
    df = pd.DataFrame(data)
    
    # 2. 비율 계산
    total = df["점수"].sum()
    if total == 0: total = 1
    df["비율"] = df["점수"] / total
    
    # 3. 차트 생성
    domain = ["목", "화", "토", "금", "수"]
    range_ = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    
    base = alt.Chart(df).encode(
        theta=alt.Theta("점수", stack=True)
    )
    
    pie = base.mark_arc(innerRadius=60, outerRadius=120).encode(
        color=alt.Color("오행", scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title="오행")),
        order=alt.Order("점수", sort="descending"),
        tooltip=["오행", "점수", alt.Tooltip("비율", format=".1%")]
    )
    
    # 🚨 [수정된 부분] .filter() 대신 .transform_filter() 사용
    text = base.mark_text(radius=140).encode(
        text=alt.Text("비율", format=".1%"),
        order=alt.Order("점수", sort="descending"),
        color=alt.value("black")
    ).transform_filter(
        alt.datum.비율 > 0.05
    )
    
    return pie + text

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 온라인 사주풀이 철학원")
st.markdown("##### 익명 보장 온라인 철학원입니다. 사주팔자를 면밀히 분석하여 정확하게 분석합니다. 특별한 고민이 있다면 위안을 얻어보세요.")

calc = SajuCalculator()

with st.form("saju_form", clear_on_submit=False):
    nickname = st.text_input("닉네임", placeholder="예: 도깨비")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    col1, col2 = st.columns(2)
    with col1: birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    with col2: birth_time = st.time_input("태어난 시간")
    is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    concern = st.text_area("고민이 있다면 적어주세요. 사주를 바탕으로 한 답변을 드립니다. ", height=150)
    contact = st.text_input("고민에 대한 상세한 답변을 받아보실 이메일을 적어주세요.", placeholder="답변 받을 이메일")
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

            # 🌟 [계산]
            element_scores, strength_score, my_elem, logs = calc.calculate_weighted_scores(pillars)
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            if strength_score > 20: power_desc = "극신강"
            elif strength_score > 0: power_desc = "신강"
            elif strength_score > -20: power_desc = "신약"
            else: power_desc = "극신약"
            
            log_text = "\n".join(logs) if logs else "특이사항 없음"
            final_contact = contact if contact else " "
            
            msg = f"""
**[🔮 퍼센트 분석 상담]**
👤 {nickname} ({gender})
🔖 {result_text}
📊 점수: {strength_score} ({power_desc})
🏆 세력전: {log_text}
📧 {final_contact}
📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}'일주** 입니다.")
            
            if logs:
                st.warning(f"🏆 **오행 세력 전쟁 리포트**\n\n" + "\n".join([f"- {log}" for log in logs]))
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="color:#333;">📜 {day_pillar}일주 분석</h4>
                <p>{my_interpretation}</p>
                <hr>
                <p><b>💡 최종 에너지 점수:</b> {strength_score}점 ({power_desc})</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader(f"📊 오행 세력 분포 (퍼센트)")
            chart = draw_pie_chart(element_scores)
            st.altair_chart(chart, use_container_width=True)


