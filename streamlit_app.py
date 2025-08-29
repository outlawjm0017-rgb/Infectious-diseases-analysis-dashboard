#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

#######################
# Page configuration
st.set_page_config(
    page_title="감염병 진료 통계 대시보드",
    page_icon="🧫",
    layout="wide",
    initial_sidebar_state="expanded"
)
alt.themes.enable("default")

#######################
# CSS (여백 + 표 스타일)
st.markdown("""
<style>
[data-testid="block-container"] {
    padding-left: 2rem; padding-right: 2rem;
    padding-top: 1rem; padding-bottom: 0rem;
}
[data-testid="stVerticalBlock"] { padding-left: 0rem; padding-right: 0rem; }

/* 공통 표 스타일 */
.ranktbl {border-collapse:collapse; width:100%; table-layout:auto;}
.ranktbl th, .ranktbl td {padding:8px 10px; border:1px solid #ddd; font-size:14px;}
.ranktbl th {background:#fafafa; font-weight:700;}
.ranktbl td:nth-child(2), .ranktbl td:nth-child(3){text-align:right; white-space:nowrap;}
</style>
""", unsafe_allow_html=True)

#######################
# Load data
df_reshaped = pd.read_csv(
    '건강보험심사평가원_감염병 건강보험 진료 통계_2023.csv', encoding="cp949"
)

#######################
# Sidebar
with st.sidebar:
    st.title("감염병 진료 통계")
    st.caption("데이터 출처: 건강보험심사평가원(2023)")

    years = sorted(df_reshaped["진료년도"].dropna().unique().tolist())
    sel_year = st.selectbox("연도 선택", years, index=0)

    color_theme = st.selectbox(
        "색상 테마 선택",
        ["blues", "viridis", "plasma", "inferno", "magma", "turbo", "teal", "mint"],
        index=0
    )

    df_year0 = df_reshaped[df_reshaped["진료년도"] == sel_year]
    disease_all = sorted(df_year0["상병명"].dropna().unique().tolist())

    search_kw = st.text_input("질환명 검색(부분일치)", value="")
    filtered_list = [d for d in disease_all if search_kw.strip() in d] if search_kw else disease_all
    sel_diseases = st.multiselect("질환(상병명) 선택", filtered_list, default=filtered_list[:0])

    metric_options = {
        "환자수": "환자수",
        "요양급여비용총액(선별포함)": "요양급여비용총액(선별포함)",
        "보험자부담금(선별포함)": "보험자부담금(선별포함)",
        "명세서청구건수": "명세서청구건수",
        "입내원일수": "입내원일수",
    }
    sel_metric_label = st.selectbox("주요 지표 선택", list(metric_options.keys()), index=0)
    sel_metric = metric_options[sel_metric_label]

    topn = st.slider("랭킹 표시 개수 (Top N)", 5, 30, 10, 1)
    sort_desc = st.radio("정렬 방식", ["내림차순(큰 값 우선)", "오름차순(작은 값 우선)"],
                         horizontal=True) == "내림차순(큰 값 우선)"

    pat_min, pat_max = int(df_year0["환자수"].min()), int(df_year0["환자수"].max())
    pat_range = st.slider("환자수 범위 필터", pat_min, pat_max, (pat_min, pat_max), 1)

    cost_min = int(df_year0["요양급여비용총액(선별포함)"].min())
    cost_max = int(df_year0["요양급여비용총액(선별포함)"].max())
    cost_range = st.slider("총진료비(원) 범위 필터", cost_min, cost_max, (cost_min, cost_max), 1000)

    st.session_state.update({
        "year": sel_year, "theme": color_theme, "disease_filter": sel_diseases,
        "metric": sel_metric, "metric_label": sel_metric_label,
        "topn": topn, "sort_desc": sort_desc,
        "환자수_range": pat_range, "총진료비_range": cost_range, "search_kw": search_kw
    })

#######################
# Dashboard Main Panel (겹침 방지: 넉넉한 비율/간격)
col = st.columns((1, 2.2, 1), gap="large")   # col[1]이 col[0]의 2배

#######################
# col[0] — 핵심 지표 요약
with col[0]:
    st.subheader("📊 핵심 지표 요약")

    df_year = df_reshaped[df_reshaped["진료년도"] == st.session_state["year"]].copy()
    if st.session_state.get("disease_filter"):
        df_year = df_year[df_year["상병명"].isin(st.session_state["disease_filter"])]
    df_year = df_year[
        (df_year["환자수"].between(*st.session_state["환자수_range"])) &
        (df_year["요양급여비용총액(선별포함)"].between(*st.session_state["총진료비_range"]))
    ].copy()

    total_patients = int(df_year["환자수"].sum())
    total_cost = int(df_year["요양급여비용총액(선별포함)"].sum())
    avg_cost_per_patient = int(total_cost / total_patients) if total_patients > 0 else 0

    st.metric("총 환자수", f"{total_patients:,} 명")
    st.metric("총 진료비", f"{total_cost:,} 원")
    st.metric("1인당 평균 비용", f"{avg_cost_per_patient:,} 원")

    st.markdown("---")
    st.markdown(f"**🏆 {st.session_state['metric_label']} 기준 Top {st.session_state['topn']} 질환**")

    df_top0 = (
        df_year.sort_values(by=st.session_state["metric"],
                            ascending=not st.session_state["sort_desc"])
        .head(st.session_state["topn"])
        .loc[:, ["상병명", "환자수", "요양급여비용총액(선별포함)"]]
        .rename(columns={"요양급여비용총액(선별포함)": "총진료비"})
    )
    df_top0["환자수"] = df_top0["환자수"].map(lambda x: f"{int(x):,}")
    df_top0["총진료비"] = df_top0["총진료비"].map(lambda x: f"{int(x):,}")

    rows_html = "\n".join(
        f"<tr><td>{r['상병명']}</td><td>{r['환자수']}</td><td>{r['총진료비']}</td></tr>"
        for _, r in df_top0.iterrows()
    )
    st.markdown(
        f"<table class='ranktbl'><tr><th>상병명</th><th>환자수</th><th>총진료비</th></tr>{rows_html}</table>",
        unsafe_allow_html=True
    )

#######################
# col[1] — 메인 시각화 (가로 막대 + 전환된 히트맵)
with col[1]:
    st.subheader("📈 메인 시각화")

    df_year = df_reshaped[df_reshaped["진료년도"] == st.session_state["year"]].copy()
    if st.session_state.get("disease_filter"):
        df_year = df_year[df_year["상병명"].isin(st.session_state["disease_filter"])]
    df_year = df_year[
        (df_year["환자수"].between(*st.session_state["환자수_range"])) &
        (df_year["요양급여비용총액(선별포함)"].between(*st.session_state["총진료비_range"]))
    ].copy()

    metric_col = st.session_state["metric"]
    metric_label = st.session_state["metric_label"]
    topn = st.session_state["topn"]
    sort_desc = st.session_state["sort_desc"]

    df_top = df_year.sort_values(by=metric_col, ascending=not sort_desc).head(topn).copy()

    # (1) 가로형 막대 그래프
    st.markdown(f"**📊 {metric_label} 기준 상병 Top {topn} (가로형 막대 그래프)**")
    theme2scale = {"blues":"Blues","viridis":"Viridis","plasma":"Plasma",
                   "inferno":"Inferno","magma":"Magma","turbo":"Turbo","teal":"Teal","mint":"Mint"}
    color_scale = theme2scale.get(st.session_state["theme"], "Blues")

    fig_bar = px.bar(
        df_top.sort_values(by=metric_col, ascending=True),   # 작은 값이 위쪽
        x=metric_col, y="상병명",
        orientation="h",
        color=metric_col,
        color_continuous_scale=color_scale,
        text=metric_col
    )
    fig_bar.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
    fig_bar.update_layout(
        height=max(400, 28 * len(df_top)),
        margin=dict(l=120, r=20, t=40, b=40),
        coloraxis_showscale=False,
        xaxis_title=metric_label, yaxis_title="상병명"
    )
    st.plotly_chart(fig_bar, use_container_width=True)  # col[1] 폭에 맞춤

    st.markdown("---")

    # (2) 히트맵 (지표=x축, 상병명=y축)
    st.markdown(f"**🔥 Top {topn} 상병의 다중 지표 히트맵 (정규화 값)**")

    heat_cols = ["환자수", "명세서청구건수", "입내원일수", "보험자부담금(선별포함)", "요양급여비용총액(선별포함)"]
    use_cols = ["상병명"] + [c for c in heat_cols if c in df_top.columns]
    df_hm = df_top[use_cols].copy()
    for c in use_cols[1:]:
        mn, mx = df_hm[c].min(), df_hm[c].max()
        df_hm[c+"_norm"] = 0 if mx==mn else (df_hm[c]-mn)/(mx-mn)
    norm_cols = [c+"_norm" for c in use_cols[1:]]
    label_map = dict(zip(norm_cols, use_cols[1:]))
    df_long = (
        df_hm.melt(id_vars="상병명", value_vars=norm_cols, var_name="지표_norm", value_name="정규화값")
        .assign(지표=lambda d: d["지표_norm"].map(label_map))
    )

    alt.data_transformers.disable_max_rows()
    scheme = st.session_state["theme"] if st.session_state["theme"] in ["blues","viridis","plasma","inferno","magma"] else "blues"

    heatmap = (
        alt.Chart(df_long)
        .mark_rect()
        .encode(
            x=alt.X("지표:N", sort=use_cols[1:], title="지표"),     # 가로축: 지표
            y=alt.Y("상병명:N", sort=df_top["상병명"].tolist(), title="상병명"),  # 세로축: 상병명
            color=alt.Color("정규화값:Q", scale=alt.Scale(scheme=scheme)),
            tooltip=["상병명","지표",alt.Tooltip("정규화값:Q", format=".2f")]
        )
        .properties(height=max(400, 28*len(df_top)), width="container")
    )
    st.altair_chart(heatmap, use_container_width=True)

#######################
# col[2] — 상세/랭킹 (각 요소는 자기 영역 내 렌더링)
with col[2]:
    st.subheader("🔎 상세/랭킹")

    # 동일 필터 적용
    df_year = df_reshaped[df_reshaped["진료년도"] == st.session_state["year"]].copy()
    if st.session_state.get("disease_filter"):
        df_year = df_year[df_year["상병명"].isin(st.session_state["disease_filter"])]
    df_year = df_year[
        (df_year["환자수"].between(*st.session_state["환자수_range"])) &
        (df_year["요양급여비용총액(선별포함)"].between(*st.session_state["총진료비_range"]))
    ].copy()

    metric_col = st.session_state["metric"]
    metric_label = st.session_state["metric_label"]
    topn = st.session_state["topn"]
    sort_desc = st.session_state["sort_desc"]

    # (1) 랭킹 보드 (선택 지표 Top N)
    st.markdown(f"**🏅 {metric_label} 랭킹 보드 (Top {topn})**")
    df_rank = df_year.sort_values(by=metric_col, ascending=not sort_desc).head(topn).copy()
    df_rank_show = df_rank[["상병명", metric_col]].rename(columns={metric_col: metric_label})
    df_rank_show[metric_label] = df_rank_show[metric_label].map(lambda x: f"{int(x):,}")
    st.dataframe(df_rank_show, use_container_width=True, hide_index=True)

    # (2) 선택 질환 상세
    st.markdown("**ℹ️ 질환 상세 보기**")
    disease_pick = st.selectbox("상세 조회할 질환 선택", df_year["상병명"].unique().tolist())
    drow = df_year[df_year["상병명"] == disease_pick].iloc[0]
    st.write(
        f"- 환자수: **{int(drow['환자수']):,} 명**\n"
        f"- 명세서청구건수: **{int(drow['명세서청구건수']):,} 건**\n"
        f"- 입내원일수: **{int(drow['입내원일수']):,} 일**\n"
        f"- 보험자부담금: **{int(drow['보험자부담금(선별포함)']):,} 원**\n"
        f"- 총진료비: **{int(drow['요양급여비용총액(선별포함)']):,} 원**"
    )

    # (3) 데이터 다운로드 (현재 필터 기준)
    st.markdown("**⬇️ 현재 필터 데이터 다운로드**")
    df_download = df_year.copy()
    csv = df_download.to_csv(index=False).encode("cp949")
    st.download_button(
        "CSV 다운로드 (cp949)",
        data=csv,
        file_name=f"감염병_진료통계_{st.session_state['year']}_filtered.csv",
        mime="text/csv"
    )

    # (4) About / 출처
    with st.expander("📄 데이터 설명 & 출처"):
        st.markdown(
            "- 자료: **건강보험심사평가원 감염병 건강보험 진료 통계(2023)**\n"
            "- 컬럼: `진료년도`, `상병명`, `환자수`, `명세서청구건수`, `입내원일수`, "
            "`보험자부담금(선별포함)`, `요양급여비용총액(선별포함)`\n"
            "- 사이드바 필터가 모든 패널에 **동기 적용**됩니다."
        )
