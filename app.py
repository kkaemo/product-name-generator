import streamlit as st
import pandas as pd
import requests
import io, time, hmac, hashlib, base64
from datetime import datetime

# -- 네이버 검색광고 API 인증 정보
NAVER_BASE = "https://api.naver.com"
CUSTOMER_ID = "1806006"
API_KEY = "1806006"
SECRET_KEY = "AQAAAACw74r1xezPDFy7DunyO5PTqpt3IjSZZUVqtxEVMp/33g=="

def make_naver_header(uri, method="GET"):
    ts = str(int(time.time() * 1000))
    msg = f"{ts}.{method}.{uri}"
    sig = base64.b64encode(hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()).decode()
    return {
        "X-Timestamp": ts,
        "X-API-KEY": API_KEY,
        "X-Customer": CUSTOMER_ID,
        "X-Signature": sig,
        "Content-Type": "application/json; charset=UTF-8"
    }

@st.cache_data(show_spinner=False)
def get_related_keywords(base_keyword):
    uri = f"/keywordstool?hintKeywords={base_keyword}&showDetail=1"
    url = NAVER_BASE + uri
    res = requests.get(url, headers=make_naver_header(uri))
    return res.json().get("keywordList", []) if res.status_code == 200 else []

@st.cache_data(show_spinner=False)
def get_domeggook_count(keyword):
    try:
        r = requests.get(
            "https://domeggook.com/ssl/api/",
            params={"ver":"4.0","mode":"getItemList","aid":"097fc5678c5b66bf0b7dd2be8d1b7fdb","market":"dome","keyword":keyword,"om":"json"},
            timeout=5
        )
        return int(r.json().get("totalCount",0))
    except:
        return 999999

def find_valid_keywords(base_keyword):
    data = get_related_keywords(base_keyword)
    valid = []
    for it in data:
        pc = it.get("monthlyPcQcCnt",0)
        mo = it.get("monthlyMobileQcCnt",0)
        comp = it.get("compIdx","")
        kw = it.get("relKeyword","")
        if pc + mo <= 3000 and comp == "LOW":
            cnt = get_domeggook_count(kw)
            if cnt <= 10000:
                valid.append(kw)
        if len(valid) >= 10:
            break
    return valid

def generate_names(kw):
    kws = find_valid_keywords(kw)
    if not kws:
        return ["조건을 만족하는 키워드가 없습니다"]
    return [f"{k} 무선 초소형 강풍 휴대용"[:49] for k in kws]

# UI 구성
st.title("📦 실시간 조건 기반 상품명 추천기")
kw = st.text_input("대표 키워드 입력 (예: 손풍기)")
if kw:
    for name in generate_names(kw):
        st.write("•", name)

uploaded = st.file_uploader("또는 엑셀 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded).iloc[:, [0]].rename(columns={uploaded: "도매처_상품명"})
    df["키워드"] = df["도매처_상품명"].str.extract("(손풍기|선풍기|보냉백|캠핑|탁상용|무선)", expand=False).fillna("")
    df["추천상품명"] = df["키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.dataframe(df.head(10))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False)
    st.download_button("📥 결과 엑셀 다운로드", buf.getvalue(), file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
