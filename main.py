import streamlit as st
import pandas as pd
import requests
import re
import calendar
from datetime import datetime
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="고등학교 달력형 급식 & 칼로리 분석",
    page_icon="🍱",
    layout="wide"
)

# 2. 학교 정보 및 기본 설정 (서울시교육청: B10)
SCHOOL_MAP = {
    "성남고등학교": "7010193",
    "당곡고등학교": "7010073",
    "수도여자고등학교": "7010090"
}
ATPT_CODE = "B10"
WEEKDAYS_KOR = ["월", "화", "수", "목", "금", "토", "일"]

# 3. 메뉴 정제 함수 (알레르기 번호 제거)
def clean_menu(text):
    if not text or not isinstance(text, str):
        return ""
    cleaned = re.sub(r'<br\s*/?>', '\n', text)
    cleaned = re.sub(r'\([0-9\.]+\)', '', cleaned)
    return cleaned.strip()

# 4. 칼로리 숫자 파싱 함수
def extract_calories(cal_str):
    if not isinstance(cal_str, str):
        return None
    match = re.search(r'([\d\.]+)', cal_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

# 5. 월 전체 급식 데이터 API 호출 함수
@st.cache_data(ttl=3600)
def fetch_monthly_meal_data(school_code, start_date, end_date, api_key):
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
    
    # 인증키가 입력되었을 경우 파라미터 추가
    if api_key and api_key.strip():
        params["KEY"] = api_key.strip()
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # 나이스 API 성공 응답 확인
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            df = pd.DataFrame(rows)
            df['DDISH_CLEAN'] = df['DDISH_NM'].apply(clean_menu)
            df['CAL_NUM'] = df['CAL_INFO'].apply(extract_calories)
            df['DATE_DT'] = pd.to_datetime(df['MLSV_YMD'], format='%Y%m%d')
            df['DAY_NUM'] = df['DATE_DT'].dt.day
            df['WEEKDAY_NAME'] = df['DATE_DT'].dt.dayofweek.apply(lambda x: WEEKDAYS_KOR[x])
            return df
        else:
            # 에러 메시지 세부 확인
            if "RESULT" in data:
                st.caption(f"API 응답: {data['RESULT'].get('MESSAGE', '')}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 수신 오류: {e}")
        return pd.DataFrame()

# --- 6. 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 옵션 설정")
    api_key_input = st.text_input("나이스 API Key (선택)", help="인증키가 없으면 최대 5건만 조회될 수 있습니다.")
    st.markdown("""
    💡 **참고**:
    나이스 교육정보 개방 포털(open.neis.go.kr)에서 무료 발급받은 KEY를 넣으면 1개월 전체 데이터가 끊김 없이 정상 조회됩니다.
    """)

# --- 7. 메인 UI 구성 ---
st.title("🍱 달력형 급식 식단표 및 요일별 칼로리 분석")

col1, col2, col3 = st.columns([2, 1, 1])

now = datetime.now()
with col1:
    selected_school_name = st.selectbox("🏫 학교 선택", list(SCHOOL_MAP.keys()))
with col2:
    selected_year = st.selectbox("📅 연도", list(range(now.year - 1, now.year + 2)), index=1)
with col3:
    selected_month = st.selectbox("🗓️ 월", list(range(1, 13)), index=now.month - 1)

# 날짜 범위 및 파라미터 계산
_, last_day = calendar.monthrange(selected_year, selected_month)
start_ymd = f"{selected_year}{selected_month:02d}01"
end_ymd = f"{selected_year}{selected_month:02d}{last_day:02d}"
school_code = SCHOOL_MAP[selected_school_name]

# 데이터 페칭
df_meal = fetch_monthly_meal_data(school_code, start_ymd, end_ymd, api_key_input)

if df_meal.empty:
    st.warning(f"⚠️ {selected_school_name}의 {selected_year}년 {selected_month}월 급식 데이터가 없거나, 주말/방학 기간입니다.")
    st.info("💡 사이드바에 나이스 Open API 키(KEY)를 입력하시면 전체 한 달 분량이 정확히 출력됩니다.")
else:
    st.markdown("---")
    st.subheader(f"📊 {selected_school_name} - {selected_year}년 {selected_month}월 요일별 평균 칼로리")
    
    # 요일별 칼로리 평균 계산 (월~금 순서 정리)
    valid_cal_df = df_meal.dropna(subset=['CAL_NUM'])
    if not valid_cal_df.empty:
        avg_cal_by_day = valid_cal_df.groupby('WEEKDAY_NAME')['CAL_NUM'].mean().reset_index()
        
        weekday_order = ["월", "화", "수", "목", "금"]
        avg_cal_by_day['WEEKDAY_NAME'] = pd.Categorical(avg_cal_by_day['WEEKDAY_NAME'], categories=weekday_order, ordered=True)
        avg_cal_by_day = avg_cal_by_day.dropna().sort_values('WEEKDAY_NAME')
        
        # Plotly 막대그래프 렌더링
        fig = px.bar(
            avg_cal_by_day,
            x='WEEKDAY_NAME',
            y='CAL_NUM',
            labels={'WEEKDAY_NAME': '요일', 'CAL_NUM': '평균 칼로리 (Kcal)'},
            text_auto='.1f',
            color='CAL_NUM',
            color_continuous_scale='Oranges'
        )
        fig.update_layout(
            height=320,
            xaxis_title="요일",
            yaxis_title="평균 칼로리 (Kcal)",
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("해당 월의 칼로리 정보 데이터가 충분하지 않습니다.")

    st.markdown("---")
    st.subheader(f"📅 {selected_year}년 {selected_month}월 급식 달력")

    # 달력 격자(Calendar Matrix) 생성
    cal_matrix = calendar.monthcalendar(selected_year, selected_month)
    
    # 요일 헤더 출력 (월 ~ 일)
    cols = st.columns(7)
    for idx, day_name in enumerate(WEEKDAYS_KOR):
        cols[idx].markdown(f"### <center>{day_name}</center>", unsafe_allow_html=True)

    # 날짜별 셀 출력
    for week in cal_matrix:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            with week_cols[i]:
                if day == 0:
                    st.write("")
                else:
                    day_data = df_meal[df_meal['DAY_NUM'] == day]
                    
                    if not day_data.empty:
                        # 총 칼로리 추출
                        cal_text = day_data['CAL_INFO'].values[0] if 'CAL_INFO' in day_data.columns else ""
                        st.markdown(f"**{day}일**  \n🔥 `<span style='color:#e74c3c;font-size:0.85em;'>{cal_text}</span>`", unsafe_allow_html=True)
                        
                        # 메뉴 리스트 정돈
                        menu_str = day_data['DDISH_CLEAN'].values[0]
                        menus = [m.strip() for m in menu_str.split('\n') if m.strip()]
                        
                        menu_html = "<ul style='font-size:0.8em; padding-left:14px; margin-top:4px; margin-bottom:12px;'>"
                        for m in menus[:6]:
                            menu_html += f"<li>{m}</li>"
                        if len(menus) > 6:
                            menu_html += f"<li>...외 {len(menus)-6}개</li>"
                        menu_html += "</ul>"
                        st.markdown(menu_html, unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{day}일**")
                        st.caption("급식 없음")
