import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="익명 철학원", page_icon="🔮", layout="wide")

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
        
        self.gan_info = {
            "갑": ("목", 0), "을": ("목", 1), "병": ("화", 0), "정": ("화", 1),
            "무": ("토", 0), "기": ("토", 1), "경": ("금", 0), "신": ("금", 1),
            "임": ("수", 0), "계": ("수", 1)
        }
        
        self.ji_info = {
            "자": ("수", 1), "축": ("토", 1), "인": ("목", 0), "묘": ("목", 1),
            "진": ("토", 0), "사": ("화", 0), "오": ("화", 1), "미": ("토", 1), 
            "신": ("금", 0), "유": ("금", 1), "술": ("토", 0), "해": ("수", 0)
        }
        
        self.gan_elements = {k: v[0] for k, v in self.gan_info.items()}
        self.ji_elements = {k: v[0] for k, v in self.ji_info.items()}
        
        self.saeng = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
        self.geuk = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

        self.chung_rules = {
            frozenset(["갑", "경"]): 8, frozenset(["을", "신"]): 5,
            frozenset(["병", "임"]): 8, frozenset(["정", "계"]): 5,
            frozenset(["무", "갑"]): 8, frozenset(["기", "계"]): 3
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
    
    def get_year_pillar(self, year): 
        return self.get_60ganji((year - 1984) % 60 % 10, (year - 1984) % 60 % 12)
        
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
        time_idx = hour // 2 % 12
        day_gan_idx = self.gan.index(day_gan)
        start_gan_idx = (day_gan_idx % 5) * 2
        return self.gan[(start_gan_idx + time_idx) % 10] + self.ji[time_idx]

    # 🌟 [NEW] 대운(10년 운) 계산 함수
    def get_daewun(self, year_pillar, month_pillar, gender, birth_date):
        is_male = (gender == "남성")
        year_stem = year_pillar[0]
        year_stem_idx = self.gan.index(year_stem)
        is_yang_year = (year_stem_idx % 2 == 0) # 양간 여부
        
        # 순행(1) / 역행(-1) 결정 로직
        if (is_male and is_yang_year) or (not is_male and not is_yang_year):
            direction = 1  # 순행
            daewun_num = (30 - birth_date.day) // 3
        else:
            direction = -1 # 역행
            daewun_num = birth_date.day // 3
            
        if daewun_num <= 0: daewun_num = 1
        if daewun_num > 10: daewun_num = 10
        
        m_gan_idx = self.gan.index(month_pillar[0])
        m_ji_idx = self.ji.index(month_pillar[1])
        
        daewuns = []
        for i in range(1, 9): # 8개의 대운 기둥 생성
            g_idx = (m_gan_idx + i * direction) % 10
            j_idx = (m_ji_idx + i * direction) % 12
            daewuns.append({
                "age": daewun_num + (i - 1) * 10,
                "pillar": self.gan[g_idx] + self.ji[j_idx]
            })
        return daewuns

    def get_ten_gods(self, day_gan, target_char):
        if target_char in ["?", "??"] or (target_char not in self.gan_info and target_char not in self.ji_info):
            return ""
        day_elem, day_pol = self.gan_info[day_gan]
        if target_char in self.gan_info:
            target_elem, target_pol = self.gan_info[target_char]
        else:
            target_elem, target_pol = self.ji_info[target_char]
            
        if day_elem == target_elem: return "비견" if day_pol == target_pol else "겁재"
        elif self.saeng[day_elem] == target_elem: return "식신" if day_pol == target_pol else "상관"
        elif self.geuk[day_elem] == target_elem: return "편재" if day_pol == target_pol else "정재"
        elif self.geuk[target_elem] == day_elem: return "편관" if day_pol == target_pol else "정관"
        elif self.saeng[target_elem] == day_elem: return "편인" if day_pol == target_pol else "정인"
        return ""

    def calculate_weighted_scores(self, pillars):
        base_weights = [[10, 7], [17, 15], [20, 20], [10, 5]]
        
        day_gan = pillars[2][0] 
        my_element = self.gan_elements[day_gan]
        
        element_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        jiji_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        total_strength_score = 0
        logs = [] 

        for i, pillar in enumerate(pillars):
            for j, char in enumerate(pillar):
                if char in ["?", "??"]: continue
                weight = base_weights[i][j]
                elem = self.gan_elements.get(char, self.ji_elements.get(char))
                element_scores[elem] += weight
                if j == 1: jiji_scores[elem] += weight
                
                if elem == my_element: total_strength_score += weight
                elif self.saeng[elem] == my_element: total_strength_score += weight
                elif self.saeng[my_element] == elem: total_strength_score -= weight
                elif self.geuk[my_element] == elem: total_strength_score -= weight
                elif self.geuk[elem] == my_element: total_strength_score -= weight

        for i, pillar in enumerate(pillars):
            if i != 2 and pillar[0] not in ["?", "??"]:
                pair = frozenset([day_gan, pillar[0]])
                if pair in self.chung_rules:
                    penalty = self.chung_rules[pair]
                    element_scores[my_element] -= penalty
                    total_strength_score -= penalty
                    logs.append(f"💥 천간충 ({day_gan} 💥 {pillar[0]})! 내 기운 -{penalty}")

        stems = [p[0] for p in pillars if p[0] not in ["?", "??"]]
        for pair, changes in self.hap_rules.items():
            if pair.issubset(set(stems)):
                for elem, score in changes.items():
                    element_scores[elem] += score
                    if score > 0:
                        if elem == my_element or self.saeng[elem] == my_element: total_strength_score += score
                        else: total_strength_score -= score
                logs.append(f"💖 천간합 ({' ❤️ '.join(pair)}) 성립!")

        branches = [p[1] for p in pillars if p[1] not in ["?", "??"]]
        branches_set = set(branches)
        for rule_set, e1, e2, sc in self.jiji_chung_rules:
            if rule_set.issubset(branches_set):
                w, l = (e1, e2) if jiji_scores[e1] >= jiji_scores[e2] else (e2, e1)
                element_scores[w] += sc
                element_scores[l] -= sc
                
                if w == my_element or self.saeng[w] == my_element: total_strength_score += sc
                else: total_strength_score -= sc
                if l == my_element or self.saeng[l] == my_element: total_strength_score -= sc
                else: total_strength_score += sc
                
                conflict_str = f"{list(rule_set)[0]} 💥 {list(rule_set)[1]}"
                logs.append(f"⚔️ 지지충 ({conflict_str})! 승자:{w}(+{sc})")

        for rules in [self.samhap_rules, self.banghap_rules]:
            for target, rule in rules.items():
                cnt = len(rule["members"].intersection(branches_set))
                add = 10 if cnt == 3 else (6 if cnt == 2 else 0)
                if add > 0:
                    element_scores[target] += add
                    matched = ",".join(rule["members"].intersection(branches_set))
                    logs.append(f"🌀 {rule['name']} ({matched}) +{add}")
                    
                    if target == my_element or self.saeng[target] == my_element: total_strength_score += add
                    else: total_strength_score -= add

        for seq in [stems, branches]:
            for k in range(len(seq)-1):
                if seq[k] == seq[k+1] and seq[k] not in ["?", "??"]:
                    elem = self.gan_elements.get(seq[k], self.ji_elements.get(seq[k]))
                    element_scores[elem] += 10
                    logs.append(f"👯 병존 ({seq[k]} 🤝 {seq[k]}) +10")
                    
                    if elem == my_element or self.saeng[elem] == my_element: total_strength_score += 10
                    else: total_strength_score -= 10

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
    
    def convert_to_sibseong(self, my_element, element_scores):
        sibseong_scores = {
            "비겁 (나/동료)": element_scores[my_element],
            "식상 (표현/재능)": element_scores[self.saeng[my_element]],
            "재성 (재물/결과)": element_scores[self.geuk[my_element]],
            "인성 (지혜/도움)": 0,
            "관성 (명예/직장)": 0
        }
        for key, value in self.saeng.items():
            if value == my_element:
                sibseong_scores["인성 (지혜/도움)"] = element_scores[key]; break
        for key, value in self.geuk.items():
            if value == my_element:
                sibseong_scores["관성 (명예/직장)"] = element_scores[key]; break
        return sibseong_scores

# ---------------------------------------------------------
# [기능] 차트 및 UI
# ---------------------------------------------------------
def draw_ohaeng_pie_chart(scores):
    data = []
    emoji_map = {"목": "🌲", "화": "🔥", "토": "⛰️", "금": "⚔️", "수": "🌊"}
    color_range = ["#66BB6A", "#EF5350", "#FFCA28", "#BDBDBD", "#42A5F5"]
    domain = ["목", "화", "토", "금", "수"]

    for elem, score in scores.items():
        safe_score = max(0, score)
        emoji = emoji_map.get(elem, "")
        data.append({"구분": elem, "점수": safe_score, "이모지": emoji})
    
    df = pd.DataFrame(data)
    total = df["점수"].sum()
    if total == 0: total = 1
    df["비율"] = df["점수"] / total
    df["라벨"] = df["이모지"] + " " + (df["비율"] * 100).round(1).astype(str) + "%"
    
    base = alt.Chart(df).encode(theta=alt.Theta("점수", stack=True))
    pie = base.mark_arc(innerRadius=55, outerRadius=110).encode(
        color=alt.Color("구분", scale=alt.Scale(domain=domain, range=color_range), legend=alt.Legend(title="오행")),
        order=alt.Order("점수", sort="descending"),
        tooltip=["구분", "점수", alt.Tooltip("비율", format=".1%")]
    )
    text = base.mark_text(radius=125).encode(
        text="라벨", order=alt.Order("점수", sort="descending"), color=alt.value("black"), size=alt.value(18)
    ).transform_filter(alt.datum.비율 > 0.03)
    return pie + text

# 만세력 원국표
def draw_manse_grid(pillars, calc, day_gan):
    color_map = {"목": "#4CAF50", "화": "#FF5252", "토": "#FFC107", "금": "#9E9E9E", "수": "#2196F3", "?": "#EEE", "??": "#EEE"}
    text_color = {"토": "black"} 
    
    display_pillars = [pillars[3], pillars[2], pillars[1], pillars[0]]
    titles = ["시주 (Time)", "일주 (Day)", "월주 (Month)", "연주 (Year)"]
    cols = st.columns(4)
    
    for i, col in enumerate(cols):
        stem = display_pillars[i][0]
        branch = display_pillars[i][1]
        
        with col:
            st.markdown(f"<div style='text-align:center; font-weight:bold; color:#555;'>{titles[i]}</div>", unsafe_allow_html=True)
            
            s_elem = calc.gan_elements.get(stem, "?")
            s_bg = color_map.get(s_elem, "#EEE")
            s_txt = text_color.get(s_elem, "white")
            s_god = "일원 (Me)" if i == 1 else calc.get_ten_gods(day_gan, stem)
            
            st.markdown(f"""
            <div style='background-color:{s_bg}; color:{s_txt}; border-radius:10px; padding:10px; margin:5px; text-align:center;'>
                <div style='font-size:13px; opacity:0.9;'>{s_god}</div>
                <div style='font-size:32px; font-weight:bold;'>{stem}</div>
            </div>
            """, unsafe_allow_html=True)
            
            b_elem = calc.ji_elements.get(branch, "?")
            b_bg = color_map.get(b_elem, "#EEE")
            b_txt = text_color.get(b_elem, "white")
            b_god = calc.get_ten_gods(day_gan, branch)
            
            st.markdown(f"""
            <div style='background-color:{b_bg}; color:{b_txt}; border-radius:10px; padding:10px; margin:5px; text-align:center;'>
                <div style='font-size:32px; font-weight:bold;'>{branch}</div>
                <div style='font-size:13px; opacity:0.9;'>{b_god}</div>
            </div>
            """, unsafe_allow_html=True)

# 🌟 [NEW] 운세 흐름 (대운/세운/월운) UI 함수
def draw_unse_grid(daewuns, sewun, wolun, calc, day_gan):
    color_map = {"목": "#4CAF50", "화": "#FF5252", "토": "#FFC107", "금": "#9E9E9E", "수": "#2196F3"}
    text_color = {"토": "black"}

    def get_pillar_card(title, stem, branch):
        s_elem = calc.gan_elements.get(stem, "?")
        s_bg = color_map.get(s_elem, "#EEE")
        s_txt = text_color.get(s_elem, "white")
        s_god = calc.get_ten_gods(day_gan, stem)
        
        b_elem = calc.ji_elements.get(branch, "?")
        b_bg = color_map.get(b_elem, "#EEE")
        b_txt = text_color.get(b_elem, "white")
        b_god = calc.get_ten_gods(day_gan, branch)
        
        return f"""
        <div style='text-align:center; font-weight:bold; color:#555; margin-bottom:5px; font-size:14px;'>{title}</div>
        <div style='background-color:{s_bg}; color:{s_txt}; border-radius:8px; padding:5px; margin-bottom:3px; text-align:center;'>
            <div style='font-size:11px; opacity:0.9;'>{s_god}</div>
            <div style='font-size:22px; font-weight:bold;'>{stem}</div>
        </div>
        <div style='background-color:{b_bg}; color:{b_txt}; border-radius:8px; padding:5px; text-align:center;'>
            <div style='font-size:22px; font-weight:bold;'>{branch}</div>
            <div style='font-size:11px; opacity:0.9;'>{b_god}</div>
        </div>
        """

    # 대운 UI (8칸)
    st.markdown("#### 🌊 10년 주기 대운 흐름")
    st.caption("※ 대운수(나이)는 절기가 아닌 생일 기준 근사치입니다.")
    cols = st.columns(8)
    for i, col in enumerate(cols):
        dw = daewuns[i]
        with col:
            st.markdown(get_pillar_card(f"{dw['age']}세", dw['pillar'][0], dw['pillar'][1]), unsafe_allow_html=True)
            
    st.write("")
    st.write("")
    
    # 세운 & 월운 UI (현재 기준)
    st.markdown("#### 🎯 현재 운세 (세운 / 월운)")
    now = datetime.now()
    col1, col2, _ = st.columns([1.5, 1.5, 5])
    
    with col1:
        st.markdown(get_pillar_card(f"올해 ({now.year}년)", sewun[0], sewun[1]), unsafe_allow_html=True)
    with col2:
        st.markdown(get_pillar_card(f"이번달 ({now.month}월)", wolun[0], wolun[1]), unsafe_allow_html=True)


# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 내 사주팔자 분석기")
st.markdown("""
<div style="font-size:15px; color:#555; line-height:1.6;">
내 팔자는 어떻길래..<br>
사주팔자를 면밀히 분석하여 정확하게 풀이합니다.<br>
특별한 고민이 있다면 위안을 얻어보세요.
</div>
<br>
""", unsafe_allow_html=True)

calc = SajuCalculator()

sibseong_desc_db = {
    "비겁 (나/동료)": """<b>💪 비겁이 가장 강한 당신은?</b><br>자기주장과 고집이 셉니다. 주관과 신념도 뚜렷합니다. 통제해줄 관성이 부족한 경우, 하고자 하는 일을 남들이 막기 쉽지 않습니다. 그만큼 남들에게 지기 싫은 경쟁심도 강합니다.""",
    "식상 (표현/재능)": """<b>🎨 식상이 가장 강한 당신은?</b><br>활달하고 호기심, 탐구심이 많습니다. 자유분방하며 자신을 표현하는 분야에서 두각을 보입니다. 관성을 적당히 지닌 경우 인간관계에서 기가 세다는 말을 듣습니다.""",
    "재성 (재물/결과)": """<b>💰 재성이 가장 강한 당신은?</b><br>사회생활의 달인입니다. 하지만 그만큼 돈과 인간관계와 관련된 에너지를 많이 소모합니다. 페르소나가 여러 개인 경우가 많습니다. 오행이 잘 갖춰진 경우 재물운을 타고나 풍요로운 삶을 누릴 수 있습니다.""",
    "관성 (명예/직장)": """<b>👑 관성이 가장 강한 당신은?</b><br>책임감이 강하고 원칙을 중요시합니다. 조직 생활에 적합하며 명예를 추구하는 성향이 있습니다. 자기 통제력이 좋지만, 너무 강하면 스스로를 억압하거나 강박이 생길 수 있습니다.""",
    "인성 (지혜/도움)": """<b>📚 인성이 가장 강한 당신은?</b><br>생각이 많고 인내심이 많습니다. 자립하기보다 연장자에게 의존하고자 하는 욕구가 있습니다. 우유부단한 면이 있어 재성을 갖춘 것이 좋습니다. 자존심이 세며, 관성을 잘 갖춘 경우 공부로 성취를 이루기 좋습니다."""
}

with st.form("saju_form", clear_on_submit=False):
    nickname = st.text_input("닉네임", placeholder="예: 북극이")
    gender = st.radio("성별", ["여성", "남성"], horizontal=True)
    col1, col2 = st.columns(2)
    with col1: birth_date = st.date_input("생년월일", min_value=datetime(1950, 1, 1))
    with col2: birth_time = st.time_input("태어난 시간")
    is_unknown_time = st.checkbox("태어난 시간을 몰라요")
    submitted = st.form_submit_button("내 사주 분석 결과 보기")

    if submitted:
        if not nickname: st.error("닉네임을 적어주세요!")
        else:
            original_dt = datetime.combine(birth_date, birth_time)
            adjusted_dt = original_dt + timedelta(minutes=30) # 한국 표준시 오차 보정
            
            year_pillar = calc.get_year_pillar(adjusted_dt.year)
            month_pillar = calc.get_month_pillar(year_pillar, adjusted_dt)
            day_pillar = calc.get_day_pillar(adjusted_dt)
            
            if not is_unknown_time:
                time_pillar = calc.get_time_pillar(day_pillar, adjusted_dt.hour)
                pillars = [year_pillar, month_pillar, day_pillar, time_pillar]
            else:
                pillars = [year_pillar, month_pillar, day_pillar, ["?", "?"]]

            element_scores, strength_score, my_elem, logs = calc.calculate_weighted_scores(pillars)
            sibseong_scores = calc.convert_to_sibseong(my_elem, element_scores)
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            if strength_score > 20: power_desc = "극신강"
            elif strength_score > 0: power_desc = "신강"
            elif strength_score > -20: power_desc = "신약"
            else: power_desc = "극신약"
            
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}'일주** 입니다.")
            
            # --- 사주 원국표 ---
            day_gan = day_pillar[0]
            st.markdown("### 📜 사주 원국표 (만세력)")
            draw_manse_grid(pillars, calc, day_gan)
            st.markdown("---")
            
            # --- 🌟 대운/세운/월운 ---
            # 현재 시간 기준으로 세운/월운 도출
            today = datetime.now()
            sewun = calc.get_year_pillar(today.year)
            wolun = calc.get_month_pillar(sewun, today)
            daewuns = calc.get_daewun(year_pillar, month_pillar, gender, birth_date)
            
            draw_unse_grid(daewuns, sewun, wolun, calc, day_gan)
            st.markdown("---")

            # --- 전투 리포트 및 해석 ---
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
            
            st.subheader("📊 사주 세력 분포 (오행 & 십성)")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.caption("🌲 오행 분포 (기질)")
                chart1 = draw_ohaeng_pie_chart(element_scores)
                st.altair_chart(chart1, use_container_width=True)
                
            with col_chart2:
                st.caption("🤝 십성 비율 (사회성)")
                data_sib = []
                total_sib = sum([max(0, s) for s in sibseong_scores.values()])
                if total_sib == 0: total_sib = 1
                for name, score in sibseong_scores.items():
                    safe_score = max(0, score)
                    ratio = safe_score / total_sib
                    data_sib.append({"name": name, "ratio": ratio})
                data_sib.sort(key=lambda x: x["ratio"], reverse=True)
                
                for item in data_sib:
                    width_percent = item["ratio"] * 100
                    st.markdown(f"""
                    <div style="margin-bottom: 12px;">
                        <div style="font-size:18px; font-weight:600; color:#333; margin-bottom: 4px;">{item['name']}</div>
                        <div style="width: 100%; background-color: #f0f2f6; border-radius: 8px; height: 16px;">
                            <div style="width: {width_percent}%; background-color: #FF4B4B; height: 100%; border-radius: 8px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                max_sib_name = data_sib[0]["name"]
                max_sib_desc = sibseong_desc_db.get(max_sib_name, "설명 정보 없음")
                st.markdown(f"""<div style='margin-top: 20px; padding: 15px; background-color: #e8f4f9; border-radius: 10px; border-left: 5px solid #42A5F5;'><p style='font-size:15px; line-height:1.6; color:#333; margin:0;'>{max_sib_desc}</p></div>""", unsafe_allow_html=True)
