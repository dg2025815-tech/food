import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import re
import glob
import os
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. 페이지 레이아웃 및 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="고교 급식 칼로리 분석 리포트",
    page_icon="🍱",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 학교 정보 및 코드 정의 (NEIS 공식 행정표준코드)
# -----------------------------------------------------------------------------
SCHOOL_DATA = {
    "당곡고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010073"},
    "수도여자고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010090"},
    "성남고등학교": {"ATPT_CODE": "B10", "SCHUL_CODE": "7010193"}
}

API_KEY = "sample"
BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# -----------------------------------------------------------------------------
# 3. 데이터 로딩 (CSV 파일 로컬 로드 + API 패치 하이브리드)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_all_school_data():
    """폴더 내의 급식식단정보 CSV 파일들을 탐색하여 하나의 데이터프레임으로 합침"""
    csv_files = glob.glob("*.csv")
    dfs = []
    for f in csv_files:
        try:
            df_temp = pd.read_csv(f)
            if '학교명' in df_temp.columns and '급식일자' in df_temp.columns:
                dfs.append(df_temp)
        except Exception:
            pass
    if dfs:
        full_df = pd.concat(dfs, ignore_index=True)
        return full_df
    return pd.DataFrame()

def fetch_api_meal_data(atpt_code, schul_code, start_ymd, end_ymd):
    """sample 키 제약(pSize=5 fixed)을 극복하기 위해 pIndex를 올려가며 반복 수집"""
    all_rows = []
    p_index = 1
    
    while True:
        params = {
            "KEY": API_KEY,
            "Type": "json",
            "pIndex": p_index,
            "pSize": 100,  # sample key일 경우 서버에서 5개로 처리됨
            "ATPT_OFCDC_SC_CODE": atpt_code,
            "SD_SCHUL_CODE": schul_code,
            "MLSV_FROM_YMD": start_ymd,
            "MLSV_TO_YMD": end_ymd
        }
        
        try:
            response = requests.get(BASE_URL, params=params, timeout=5)
            data = response.json()
            
            if "mealServiceDietInfo" in data:
                rows = data["mealServiceDietInfo"][1]["row"]
                all_rows.extend(rows)
                # 만약 가져온 개수가 적으면 마지막 페이지로 판단
                if len(rows) < 5:
                    break
                p_index += 1
                if p_index > 40: # 안전장치 (최대 200건)
                    break
            else:
                break
        except Exception:
            break
            
    return all_rows

def parse_calorie(cal_str):
    if not cal_str or pd.isna(cal_str):
        return 0.0
    match = re.search(r"([\d\.]+)", str(cal_str))
    return float(match.group(1)) if match else 0.0

# -----------------------------------------------------------------------------
# 4. 사이드바 - 학교 및 날짜 선택 UI
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 조회 조건 설정")

# 필수 조건: 당곡고등학교 기본 선택 + 3개 이상 선택 옵션
selected_school = st.sidebar.selectbox(
    "학교 선택",
    options=list(SCHOOL_DATA.keys()),
    index=0  # 당곡고등학교
)

# 날짜 범위를 자유롭게 선택 (기본값: 2024년 5월 1일 ~ 5월 31일)
default_start_date = datetime(2024, 5, 1)
default_end_date = datetime(2024, 5, 31)

date_range = st.sidebar.date_input(
    "조회 기간 선택",
    value=(default_start_date, default_end_date)
)

# -----------------------------------------------------------------------------
# 5. 메인 화면 - 주제 및 설명
# -----------------------------------------------------------------------------
st.title("🔥 급식 칼로리 탐험대: 다이어트 주의보!")
st.subheader("“오늘 우리 학교 급식, 칼로리 폭탄일까?”")

st.markdown("""
> **💡 팀 미션 주제 & 해결 과제**
> - **새로운 사실 발견**: 나이스(NEIS) 데이터를 분석하여 급식 메뉴 중 칼로리가 유독 높아지는 날과 요일을 찾아냅니다.
> - **문제 해결**: 다이어트나 식단 관리가 필요한 학생들에게 **고칼로리 급식 날짜를 미리 알려주어** 식사량 및 운동량을 조절하도록 돕습니다.
""")

st.divider()

# -----------------------------------------------------------------------------
# 6. 데이터 가져오기 및 가공
# -----------------------------------------------------------------------------
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_ymd = date_range[0].strftime("%Y%m%d")
    end_ymd = date_range[1].strftime("%Y%m%d")
    
    # 1차: 파일(CSV) 데이터 우선 조회
    local_df = load_all_school_data()
    df_filtered = pd.DataFrame()
    
    if not local_df.empty:
        # 조건에 맞게 로컬 파일에서 필터링
        df_filtered = local_df[
            (local_df['학교명'] == selected_school) & 
            (local_df['급식일자'].astype(str) >= start_ymd) & 
            (local_df['급식일자'].astype(str) <= end_ymd)
        ].copy()
        
        if not df_filtered.empty:
            df_filtered = df_filtered.rename(columns={
                '급식일자': 'MLSV_YMD',
                '식사명': 'MMEAL_SC_NM',
                '요리명': 'DDISH_NM',
                '칼로리정보': 'CAL_INFO'
            })
    
    # 2차: 로컬 데이터가 없을 시 NEIS API 호출
    if df_filtered.empty:
        school_info = SCHOOL_DATA[selected_school]
        raw_api_data = fetch_api_meal_data(school_info["ATPT_CODE"], school_info["SCHUL_CODE"], start_ymd, end_ymd)
        if raw_api_data:
            df_filtered = pd.DataFrame(raw_api_data)
            
    # -------------------------------------------------------------------------
    # 7. 데이터 출력 및 Plotly 시각화
    # -------------------------------------------------------------------------
    if not df_filtered.empty:
        df = df_filtered.copy()
        df['CAL_NUM'] = df['CAL_INFO'].apply(parse_calorie)
        df['MLSV_YMD'] = df['MLSV_YMD'].astype(str)
        df['DATE'] = pd.to_datetime(df['MLSV_YMD'], format='%Y%m%d')
        
        day_map = {'Monday': '월', 'Tuesday': '화', 'Wednesday': '수', 'Thursday': '목', 'Friday': '금', 'Saturday': '토', 'Sunday': '일'}
        df['DAY_KOR'] = df['DATE'].dt.day_name().map(day_map)
        
        # 0kcal 데이터 제외
        df = df[df['CAL_NUM'] > 0]
        
        if not df.empty:
            # 주요 요약 KPI 카드
            col1, col2, col3, col4 = st.columns(4)
            avg_cal = df['CAL_NUM'].mean()
            max_row = df.loc[df['CAL_NUM'].idxmax()]
            min_row = df.loc[df['CAL_NUM'].idxmin()]
            
            col1.metric("선택한 학교", selected_school)
            col2.metric("평균 칼로리", f"{avg_cal:.1f} kcal")
            col3.metric("최고 칼로리", f"{max_row['CAL_NUM']} kcal", f"{max_row['MLSV_YMD']}")
            col4.metric("최저 칼로리", f"{min_row['CAL_NUM']} kcal", f"{min_row['MLSV_YMD']}")
            
            st.divider()
            
            # [Plotly 시각화 1] 일자별 칼로리 막대 그래프
            st.write(f"### 📊 {selected_school} 일자별 급식 칼로리 추이")
            
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
            
            fig_bar.add_hline(
                y=avg_cal,
                line_dash="dash",
                line_color="black",
                annotation_text=f"기간 평균: {avg_cal:.1f} kcal"
            )
            
            fig_bar.update_layout(xaxis_type='category', height=450)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # [Plotly 시각화 2] 요일별 평균 & 고칼로리 Top 3
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
                    
            with st.expander("📄 전체 급식 데이터 표 보기"):
                st.dataframe(df[['MLSV_YMD', 'DAY_KOR', 'MMEAL_SC_NM', 'CAL_INFO', 'DDISH_NM']])
        else:
            st.warning("선택한 기간 내에 칼로리 데이터가 있는 급식이 없습니다.")
    else:
        st.error("데이터를 찾을 수 없습니다. 선택하신 학교와 날짜 범위에 급식 기록이 존재하는지 확인해 주세요.")
else:
    st.info("사이드바에서 시작일과 종료일을 모두 선택해 주세요.")
