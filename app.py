상품명 자동 생성기 (업그레이드 버전: 파일 업로드 + 검색창 입력 동시 지원) 

import pandas as pd import streamlit as st import io from datetime import datetime

키워드 DB (샘플) 

KEYWORD_DB = { "손풍기": { "중소형키워드": ["무선 손풍기", "탁상용 손풍기", "손목 손풍기", "휴대 손풍기"], "속성키워드": ["저소음", "강풍", "미니", "무소음", "초소형"], "용도키워드": ["사무실용", "캠핑용", "공부방", "출퇴근", "야외활동"] }, "보냉백": { "중소형키워드": ["미니 보냉백", "피크닉 보냉가방", "아기 이유식 보냉백"], "속성키워드": ["가볍고", "이중단열", "접이식"], "용도키워드": ["도시락용", "여행용", "캠핑용"] } }

@st.cache_data def generate_names(keyword): if keyword not in KEYWORD_DB: return ["키워드 DB 없음"] data = KEYWORD_DB[keyword] mids, attrs, uses = data["중소형키워드"], data["속성키워드"], data["용도키워드"] results = [] for mid in mids: for attr in attrs: for use in uses: name = f"{mid} {attr} {use} {keyword}" if len(name) <= 45: results.append(name) if len(results) >= 10: return results return results

def extract_keyword(title): for keyword in KEYWORD_DB.keys(): if keyword in title: return keyword return "키워드 없음"

UI 시작 

st.title("📦 상품명 자동 추천기 (검색 + 엑셀)")

st.markdown("① 키워드 직접 검색 또는 ② 엑셀 업로드 중 선택하세요")

👉 입력 방식 1: 직접 키워드 입력 

input_keyword = st.text_input("대표 키워드를 직접 입력해보세요 (예: 손풍기)") if input_keyword: st.subheader(f"🔍 '{input_keyword}' 추천 상품명") result = generate_names(input_keyword) for name in result: st.write("- ", name)

👉 입력 방식 2: 엑셀 파일 업로드 

uploaded_file = st.file_uploader("또는, 도매처 상품명 엑셀 업로드 (.xlsx)", type=["xlsx"]) if uploaded_file: df = pd.read_excel(uploaded_file) df.columns = ["도매처_상품명"] df["대표키워드"] = df["도매처_상품명"].apply(extract_keyword) df["추천 상품명"] = df["대표키워드"].apply(lambda x: "; ".join(generate_names(x))) st.subheader("📊 엑셀 분석 결과") st.dataframe(df.head(20))

output = io.BytesIO() with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False, sheet_name="추천결과") st.download_button( label="📥 엑셀로 다운로드", data=output.getvalue(), file_name=f"추천상품명_{datetime.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ) 
