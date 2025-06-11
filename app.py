import pandas as pd
import streamlit as st
import io
from datetime import datetime

# 예시 키워드 DB (필요 시 추가 가능)
KEYWORD_DB = {
    "손풍기": {
        "중소형키워드": ["무선 손풍기", "탁상용 손풍기", "손목 손풍기", "휴대 손풍기"],
        "속성키워드": ["저소음", "강풍", "미니", "무소음", "초소형"],
        "용도키워드": ["사무실용", "캠핑용", "공부방", "출퇴근", "야외활동"]
    },
    "보냉백": {
        "중소형키워드": ["미니 보냉백", "피크닉 보냉가방", "아기 이유식 보냉백"],
        "속성키워드": ["가볍고", "이중단열", "접이식"],
        "용도키워드": ["도시락용", "여행용", "캠핑용"]
    }
}

@st.cache_data
def generate_names(keyword):
    if keyword not in KEYWORD_DB:
        return ["키워드 DB 없음"]
    data = KEYWORD_DB[keyword]
    mids, attrs, uses = data["중소형키워드"], data["속성키워드"], data["용도키워드"]
    results = []
    for mid in mids:
        for attr in attrs:
            for use in uses:
                name = f"{mid} {attr} {use} {keyword}"
                if len(name) <= 45:
                    results.append(name)
                if len(results) >= 10:
                    return results
    return results

def extract_keyword(title):
    for keyword in KEYWORD_DB.keys():
        if keyword in title:
            return keyword
    return "키워드 없음"

st.title("📦 상품명 자동 추천 시스템")
uploaded_file = st.file_uploader("엑셀 업로드 (A열에 상품명 포함)", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = ["도매처_상품명"]
    df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword)
    df["추천 상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x)))
    st.dataframe(df.head(20))
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="추천결과")
    st.download_button(
        label="📥 추천결과 엑셀 다운로드",
        data=output.getvalue(),
        file_name=f"추천상품명_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
