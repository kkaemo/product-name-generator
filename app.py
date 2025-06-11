상품명 자동 생성기 (실시간 키워드 검색량 + 상품수 필터 반영)

import streamlit as st import pandas as pd import requests import io from datetime import datetime

✅ 네이버 키워드 API 설정

KEYWORD_API_URL = "https://api.aicodelab.mycafe24.com/jit-plugin/getKeywordSearchData" SEARCH_API_URL = "https://api.aicodept.mycafe24.com/jit-plugin/getNaverSearchResults"

✅ 검색량 + 상품수 필터 적용한 키워드 분석 함수

@st.cache_data(show_spinner=False) def fetch_filtered_keywords(keyword): try: kw_res = requests.post(KEYWORD_API_URL, json={"keyword": keyword}, timeout=10) kw_data = kw_res.json().get("keywords", []) filtered = []

for k in kw_data:
        total_search = k["PC 월간검색수"] + k["모바일 월간검색수"]
        if total_search > 3000 or k["경쟁정도"] != "낮음":
            continue

        query = k["키워드"]
        sr_res = requests.post(SEARCH_API_URL, json={"query": query}, timeout=10)
        total_items = len(sr_res.json().get("items", []))

        if total_items <= 10000:
            filtered.append(query)

    return filtered[:10]  # 최대 10개까지만

except:
    return []

✅ 추천 상품명 생성

@st.cache_data(show_spinner=False) def generate_filtered_names(keyword): filtered_keywords = fetch_filtered_keywords(keyword) if not filtered_keywords: return ["❌ 조건을 만족하는 키워드가 없습니다"]

names = []
for kw in filtered_keywords:
    name = f"{kw} 무선 초소형 강풍 휴대용 선풍기"
    if len(name) <= 49:
        names.append(name)
    if len(names) >= 10:
        break
return names

키워드 추출 함수

def extract_keyword(title): for kw in ["손풍기", "선풍기", "보냉백", "피크닉", "캠핑"]: if kw in title: return kw return title.split()[0] if title else ""

✅ UI 구성

st.title("📦 상품명 자동 생성기 (실시간 조건 필터링)") st.markdown("키워드 직접 입력 or 엑셀 업로드 → 실시간 필터 기반 추천")

🔍 키워드 입력창

input_keyword = st.text_input("대표 키워드를 입력하세요 (예: 손풍기, 보냉백 등)") if input_keyword: st.subheader(f"'{input_keyword}' 추천 상품명 (49자 이내)") results = generate_filtered_names(input_keyword) for name in results: st.write("- ", name)

📁 엑셀 업로드

uploaded_file = st.file_uploader("또는, 엑셀 업로드 (.xlsx) — A열: 상품명", type=["xlsx"]) if uploaded_file: df = pd.read_excel(uploaded_file) df.columns = ["도매처_상품명"] df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword) df["추천 상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_filtered_names(x)))

st.subheader("📊 분석 결과 미리보기")
st.dataframe(df.head(20))

output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df.to_excel(writer, index=False, sheet_name="추천결과")

st.download_button(
    label="📥 엑셀 다운로드",
    data=output.getvalue(),
    file_name=f"추천상품명_{datetime.today().strftime('%Y%m%d')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

