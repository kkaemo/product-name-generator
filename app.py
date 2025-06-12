import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime
import hashlib, hmac, base64, time, json

# 네이버 검색광고 API 설정
NAVER_API_URL = "https://api.naver.com/ncc/keywords"
CUSTOMER_ID = "1806006"
SECRET_KEY = "AQAAAACw74r1xezPDFy7DunyO5PTqpt3IjSZZUVqtxEVMp/33g=="

def get_naver_headers(method, path, body_str):
    timestamp = str(int(time.time() * 1000))
    message = f"{method} {path}\n{timestamp}\n{CUSTOMER_ID}\n{body_str}"
    signature = base64.b64encode(hmac.new(SECRET_KEY.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    return {
        "X-Timestamp": timestamp,
        "X-Client-Id": CUSTOMER_ID,
        "X-Client-Secret": SECRET_KEY,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }

@st.cache_data(show_spinner=False)
def fetch_naver_keyword_data(keyword):
    path = "/ncc/keywords"
    body = {
        "hintKeywords": [keyword],
        "range": "MONTHLY",
        "timeRange": "LAST_12_MONTHS"
    }
    res = requests.post(NAVER_API_URL, headers=get_naver_headers("POST", path, json.dumps(body)), json=body, timeout=10)
    if res.status_code == 200:
        return res.json().get("keywordList", [])
    return []

@st.cache_data(show_spinner=False)
def fetch_domaggook_count(keyword):
    res = requests.get(
        "https://domeggook.com/ssl/api/",
        params={
            "ver": "4.0",
            "mode": "getItemList",
            "aid": "097fc5678c5b66bf0b7dd2be8d1b7fdb",
            "market": "dome",
            "keyword": keyword,
            "om": "json"
        },
        timeout=10
    )
    data = res.json()
    return int(data.get("totalCount", 0))

@st.cache_data(show_spinner=False)
def fetch_filtered_keywords(keyword):
    data = fetch_naver_keyword_data(keyword)
    results = []
    for item in data:
        search_sum = item["pcKeyword"]["monthlyAvgSearchAmount"] + item["mobileKeyword"]["monthlyAvgSearchAmount"]
        if search_sum <= 3000 and item["competitor"] == "LOW":
            count = fetch_domaggook_count(item["keyword"])
            if count <= 10000:
                results.append(item["keyword"])
        if len(results) >= 10:
            break
    return results

@st.cache_data(show_spinner=False)
def generate_filtered_names(keyword):
    kws = fetch_filtered_keywords(keyword)
    if not kws:
        return ["조건을 만족하는 키워드가 없습니다"]
    names = []
    for k in kws:
        nm = f"{k} 무선 초소형 강풍 휴대용 선풍기"
        if len(nm) <= 49:
            names.append(nm)
    return names[:10]

def extract_keyword(title):
    for kw in ["손풍기","선풍기","보냉백","피크닉","캠핑"]:
        if kw in title:
            return kw
    return title.split()[0] if title else ""

st.title("📦 자동 상품명 생성기 (실시간 필터링)")
st.markdown("키워드 입력 또는 엑셀 업로드 → 조건 만족 시 추천 상품명 10개 생성")

input_kw = st.text_input("대표 키워드 입력 (예: 손풍기)")
if input_kw:
    for nm in generate_filtered_names(input_kw):
        st.write("- ", nm)

uploaded = st.file_uploader("또는 엑셀 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded)
    df.columns = ["도매처_상품명"]
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_filtered_names(x)))
    st.dataframe(df)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name="추천")
    st.download_button("엑셀 다운로드", buf.getvalue(), file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
