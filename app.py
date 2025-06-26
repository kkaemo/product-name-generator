import streamlit as st
import pandas as pd
import requests
import io
import hmac
import hashlib
import base64
import time
from datetime import datetime

# 🔐 API 인증 정보
CUSTOMER_ID = st.secrets["NAVER_CUSTOMER_ID"]
API_KEY = st.secrets["NAVER_API_KEY"]
SECRET_KEY = st.secrets["NAVER_SECRET_KEY"]
DOMEGG_API_KEY = st.secrets["DOMEGGOOK_API_KEY"]
NAVER_API_HOST = "https://api.naver.com"

# ✅ 네이버 API 서명 생성
def make_signature(uri, method="GET"):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()).decode()
    return timestamp, signature

# ✅ 네이버 키워드툴 API 호출
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
        else:
            st.warning(f"⛔ 네이버 API 오류: {res.status_code}")
            return []
    except Exception as e:
        st.error(f"요청 실패: {e}")
        return []

# ✅ 도매꾹 상품 수 조회
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

# ✅ 조건에 맞는 키워드 필터링
def find_valid_keywords(base_keyword):
    data = get_naver_keywords(base_keyword)
    valid = []
    for item in data:
        pc = item.get("monthlyPcQcCnt", 0)
        mo = item.get("monthlyMobileQcCnt", 0)
        comp = item.get("compIdx", "").lower()
        kw = item.get("relKeyword", "")
        if pc + mo <= 3000 and comp in ["낮음", "low"]:
            cnt = get_domeggook_count(kw)
            if cnt <= 10000:
                valid.append(kw)
        if len(valid) >= 10:
            break
    return valid

# ✅ 상품명 자동 생성
def generate_names(base_keyword):
    keywords = find_valid_keywords(base_keyword)
    if not keywords:
        return ["조건을 만족하는 키워드가 없습니다."]
    return [f"{k} 무선 초소형 강풍 휴대용"[:49] for k in keywords]

# ✅ 상품명에서 대표 키워드 추출
def extract_keyword(text):
    for kw in ["손풍기", "보냉백", "선풍기", "캠핑", "무선"]:
        if kw in text:
            return kw
    return text.split()[0] if text else ""

# 🖥️ Streamlit UI 구성
st.title("📦 조건 기반 상품명 추천 도구 (네이버+도매꾹 연동)")

# 🔍 텍스트 기반 추천
kw = st.text_input("대표 키워드 입력 (예: 손풍기)")
if kw:
    st.subheader("🎯 추천 상품명")
    for name in generate_names(kw):
        st.write("•", name)

    st.markdown("---")
    st.subheader("📊 네이버 API 키워드 상세")
    with st.expander("키워드 상세 리스트 펼치기"):
        for item in get_naver_keywords(kw):
            st.markdown(f"- **키워드**: `{item['relKeyword']}`")
            st.markdown(f"    - 📈 검색량: PC {item['monthlyPcQcCnt']} / 모바일 {item['monthlyMobileQcCnt']}")
            st.markdown(f"    - 🎯 클릭률: PC {item['monthlyAvePcCtr']}, 모바일 {item['monthlyAveMobileCtr']}")
            st.markdown(f"    - 🏁 경쟁도: {item['compIdx']}")

# 📁 엑셀 업로드 기능
uploaded = st.file_uploader("또는 Excel 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded).iloc[:, [0]].rename(columns={df.columns[0]: "도매처_상품명"})
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.subheader("📑 엑셀 분석 결과 미리보기")
    st.dataframe(df.head(10))

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="추천")
    st.download_button("📥 엑셀 결과 다운로드", buf.getvalue(), file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
