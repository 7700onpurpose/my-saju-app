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
# [핵심] 사주팔자 계산기 (천간합충 + 지지합충)
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

        # 1. 천간충
        self.chung_rules = {
            frozenset(["갑", "경"]): 8, frozenset(["을", "신"]): 5,
            frozenset(["병", "임"]): 8, frozenset(["정", "계"]): 5,
            frozenset(["무", "갑"]): 3, frozenset(["기", "계"]): 3
        }
        
        # 2. 천간합
        self.hap_rules = {
            frozenset(["갑", "기"]): {"토": 8, "목": -5},
            frozenset(["을", "경"]): {"금": 8, "목": -5},
            frozenset(["병", "신"]): {"수": 5, "화": -3, "금": -3},
            frozenset(["정", "임"]): {"목": 5, "화": 3, "수": -3},
            frozenset(["무", "계"]): {"화": 5, "토": 3, "수": -3}
        }

        # 3. ⚡ [NEW] 지지충 (승패 판정용)
        # (글자세트, 오행1, 오행2, 점수)
        self.jiji_chung_rules = [
            ({"자", "오"}, "수", "화", 7), # 자오충
            ({"묘", "유"}, "목", "금", 5), # 묘유충
            ({"사", "해"}, "화", "수", 8)  # 사해충 (사=화, 해=수)
        ]

        # 4. 지지 삼합
        self.samhap_rules = {
            "목": {"members": {"해", "묘", "미"}, "name": "해묘미(삼합)"},
            "화": {"members": {"인", "오", "술"}, "name": "인오술(삼합)"},
            "금": {"members": {"사", "유", "축"}, "name": "사유축(삼합)"},
            "수": {"members": {"신", "자", "진"}, "name": "신자진(삼합)"}
        }

        # 5. 지지 방합
        self.banghap_rules = {
            "목": {"members": {"인", "묘", "진"}, "name": "인묘진(방합)"},
            "화": {"members": {"사", "오", "미"}, "name": "사오미(방합)"},
            "금": {"members": {"신", "유", "술"}, "name": "신유술(방합)"},
            "수": {"members": {"해", "자", "축"}, "name": "해자축(방합)"}
        }

    def get_60ganji(self, gan_idx, ji_idx):
        return self.gan[gan_idx % 10] + self.ji[ji_idx % 12]

    # ... (연월일시 계산 함수 동일) ...
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

    # 🌟 [최종 업그레이드] 지지충 승자독식 로직 반영
    def calculate_weighted_scores(self, pillars):
        base_weights = [[10, 7], [17, 15], [50, 20], [10, 5]]
        
        day_gan = pillars[2][0] 
        my_element = self.gan_elements[day_gan]
        
        element_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        
        # 지지 세력 판독용 (승패 결정 위해 지지 점수만 따로 저장)
        jiji_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        
        total_strength_score = 0
        logs = [] 

        # 1. 기본 점수 계산 (전체 & 지지별)
        for i, pillar in enumerate(pillars):
            for j, char in enumerate(pillar):
                weight = base_weights[i][j]
                elem = self.gan_elements.get(char, self.ji_elements.get(char))
                
                # 전체 점수
                element_scores[elem] += weight
                
                # 지지 점수만 따로 집계 (j=1이 지지)
                if j == 1:
                    jiji_scores[elem] += weight

                # 신강/신약
                if elem == my_element: total_strength_score += weight
                elif self.saeng[elem] == my_element: total_strength_score += weight
                elif self.saeng[my_element] == elem: total_strength_score -= weight
                elif self.geuk[my_element] == elem: total_strength_score -= weight
                elif self.geuk[elem] == my_element: total_strength_score -= weight

        # 2. 천간충
        for i, pillar in enumerate(pillars):
            if i != 2:
                char = pillar[0]
                pair = frozenset([day_gan, char])
                if pair in self.chung_rules:
                    penalty = self.chung_rules[pair]
                    element_scores[my_element] -= penalty
                    total_strength_score -= penalty
                    logs.append(f"💥 천간충('{char}')! 내 기운 -{penalty}")

        # 3. 천간합
        stems = [p[0] for p in pillars if p[0] != "?"]
        for pair, changes in self.hap_rules.items():
            if pair.issubset(set(stems)):
                pair_str = "+".join(pair)
                logs.append(f"💖 천간합({pair_str}) 성립!")
                for elem, score in changes.items():
                    element_scores[elem] += score
                    if score > 0:
                        if elem == my_element or self.saeng[elem] == my_element: total_strength_score += score
                        else: total_strength_score -= score
                    else:
                        abs_score = abs(score)
                        if elem == my_element or self.saeng[elem] == my_element: total_strength_score -= abs_score
                        else: total_strength_score += abs_score
                    sign = "+" if score > 0 else ""
                    logs.append(f"   -> {elem} {sign}{score}")

        # 4. ⚡ [NEW] 지지충 (Jiji Clash - 승자독식)
        branches = [p[1] for p in pillars if p[1] != "?"]
        branches_set = set(branches)
        
        for rule_set, elem1, elem2, score in self.jiji_chung_rules:
            # 해당 충 글자들이 모두 지지에 있는지 확인
            if rule_set.issubset(branches_set):
                # 지지 점수만 비교 (승자 판별)
                score1 = jiji_scores[elem1]
                score2 = jiji_scores[elem2]
                
                winner = None
                loser = None
                
                if score1 >= score2: # elem1 승리 (동점이면 일단 앞 순서 승리로 간주)
                    winner, loser = elem1, elem2
                else: # elem2 승리
                    winner, loser = elem2, elem1
                
                # 점수 반영 (메인 점수에 반영)
                element_scores[winner] += score
                element_scores[loser] -= score
                
                logs.append(f"⚔️ 지지충({','.join(rule_set)}) 발생! 승자:{winner}(+{score}), 패자:{loser}(-{score})")
                
                # 신강/신약 재계산 (승자 점수 추가)
                if winner == my_element or self.saeng[winner] == my_element: total_strength_score += score
                else: total_strength_score -= score
                
                # 신강/신약 재계산 (패자 점수 차감)
                if loser == my_element or self.saeng[loser] == my_element: total_strength_score -= score # 내 편이 짐
                else: total_strength_score += score # 적군이 짐 (나한텐 이득)

        # 5. 지지 삼합 & 방합
        for target_elem, rule in self.samhap_rules.items():
            members = rule["members"]
            intersection = members.intersection(branches_set)
            count = len(intersection)
            score_add = 0
            if count == 3: score_add = 10
            elif count == 2: score_add = 6
            
            if score_add > 0:
                element_scores[target_elem] += score_add
                logs.append(f"🌀 {rule['name']} +{score_add}")
                if target_elem == my_element or self.saeng[target_elem] == my_element: total_strength_score += score_add
                else: total_strength_score -= score_add

        for target_elem, rule in self.banghap_rules.items():
            members = rule["members"]
            intersection = members.intersection(branches_set)
            count = len(intersection)
            score_add = 0
            if count == 3: score_add = 10
            elif count == 2: score_add = 6
            
            if score_add > 0:
                element_scores[target_elem] += score_add
                logs.append(f"🏯 {rule['name']} +{score_add}")
                if target_elem == my_element or self.saeng[target_elem] == my_element: total_strength_score += score_add
                else: total_strength_score -= score_add

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
        y=alt.Y('점수', title='최종 세력'),
        color=alt.Color('오행', scale=alt.Scale(domain=domain, range=range_), legend=None),
        tooltip=['오행', '점수']
    ).properties(height=250).configure_axis(grid=False).configure_view(strokeWidth=0)
    return chart

# ---------------------------------------------------------
# [화면 구성]
# ---------------------------------------------------------
st.title("🔮 익명 정밀 사주풀이")
st.markdown("##### [지지충]의 승패 판정까지 포함된 완전체 분석")

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

            # 🌟 [계산] 모든 로직 실행
            element_scores, strength_score, my_elem, logs = calc.calculate_weighted_scores(pillars)
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            if strength_score > 20: power_desc = "매우 신강 (주관 뚜렷)"
            elif strength_score > 0: power_desc = "약간 신강 (주도적)"
            elif strength_score > -20: power_desc = "약간 신약 (조화 중시)"
            else: power_desc = "매우 신약 (환경 민감)"
            
            log_text = "\n".join(logs) if logs else "특이사항 없음"
            final_contact = contact if contact else "블로그 게시 희망"
            
            msg = f"""
**[🔮 마스터급 정밀상담]**
👤 {nickname} ({gender})
🔖 {result_text}
📊 점수: {strength_score} ({power_desc})
⚔️ 변화: {log_text}
📧 {final_contact}
📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}'** 입니다.")
            
            if logs:
                st.warning(f"⚔️ **사주 내 충돌과 연합(합/충) 상세 내역**\n\n" + "\n".join([f"- {log}" for log in logs]))
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="color:#333;">📜 {day_pillar}일주 분석</h4>
                <p>{my_interpretation}</p>
                <hr>
                <p><b>💡 최종 에너지 점수:</b> {strength_score}점 ({power_desc})</p>
                <p style='font-size:12px; color:gray;'>* 지지충이 발생하면 세력이 강한 쪽이 약한 쪽의 점수를 흡수하거나 파괴합니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader(f"📊 오행 세력 그래프")
            chart = draw_pretty_chart(element_scores, my_elem)
            st.altair_chart(chart, use_container_width=True)
