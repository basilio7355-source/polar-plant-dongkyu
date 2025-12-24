import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 유틸 함수
# =========================
def normalize_name(name: str):
    return unicodedata.normalize("NFC", name)

def find_file_by_name(directory: Path, target_name: str):
    target_norm = normalize_name(target_name)
    for file in directory.iterdir():
        if normalize_name(file.name) == target_norm:
            return file
    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    school_files = {}
    for f in data_dir.iterdir():
        if f.suffix == ".csv":
            school_name = f.stem.split("_")[0]
            school_files[school_name] = f

    env_data = {}
    for school, path in school_files.items():
        env_data[school] = pd.read_csv(path)

    return env_data

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    xlsx_file = None
    for f in data_dir.iterdir():
        if f.suffix == ".xlsx":
            xlsx_file = f
            break

    if xlsx_file is None:
        return None

    xls = pd.ExcelFile(xlsx_file)
    growth_data = {}

    for sheet in xls.sheet_names:
        growth_data[sheet] = pd.read_excel(xlsx_file, sheet_name=sheet)

    return growth_data

# =========================
# 데이터 불러오기
# =========================
with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더를 확인하세요.")
    st.stop()

# =========================
# 메타 정보
# =========================
ec_conditions = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

school_colors = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# =========================
# 사이드바
# =========================
schools = ["전체"] + list(env_data.keys())
selected_school = st.sidebar.selectbox("🏫 학교 선택", schools)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =========================
# Tab 1: 실험 개요
# =========================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("""
    극지 환경에 적응한 식물의 생육 특성을 분석하여  
    **최적 EC(전기전도도) 농도 조건**을 도출하는 것이 본 연구의 목적이다.
    """)

    summary_rows = []
    total_count = 0
    temps, hums = [], []

    for school, df in env_data.items():
        count = len(growth_data.get(school, []))
        total_count += count
        temps.append(df["temperature"].mean())
        hums.append(df["humidity"].mean())

        summary_rows.append({
            "학교명": school,
            "EC 목표": ec_conditions.get(school),
            "개체수": count,
            "색상": school_colors.get(school)
        })

    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_count)
    c2.metric("평균 온도", f"{sum(temps)/len(temps):.1f} ℃")
    c3.metric("평균 습도", f"{sum(hums)/len(hums):.1f} %")
    c4.metric("최적 EC", "2.0 (하늘고) ⭐")

# =========================
# Tab 2: 환경 데이터
# =========================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_df = []
    for school, df in env_data.items():
        avg_df.append({
            "학교": school,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "EC": df["ec"].mean(),
            "목표 EC": ec_conditions.get(school)
        })

    avg_df = pd.DataFrame(avg_df)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)

    fig.add_bar(x=avg_df["학교"], y=avg_df["EC"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표 EC", row=2, col=2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]

        fig_ts = go.Figure()
        fig_ts.add_line(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_line(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_line(x=df["time"], y=df["ec"], name="EC")
        fig_ts.add_hline(y=ec_conditions[selected_school], line_dash="dash", name="목표 EC")

        fig_ts.update_layout(
            title=f"{selected_school} 환경 시계열",
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📥 환경 데이터 원본"):
        for school, df in env_data.items():
            st.write(f"### {school}")
            st.dataframe(df)
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                f"{school} CSV 다운로드",
                data=buffer,
                file_name=f"{school}_환경데이터.csv",
                mime="text/csv"
            )

# =========================
# Tab 3: 생육 결과
# =========================
with tab3:
    st.subheader("EC별 생육 결과 비교")

    summary = []
    for school, df in growth_data.items():
        summary.append({
            "학교": school,
            "EC": ec_conditions.get(school),
            "평균 생중량": df["생중량(g)"].mean(),
            "평균 잎 수": df["잎 수(장)"].mean(),
            "평균 지상부 길이": df["지상부 길이(mm)"].mean(),
            "개체수": len(df)
        })

    summary_df = pd.DataFrame(summary)

    best = summary_df.loc[summary_df["평균 생중량"].idxmax()]

    st.metric(
        "🥇 최적 EC 평균 생중량",
        f"{best['평균 생중량']:.2f} g",
        f"EC {best['EC']}"
    )

    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량 ⭐", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig2.add_bar(x=summary_df["EC"], y=summary_df["평균 생중량"], row=1, col=1)
    fig2.add_bar(x=summary_df["EC"], y=summary_df["평균 잎 수"], row=1, col=2)
    fig2.add_bar(x=summary_df["EC"], y=summary_df["평균 지상부 길이"], row=2, col=1)
    fig2.add_bar(x=summary_df["EC"], y=summary_df["개체수"], row=2, col=2)

    fig2.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig2, use_container_width=True)

    concat_df = pd.concat(
        [df.assign(학교=school) for school, df in growth_data.items()]
    )

    fig_box = px.box(
        concat_df,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    fig_corr1 = px.scatter(concat_df, x="잎 수(장)", y="생중량(g)", color="학교")
    fig_corr2 = px.scatter(concat_df, x="지상부 길이(mm)", y="생중량(g)", color="학교")

    st.plotly_chart(fig_corr1, use_container_width=True)
    st.plotly_chart(fig_corr2, use_container_width=True)

    with st.expander("📥 생육 데이터 다운로드"):
        buffer = io.BytesIO()
        concat_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "전체 생육 데이터 XLSX 다운로드",
            data=buffer,
            file_name="4개교_생육결과데이터.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
