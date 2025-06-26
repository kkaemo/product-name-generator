import streamlit as st
import pandas as pd
import requests
import io
import hmac
import hashlib
import base64
import time
from datetime import datetime

# 🔐 시크릿 정보 (Streamlit Cloud > Settings > Secrets에 등록 필요)
CUSTOMER_ID = st.secrets["NAVER_CUSTOMER_ID"]
API_KEY = st.secrets["NAVER_API_KEY"]
SECRET_KEY = st.secrets["NAVER_SECRET_KEY"]
DOMEGG_API_KEY = st.secrets["DOMEGGOOK_API_KEY"]
NAVER_API_HOST = "https://api.naver.com"

# 📌 네이버 검색광고 API 서명 생성 함수
def make_signature(uri, method="GET"):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()).decode()
    return timestamp, signature

# 📡 네이버 연관 키워드 데이터 가져오기
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
        st.session_state['last_naver_response'] = res
        if res.status_code == 200:
            return res.json().get("keywordList", [])
        else:
            return []
    except Exception as e:
        st.error(f"네이버 API 요청 오류: {e}")
        return []

# 📦 도매꾹 상품 수량 확인
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

# 🎯 조건 필터링 키워드 추출
def find_valid_keywords(base_keyword):
    data = get_naver_keywords(base_keyword)
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

# 🧠 최종 상품명 생성
def generate_names(kw):
    try:
        kws = find_valid_keywords(kw)
        if not kws:
            return ["조건을 만족하는 키워드가 없습니다"]
        return [f"{k} 무선 초소형 강풍 휴대용"[:49] for k in kws]
    except Exception as e:
        return [f"🚫 네이버 API 오류: {st.session_state.get('last_naver_response').status_code}"]

# 🔍 상품명에서 대표 키워드 추출
def extract_keyword(text):
    for kw in ["손풍기", "선풍기", "보냉백", "캠핑", "무선"]:
        if kw in text:
            return kw
    return text.split()[0] if text else ""

# 🖥️ UI
st.title("📦 조건 기반 상품명 추천 도구 (네이버+도매꾹 연동)")

# 👉 키워드 입력
kw = st.text_input("대표 키워드 입력 (예: 손풍기)")

# 👉 결과 출력
if kw:
    st.subheader("🎯 추천 상품명")
    names = generate_names(kw)
    for name in names:
        st.write("•", name)

    # 네이버 응답 결과 원문 확인
    st.subheader("📊 네이버 API 키워드 상세")
    with st.expander("키워드 상세 리스트 펼치기"):
        res = st.session_state.get('last_naver_response')
        if res is not None and res.status_code == 200:
            data = res.json().get("keywordList", [])
            for item in data:
                st.markdown(f"- 🔑 **{item['relKeyword']}** | PC: {item['monthlyPcQcCnt']}, 모바일: {item['monthlyMobileQcCnt']} | 클릭률: PC {item['monthlyAvePcCtr']}, 모바일 {item['monthlyAveMobileCtr']} | 경쟁도: {item['compIdx']}")
        else:
            st.error(f"❌ 네이버 API 오류: {res.status_code if res else '연결 실패'}")

# 📁 엑셀 업로드 기능
uploaded = st.file_uploader("또는 Excel 업로드 (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded).iloc[:, [0]].rename(columns={df.columns[0]: "도매처_상품명"})
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.dataframe(df.head(10))

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 결과 Excel 다운로드", buf.getvalue(), file_name=f"추천_{datetime.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
