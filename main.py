import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="고교 급식 칼로리 다이어트 리포트",
    page_icon="🍱",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 학교 정보 및 기본 데이터 정의
# 서울특별시교육청 코드: B10
# -----------------------------------------------------------------------------
SCHOOL_DATA = {
    "당곡고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010561"},
    "수도여자고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010115"},
    "성남고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010108"}
}

API_KEY = "sample"  # 샘플키 사용 (실제 발급받은 키가 있다면 대체)
BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# -----------------------------------------------------------------------------
# 3. 데이터 수집 함수 (NEIS API 호출)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # 캐싱을 이용해 데이터 재요청 속도 최적화
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
    
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    
    if "mealServiceDietInfo" in data:
        rows = data["mealServiceDietInfo"][1]["row"]
        return rows
    else:
        return []

# 칼로리 문자열(예: "820.5 Kcal")에서 숫자만 추출하는 함수
def parse_calorie(cal_str):
    if not cal_str:
        return 0.0
    match = re.search(r"([\d\.]+)", str(cal_str))
    if match:
        return float(match.group(1))
    return 0.0

# -----------------------------------------------------------------------------
# 4. 사이드바 - 학교 및 날짜 선택
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 조회 조건 설정")

# 3개 학교 중 선택 (기본값: 당곡고등학교)
selected_school = st.sidebar.selectbox(
    "학교 선택",
    options=list(SCHOOL_DATA.keys()),
    index=0  # 당곡고등학교 기본 선택
)

# 날짜 범위 선택 (기본값: 최근 30일)
today = datetime.now()
default_start = today - timedelta(days=30)
date_range = st.sidebar.date_input(
    "조회 기간",
    value=(default_start, today)
)

# -----------------------------------------------------------------------------
# 5. 메인 화면 - 주제 및 개요
# -----------------------------------------------------------------------------
st.title("🔥 급식 칼로리 탐험대: 다이어트 주의보!")
st.subheader("“오늘 급식, 다이어트의 적일까 친구일까?”")

st.markdown("""
> **💡 프로젝트 탐구 목적**
> - 우리는 평소 학교 급식을 먹으며 특정 날에 칼로리가 유독 높다는 사실을 눈치채지 못합니다.
> - **나이스(NEIS) 급식 정보 데이터**를 분석하여 **어느 날, 어느 식단이 유독 높은 칼로리를 기록하는지** 추적합니다.
> - 다이어트 중인 학생들에게 **"칼로리 폭탄 식단일"을 미리 경고**하고 건강한 식습관을 유지할 수 있도록 돕습니다!
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
        
        # 데이터 정제
        df['CAL_NUM'] = df['CAL_INFO'].apply(parse_calorie)
        df['DATE'] = pd.to_datetime(df['MLSV_YMD'], format='%Y%m%d')
        df['DAY_NAME'] = df['DATE'].dt.day_name()
        # 한국어 요일 변환
        day_map = {'Monday': '월', 'Tuesday': '화', 'Wednesday': '수', 'Thursday': '목', 'Friday': '금', 'Saturday': '토', 'Sunday': '일'}
        df['DAY_KOR'] = df['DAY_NAME'].map(day_map)
        
        # -----------------------------------------------------------------------------
        # 7. 주요 요약 지표 (KPI Cards)
        # -----------------------------------------------------------------------------
        col1, col2, col3, col4 = st.columns(4)
        
        avg_cal = df['CAL_NUM'].mean()
        max_row = df.loc[df['CAL_NUM'].idxmax()]
        min_row = df.loc[df['CAL_NUM'].idxmin()]
        
        col1.metric("선택 학교", selected_school)
        col2.metric("평균 급식 칼로리", f"{avg_cal:.1f} kcal")
        col3.metric("최고 칼로리", f"{max_row['CAL_NUM']} kcal", f"{max_row['MLSV_YMD']}")
        col4.metric("최저 칼로리", f"{min_row['CAL_NUM']} kcal", f"{min_row['MLSV_YMD']}")
        
        st.divider()
        
        # -----------------------------------------------------------------------------
        # 8. Plotly 그래프 시각화
        # -----------------------------------------------------------------------------
        st.write(f"### 📊 {selected_school} 일자별 급식 칼로리 추이")
        
        # [그래프 1] 날짜별 칼로리 선/막대 그래프 (기준선 포함)
        fig_line = px.bar(
            df, 
            x='MLSV_YMD', 
            y='CAL_NUM',
            hover_data=['MMEAL_SC_NM', 'DDISH_NM'],
            labels={'MLSV_YMD': '급식일자', 'CAL_NUM': '칼로리(kcal)'},
            title=f"일자별 칼로리 (Red: 평균 이상 / Blue: 평균 이하)",
            color='CAL_NUM',
            color_continuous_scale=['#4A90E2', '#E74C3C']
        )
        
        # 평균 칼로리 선 추가
        fig_line.add_hline(
            y=avg_cal, 
            line_dash="dash", 
            line_color="black",
            annotation_text=f"평균 ({avg_cal:.1f} kcal)", 
            annotation_position="top left"
        )
        
        fig_line.update_layout(xaxis_type='category', height=450)
        st.plotly_chart(fig_line, use_container_width=True)
        
        # [그래프 2] 요일별 평균 칼로리 비교
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
            st.write("### ⚠️ 다이어트 주의보! Top 3 고칼로리 식단")
            top3 = df.sort_values(by='CAL_NUM', ascending=False).head(3)
            for idx, row in top3.iterrows():
                # <br/> 태그 정제하여 깔끔하게 요리명만 표시
                dishes = str(row['DDISH_NM']).replace('<br/>', ', ')
                st.warning(f"**[{row['MLSV_YMD']}] - {row['CAL_NUM']} kcal**\n\n🍽️ **메뉴**: {dishes}")
        
        # -----------------------------------------------------------------------------
        # 9. 원본 데이터 보기
        # -----------------------------------------------------------------------------
        with st.expander("📄 전체 급식 데이터 상세보기"):
            st.dataframe(df[['MLSV_YMD', 'MMEAL_SC_NM', 'CAL_INFO', 'DDISH_NM']])

    else:
        st.error("해당 기간의 급식 데이터가 존재하지 않습니다.")
else:
    st.info("조회할 날짜 범위를 선택해주세요.")
