import urllib.request
import json
import pandas as pd
import re

# 1. 학교 코드 및 관할 교육청 설정
# B10: 서울특별시교육청
ATPT_OFCDC_SC_CODE = "B10" 
API_KEY = "YOUR_API_KEY"  # 나이스 오픈API 키 (없을 경우 공백 처리 가능하나 조회 제한이 있을 수 있음)

# 학교 코드 매핑
SCHOOL_CODES = {
    "7010073": "당곡고등학교",
    "7010193": "성남고등학교",
    "7010090": "수도여자고등학교"
}

def clean_menu_string(text):
    """급식 메뉴 내 알레르기 유발물질 번호 및 기타 특수문자 제거 함수"""
    if not isinstance(text, str):
        return ""
    # 메뉴명 뒤의 <br/> 태그 및 알레르기 원산지 정보 번호 제거
    cleaned = re.sub(r'<br\s*/?>', '\n', text)
    cleaned = re.sub(r'\([0-9\.]+\)', '', cleaned)
    return cleaned.strip()

def fetch_school_meals(school_code, start_date, end_date):
    """
    특정 학교의 급식 정보를 API로 조회합니다.
    start_date / end_date 포맷: 'YYYYMMDD' (예: '20240301')
    """
    base_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = (
        f"?KEY={API_KEY}"
        f"&Type=json"
        f"&pIndex=1"
        f"&pSize=1000"
        f"&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}"
        f"&SD_SCHUL_CODE={school_code}"
        f"&MLSV_FROM_YMD={start_date}"
        f"&MLSV_TO_YMD={end_date}"
    )
    
    url = base_url + params
    
    try:
        req = urllib.request.urlopen(url)
        res = req.read().decode('utf-8')
        data = json.loads(res)
        
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            df = pd.DataFrame(rows)
            
            # 메뉴 가공
            df['DDISH_NM_CLEAN'] = df['DDISH_NM'].apply(clean_menu_string)
            return df
        else:
            print(f"[{SCHOOL_CODES.get(school_code, school_code)}] 해당 기간 내 급식 데이터가 없습니다.")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"데이터 수집 중 오류 발생 ({school_code}): {e}")
        return pd.DataFrame()

# 2. 3개 고등학교 데이터 일괄 수집 실행
start_ymd = "20240301"  # 조회 시작일
end_ymd = "20240331"    # 조회 종료일

df_list = []
for code in SCHOOL_CODES.keys():
    df_school = fetch_school_meals(code, start_ymd, end_ymd)
    if not df_school.empty:
        df_list.append(df_school)

# 3. 데이터 합치기 및 컬럼 정리
if df_list:
    total_df = pd.concat(df_list, ignore_index=True)
    
    # 핵심 컬럼 재정렬
    selected_cols = {
        'SD_SCHUL_CODE': '학교코드',
        'SCHUL_NM': '학교명',
        'MLSV_YMD': '급식일자',
        'MMEAL_SC_NM': '식사구분',  # 중식/석식
        'DDISH_NM_CLEAN': '메뉴',
        'CAL_INFO': '열량(kcal)',
        'NTR_INFO': '영양정보'
    }
    
    result_df = total_df[list(selected_cols.keys())].rename(columns=selected_cols)
    print(result_df.head(10))
