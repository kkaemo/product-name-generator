import streamlit as st
import pandas as pd
import requests
import io
import hmac
import hashlib
import base64
import time
from datetime import datetime

# 시크릿 키 정보 불러오기 (Streamlit Secrets 사용)
CUSTOMER_ID = st.secrets["NAVER_CUSTOMER_ID"]
API_KEY = st.secrets["NAVER_API_KEY"]
SECRET_KEY = st.secrets["NAVER_SECRET_KEY"]
DOMEGGOOK_API_KEY = st.secrets["DOMEGGOOK_API_KEY"]
NAVER_API_HOST = "https://api.naver.com"

# 인증 헤더 생성 함수
def make_signature(uri, method="GET"):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return timestamp, signature

# 네이버 키워드 조회
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
    res = requests.get(url, headers=headers, timeout=10)
    st.markdown(f"🔎 응답 상태 코드: `{res.status_code}`")
    try:
        st.markdown(f"🔎 응답 원문:\n```json\n{res.text}```")
    except:
        pass
    if res.status_code == 200:
        return res.json().get("keywordList", [])
    return []

# 도매꾹 상품 수 확인 API
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

# 유효한 키워드 필터링
def find_valid_keywords(base_keyword):
    data = get_naver_keywords(base_keyword)
    st.markdown("🔍 API 응답 키워드 샘플\n```json\n" + str(data[:3]) + "\n```")
    valid = []
    for it in data:
        pc = it.get("monthlyPcQcCnt", 0)
        mo = it.get("monthlyMobileQcCnt", 0)
        comp = it.get("compIdx", "")
        kw = it.get("relKeyword", "")
        if pc + mo <= 3000 and comp in ["낮음", "LOW"]:
            cnt = get_domeggook_count(kw)
            if cnt <= 10000:
                valid.append(kw)
        if len(valid) >= 10:
            break
    return valid

# 상품명 조합
def generate_names(kw):
    kws = find_valid_keywords(kw)
    if not kws:
        return ["• 조건을 만족하는 키워드가 없습니다"]
    return [f"{k} 무선 초소형 강풍 휴대용"[:49] for k in kws]

# 대표 키워드 추출
def extract_keyword(text):
    for kw in ["손풍기", "보냉백", "선풍기", "캠핑", "무선"]:
        if kw in text:
            return kw
    return text.split()[0] if text else ""

# UI 영역
st.title("📦 실시간 조건 기반\n상품명 추천기")
kw = st.text_input("대표 키워드 입력 (예: 손풍기)")
if kw:
    for name in generate_names(kw):
        st.write(name)

uploaded = st.file_uploader("또는 엑셀 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded).iloc[:, [0]].rename(columns={df.columns[0]: "도매처_상품명"})
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.dataframe(df.head(10))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="추천")
    st.download_button(
        "📥 결과 엑셀 다운로드",
        buf.getvalue(),
        file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
