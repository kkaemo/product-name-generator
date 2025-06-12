import streamlit as st
import pandas as pd
import requests
import io
import hmac
import hashlib
import base64
import time
from datetime import datetime

# 네이버 검색광고 API 정보
CUSTOMER_ID = "1806006"
API_KEY = "1806006"
SECRET_KEY = "AQAAAACw74r1xezPDFy7DunyO5PTqpt3IjSZZUVqtxEVMp/33g=="
NAVER_API_HOST = "https://api.naver.com"

# 도매꾹 API 키
DOMEGG_API_KEY = "097fc5678c5b66bf0b7dd2be8d1b7fdb"

# 인증 헤더 생성

def make_signature(uri, method="GET"):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()).decode()
    return timestamp, signature


def get_naver_keywords(base_keyword):
    uri = f"/keywordstool?hintKeywords={base_keyword}&showDetail=1"
    url = NAVER_API_HOST + uri
    timestamp, signature = make_signature(uri)
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-Customer": CUSTOMER_ID,
        "X-Signature": signature,
        "Content-Type": "application/json; charset=UTF-8"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("keywordList", [])
    except:
        pass
    return []


def get_domeggook_count(keyword):
    try:
        res = requests.get(
            "https://domeggook.com/ssl/api/",
            params={
                "ver": "4.0",
                "mode": "getItemList",
                "aid": DOMEGG_API_KEY,
                "market": "dome",
                "keyword": keyword,
                "om": "json"
            },
            timeout=5
        )
        return int(res.json().get("totalCount", 0))
    except:
        return 999999


def generate_names(base_keyword):
    candidates = get_naver_keywords(base_keyword)
    st.write("API 응답 키워드 샘플", candidates[:3])
    valid = []
    for item in candidates:
        pc = item.get("monthlyPcQcCnt", 0)
        mo = item.get("monthlyMobileQcCnt", 0)
        comp = item.get("compIdx", "")
        kw = item.get("relKeyword", "")
        if pc + mo <= 3000 and comp == "낮음":
            prod_count = get_domeggook_count(kw)
            if prod_count <= 10000:
                valid.append(kw)
        if len(valid) >= 10:
            break

    if not valid:
        return ["조건을 만족하는 키워드가 없습니다"]
    names = []
    for k in valid:
        name = f"{k} 무선 초소형 강풍 휴대용"
        if len(name) <= 49:
            names.append(name)
    return names[:10]


def extract_keyword(text):
    for kw in ["손풍기", "보냉백", "선풍기", "캠핑", "무선"]:
        if kw in text:
            return kw
    return text.split()[0] if text else ""

# UI
st.title("📦 실시간 조건 기반 상품명 추천기")
input_kw = st.text_input("대표 키워드 입력 (예: 손풍기)")
if input_kw:
    names = generate_names(input_kw)
    for n in names:
        st.write("•", n)

uploaded = st.file_uploader("또는 엑셀 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded).iloc[:, [0]].rename(columns={df.columns[0]: "도매처_상품명"})
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.dataframe(df.head(10))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="추천")
    st.download_button("📥 결과 엑셀 다운로드", buf.getvalue(), file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
