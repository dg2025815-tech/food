import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. 페이지 레이아웃 및 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="고교 급식 칼로리 다이어트 리포트",
    page_icon="🍱",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 학교 정보 및 NEIS API 설정
# - 시도교육청코드(ATPT_OFCDC_SC_CODE): 서울특별시교육청(B10)
# - 행정표준코드(SD_SCHUL_CODE): 당곡고(7010561), 수도여고(7010115), 성남고(7010108)
# -----------------------------------------------------------------------------
SCHOOL_DATA = {
    "당곡고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010561"},
    "수도여자고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010115"},
    "성남고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010108"}
}

API_KEY = "sample"  # 나이스 오픈API 인증키 (샘플키 사용 중)
BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# -----------------------------------------------------------------------------
# 3. API 데이터 수집 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # 동일 조건 재요청 시 빠르게 로딩
def fetch_meal_data(atpt_code, schul_code, start_ymd, end_ymd):
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_FROM_YMD": start_ymd,
        "MLSV_TO_YMD": end_ymd
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
        
        # NEIS API 응답 처리
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            return rows
        else:
            return []
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return []

# 칼로리 문자열(예: "820.5 Kcal")에서 숫자값만 추출하는 함수
def parse_calorie(cal_str):
    if not cal_str or pd.isna(cal_str):
        return 0.0
    match = re.search(r"([\d\.]+)", str(cal_str))
    if match:
        return float(match.group(1))
    return 0.0

# -----------------------------------------------------------------------------
# 4. 사이드바 UI (학교 선택 & 날짜 범위)
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 조회 조건 설정")

# 필수 조건: 당곡고등학교 기본 선택 + 3개 이상 선택 옵션 제공
selected_school = st.sidebar.selectbox(
    "학교 선택",
    options=list(SCHOOL_DATA.keys()),
    index=0  # 당곡고등학교 기본 선택
)

# 날짜 범위 설정 (기본값: 최근 30일)
today = datetime.now()
default_start = today - timedelta(days=30)
date_range = st.sidebar.date_input(
    "조회 기간 설정",
    value=(default_start, today)
)

# -----------------------------------------------------------------------------
# 5. 메인 화면 - 미션 주제 및 탐구 목적
# -----------------------------------------------------------------------------
st.title("🔥 급식 칼로리 탐험대: 다이어트 주의보!")
st.subheader("“오늘 우리 학교 급식, 칼로리 폭탄일까?”")

st.markdown("""
> **💡 팀 미션 주제 & 해결 과제**
> - **알지 못했던 새로운 사실 탐구**: 급식 메뉴 조합에 따라 특정 날짜의 칼로리가 표준 수치를 크게 웃도는 패턴을 발견합니다.
> - **해결하고자 하는 문제**: 다이어트나 체중 관리를 하는 학생들이 **"칼로리가 많은 날"**을 사전에 파악하여 식단을 조절하고 건강한 식습관을 유지할 수 있도록 돕습니다.
""")

st.divider()

# -----------------------------------------------------------------------------
# 6. 데이터 로드 및 가공
# -----------------------------------------------------------------------------
if len(date_range) == 2:
    start_ymd = date_range[0].strftime("%Y%m%d")
    end_ymd = date_range[1].strftime("%Y%m%d")
    
    school_info = SCHOOL_DATA[selected_school]
    raw_data = fetch_meal_data(school_info["ATPT_CODE"], school_info["SCHUL_CODE"], start_ymd, end_ymd)
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        
        # 칼로리 수치화 및 날짜 파싱
        df['CAL_NUM'] = df['CAL_INFO'].apply(parse_calorie)
        df['DATE'] = pd.to_datetime(df['MLSV_YMD'], format='%Y%m%d')
        
        # 요일 표기 추가
        day_map = {'Monday': '월', 'Tuesday': '화', 'Wednesday': '수', 'Thursday': '목', 'Friday': '금', 'Saturday': '토', 'Sunday': '일'}
        df['DAY_KOR'] = df['DATE'].dt.day_name().map(day_map)
        
        # -----------------------------------------------------------------------------
        # 7. 핵심 수치 요약 (KPI Cards)
        # -----------------------------------------------------------------------------
        col1, col2, col3, col4 = st.columns(4)
        
        avg_cal = df['CAL_NUM'].mean()
        max_idx = df['CAL_NUM'].idxmax()
        min_idx = df['CAL_NUM'].idxmin()
        
        max_row = df.loc[max_idx]
        min_row = df.loc[min_idx]
        
        col1.metric("선택한 학교", selected_school)
        col2.metric("평균 급식 칼로리", f"{avg_cal:.1f} kcal")
        col3.metric("최고 칼로리 날짜", f"{max_row['CAL_NUM']} kcal", f"{max_row['MLSV_YMD']}")
        col4.metric("최저 칼로리 날짜", f"{min_row['CAL_NUM']} kcal", f"{min_row['MLSV_YMD']}")
        
        st.divider()
        
        # -----------------------------------------------------------------------------
        # 8. Plotly 기반 시각화 그래프
        # -----------------------------------------------------------------------------
        st.write(f"### 📊 {selected_school} 일자별 급식 칼로리 변화 추이")
        
        # [그래프 1] Plotly 일자별 칼로리 막대 차트
        fig_bar = px.bar(
            df,
            x='MLSV_YMD',
            y='CAL_NUM',
            hover_data=['MMEAL_SC_NM', 'DDISH_NM'],
            labels={'MLSV_YMD': '급식일자', 'CAL_NUM': '칼로리(kcal)'},
            color='CAL_NUM',
            color_continuous_scale=['#3498DB', '#E74C3C'],
            title="일자별 칼로리 수치 (색상이 붉을수록 높은 칼로리)"
        )
        
        # 평균 칼로리 가로 가이드라인 추가
        fig_bar.add_hline(
            y=avg_cal,
            line_dash="dash",
            line_color="black",
            annotation_text=f"기간 평균: {avg_cal:.1f} kcal",
            annotation_position="top left"
        )
        
        fig_bar.update_layout(xaxis_type='category', height=450)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # [그래프 2 & 리포트] 요일별 평균 및 고칼로리 Top 3 메뉴
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.write("### 📅 요일별 평균 칼로리 비교")
            day_order = ['월', '화', '수', '목', '금']
            df_day = df.groupby('DAY_KOR')['CAL_NUM'].mean().reindex(day_order).dropna().reset_index()
            
            fig_day = px.bar(
                df_day,
                x='DAY_KOR',
                y='CAL_NUM',
                color='CAL_NUM',
                labels={'DAY_KOR': '요일', 'CAL_NUM': '평균 칼로리(kcal)'},
                color_continuous_scale='Purples'
            )
            fig_day.update_layout(height=400)
            st.plotly_chart(fig_day, use_container_width=True)
            
        with col_right:
            st.write("### 🚨 다이어트 주의보! 고칼로리 Top 3 식단")
            top3 = df.sort_values(by='CAL_NUM', ascending=False).head(3)
            for _, row in top3.iterrows():
                # HTML 줄바꿈 태그(<br/>)를 깔끔하게 쉼표로 정제
                dishes = str(row['DDISH_NM']).replace('<br/>', ', ')
                st.warning(f"**[{row['MLSV_YMD']} ({row['DAY_KOR']})] - {row['CAL_NUM']} kcal**\n\n🍽️ **메뉴**: {dishes}")
        
        # -----------------------------------------------------------------------------
        # 9. 원본 데이터 펼쳐보기
        # -----------------------------------------------------------------------------
        with st.expander("📄 전체 급식 데이터 표 보기"):
            st.dataframe(df[['MLSV_YMD', 'DAY_KOR', 'MMEAL_SC_NM', 'CAL_INFO', 'DDISH_NM']])

    else:
        st.info("해당 기간의 급식 데이터가 존재하지 않거나 주말/휴교일입니다.")
else:
    st.info("사이드바에서 조회할 날짜 범위를 선택해주세요.")
