import streamlit as st
import pandas as pd
import requests
import io
import hmac
import hashlib
import base64
import time
from datetime import datetime

# 네이버 광고 API 인증 정보
API_BASE_URL = "https://api.naver.com"
CUSTOMER_ID = "1806006"
API_KEY = "1806006"
SECRET_KEY = "AQAAAACw74r1xezPDFy7DunyO5PTqpt3IjSZZUVqtxEVMp/33g=="

# 도매꾹 API 키
DOMEGGOOK_API_KEY = "097fc5678c5b66bf0b7dd2be8d1b7fdb"

# Header 생성 함수
def get_naver_headers(uri, method="GET"):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-CUSTOMER": CUSTOMER_ID,
        "X-Signature": signature,
    }

# 키워드 검색량 + 경쟁도 조회
@st.cache_data(show_spinner=False)
def get_naver_keywords(base_keyword):
    uri = f"/keywordstool?hintKeywords={base_keyword}&showDetail=1"
    headers = get_naver_headers(uri)
    response = requests.get(f"{API_BASE_URL}{uri}", headers=headers)
    if response.status_code == 200:
        data = response.json().get("keywordList", [])
        return data
    return []

# 도매꾹 상품 수 조회
@st.cache_data(show_spinner=False)
def get_domeggook_count(keyword):
    try:
        res = requests.get(
            "https://domeggook.com/ssl/api/",
            params={
                "ver": "4.0",
                "mode": "getItemList",
                "aid": DOMEGGOOK_API_KEY,
                "market": "dome",
                "keyword": keyword,
                "om": "json"
            },
            timeout=5
        )
        return int(res.json().get("totalCount", 0))
    except:
        return 999999  # 오류 시 제외 처리

# 필터링된 키워드 추출
@st.cache_data(show_spinner=False)
def get_filtered_keywords(base_keyword):
    candidates = get_naver_keywords(base_keyword)
    filtered = []
    for item in candidates:
        search_vol = item.get("monthlyPcQcCnt", 0) + item.get("monthlyMobileQcCnt", 0)
        comp = item.get("compIdx", "")
        kw = item.get("relKeyword", "")
        if search_vol <= 3000 and comp == "낮음":
            product_count = get_domeggook_count(kw)
            if product_count <= 10000:
                filtered.append(kw)
        if len(filtered) >= 10:
            break
    return filtered

# 추천 상품명 생성
def generate_product_names(base_keyword):
    kws = get_filtered_keywords(base_keyword)
    if not kws:
        return ["조건을 만족하는 키워드가 없습니다"]
    names = []
    for kw in kws:
        name = f"{kw} 무선 초소형 강풍 휴대용 선풍기"
        if len(name) <= 49:
            names.append(name)
    return names[:10]

# 도매처 상품명에서 키워드 추출
def extract_base_keyword(text):
    for kw in ["손풍기", "선풍기", "보냉백", "캠핑", "탁상용", "무선"]:
        if kw in text:
            return kw
    return text.split()[0] if text else ""

# UI 시작
st.title("📦 실시간 조건 필터 기반 상품명 생성기")

st.markdown("🔍 **대표 키워드를 입력하면 조건 만족 키워드로 구성된 상품명이 생성됩니다**")

# 키워드 직접 입력
input_kw = st.text_input("대표 키워드를 입력하세요 (예: 손풍기)")
if input_kw:
    st.subheader(f"추천 상품명 (기준 키워드: {input_kw})")
    for name in generate_product_names(input_kw):
        st.write("- ", name)

# 엑셀 업로드
st.markdown("---")
uploaded_file = st.file_uploader("또는 엑셀 업로드 (.xlsx) - A열에 도매처 상품명", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = ["도매처_상품명"]
    df["대표키워드"] = df["도매처_상품명"].apply(extract_base_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_product_names(x)))

    st.subheader("📊 분석 결과 미리보기")
    st.dataframe(df.head(10))

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="추천결과")

    st.download_button(
        label="📥 추천결과 엑셀 다운로드",
        data=output.getvalue(),
        file_name=f"추천상품명_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
