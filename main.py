import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime
import calendar

# 1. 페이지 설정
st.set_page_config(
    page_title="고등학교 월별 급식 정보 조회",
    page_icon="🍱",
    layout="wide"
)

# 2. 학교 정보 설정 (서울시교육청: B10)
SCHOOL_MAP = {
    "성남고등학교": "7010193",
    "당곡고등학교": "7010073",
    "수도여자고등학교": "7010090"
}
ATPT_CODE = "B10"

# 3. 메뉴 정제 함수 (알레르기 번호 및 태그 제거)
def clean_menu(text):
    if not text:
        return ""
    cleaned = re.sub(r'<br\s*/?>', '\n', text)
    cleaned = re.sub(r'\([0-9\.]+\)', '', cleaned)
    return cleaned.strip()

# 4. 월 전체 급식 데이터 조회 함수
@st.cache_data(ttl=3600)
def fetch_monthly_meal_data(school_code, start_date, end_date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": ATPT_CODE,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            df = pd.DataFrame(rows)
            df['DDISH_CLEAN'] = df['DDISH_NM'].apply(clean_menu)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류 발생: {e}")
        return pd.DataFrame()

# 5. UI 구성
st.title("🍱 고등학교 월별 급식 메뉴 조회")

col1, col2, col3 = st.columns(3)

with col1:
    selected_school_name = st.selectbox("학교 선택", list(SCHOOL_MAP.keys()))

now = datetime.now()
with col2:
    # 연도 선택 (현재 연도 기준 전후 1년)
    selected_year = st.selectbox("연도 선택", list(range(now.year - 1, now.year + 2)), index=1)

with col3:
    # 월 선택
    selected_month = st.selectbox("월 선택", list(range(1, 13)), index=now.month - 1)

# 선택한 월의 시작일과 마지막일 계산
_, last_day = calendar.monthrange(selected_year, selected_month)
start_ymd = f"{selected_year}{selected_month:02d}01"
end_ymd = f"{selected_year}{selected_month:02d}{last_day:02d}"

school_code = SCHOOL_MAP[selected_school_name]

if st.button(f"{selected_year}년 {selected_month}월 급식 전체 조회", use_container_width=True):
    with st.spinner("월별 급식 데이터를 불러오는 중입니다..."):
        df_meal = fetch_monthly_meal_data(school_code, start_ymd, end_ymd)
        
        if not df_meal.empty:
            st.subheader(f"📅 {selected_school_name} - {selected_year}년 {selected_month}월 급식")
            
            # 일자순 정렬
            df_meal['MLSV_YMD'] = pd.to_datetime(df_meal['MLSV_YMD'], format='%Y%m%d')
            df_meal = df_meal.sort_values(by='MLSV_YMD')
            
            # 날짜별 탭 또는 Grid 구성
            dates = df_meal['MLSV_YMD'].unique()
            
            # 날짜별로 펼침 상자(Expander) 형태로 출력
            for date_val in dates:
                date_str = pd.to_datetime(date_val).strftime("%Y-%m-%d (%a)")
                day_meals = df_meal[df_meal['MLSV_YMD'] == date_val]
                
                with st.expander(f"📌 {date_str}", expanded=False):
                    for _, row in day_meals.iterrows():
                        meal_type = row.get('MMEAL_SC_NM', '급식')
                        cal_info = row.get('CAL_INFO', '정보 없음')
                        menu_text = row.get('DDISH_CLEAN', '메뉴 정보 없음')
                        
                        st.markdown(f"**[{meal_type}]** - 🔥 {cal_info}")
                        st.text(menu_text)
                        st.markdown("---")
        else:
            st.warning(f"선택한 {selected_year}년 {selected_month}월에는 급식 정보가 없거나 방학 기간입니다.")
