import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime

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
        return self.gan[(start_gan_idx + time_
