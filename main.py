import requests
import re
import calendar
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import platform

# 1. 한글 폰트 설정 (운영체제별 자동 설정하여 한글 깨짐 방지)
os_name = platform.system()
if os_name == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif os_name == 'Darwin':  # Mac
    plt.rcParams['font.family'] = 'AppleGothic'
else:  # Linux / 기타
    plt.rcParams['font.family'] = 'NanumGothic'

plt.rcParams['axes.unicode_minus'] = False

# 2. 학교 정보 및 기본 설정 (서울시교육청: B10)
SCHOOL_MAP = {
    "1": ("성남고등학교", "7010193"),
    "2": ("당곡고등학교", "7010073"),
    "3": ("수도여자고등학교", "7010090")
}
ATPT_CODE = "B10"
WEEKDAYS_KOR = ["월", "화", "수", "목", "금", "토", "일"]

# 3. 메뉴 정제 함수 (알레르기 번호 제거)
def clean_menu(text):
    if not text or not isinstance(text, str):
        return ""
    cleaned = re.sub(r'<br\s*/?>', ', ', text)
    cleaned = re.sub(r'\([0-9\.]+\)', '', cleaned)
    return cleaned.strip()

# 4. 칼로리 수치 파싱 함수
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

# 5. 나이스 API 데이터 수집 함수
def fetch_monthly_meal(school_code, start_ymd, end_ymd, api_key=""):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": ATPT_CODE,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": start_ymd,
        "MLSV_TO_YMD": end_ymd
    }
    if api_key:
        params["KEY"] = api_key

    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            df = pd.DataFrame(rows)
            df['DDISH_CLEAN'] = df['DDISH_NM'].apply(clean_menu)
            df['CAL_NUM'] = df['CAL_INFO'].apply(extract_calories)
            df['DATE_DT'] = pd.to_datetime(df['MLSV_YMD'], format='%Y%m%d')
            df['DAY_NUM'] = df['DATE_DT'].dt.day
            df['WEEKDAY_NAME'] = df['DATE_DT'].dt.dayofweek.apply(lambda x: WEEKDAYS_KOR[x])
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ 데이터 수신 오류: {e}")
        return pd.DataFrame()

# 6. 요일별 칼로리 막대그래프 출력 함수
def plot_calorie_chart(df, school_name, year, month):
    valid_df = df.dropna(subset=['CAL_NUM'])
    if valid_df.empty:
        print("\n⚠️ 칼로리 데이터가 충분하지 않아 그래프를 출력할 수 없습니다.")
        return

    # 요일별 평균 계산 (월~금)
    avg_cal = valid_df.groupby('WEEKDAY_NAME')['CAL_NUM'].mean().reindex(["월", "화", "수", "목", "금"]).dropna()
    
    plt.figure(figsize=(9, 5.5))
    bars = plt.bar(avg_cal.index, avg_cal.values, color='#ff9f43', edgecolor='#ee5253', width=0.55)
    
    # 막대 상단에 수치 표시
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 8, f'{height:.1f} kcal', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.title(f"{school_name} - {year}년 {month}월 요일별 평균 칼로리", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("요일", fontsize=11, labelpad=8)
    plt.ylabel("평균 칼로리 (Kcal)", fontsize=11, labelpad=8)
    plt.ylim(0, max(avg_cal.values) + 150)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    print("\n📊 요일별 평균 칼로리 막대그래프 창을 엽니다...")
    plt.show()

# 7. 메인 실행 함수
def main():
    print("=" * 60)
    print("🍱 고등학교 월별 급식 달력 & 요일별 칼로리 분석기")
    print("=" * 60)
    
    print("\n[학교 선택]")
    for k, v in SCHOOL_MAP.items():
        print(f"  {k}. {v[0]}")
    
    school_choice = input("학교 번호를 입력하세요 (기본값 1): ").strip() or "1"
    school_name, school_code = SCHOOL_MAP.get(school_choice, SCHOOL_MAP["1"])
    
    now = datetime.now()
    year_input = input(f"연도를 입력하세요 (기본값 {now.year}): ").strip() or str(now.year)
    month_input = input(f"월을 입력하세요 (기본값 {now.month}): ").strip() or str(now.month)
    
    year = int(year_input)
    month = int(month_input)
    
    api_key = input("나이스 Open API Key (선택/없으면 엔터): ").strip()
    
    # 날짜 범위 산출
    _, last_day = calendar.monthrange(year, month)
    start_ymd = f"{year}{month:02d}01"
    end_ymd = f"{year}{month:02d}{last_day:02d}"
    
    print(f"\n⏳ {school_name}의 {year}년 {month}월 급식 정보를 조회하는 중입니다...")
    df = fetch_monthly_meal(school_code, start_ymd, end_ymd, api_key)
    
    if df.empty:
        print(f"\n⚠️ {year}년 {month}월에는 급식 정보가 없거나 방학/휴교 기간입니다.")
        return

    # 1) 요일별 평균 칼로리 막대그래프 출력
    plot_calorie_chart(df, school_name, year, month)
    
    # 2) 터미널에 달력 형태로 식단표 출력
    print(f"\n==================== 📅 {school_name} {year}년 {month}월 급식 달력 ====================")
    
    cal_matrix = calendar.monthcalendar(year, month)
    for week in cal_matrix:
        for day in week:
            if day == 0:
                continue
            
            day_data = df[df['DAY_NUM'] == day]
            if not day_data.empty:
                cal_info = day_data['CAL_INFO'].values[0]
                menu_info = day_data['DDISH_CLEAN'].values[0]
                weekday_str = day_data['WEEKDAY_NAME'].values[0]
                
                print(f"\n📌 [{year}-{month:02d}-{day:02d} ({weekday_str})] 🔥 칼로리: {cal_info}")
                print(f"   🍱 메뉴: {menu_info}")
                print("-" * 65)

if __name__ == "__main__":
    main()
