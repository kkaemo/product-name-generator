import streamlit as st
import requests
import time
import hmac
import hashlib
import base64
import pandas as pd
import io
from datetime import datetime

# 📌 Streamlit Secrets 에서 API 정보 불러오기
NAVER_API_KEY = st.secrets["NAVER_API_KEY"]
NAVER_SECRET_KEY = st.secrets["NAVER_SECRET_KEY"]
NAVER_CUSTOMER_ID = st.secrets["NAVER_CUSTOMER_ID"]
DOMEGGOOK_API_KEY = st.secrets["DOMEGGOOK_API_KEY"]

# 📌 시그니처 생성 함수
def make_signature(path: str, method="GET"):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{path}"
    signature = base64.b64encode(
        hmac.new(NAVER_SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return timestamp, signature

# 📌 네이버 키워드 API 요청 함수
def get_keywords(keyword):
    path = "/keywordstool"
    url = f"https://api.naver.com{path}"
    params = {"hintKeywords": keyword, "showDetail": "1"}
    timestamp, signature = make_signature(path)
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": NAVER_API_KEY,
        "X-Customer": NAVER_CUSTOMER_ID,
        "X-Signature": signature,
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        st.markdown(f"🔍 응답 상태 코드: `{response.status_code}`")
        if response.status_code == 200:
            return response.json().get("keywordList", [])
        else:
            st.error(f"❌ 네이버 API 오류: {response.status_code}")
            st.json(response.json())
            return []
    except Exception as e:
        st.error(f"연결 실패: {e}")
        return []

# 📌 도매꾹 상품 수 확인 함수
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
        return 999999

# 📌 유효한 키워드 필터링
def find_valid_keywords(base_keyword):
    data = get_keywords(base_keyword)
    valid = []
    for item in data:
        pc = item.get("monthlyPcQcCnt", 0)
        mo = item.get("monthlyMobileQcCnt", 0)
        comp = item.get("compIdx", "")
        kw = item.get("relKeyword", "")
        if pc + mo <= 3000 and comp in ["낮음", "LOW"]:
            cnt = get_domeggook_count(kw)
            if cnt <= 10000:
                valid.append(kw)
        if len(valid) >= 10:
            break
    return valid

# 📌 상품명 생성
def generate_names(kw):
    kws = find_valid_keywords(kw)
    if not kws:
        return ["조건을 만족하는 키워드가 없습니다"]
    return [f"{k} 무선 초소형 강풍 휴대용"[:49] for k in kws]

# 📌 키워드 추출
def extract_keyword(text):
    for kw in ["손풍기", "보냉백", "선풍기", "캠핑", "무선"]:
        if kw in text:
            return kw
    return text.split()[0] if text else ""

# 📌 Streamlit UI
st.set_page_config(page_title="상품명 키워드 추천기", layout="centered")
st.title("📦 조건 기반 상품명 추천 도구 (네이버+도매꾹 연동)")

keyword = st.text_input("대표 키워드 입력 (예: 손풍기)")
if keyword:
    st.subheader("🎯 추천 상품명")
    names = generate_names(keyword)
    for n in names:
        st.write("•", n)

    st.subheader("📊 네이버 API 키워드 상세")
    raw_data = get_keywords(keyword)
    if raw_data:
        df = pd.DataFrame(raw_data)[["relKeyword", "monthlyPcQcCnt", "monthlyMobileQcCnt", "compIdx"]]
        df.columns = ["키워드", "PC검색량", "모바일검색량", "경쟁도"]
        st.dataframe(df, use_container_width=True)

# 📁 엑셀 업로드
uploaded = st.file_uploader("또는 Excel 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded).iloc[:, [0]].rename(columns={df.columns[0]: "도매처_상품명"})
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.dataframe(df.head(10))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="추천")
    st.download_button("📥 결과 엑셀 다운로드", buf.getvalue(), file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
