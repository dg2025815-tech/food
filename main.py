import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime

# 1. 스트림릿 기본 페이지 설정
st.set_page_config(
    page_title="학교 급식 정보 조회",
    page_icon="🍱",
    layout="centered"
)

# 2. 학교 정보 및 관할 교육청 설정 (서울시교육청: B10)
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

# 4. 나이스 API 데이터 조회 함수 (캐싱 적용)
@st.cache_data(ttl=3600)
def fetch_meal_data(school_code, start_date, end_date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
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

# 5. 메인 UI 화면
st.title("🍱 고등학교 급식 메뉴 조회")
st.write("성남고, 당곡고, 수도여고의 급식 정보를 확인하세요.")

col1, col2 = st.columns(2)
with col1:
    selected_school_name = st.selectbox("학교 선택", list(SCHOOL_MAP.keys()))
with col2:
    selected_date = st.date_input("날짜 선택", datetime.now())

ymd = selected_date.strftime("%Y%m%d")
school_code = SCHOOL_MAP[selected_school_name]

if st.button("급식 조회", use_container_width=True):
    with st.spinner("급식 정보를 조회 중입니다..."):
        df_meal = fetch_meal_data(school_code, ymd, ymd)
        
        if not df_meal.empty:
            for _, row in df_meal.iterrows():
                meal_type = row.get('MMEAL_SC_NM', '급식')
                cal_info = row.get('CAL_INFO', '정보 없음')
                menu_text = row.get('DDISH_CLEAN', '메뉴 정보 없음')
                
                st.success(f"**{selected_school_name} - {meal_type}**")
                st.caption(f"🔥 열량: {cal_info}")
                st.markdown("---")
                
                # 메뉴 리스트 출력
                menus = menu_text.split('\n')
                for m in menus:
                    if m.strip():
                        st.markdown(f"* {m.strip()}")
        else:
            st.warning(f"선택한 날짜({selected_date.strftime('%Y-%m-%d')})에는 급식 정보가 없거나 주말/방학입니다.")
