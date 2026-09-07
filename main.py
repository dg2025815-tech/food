import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 레이아웃 및 제목 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="고교 급식 칼로리 다이어트 리포트",
    page_icon="🍱",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 정확한 학교 행정표준코드 설정 (첨부 CSV 기준 검증 완료)
# - 시도교육청코드: B10 (서울특별시교육청)
# -----------------------------------------------------------------------------
SCHOOL_DATA = {
    "당곡고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010073"},
    "수도여자고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010090"},
    "성남고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010193"}
}

API_KEY = "sample"  # 나이스 오픈API 인증키 (샘플키)
BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# -----------------------------------------------------------------------------
# 3. 데이터 수집 및 정제 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_meal_data(atpt_code, schul_code, start_ymd, end_ymd):
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_FROM_YMD": start_ymd,
        "MLSV_TO_YMD": end_ymd
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
        
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
        else:
            return []
    except Exception as e:
        st.error(f"API 통신 오류가 발생했습니다: {e}")
        return []

# "820.5 Kcal" 형태의 문자열에서 숫자만 추출하는 함수
def parse_calorie(cal_str):
    if not cal_str or pd.isna(cal_str):
        return 0.0
    match = re.search(r"([\d\.]+)", str(cal_str))
    return float(match.group(1)) if match else 0.0

# -----------------------------------------------------------------------------
# 4. 사이드바 - 학교 및 직관적인 연/월 선택 UI
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 조회 조건 설정")

# 필수 조건: 당곡고등학교 기본 선택 + 3개 이상 선택 옵션
selected_school = st.sidebar.selectbox(
    "학교 선택",
    options=list(SCHOOL_DATA.keys()),
    index=0  # 당곡고등학교 기본 선택
)

# 간편한 날짜 선택 (연도 & 월 슬라이더/드롭다운)
col_y, col_m = st.sidebar.columns(2)
with col_y:
    selected_year = st.number_input("연도", min_value=2020, max_value=2026, value=2024)
with col_m:
    selected_month = st.selectbox("월", options=list(range(1, 13)), index=4) # 기본 5월

# 선택한 월의 시작일과 종료일 자동 계산 (예: 20240501 ~ 20240531)
start_ymd = f"{selected_year}{selected_month:02d}01"
if selected_month == 12:
    end_ymd = f"{selected_year}1231"
else:
    next_month_first = datetime(selected_year, selected_month + 1, 1)
    last_day = (next_month_first - pd.Timedelta(days=1)).day
    end_ymd = f"{selected_year}{selected_month:02d}{last_day:02d}"

# -----------------------------------------------------------------------------
# 5. 메인 화면 - 탐구 주제 및 목적
# -----------------------------------------------------------------------------
st.title("🔥 급식 칼로리 탐험대: 다이어트 주의보!")
st.subheader("“오늘 우리 학교 급식, 칼로리 폭탄일까?”")

st.markdown("""
> **💡 팀 미션 주제 & 해결 과제**
> - **새로운 사실 발견**: 나이스(NEIS) 데이터를 통해 유독 칼로리가 높은 특정 날짜와 메뉴 조합(특식, 튀김류 등)을 사전에 파악합니다.
> - **문제 해결**: 다이어트나 식단 관리가 필요한 학생들이 **고칼로리 급식 날을 미리 확인**하여 운동량을 조절하거나 식사량을 조절할 수 있도록 돕습니다.
""")

st.divider()

# -----------------------------------------------------------------------------
# 6. 데이터 데이터 처리 및 시각화
# -----------------------------------------------------------------------------
school_info = SCHOOL_DATA[selected_school]
raw_data = fetch_meal_data(school_info["ATPT_CODE"], school_info["SCHUL_CODE"], start_ymd, end_ymd)

if raw_data:
    df = pd.DataFrame(raw_data)
    
    # 데이터 전처리
    df['CAL_NUM'] = df['CAL_INFO'].apply(parse_calorie)
    df['DATE'] = pd.to_datetime(df['MLSV_YMD'], format='%Y%m%d')
    
    day_map = {'Monday': '월', 'Tuesday': '화', 'Wednesday': '수', 'Thursday': '목', 'Friday': '금', 'Saturday': '토', 'Sunday': '일'}
    df['DAY_KOR'] = df['DATE'].dt.day_name().map(day_map)
    
    # 칼로리 정보가 존재하는 데이터만 필터링
    df = df[df['CAL_NUM'] > 0]
    
    if not df.empty:
        # 요약 KPI 카드
        col1, col2, col3, col4 = st.columns(4)
        avg_cal = df['CAL_NUM'].mean()
        max_row = df.loc[df['CAL_NUM'].idxmax()]
        min_row = df.loc[df['CAL_NUM'].idxmin()]
        
        col1.metric("선택한 학교", selected_school)
        col2.metric("월 평균 칼로리", f"{avg_cal:.1f} kcal")
        col3.metric("최고 칼로리 날짜", f"{max_row['CAL_NUM']} kcal", f"{max_row['MLSV_YMD']}")
        col4.metric("최저 칼로리 날짜", f"{min_row['CAL_NUM']} kcal", f"{min_row['MLSV_YMD']}")
        
        st.divider()
        
        # Plotly 메인 그래프 (일자별 칼로리)
        st.write(f"### 📊 {selected_school} ({selected_year}년 {selected_month}월) 일자별 칼로리 추이")
        
        fig_bar = px.bar(
            df,
            x='MLSV_YMD',
            y='CAL_NUM',
            hover_data=['MMEAL_SC_NM', 'DDISH_NM'],
            labels={'MLSV_YMD': '급식일자', 'CAL_NUM': '칼로리(kcal)'},
            color='CAL_NUM',
            color_continuous_scale=['#3498DB', '#E74C3C'],
            title="일자별 칼로리 (붉은색일수록 고칼로리)"
        )
        
        # 평균선 추가
        fig_bar.add_hline(
            y=avg_cal,
            line_dash="dash",
            line_color="black",
            annotation_text=f"월 평균: {avg_cal:.1f} kcal"
        )
        
        fig_bar.update_layout(xaxis_type='category', height=450)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 요일별 평균 및 고칼로리 Top 3
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.write("### 📅 요일별 평균 칼로리")
            day_order = ['월', '화', '수', '목', '금']
            df_day = df.groupby('DAY_KOR')['CAL_NUM'].mean().reindex(day_order).dropna().reset_index()
            
            fig_day = px.bar(
                df_day,
                x='DAY_KOR',
                y='CAL_NUM',
                color='CAL_NUM',
                labels={'DAY_KOR': '요일', 'CAL_NUM': '평균(kcal)'},
                color_continuous_scale='Purples'
            )
            fig_day.update_layout(height=400)
            st.plotly_chart(fig_day, use_container_width=True)
            
        with col_right:
            st.write("### 🚨 다이어트 주의보! 고칼로리 Top 3 식단")
            top3 = df.sort_values(by='CAL_NUM', ascending=False).head(3)
            for _, row in top3.iterrows():
                clean_dishes = str(row['DDISH_NM']).replace('<br/>', ', ')
                st.warning(f"**[{row['MLSV_YMD']} ({row['DAY_KOR']})] - {row['CAL_NUM']} kcal**\n\n🍽️ {clean_dishes}")
                
        with st.expander("📄 전체 급식 데이터 상세 보기"):
            st.dataframe(df[['MLSV_YMD', 'DAY_KOR', 'MMEAL_SC_NM', 'CAL_INFO', 'DDISH_NM']])
    else:
        st.warning("선택하신 월에 등록된 급식 데이터가 없습니다.")
else:
    st.info(f"💡 {selected_year}년 {selected_month}월은 방학 기간이거나 주말/휴교일이라 급식 데이터가 없습니다. 학기 중(예: 2024년 5월 또는 2023년 10월 등)으로 연월을 변경해 보세요!")
