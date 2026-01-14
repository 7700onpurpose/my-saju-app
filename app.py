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
# [핵심] 사주팔자 계산기 (과다 로직 추가됨)
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
        
        # 상생 (생해주는 관계)
        self.saeng = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
        # 상극 (극하는 관계)
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

        # 3. 지지충
        self.jiji_chung_rules = [
            ({"자", "오"}, "수", "화", 7),
            ({"묘", "유"}, "목", "금", 5),
            ({"사", "해"}, "화", "수", 8)
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

    # 🌟 [최종 업그레이드] 과다(Excess) 로직 추가
    def calculate_weighted_scores(self, pillars):
        base_weights = [[10, 7], [17, 15], [50, 20], [10, 5]]
        
        day_gan = pillars[2][0] 
        my_element = self.gan_elements[day_gan]
        
        element_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        jiji_scores = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        
        # 지지 오행 개수 카운트 (과다 판별용)
        branch_counts = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
        
        total_strength_score = 0
        logs = [] 

        # 1. 기본 점수 & 지지 카운팅
        for i, pillar in enumerate(pillars):
            for j, char in enumerate(pillar):
                weight = base_weights[i][j]
                elem = self.gan_elements.get(char, self.ji_elements.get(char))
                
                element_scores[elem] += weight
                if j == 1: 
                    jiji_scores[elem] += weight
                    # 지지 오행 개수 세기 (시간 모름 '?' 제외)
                    if char != "?":
                        branch_counts[elem] += 1

                if elem == my_element: total_strength_score += weight
                elif self.saeng[elem] == my_element: total_strength_score += weight
                elif self.saeng[my_element] == elem: total_strength_score -= weight
                elif self.geuk[my_element] == elem: total_strength_score -= weight
                elif self.geuk[elem] == my_element: total_strength_score -= weight

        # 2~6. 충/합/병존 등 기존 로직들 ...
        # (편의상 코드가 너무 길어져서 핵심 로직은 유지하되, 여기서는 생략하고 아래에 추가된 7번만 보세요!)
        # 실제 코드 복사할 땐 위에서 짠 충/합 코드들이 여기 사이에 다 들어있다고 가정합니다.
        
        # ... (천간충, 천간합, 지지충, 삼합, 방합, 병존 코드들) ...
        # (이전 단계에서 작성된 코드를 그대로 두시면 됩니다.)
        # ⚠️ 여기서는 과다 로직을 보여드리기 위해 바로 7번으로 넘어갑니다.
        
        # ----------------------------------------------------
        # 7. ⚡ [NEW] 지지 오행 과다(Excess)에 의한 상생 점수 부여
        # ----------------------------------------------------
        for elem, count in branch_counts.items():
            # 지지에 3글자 이상이면 '과다'로 판단
            if count >= 3:
                # 과다한 오행이 생(Generate)해주는 오행 찾기
                child_elem = self.saeng[elem] # 예: 토 -> 금
                
                bonus_score = 10 # 보너스 점수
                element_scores[child_elem] += bonus_score
                
                logs.append(f"🌊 지지에 '{elem}' 기운 과다({count}개)! -> 자식인 '{child_elem}' +{bonus_score}점")
                
                # 신강/신약 반영
                if child_elem == my_element or self.saeng[child_elem] == my_element:
                    total_strength_score += bonus_score # 내 편이 강해짐
                else:
                    total_strength_score -= bonus_score # 남의 편이 강해짐

        return element_scores, total_strength_score, my_element, logs

# ---------------------------------------------------------
# [기능] 차트 & 전송
# ---------------------------------------------------------
# (기존과 동일)
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
st.markdown("##### [과다(쏠림)] 현상까지 분석하는 전문가 만세력")

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

            # 🌟 [계산] 과다 로직 포함 실행
            # (주의: 실제 사용 시엔 위의 calc 클래스 안에 기존 충/합 로직을 다 합쳐두셔야 합니다!)
            element_scores, strength_score, my_elem, logs = calc.calculate_weighted_scores(pillars)
            my_interpretation = ilju_data.get(day_pillar, default_desc)

            if strength_score > 20: power_desc = "매우 신강 (주관 뚜렷)"
            elif strength_score > 0: power_desc = "약간 신강 (주도적)"
            elif strength_score > -20: power_desc = "약간 신약 (조화 중시)"
            else: power_desc = "매우 신약 (환경 민감)"
            
            log_text = "\n".join(logs) if logs else "특이사항 없음"
            final_contact = contact if contact else "블로그 게시 희망"
            
            msg = f"""
**[🔮 과다 분석 상담]**
👤 {nickname} ({gender})
🔖 {result_text}
📊 점수: {strength_score} ({power_desc})
🌊 변화: {log_text}
📧 {final_contact}
📜 **고민**: {concern}
"""
            send_discord_message(msg)
            
            st.success(f"✅ 분석 완료! {nickname}님은 **'{day_pillar}'** 입니다.")
            
            if logs:
                st.warning(f"🌊 **세력 쏠림/충돌 현상 발견!**\n\n" + "\n".join([f"- {log}" for log in logs]))
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h4 style="color:#333;">📜 {day_pillar}일주 분석</h4>
                <p>{my_interpretation}</p>
                <hr>
                <p><b>💡 최종 에너지 점수:</b> {strength_score}점 ({power_desc})</p>
                <p style='font-size:12px; color:gray;'>* 지지에 특정 오행이 과다하면(3개 이상) 그 기운이 낳아주는(생) 오행도 덩달아 강해집니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader(f"📊 오행 세력 그래프")
            chart = draw_pretty_chart(element_scores, my_elem)
            st.altair_chart(chart, use_container_width=True)
