import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

from utils import (
    load_energy_data,
    preprocess_data,
    generate_country_insight,
    generate_global_insight,
    get_energy_columns,
    ENERGY_UNIT,
    PER_CAPITA_COLS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="World Energy Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    with open("style.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Load Data (cached)
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

@st.cache_data
def get_cached_data():
    energy_path = BASE_DIR / "data" / "World_Energy_Terbaru.xlsx"

    if not energy_path.is_file():
        st.error(f"Dataset tidak ditemukan: {energy_path}")
        st.stop()

    en_df = load_energy_data(str(energy_path))
    processed_df = preprocess_data(en_df)
    categories = get_energy_columns(en_df)

    return processed_df, categories

# Muat dataset sebelum sidebar/filter dibuat agar variabel data tersedia.
with st.spinner("Memuat dataset energi dunia..."):
    df, energy_categories = get_cached_data()

if df.empty:
    st.error("Dataset kosong.")
    st.stop()

if "year" not in df.columns or "country" not in df.columns:
    st.error("Dataset harus memiliki kolom year dan country.")
    st.stop()

if not energy_categories:
    st.error("Tidak ditemukan kolom kategori energi pada dataset.")
    st.stop()

available_years = sorted(
    pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique().tolist()
)
all_countries = sorted(df["country"].dropna().astype(str).unique().tolist())

if not available_years:
    st.error("Dataset tidak memiliki tahun yang valid.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
def _fmt(val):
    if pd.isna(val) or val is None:
        return "N/A"
    try:
        v = float(val)
    except Exception:
        return str(val)
    if abs(v) >= 1e12:
        return f"{v/1e12:.2f} T"
    if abs(v) >= 1e9:
        return f"{v/1e9:.2f} B"
    if abs(v) >= 1e6:
        return f"{v/1e6:.2f} M"
    if abs(v) >= 1e3:
        return f"{v/1e3:.2f} K"
    return f"{v:,.4f}"

CHART_FONT = dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#334155")
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(248,250,252,0.5)",
    font=CHART_FONT,
)
# Default margin used when no explicit margin override is needed
_DEFAULT_MARGIN = dict(l=10, r=10, t=40, b=10)

# ─────────────────────────────────────────────────────────────────────────────
# Navigation (Sidebar)
# ─────────────────────────────────────────────────────────────────────────────
PAGES = [
    "🌎 Global Overview & Peta",
    "📈 Global Trend",
    "🏳️ Detail Negara",
    "📊 Perbandingan Banyak Negara",
    "⚖️ Perbandingan 2 Negara",
    "🛠️ Dynamic Chart Builder",
    "💡 Wawasan & Data",
    "📖 Glosarium Energi",
    "ℹ️ Tentang Dashboard",
]

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:16px 0 12px;">
        <div style="font-size:1.6rem;">⚡</div>
        <div style="font-size:1rem; font-weight:800; color:#1e293b; letter-spacing:-0.02em;">World Energy Analytics</div>
        <div style="font-size:0.72rem; color:#64748b; margin-top:2px;">Dashboard Visualisasi Energi Global</div>
    </div>
    <hr style="border:none; border-top:1px solid #e2e8f0; margin:0 0 12px;">
    """, unsafe_allow_html=True)

    page = st.radio("Navigasi Halaman", PAGES, label_visibility="collapsed")

    # ── Filter hanya relevan untuk halaman tertentu ──
    FILTERED_PAGES = [
        "🌎 Global Overview & Peta",
        "📈 Global Trend",
        "💡 Wawasan & Data",
    ]

    if page in FILTERED_PAGES:
        st.markdown("""
        <hr style="border:none; border-top:1px solid #e2e8f0; margin:12px 0 8px;">
        <div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#6366f1; margin-bottom:8px;">
            🎛️ Filter Visualisasi Terfilter
        </div>
        """, unsafe_allow_html=True)

        # Metode filter tahun
        year_filter_method = st.radio(
            "Metode Filter Tahun",
            ["📅 Rentang Tahun (Slider)", "🗓️ Tahun Spesifik (Multiselect)"],
            label_visibility="visible"
        )
        if year_filter_method == "📅 Rentang Tahun (Slider)":
            yr_range = st.slider(
                "Rentang Tahun",
                min_value=int(min(available_years)),
                max_value=int(max(available_years)),
                value=(max(int(min(available_years)), int(max(available_years)) - 10), int(max(available_years)))
            )
            selected_years = list(range(yr_range[0], yr_range[1] + 1))
        else:
            selected_years = st.multiselect(
                "Pilih Tahun Spesifik",
                available_years,
                default=[available_years[-1]]
            )
            if not selected_years:
                selected_years = [available_years[-1]]

        selected_countries_filter = st.multiselect("Saring Negara (Kosong = Semua)", all_countries)
        selected_energy_type = st.selectbox("Kategori Energi", list(energy_categories.keys()))
        color_palette = st.selectbox("Palet Warna", ["Viridis", "Plasma", "Turbo", "Magma", "Inferno", "Cividis"])
        energy_metric = energy_categories[selected_energy_type]
        energy_unit = ENERGY_UNIT.get(selected_energy_type, "TWh")
        energy_min = float(df[energy_metric].dropna().min()) if not df[energy_metric].dropna().empty else 0.0
        energy_max = float(df[energy_metric].dropna().max()) if not df[energy_metric].dropna().empty else 100.0
        selected_energy_range = st.slider(
            f"Rentang Nilai ({energy_unit})",
            min_value=energy_min, max_value=energy_max,
            value=(energy_min, energy_max)
        )

        # Summary filter
        tahun_str = f"{min(selected_years)}–{max(selected_years)}" if len(selected_years) > 1 else str(selected_years[0])
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(168,85,247,0.06));
             border:1px solid rgba(99,102,241,0.15); border-radius:10px; padding:12px 14px;
             font-size:0.8rem; color:#475569; line-height:1.8; margin-top:10px;">
            <strong style="color:#1e293b;">Filter Aktif</strong><br>
            Tahun: <strong>{tahun_str}</strong><br>
            Energi: <strong>{selected_energy_type}</strong><br>
            Negara: <strong>{"Semua" if not selected_countries_filter else f"{len(selected_countries_filter)} dipilih"}</strong>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Default values agar tidak error di halaman lain
        selected_years = available_years[-11:]
        selected_countries_filter = []
        selected_energy_type = list(energy_categories.keys())[0]
        color_palette = "Viridis"
        energy_metric = energy_categories[selected_energy_type]
        energy_unit = ENERGY_UNIT.get(selected_energy_type, "TWh")
        selected_energy_range = (
            float(df[energy_metric].dropna().min()),
            float(df[energy_metric].dropna().max())
        )

# ─────────────────────────────────────────────────────────────────────────────
# Apply Filters
# ─────────────────────────────────────────────────────────────────────────────
filtered_df = df[df["year"].isin(selected_years)]
filtered_df = filtered_df[
    (filtered_df[energy_metric] >= selected_energy_range[0]) &
    (filtered_df[energy_metric] <= selected_energy_range[1])
]
if selected_countries_filter:
    filtered_df = filtered_df[filtered_df["country"].isin(selected_countries_filter)]
filtered_clean_df = filtered_df.dropna(subset=[energy_metric]).copy()

if not filtered_clean_df.empty:
    agg_filtered_df = (
        filtered_clean_df.groupby("country")
        .agg(population=("population", "mean"), **{energy_metric: (energy_metric, "mean")})
        .reset_index()
    )
else:
    agg_filtered_df = pd.DataFrame()

plotly_scale = color_palette

# ═════════════════════════════════════════════════════════════════════════════
# HERO BANNER (always shown)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-banner">
    <div class="hero-content">
        <div class="hero-icon">⚡</div>
        <div class="hero-title">WORLD ENERGY ANALYTICS</div>
        <div class="hero-subtitle">
            Analisis interaktif konsumsi energi global, tren per tahun,
            perbandingan antar negara, dan wawasan mendalam berbasis data.
        </div>
        <div class="hero-badges">
            <span class="badge badge-green">🌱 Renewable</span>
            <span class="badge badge-blue">💧 Hydro</span>
            <span class="badge badge-orange">☀️ Solar</span>
            <span class="badge badge-purple">☢️ Nuclear</span>
            <span class="badge badge-red">🛢️ Fossil</span>
        </div>
    </div>
    <div class="hero-visual">
        <div class="globe-ring ring1"></div>
        <div class="globe-ring ring2"></div>
        <div class="globe-ring ring3"></div>
        <div class="globe-core">🌎</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1: Global Overview & Peta
# ═════════════════════════════════════════════════════════════════════════════
if page == "🌎 Global Overview & Peta":
    st.markdown("## 🌎 Global Overview & Peta Energi Dunia")
    st.caption("Peta kiri: data terpengaruh filter sidebar. Peta kanan: total energi global, tidak terpengaruh filter apapun.")

    col1, col2 = st.columns(2)

    # ── Kolom 1: Filtered Map ──
    with col1:
        st.markdown(f"""
        <div class="chart-container">
            <div class="section-title" style="margin-top:0;">
                🔍 Peta Konsumsi Energi
                <span class="year-badge">{selected_energy_type} [Terfilter]</span>
            </div>
        """, unsafe_allow_html=True)
        if agg_filtered_df.empty:
            st.warning("Tidak ada data terfilter untuk ditampilkan di peta.")
        else:
            fig_map1 = px.choropleth(
                agg_filtered_df, locations="country", locationmode="country names",
                color=energy_metric, hover_name="country",
                hover_data={energy_metric: ":,.2f", "population": ":,.0f"},
                color_continuous_scale=plotly_scale, template="plotly_white",
            )
            fig_map1.update_layout(
                **CHART_LAYOUT, height=380,
                margin=dict(l=0, r=0, t=10, b=0),
                geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False, showcoastlines=True,
                         coastlinecolor="rgba(100,116,139,0.3)", showland=True,
                         landcolor="rgba(241,245,249,0.6)", showocean=True,
                         oceancolor="rgba(186,230,253,0.3)", projection_type="natural earth"),
                coloraxis_colorbar=dict(title=energy_unit, thickness=12, len=0.7, tickfont=dict(size=8))
            )
            fig_map1.update_geos(fitbounds="locations", visible=True)
            st.plotly_chart(fig_map1, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Kolom 2: Global Map (unfiltered) ──
    with col2:
        st.markdown("""
        <div class="chart-container">
            <div class="section-title" style="margin-top:0;">
                🌎 Total Konsumsi Energi Primer Global
                <span class="year-badge" style="background:linear-gradient(135deg,#10b981,#059669);">Global – Statis</span>
            </div>
        """, unsafe_allow_html=True)
        global_map_df = df.groupby("country").agg(
            avg_primary_energy=("primary_energy_consumption", "mean"),
            population=("population", "mean")
        ).reset_index().dropna(subset=["avg_primary_energy"])
        fig_map2 = px.choropleth(
            global_map_df, locations="country", locationmode="country names",
            color="avg_primary_energy", hover_name="country",
            hover_data={"avg_primary_energy": ":,.2f", "population": ":,.0f"},
            color_continuous_scale="Viridis", template="plotly_white",
        )
        fig_map2.update_layout(
            **CHART_LAYOUT, height=380,
            margin=dict(l=0, r=0, t=10, b=0),
            geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False, showcoastlines=True,
                     coastlinecolor="rgba(100,116,139,0.3)", showland=True,
                     landcolor="rgba(241,245,249,0.6)", showocean=True,
                     oceancolor="rgba(186,230,253,0.3)", projection_type="natural earth"),
            coloraxis_colorbar=dict(title="TWh", thickness=12, len=0.7, tickfont=dict(size=8))
        )
        st.plotly_chart(fig_map2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Top 8 Energi (unfiltered, global) ──
    st.markdown("""
    <div class="chart-container">
        <div class="section-title" style="margin-top:0;">
            📊 Top 8 Kategori Energi Terbesar di Dunia
            <span class="year-badge" style="background:linear-gradient(135deg,#f59e0b,#d97706);">Global – Tidak Terpengaruh Filter</span>
        </div>
    """, unsafe_allow_html=True)
    primary_energy_sources = {
        "🛢️ Minyak (Oil)": "oil_consumption",
        "🪨 Batu Bara (Coal)": "coal_consumption",
        "🔥 Gas Alam": "gas_consumption",
        "💧 Air (Hydro)": "hydro_consumption",
        "☢️ Nuklir": "nuclear_consumption",
        "🌱 Biofuel": "biofuel_consumption",
        "💨 Angin (Wind)": "wind_consumption",
        "☀️ Surya (Solar)": "solar_consumption",
    }
    global_sums = {}
    for label, col in primary_energy_sources.items():
        if col in df.columns:
            global_sums[label] = df[col].dropna().sum()
    top8_df = pd.DataFrame(list(global_sums.items()), columns=["Kategori Energi", "Total Konsumsi (TWh)"])
    top8_df = top8_df.sort_values("Total Konsumsi (TWh)", ascending=True)
    fig_top8 = px.bar(
        top8_df, x="Total Konsumsi (TWh)", y="Kategori Energi", orientation="h",
        text="Total Konsumsi (TWh)", template="plotly_white",
        color="Total Konsumsi (TWh)", color_continuous_scale="Plasma"
    )
    fig_top8.update_traces(texttemplate="%{text:,.0f} TWh", textposition="outside")
    fig_top8.update_layout(
        **CHART_LAYOUT, height=380,
        margin=_DEFAULT_MARGIN,
        xaxis_title="Konsumsi Akumulatif (TWh)", yaxis_title="",
        coloraxis_showscale=False
    )
    fig_top8.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(100,116,139,0.1)", zeroline=False)
    fig_top8.update_yaxes(showgrid=False, zeroline=False)
    st.plotly_chart(fig_top8, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2: Global Trend
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📈 Global Trend":
    st.markdown("## 📈 Tren Konsumsi Energi Global (Rata-rata per Tahun)")
    st.caption("Menggunakan rata-rata (mean) data per tahun. Chart kiri: terpengaruh filter. Chart kanan: data global historis penuh.")

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown(f"""
        <div class="chart-container">
            <div class="section-title" style="margin-top:0;">📈 Tren Rata-rata Tahunan [Terfilter]
                <span class="year-badge">{selected_energy_type}</span>
            </div>
        """, unsafe_allow_html=True)
        if filtered_clean_df.empty:
            st.warning("Tidak ada data terfilter untuk menampilkan tren.")
        else:
            ft = filtered_clean_df.groupby("year")[energy_metric].mean().reset_index()
            fig_tf = px.area(
                ft, x="year", y=energy_metric, template="plotly_white",
                color_discrete_sequence=["#6366f1"],
                labels={"year": "Tahun", energy_metric: f"Rata-rata ({energy_unit})"}
            )
            fig_tf.update_traces(fill="tozeroy", fillcolor="rgba(99,102,241,0.12)",
                                 line=dict(color="#6366f1", width=2.5))
            fig_tf.update_layout(**CHART_LAYOUT, height=320, margin=_DEFAULT_MARGIN)
            st.plotly_chart(fig_tf, use_container_width=True)
            if len(ft) > 1:
                s, e = float(ft.iloc[0][energy_metric]), float(ft.iloc[-1][energy_metric])
                pct = ((e - s) / s * 100) if s > 0 else 0
                st.info(f"💡 **Insight:** Rata-rata {selected_energy_type} berubah **{pct:+.2f}%** dari {int(ft.iloc[0]['year'])} ke {int(ft.iloc[-1]['year'])}.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_t2:
        st.markdown(f"""
        <div class="chart-container">
            <div class="section-title" style="margin-top:0;">🌎 Tren Global Historis [Tidak Terpengaruh Filter]
                <span class="year-badge" style="background:linear-gradient(135deg,#10b981,#059669);">Statis</span>
            </div>
        """, unsafe_allow_html=True)
        gt_df = df.dropna(subset=[energy_metric])
        gt = gt_df.groupby("year")[energy_metric].mean().reset_index()
        fig_gt = px.line(
            gt, x="year", y=energy_metric, template="plotly_white",
            color_discrete_sequence=["#10b981"],
            labels={"year": "Tahun", energy_metric: f"Rata-rata ({energy_unit})"}
        )
        fig_gt.update_traces(line=dict(color="#10b981", width=3))
        fig_gt.update_layout(**CHART_LAYOUT, height=320, margin=_DEFAULT_MARGIN)
        st.plotly_chart(fig_gt, use_container_width=True)
        if len(gt) > 1:
            gs, ge = float(gt.iloc[0][energy_metric]), float(gt.iloc[-1][energy_metric])
            gpct = ((ge - gs) / gs * 100) if gs > 0 else 0
            st.success(f"💡 **Insight Global:** Rata-rata konsumsi {selected_energy_type} di seluruh dunia berubah **{gpct:+.2f}%** sejak {int(gt.iloc[0]['year'])} hingga {int(gt.iloc[-1]['year'])}.")
        st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3: Detail Negara
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🏳️ Detail Negara":
    st.markdown("## 🏳️ Detail Tren Energi Satu Negara")
    st.caption("Halaman ini memiliki filter sendiri dan tidak dipengaruhi sidebar global.")

    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    dc1, dc2 = st.columns([1, 2])
    with dc1:
        selected_single_country = st.selectbox(
            "Pilih 1 Negara",
            all_countries,
            index=all_countries.index("Indonesia") if "Indonesia" in all_countries else 0,
            key="detail_country"
        )
    with dc2:
        selected_detail_energies = st.multiselect(
            "Pilih Kategori Energi (bisa banyak)",
            list(energy_categories.keys()),
            default=["Biofuel", "Coal", "Solar", "Wind"],
            key="detail_energies"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    country_df = df[df["country"] == selected_single_country].copy()
    melt_cols = [energy_categories[c] for c in selected_detail_energies if energy_categories[c] in df.columns]

    if not melt_cols:
        st.warning("Pilih minimal satu kategori energi.")
    else:
        country_clean = country_df.dropna(subset=melt_cols, how="all")
        if country_clean.empty:
            st.error(f"Tidak ada data valid untuk {selected_single_country}.")
        else:
            melted = country_clean.melt(
                id_vars=["year"], value_vars=melt_cols,
                var_name="Energy_Col", value_name="Konsumsi (TWh)"
            )
            col_to_label = {v: k for k, v in energy_categories.items()}
            melted["Kategori Energi"] = melted["Energy_Col"].map(col_to_label)
            melted = melted.dropna(subset=["Konsumsi (TWh)"])

            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig_detail = px.line(
                melted, x="year", y="Konsumsi (TWh)", color="Kategori Energi",
                markers=True, template="plotly_white",
                title=f"Tren Konsumsi Energi di {selected_single_country}",
                labels={"year": "Tahun"}
            )
            fig_detail.update_layout(**CHART_LAYOUT, height=430, margin=_DEFAULT_MARGIN)
            st.plotly_chart(fig_detail, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Metrik ringkasan
            st.markdown("#### Ringkasan Nilai Terbaru")
            latest = country_clean.sort_values("year").iloc[-1]
            latest_year = int(latest["year"])
            met_cols_ui = st.columns(min(len(selected_detail_energies), 4))
            for idx, ename in enumerate(selected_detail_energies):
                col_n = energy_categories[ename]
                val = latest.get(col_n, np.nan)
                unit = ENERGY_UNIT.get(ename, "TWh")
                with met_cols_ui[idx % len(met_cols_ui)]:
                    st.metric(label=f"{ename} ({latest_year})", value=f"{_fmt(val)} {unit}")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4: Perbandingan Banyak Negara
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📊 Perbandingan Banyak Negara":
    st.markdown("## 📊 Perbandingan Tren Energi Banyak Negara")
    st.caption("Pilih beberapa negara dan satu kategori energi untuk membandingkan tren dari waktu ke waktu.")

    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    mc1, mc2 = st.columns([2, 1])
    with mc1:
        sel_comp_countries = st.multiselect(
            "Pilih Negara (boleh banyak)",
            all_countries,
            default=[c for c in ["Indonesia", "Malaysia", "Singapore", "Thailand"] if c in all_countries],
            key="comp_countries"
        )
    with mc2:
        sel_comp_energy = st.selectbox(
            "Kategori Energi",
            list(energy_categories.keys()), index=1, key="comp_energy"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if not sel_comp_countries:
        st.warning("Pilih minimal satu negara.")
    else:
        comp_metric = energy_categories[sel_comp_energy]
        comp_unit = ENERGY_UNIT.get(sel_comp_energy, "TWh")
        comp_df = df[df["country"].isin(sel_comp_countries)].dropna(subset=[comp_metric])
        if comp_df.empty:
            st.error("Tidak ada data valid untuk kombinasi negara dan energi ini.")
        else:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig_comp = px.line(
                comp_df, x="year", y=comp_metric, color="country",
                markers=True, template="plotly_white",
                title=f"Perbandingan Tren: {sel_comp_energy} ({comp_unit})",
                labels={"year": "Tahun", comp_metric: f"{sel_comp_energy} ({comp_unit})", "country": "Negara"}
            )
            fig_comp.update_layout(**CHART_LAYOUT, height=430, margin=_DEFAULT_MARGIN)
            st.plotly_chart(fig_comp, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Tabel ringkasan rata-rata
            st.markdown("#### Rata-rata Konsumsi per Negara")
            summary_rows = []
            for c in sel_comp_countries:
                cdf = comp_df[comp_df["country"] == c]
                if not cdf.empty:
                    summary_rows.append({
                        "Negara": c,
                        f"Rata-rata {sel_comp_energy} ({comp_unit})": round(cdf[comp_metric].mean(), 2),
                        f"Maks ({comp_unit})": round(cdf[comp_metric].max(), 2),
                        f"Min ({comp_unit})": round(cdf[comp_metric].min(), 2),
                    })
            if summary_rows:
                st.dataframe(pd.DataFrame(summary_rows).set_index("Negara"), use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5: Perbandingan 2 Negara (Dedicated Professional Page)
# ═════════════════════════════════════════════════════════════════════════════
elif page == "⚖️ Perbandingan 2 Negara":
    st.markdown("## ⚖️ Perbandingan Mendalam: Dua Negara")
    st.caption("Analisis sisi-ke-sisi antara dua negara pilihan dengan berbagai metrik energi secara profesional.")

    # Filter
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        c1 = st.selectbox("🔵 Negara Pertama", all_countries,
                           index=all_countries.index("Indonesia") if "Indonesia" in all_countries else 0,
                           key="two_c1")
    with fc2:
        c2 = st.selectbox("🟢 Negara Kedua", all_countries,
                           index=all_countries.index("Malaysia") if "Malaysia" in all_countries else min(1, len(all_countries)-1),
                           key="two_c2")
    with fc3:
        c2_energy = st.selectbox("Kategori Energi", list(energy_categories.keys()), key="two_energy")
    st.markdown("</div>", unsafe_allow_html=True)

    c2_metric = energy_categories[c2_energy]
    c2_unit = ENERGY_UNIT.get(c2_energy, "TWh")

    df_c1 = df[df["country"] == c1].dropna(subset=[c2_metric]).sort_values("year")
    df_c2 = df[df["country"] == c2].dropna(subset=[c2_metric]).sort_values("year")

    if df_c1.empty or df_c2.empty:
        st.error("Salah satu atau kedua negara tidak memiliki data valid untuk kategori energi ini.")
    else:
        # ── KPI Cards ──
        st.markdown("### 📊 Statistik Perbandingan Utama")
        k1, k2 = st.columns(2)
        with k1:
            c1_avg = df_c1[c2_metric].mean()
            c1_max = df_c1[c2_metric].max()
            c1_min = df_c1[c2_metric].min()
            c1_latest_pop = df_c1.iloc[-1]["population"] if "population" in df_c1.columns else np.nan
            c1_trend = "📈" if df_c1[c2_metric].iloc[-1] > df_c1[c2_metric].iloc[0] else "📉"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.08));
                 border:2px solid #6366f1; border-radius:16px; padding:24px;">
                <div style="font-size:1.1rem; font-weight:800; color:#4f46e5; margin-bottom:14px;">🔵 {c1}</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#4f46e5;">{c1_avg:,.1f}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Rata-rata ({c2_unit})</div>
                    </div>
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#7c3aed;">{c1_max:,.1f}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Tertinggi ({c2_unit})</div>
                    </div>
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#0ea5e9;">{c1_min:,.1f}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Terendah ({c2_unit})</div>
                    </div>
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#1e293b;">{_fmt(c1_latest_pop)}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Populasi Terbaru</div>
                    </div>
                </div>
                <div style="margin-top:12px; font-size:0.85rem; color:#475569;">
                    Tren historis: <strong>{c1_trend}</strong>
                    dari <strong>{df_c1[c2_metric].iloc[0]:,.1f}</strong>
                    ke <strong>{df_c1[c2_metric].iloc[-1]:,.1f} {c2_unit}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k2:
            c2_avg = df_c2[c2_metric].mean()
            c2_max = df_c2[c2_metric].max()
            c2_min = df_c2[c2_metric].min()
            c2_latest_pop = df_c2.iloc[-1]["population"] if "population" in df_c2.columns else np.nan
            c2_trend = "📈" if df_c2[c2_metric].iloc[-1] > df_c2[c2_metric].iloc[0] else "📉"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(16,185,129,0.08),rgba(5,150,105,0.08));
                 border:2px solid #10b981; border-radius:16px; padding:24px;">
                <div style="font-size:1.1rem; font-weight:800; color:#059669; margin-bottom:14px;">🟢 {c2}</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#059669;">{c2_avg:,.1f}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Rata-rata ({c2_unit})</div>
                    </div>
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#10b981;">{c2_max:,.1f}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Tertinggi ({c2_unit})</div>
                    </div>
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#0ea5e9;">{c2_min:,.1f}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Terendah ({c2_unit})</div>
                    </div>
                    <div style="background:white; border-radius:10px; padding:12px; text-align:center;">
                        <div style="font-size:1.3rem; font-weight:800; color:#1e293b;">{_fmt(c2_latest_pop)}</div>
                        <div style="font-size:0.72rem; color:#64748b;">Populasi Terbaru</div>
                    </div>
                </div>
                <div style="margin-top:12px; font-size:0.85rem; color:#475569;">
                    Tren historis: <strong>{c2_trend}</strong>
                    dari <strong>{df_c2[c2_metric].iloc[0]:,.1f}</strong>
                    ke <strong>{df_c2[c2_metric].iloc[-1]:,.1f} {c2_unit}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Line Chart Gabungan ──
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        combined_df = pd.concat([df_c1, df_c2])
        fig_2c = px.line(
            combined_df, x="year", y=c2_metric, color="country",
            markers=True, template="plotly_white",
            title=f"Tren {c2_energy}: {c1} vs {c2}",
            labels={"year": "Tahun", c2_metric: f"{c2_energy} ({c2_unit})", "country": "Negara"},
            color_discrete_map={c1: "#6366f1", c2: "#10b981"}
        )
        fig_2c.update_traces(line=dict(width=2.5))
        fig_2c.update_layout(**CHART_LAYOUT, height=380, margin=_DEFAULT_MARGIN)
        st.plotly_chart(fig_2c, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Multi-Energi Radar / Bar ──
        st.markdown("### 🕸️ Perbandingan Multi-Kategori Energi (Rata-rata Historis)")
        multi_cats = {k: v for k, v in energy_categories.items() if "CO2" not in k and "Electricity" not in k}
        radar_rows = []
        for en_name, en_col in multi_cats.items():
            v1 = df[df["country"] == c1][en_col].dropna().mean()
            v2 = df[df["country"] == c2][en_col].dropna().mean()
            if not (pd.isna(v1) and pd.isna(v2)):
                radar_rows.append({"Kategori": en_name, c1: round(v1, 2) if not pd.isna(v1) else 0,
                                   c2: round(v2, 2) if not pd.isna(v2) else 0})
        if radar_rows:
            radar_df = pd.DataFrame(radar_rows)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Bar(
                name=c1, x=radar_df["Kategori"], y=radar_df[c1],
                marker_color="#6366f1", opacity=0.85
            ))
            fig_radar.add_trace(go.Bar(
                name=c2, x=radar_df["Kategori"], y=radar_df[c2],
                marker_color="#10b981", opacity=0.85
            ))
            fig_radar.update_layout(
                **CHART_LAYOUT, height=380, barmode="group",
                margin=_DEFAULT_MARGIN,
                title=f"Rata-rata Konsumsi per Kategori Energi: {c1} vs {c2}",
                xaxis_title="Kategori Energi", yaxis_title="Rata-rata (TWh)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 6: Dynamic Chart Builder
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🛠️ Dynamic Chart Builder":
    st.markdown("## 🛠️ Dynamic Chart Builder")
    st.caption("Visualisasikan korelasi atau tren antar variabel numerik manapun secara dinamis. Data dan sumbu chart benar-benar berubah sesuai pilihan X dan Y.")

    DYNAMIC_COLS = {
        "Tahun": "year",
        "Populasi": "population",
        "GDP": "gdp",
        "Biofuel (TWh)": "biofuel_consumption",
        "Batu Bara (TWh)": "coal_consumption",
        "Gas Alam (TWh)": "gas_consumption",
        "Energi Air/Hydro (TWh)": "hydro_consumption",
        "Nuklir (TWh)": "nuclear_consumption",
        "Minyak (TWh)": "oil_consumption",
        "Surya/Solar (TWh)": "solar_consumption",
        "Angin/Wind (TWh)": "wind_consumption",
        "Energi Fosil (TWh)": "fossil_fuel_consumption",
        "Energi Rendah Karbon (TWh)": "low_carbon_consumption",
        "Energi Terbarukan (TWh)": "renewables_consumption",
        "Energi Primer (TWh)": "primary_energy_consumption",
        "Pembangkitan Listrik (TWh)": "electricity_generation",
        "Emisi CO2 (MtCO₂)": "greenhouse_gas_emissions",
        "Energi per Kapita (kWh/orang)": "energy_per_capita",
    }
    # Filter hanya kolom yang ada di dataset
    DYNAMIC_COLS = {k: v for k, v in DYNAMIC_COLS.items() if v in df.columns}

    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        x_label = st.selectbox("Sumbu X", list(DYNAMIC_COLS.keys()), index=0)
    with b2:
        y_label = st.selectbox("Sumbu Y", list(DYNAMIC_COLS.keys()), index=3)
    with b3:
        chart_type = st.selectbox("Tipe Grafik", ["Line Chart", "Bar Chart", "Scatter Plot", "Area Chart"], index=2)
    with b4:
        group_by = st.checkbox("Bedakan warna per negara", value=True)
    builder_countries = st.multiselect("Saring Negara (kosong = semua)", all_countries, default=[], key="builder_countries")
    st.markdown("</div>", unsafe_allow_html=True)

    x_col = DYNAMIC_COLS[x_label]
    y_col = DYNAMIC_COLS[y_label]
    bdf = df.copy()
    if builder_countries:
        bdf = bdf[bdf["country"].isin(builder_countries)]
    bdf_clean = bdf.dropna(subset=[x_col, y_col])

    if bdf_clean.empty:
        st.error("Tidak ada data valid. Coba kombinasi kolom atau negara lain.")
    else:
        color_p = "country" if group_by else None
        title_s = f"{chart_type}: {y_label} vs {x_label}"
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        if chart_type == "Line Chart":
            fig_b = px.line(bdf_clean, x=x_col, y=y_col, color=color_p, hover_name="country",
                            template="plotly_white", title=title_s,
                            labels={x_col: x_label, y_col: y_label})
        elif chart_type == "Bar Chart":
            fig_b = px.bar(bdf_clean, x=x_col, y=y_col, color=color_p, hover_name="country",
                           template="plotly_white", title=title_s,
                           labels={x_col: x_label, y_col: y_label})
        elif chart_type == "Scatter Plot":
            size_col = "population" if "population" in bdf_clean.columns and bdf_clean["population"].min() >= 0 else None
            fig_b = px.scatter(bdf_clean, x=x_col, y=y_col, color=color_p, hover_name="country",
                               size=size_col, template="plotly_white", title=title_s,
                               labels={x_col: x_label, y_col: y_label})
        else:
            fig_b = px.area(bdf_clean, x=x_col, y=y_col, color=color_p, hover_name="country",
                            template="plotly_white", title=title_s,
                            labels={x_col: x_label, y_col: y_label})
        fig_b.update_layout(**CHART_LAYOUT, height=460, margin=_DEFAULT_MARGIN)
        st.plotly_chart(fig_b, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 7: Wawasan & Data
# ═════════════════════════════════════════════════════════════════════════════
elif page == "💡 Wawasan & Data":
    import streamlit.components.v1 as components

    st.markdown("## 💡 Wawasan Analitis & Ekspor Data")

    # ── Build Top 5 HTML ──
    top5_df = (
        agg_filtered_df[agg_filtered_df[energy_metric] > 0]
        .sort_values(energy_metric, ascending=False)
        .head(5)
        if not agg_filtered_df.empty else pd.DataFrame()
    )

    if top5_df.empty:
        top5_cards = f"""
        <p style="color:#94a3b8; font-size:0.85rem; font-style:italic; margin:0;">
            Tidak ada data {selected_energy_type} yang valid (lebih dari nol) untuk filter yang dipilih.
        </p>"""
    else:
        top5_cards = ""
        for _, row in top5_df.iterrows():
            insight = generate_country_insight(row[energy_metric], selected_energy_type)
            val_fmt = f"{float(row[energy_metric]):,.2f}" if pd.notna(row[energy_metric]) else "N/A"
            top5_cards += f"""
            <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.3);
                 border-radius:10px;padding:12px 14px;margin-bottom:10px;">
                <div style="font-weight:700;color:#065f46;font-size:0.88rem;margin-bottom:4px;">
                    &#127987; {row['country']}
                </div>
                <div style="font-size:0.82rem;color:#374151;">
                    {selected_energy_type}: <strong>{val_fmt} {energy_unit}</strong>
                </div>
                <div style="font-size:0.80rem;color:#059669;font-style:italic;margin-top:2px;">
                    {insight}
                </div>
            </div>"""

    # ── Build Global Insight HTML ──
    if agg_filtered_df.empty:
        global_cards = """
        <p style="color:#94a3b8; font-size:0.85rem; font-style:italic; margin:0;">
            Tidak ada data untuk insight global.
        </p>"""
    else:
        g_insights = generate_global_insight(agg_filtered_df, energy_metric, selected_energy_type)
        icons_list = ["&#127760;", "&#128681;", "&#9889;", "&#128202;"]
        global_cards = ""
        for i, g in enumerate(g_insights):
            global_cards += f"""
            <div style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.3);
                 border-radius:10px;padding:12px 14px;margin-bottom:10px;">
                <span style="font-size:0.85rem;color:#1e3a8a;font-weight:500;">
                    {icons_list[i % 4]} {g}
                </span>
            </div>"""

    # ── Render via components.html (bypasses Streamlit sanitizer) ──
    panel_style = (
        "background:white;border:1px solid rgba(99,102,241,0.15);padding:24px;"
        "border-radius:16px;min-height:420px;box-shadow:0 4px 20px rgba(99,102,241,0.06);"
        "font-family:'Segoe UI',sans-serif;"
    )
    title_style = (
        "margin:0 0 14px;padding-bottom:10px;font-size:0.95rem;font-weight:700;"
        "color:#1e293b;border-bottom:2px solid rgba(99,102,241,0.12);"
    )

    full_html = f"""
    <!DOCTYPE html><html><body style="margin:0;padding:0;background:transparent;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
        <div style="{panel_style}">
            <div style="{title_style}">&#127987; Top 5 Negara (Terfilter)</div>
            {top5_cards}
        </div>
        <div style="{panel_style}">
            <div style="{title_style}">&#127758; Insight Global</div>
            {global_cards}
        </div>
    </div>
    </body></html>"""

    components.html(full_html, height=480, scrolling=False)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("**Preview Data Terfilter**")
    if agg_filtered_df.empty:
        st.warning("Tidak ada data untuk ditampilkan.")
    else:
        st.dataframe(agg_filtered_df.head(60), use_container_width=True)
        st.download_button(
            "⬇️ Download Filtered CSV",
            data=agg_filtered_df.to_csv(index=False),
            file_name="filtered_energy_data.csv",
            mime="text/csv"
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 8: Glosarium Energi (NEW)
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📖 Glosarium Energi":
    st.markdown("## 📖 Glosarium Energi & Kamus Kolom Data")
    st.caption("Penjelasan lengkap tentang jenis-jenis energi, istilah teknis, dan makna setiap kolom dalam dataset.")

    # ── Biofuel & Jenis Energi ──
    st.markdown("### ⚡ Jenis-Jenis Sumber Energi")
    energy_glossary = [
        {
            "icon": "🌱", "name": "Biofuel (Bahan Bakar Hayati)",
            "color": "#065f46", "bg": "rgba(16,185,129,0.06)", "border": "#10b981",
            "desc": (
                "<strong>Biofuel</strong> adalah bahan bakar yang diproduksi dari materi organik (biomassa) "
                "seperti tanaman, minyak nabati, limbah pertanian, atau ganggang. Biofuel dikategorikan sebagai "
                "<em>energi terbarukan</em> karena sumbernya dapat diperbarui secara alami.<br><br>"
                "<strong>Jenis-jenis Biofuel:</strong><br>"
                "&#8226; <strong>Bioetanol</strong> – Difermentasi dari tebu, jagung, atau singkong. Digunakan sebagai campuran bensin.<br>"
                "&#8226; <strong>Biodiesel</strong> – Diolah dari minyak kelapa sawit, kedelai, atau minyak goreng bekas. Pengganti solar.<br>"
                "&#8226; <strong>Biogas</strong> – Gas metana dari fermentasi limbah organik. Digunakan untuk memasak dan listrik.<br>"
                "&#8226; <strong>Biomassa Padat</strong> – Kayu, sekam, dan pelet biomassa untuk pembangkit listrik."
            )
        },
        {
            "icon": "🪨", "name": "Coal (Batu Bara)",
            "color": "#1c1917", "bg": "rgba(120,113,108,0.06)", "border": "#78716c",
            "desc": (
                "<strong>Batu bara</strong> adalah bahan bakar fosil padat kaya karbon yang terbentuk selama jutaan tahun "
                "dari sisa-sisa tumbuhan yang terkubur dan mengalami tekanan dan panas tinggi.<br><br>"
                "<strong>Jenis batu bara:</strong> Antrasit (paling keras), Bituminous, Sub-bituminous, Lignit (paling lunak).<br><br>"
                "Batu bara adalah penghasil emisi CO&#8322; terbesar di sektor energi dan menjadi target utama transisi energi global."
            )
        },
        {
            "icon": "🔥", "name": "Gas (Gas Alam / Natural Gas)",
            "color": "#92400e", "bg": "rgba(245,158,11,0.06)", "border": "#f59e0b",
            "desc": (
                "<strong>Gas alam</strong> adalah bahan bakar fosil yang sebagian besar terdiri dari metana (CH&#8324;), "
                "terbentuk dari sisa organisme laut yang terperangkap di bawah lapisan bumi selama jutaan tahun.<br><br>"
                "Gas alam dianggap sebagai \"bahan bakar transisi\" karena emisi CO&#8322;-nya lebih rendah dibanding "
                "batu bara dan minyak, namun masih merupakan bahan bakar fosil."
            )
        },
        {
            "icon": "💧", "name": "Hydro (Energi Air / Hydropower)",
            "color": "#1e40af", "bg": "rgba(59,130,246,0.06)", "border": "#3b82f6",
            "desc": (
                "<strong>Hydropower</strong> menggunakan energi kinetik dan potensial air mengalir untuk menghasilkan "
                "listrik melalui turbin.<br><br>"
                "<strong>Jenis PLTA:</strong><br>"
                "&#8226; <strong>Run-of-river</strong> – Menggunakan aliran sungai langsung tanpa bendungan besar.<br>"
                "&#8226; <strong>Reservoir/Bendungan</strong> – Menyimpan air di waduk untuk dilepaskan saat dibutuhkan.<br>"
                "&#8226; <strong>Pumped-storage</strong> – Memompa air ke reservoir atas saat kelebihan listrik, lalu melepasnya kembali."
            )
        },
        {
            "icon": "☢️", "name": "Nuclear (Nuklir)",
            "color": "#7c3aed", "bg": "rgba(124,58,237,0.06)", "border": "#8b5cf6",
            "desc": (
                "<strong>Energi nuklir</strong> dihasilkan dari reaksi fisi (pembelahan) inti atom uranium-235 atau plutonium-239, "
                "yang menghasilkan panas luar biasa untuk memanaskan air dan menggerakkan turbin generator.<br><br>"
                "Nuklir menghasilkan listrik dalam jumlah besar dengan emisi CO&#8322; hampir nol saat beroperasi, "
                "namun menimbulkan tantangan dalam pengelolaan limbah radioaktif."
            )
        },
        {
            "icon": "🛢️", "name": "Oil (Minyak Bumi / Petroleum)",
            "color": "#9f1239", "bg": "rgba(239,68,68,0.06)", "border": "#ef4444",
            "desc": (
                "<strong>Minyak bumi</strong> adalah bahan bakar fosil cair yang diolah menjadi berbagai produk: "
                "bensin (petrol), solar (diesel), avtur (jet fuel), minyak tanah, LPG, dan aspal.<br><br>"
                "Minyak mendominasi sektor transportasi global dan merupakan bahan baku utama industri petrokimia."
            )
        },
        {
            "icon": "☀️", "name": "Solar (Energi Surya)",
            "color": "#b45309", "bg": "rgba(251,191,36,0.06)", "border": "#fbbf24",
            "desc": (
                "<strong>Energi surya</strong> mengonversi radiasi sinar matahari menjadi listrik menggunakan "
                "panel fotovoltaik (PV) atau Concentrated Solar Power (CSP).<br><br>"
                "<strong>Teknologi:</strong><br>"
                "&#8226; <strong>Fotovoltaik (PV)</strong> – Panel silikon mengonversi cahaya menjadi listrik secara langsung.<br>"
                "&#8226; <strong>CSP (Concentrated Solar Power)</strong> – Cermin memfokuskan sinar matahari untuk memanaskan fluida dan menggerakkan turbin.<br>"
                "&#8226; <strong>Solar thermal</strong> – Pemanas air rumah tangga atau industri menggunakan kolektor surya."
            )
        },
        {
            "icon": "💨", "name": "Wind (Energi Angin)",
            "color": "#0369a1", "bg": "rgba(14,165,233,0.06)", "border": "#0ea5e9",
            "desc": (
                "<strong>Energi angin</strong> diperoleh dari hembusan angin yang memutar bilah turbin, "
                "menggerakkan generator untuk menghasilkan listrik.<br><br>"
                "<strong>Jenis turbin angin:</strong><br>"
                "&#8226; <strong>Onshore Wind</strong> – Dipasang di darat, biaya lebih murah, kapasitas lebih kecil.<br>"
                "&#8226; <strong>Offshore Wind</strong> – Dipasang di laut, angin lebih kencang dan stabil, kapasitas lebih besar."
            )
        },
    ]

    for item in energy_glossary:
        st.markdown(f"""
        <div style="background:{item['bg']}; border:1.5px solid {item['border']}; border-radius:14px;
             padding:20px 24px; margin-bottom:14px;">
            <div style="font-size:1rem; font-weight:800; color:{item['color']}; margin-bottom:10px;">
                {item['icon']} {item['name']}
            </div>
            <div style="font-size:0.85rem; color:#334155; line-height:1.7;">
                {item['desc']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Penjelasan Kolom Per Kapita ──
    st.markdown("---")
    st.markdown("### 👤 Apa Itu Energi Per Kapita?")
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(168,85,247,0.06));
         border:1.5px solid #6366f1; border-radius:14px; padding:24px; margin-bottom:14px;">
        <div style="font-size:1rem; font-weight:800; color:#4f46e5; margin-bottom:12px;">
            📊 Konsep Energi Per Kapita (Per Orang)
        </div>
        <div style="font-size:0.85rem; color:#334155; line-height:1.8;">
            <p><strong>Energi per kapita</strong> adalah rata-rata konsumsi energi per individu dalam suatu negara atau wilayah. 
            Ini mengukur seberapa banyak energi yang "dikonsumsi" oleh setiap orang, tidak peduli apakah digunakan langsung 
            (listrik rumah tangga, transportasi) atau tidak langsung (industri, manufaktur).</p>
            <p><strong>Rumus:</strong> <code>Energi Per Kapita = Total Konsumsi Energi Nasional ÷ Jumlah Populasi</code></p>
            <p><strong>Satuan:</strong> kWh/orang/tahun atau TWh dibagi dengan jumlah orang.</p>
            <p><strong>Mengapa penting?</strong> Energi per kapita memungkinkan perbandingan yang lebih adil antar negara — 
            negara besar seperti China mungkin mengkonsumsi jauh lebih banyak total energi, namun per kapita-nya bisa 
            lebih rendah dari negara kecil yang sangat industrialisasi.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabel kolom per kapita
    st.markdown("#### Kolom Per Kapita dalam Dataset")
    per_cap_data = []
    for col, label in PER_CAPITA_COLS.items():
        if col in df.columns:
            sample_val = df[col].dropna().mean()
            per_cap_data.append({
                "Nama Kolom": col,
                "Deskripsi": label,
                "Rata-rata Global": f"{sample_val:,.2f}" if not pd.isna(sample_val) else "N/A"
            })
    if per_cap_data:
        st.dataframe(pd.DataFrame(per_cap_data), use_container_width=True, hide_index=True)

    # ── Istilah Lain ──
    st.markdown("---")
    st.markdown("### 📚 Istilah Penting Lainnya")
    other_terms = [
        ("🔋 Primary Energy Consumption", "primary_energy_consumption",
         "Total semua energi yang dikonsumsi suatu negara dari semua sumber (fosil + terbarukan), diukur dalam TWh."),
        ("⚡ Electricity Generation", "electricity_generation",
         "Total listrik yang dibangkitkan dari semua sumber pembangkit, diukur dalam TWh."),
        ("🌡️ Greenhouse Gas Emissions", "greenhouse_gas_emissions",
         "Total emisi gas rumah kaca (CO₂, CH₄, N₂O, dll.) yang dihasilkan dari konsumsi energi, dalam MtCO₂eq."),
        ("🏭 Fossil Fuel Consumption", "fossil_fuel_consumption",
         "Total konsumsi energi dari batubara, minyak, dan gas alam — sumber karbon utama."),
        ("🌿 Low Carbon Consumption", "low_carbon_consumption",
         "Total konsumsi dari sumber rendah karbon: nuklir + semua energi terbarukan."),
        ("♻️ Renewables Consumption", "renewables_consumption",
         "Konsumsi dari sumber terbarukan: surya, angin, hidro, biofuel, dan lainnya (tidak termasuk nuklir)."),
        ("📉 Energy per GDP", "energy_per_gdp",
         "Intensitas energi ekonomi — berapa banyak energi dibutuhkan per unit GDP. Semakin rendah semakin efisien."),
        ("🔌 Carbon Intensity Elec", "carbon_intensity_elec",
         "Emisi CO₂ per kWh listrik yang diproduksi. Mengukur seberapa 'bersih' sistem kelistrikan suatu negara."),
    ]
    ot_cols = st.columns(2)
    for i, (term, col, desc) in enumerate(other_terms):
        col_exists = col in df.columns
        with ot_cols[i % 2]:
            st.markdown(f"""
            <div style="background:white; border:1px solid rgba(100,116,139,0.2); border-radius:10px;
                 padding:14px 16px; margin-bottom:10px;">
                <div style="font-size:0.88rem; font-weight:700; color:#1e293b; margin-bottom:6px;">{term}</div>
                <div style="font-size:0.78rem; color:#64748b; margin-bottom:4px;">{desc}</div>
                <div style="font-size:0.72rem; color:{'#059669' if col_exists else '#dc2626'}; font-weight:600;">
                    Kolom: <code>{col}</code> {'✅ Tersedia' if col_exists else '❌ Tidak ada'}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 9: Tentang Dashboard
# ═════════════════════════════════════════════════════════════════════════════
elif page == "ℹ️ Tentang Dashboard":
    st.markdown("## ℹ️ Tentang Dashboard")

    col_a, col_b = st.columns([1.1, 1])

    with col_a:
        st.markdown("""
        <div style="background:white; border:1px solid rgba(99,102,241,0.12); padding:28px;
             border-radius:16px; min-height:500px; box-shadow:0 4px 20px rgba(99,102,241,0.05);">
            <h4 style="margin:0 0 16px; color:#4f46e5; border-bottom:2px solid rgba(99,102,241,0.1); padding-bottom:8px;">
                🎯 Tujuan Dashboard
            </h4>
            <p style="font-size:0.87rem; color:#334155; line-height:1.7;">
                Dashboard <strong>World Energy Analytics</strong> dibangun untuk mempermudah eksplorasi, 
                pemantauan, dan analisis konsumsi berbagai jenis energi di tingkat global maupun negara 
                dari tahun ke tahun. Dashboard ini ditujukan untuk:
            </p>
            <ul style="font-size:0.87rem; color:#334155; line-height:2;">
                <li>Mahasiswa dan peneliti energi dan lingkungan</li>
                <li>Analis data dan ilmuwan data</li>
                <li>Pembuat kebijakan dan perencana energi</li>
                <li>Siapapun yang ingin memahami pola konsumsi energi global</li>
            </ul>
            <br>
            <h4 style="margin:0 0 12px; color:#4f46e5; border-bottom:2px solid rgba(99,102,241,0.1); padding-bottom:8px;">
                📦 Dataset & Sumber Data
            </h4>
            <p style="font-size:0.87rem; color:#334155; line-height:1.7;">
                Data yang digunakan berasal dari dataset <strong>World Energy</strong> yang mencakup:
            </p>
            <ul style="font-size:0.87rem; color:#334155; line-height:2;">
                <li><strong>Cakupan:</strong> 200+ negara di seluruh dunia</li>
                <li><strong>Periode:</strong> Beberapa dekade historis hingga terbaru</li>
                <li><strong>130+ kolom:</strong> Mencakup konsumsi, produksi, per kapita, pangsa energi, emisi, GDP, dan populasi</li>
                <li><strong>Sumber asli:</strong> Our World in Data / BP Statistical Review</li>
                <li><strong>Format:</strong> Excel (.xlsx) dengan preprocessing Python</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div style="background:white; border:1px solid rgba(99,102,241,0.12); padding:28px;
             border-radius:16px; min-height:500px; box-shadow:0 4px 20px rgba(99,102,241,0.05);">
            <h4 style="margin:0 0 16px; color:#10b981; border-bottom:2px solid rgba(16,185,129,0.1); padding-bottom:8px;">
                🚀 Fitur-Fitur Dashboard
            </h4>
            <ul style="font-size:0.85rem; color:#334155; line-height:2.1; padding-left:18px;">
                <li><strong>🌎 Global Overview & Peta</strong> – Peta interaktif terfilter + peta global statis + Top 8 energi</li>
                <li><strong>📈 Global Trend</strong> – Area/line chart rata-rata tahunan (filtered vs global)</li>
                <li><strong>🏳️ Detail Negara</strong> – Multi-line chart satu negara, banyak kategori energi</li>
                <li><strong>📊 Perbandingan Banyak Negara</strong> – Line chart multi-negara + tabel statistik</li>
                <li><strong>⚖️ Perbandingan 2 Negara</strong> – KPI mendalam, line chart, & bar chart multi-kategori</li>
                <li><strong>🛠️ Dynamic Chart Builder</strong> – Pilih X, Y, tipe chart secara bebas</li>
                <li><strong>💡 Wawasan & Data</strong> – Insight otomatis + ekspor CSV</li>
                <li><strong>📖 Glosarium Energi</strong> – Penjelasan lengkap setiap jenis energi & kolom</li>
            </ul>
            <br>
            <h4 style="margin:0 0 12px; color:#10b981; border-bottom:2px solid rgba(16,185,129,0.1); padding-bottom:8px;">
                🛠️ Teknologi yang Digunakan
            </h4>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div style="background:rgba(99,102,241,0.06); border-radius:10px; padding:12px; text-align:center;">
                    <div style="font-size:1.4rem;">🚀</div>
                    <div style="font-size:0.82rem; font-weight:700; color:#4f46e5;">Streamlit</div>
                    <div style="font-size:0.72rem; color:#64748b;">Web App Framework</div>
                </div>
                <div style="background:rgba(16,185,129,0.06); border-radius:10px; padding:12px; text-align:center;">
                    <div style="font-size:1.4rem;">🐼</div>
                    <div style="font-size:0.82rem; font-weight:700; color:#059669;">Pandas & NumPy</div>
                    <div style="font-size:0.72rem; color:#64748b;">Data Processing</div>
                </div>
                <div style="background:rgba(245,158,11,0.06); border-radius:10px; padding:12px; text-align:center;">
                    <div style="font-size:1.4rem;">📊</div>
                    <div style="font-size:0.82rem; font-weight:700; color:#d97706;">Plotly Express</div>
                    <div style="font-size:0.72rem; color:#64748b;">Interactive Charts</div>
                </div>
                <div style="background:rgba(124,58,237,0.06); border-radius:10px; padding:12px; text-align:center;">
                    <div style="font-size:1.4rem;">🐍</div>
                    <div style="font-size:0.82rem; font-weight:700; color:#7c3aed;">Python 3.x</div>
                    <div style="font-size:0.72rem; color:#64748b;">Backend Language</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Stats
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Statistik Dataset")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Baris Data", f"{len(df):,}")
    with s2:
        st.metric("Jumlah Negara", f"{df['country'].nunique():,}")
    with s3:
        st.metric("Rentang Tahun", f"{int(df['year'].min())} – {int(df['year'].max())}")
    with s4:
        st.metric("Jumlah Kolom", f"{len(df.columns)}")
