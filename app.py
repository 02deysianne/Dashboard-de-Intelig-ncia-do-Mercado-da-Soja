# ============================================================
# AGRODATA PR | Dashboard de monitoramento e análise da soja
# Versão integrada e aprimorada - Streamlit + Plotly
# ============================================================
import os
import json
import re
import unicodedata
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="AgroData PR | Inteligência no Agronegócio",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- VISUAL ----------------------------
st.markdown("""<style>body, [class*="css"] {font-family: 'DM Sans', sans-serif;}
.stApp {background:#F5F7F4; color:#203128;}
[data-testid="stHeader"] {background:rgba(245,247,244,.94);}
#MainMenu, footer {visibility:hidden;}
section[data-testid="stSidebar"] {background:#173D32;}
section[data-testid="stSidebar"] * {color:#203128 !important;}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {color:#203128 !important;}
section[data-testid="stSidebar"] [data-testid="stDateInput"] label {color:#203128 !important;}
section[data-testid="stSidebar"] [data-testid="stDateInput"] input {color:#203128 !important; background:#FFFFFF !important; -webkit-text-fill-color:#203128 !important;}
.brand {font-size:25px;font-weight:800;letter-spacing:-.8px;color:white;}
.brand-sub,.side-caption {color:#C8D9CD !important;font-size:11px;line-height:1.5;}
.eyebrow {color:#47745A;text-transform:uppercase;font-weight:800;letter-spacing:1.5px;font-size:10px;margin-bottom:6px;}
.page-title {font-weight:800;color:#183C30;letter-spacing:-.7px;font-size:30px;margin:0;}
.page-subtitle {color:#222222;font-size:13px;margin:4px 0 16px;}
.hero {background:linear-gradient(115deg,#173D32 0%,#286247 68%,#477D55 100%);border-radius:16px;padding:21px 24px;color:white;margin:2px 0 18px;}
.hero-kicker {color:#D5E6D8;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;font-weight:800;}
.hero-title {color:white;font-size:24px;font-weight:800;margin:6px 0;}
.hero-text {color:#E0ECE2;font-size:12px;max-width:800px;}
.kpi-card {background:white;border:1px solid #E5EBE5;border-radius:13px;padding:14px 16px;min-height:95px;box-shadow:0 3px 12px rgba(28,55,39,.035);}
.kpi-label {color:#7B8980;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;}
.kpi-value {color:#193F31;font-size:23px;font-weight:800;margin-top:7px;line-height:1.15;}
.kpi-note {color:#849087;font-size:10px;margin-top:4px;}
.section-heading {color:#214635;font-size:17px;font-weight:800;margin:7px 0 2px;}
.section-caption {color:#222222;font-size:11px;margin-bottom:10px;}
.note-box {background:#EDF4ED;border-left:4px solid #4C805B;border-radius:8px;padding:10px 13px;color:#355440;font-size:12px;}
.footer-line {color:#91A097;font-size:10px;text-align:center;padding:16px 0 4px;}
div[data-testid="stMetric"] {background:white;border:1px solid #E5EBE5;padding:12px 14px;border-radius:12px;}
div[data-testid="stMetric"] label {color:#718078 !important;font-size:10px !important;text-transform:uppercase;}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {color:#193F31;font-weight:800;}
.stTabs [data-baseweb="tab-list"] {gap:6px;}
.stTabs [data-baseweb="tab"] {background:white;border:1px solid #E5EBE5;border-radius:8px 8px 0 0;padding:7px 12px;font-size:12px;}
.stTabs [aria-selected="true"] {color:#245744 !important;border-bottom:3px solid #3E805B !important;}

.insight-card {background:#FFFFFF;border:1px solid #E3EAE3;border-radius:13px;padding:15px 16px;margin-bottom:12px;box-shadow:0 3px 12px rgba(28,55,39,.035);}
.insight-label {color:#7B8980;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;}
.insight-number {color:#193F31;font-size:23px;font-weight:800;margin-top:7px;line-height:1.2;}
.insight-description {color:#718078;font-size:11px;line-height:1.5;margin-top:6px;}
</style>
""", unsafe_allow_html=True)

# ------------------------- NOMES AMIGÁVEIS -----------------------
NOMES = {
    "soja_internacional_usd_t": "Preço internacional da soja (US$/tonelada)",
    "exportacao_soja_ton": "Exportações brasileiras de soja (toneladas)",
    "ipca_num_indice": "Índice de inflação (IPCA)",
    "brent_usd_barril": "Petróleo Brent (US$/barril)",
    "fertilizantes_indice": "Índice de fertilizantes",
    "var_exportacao_soja_pct": "Variação das exportações de soja (%)",
    "var_preco_soja_pr_pct": "Variação do preço da soja no Paraná (%)",
    "var_cambio_usd_brl_pct": "Variação do câmbio (%)",
    "var_soja_internacional_pct": "Variação da soja internacional (%)",
    "var_brent_pct": "Variação do Brent (%)",
    "var_fertilizantes_pct": "Variação dos fertilizantes (%)",
    "var_ipca_indice_pct": "Variação do IPCA (%)",
    "soja_internacional_usd": "Preço internacional da soja (US$)",
    "preco_soja_deral": "Preço da soja no Paraná (DERAL)",
    "preco_soja_pr": "Preço da soja no Paraná (DERAL, R$/saca de 60 kg)",
    "soja_deral": "Preço da soja – DERAL", "cambio_brl_usd": "Taxa de câmbio (R$/US$)",
    "cambio": "Taxa de câmbio", "dolar": "Cotação do dólar", "milho": "Preço do milho",
    "petroleo": "Preço do petróleo", "petróleo": "Preço do petróleo",
    "fertilizantes": "Índice de preços de fertilizantes", "ipca": "Inflação (IPCA)",
    "selic": "Taxa básica de juros (Selic)", "data": "Data", "preco_observado": "Preço observado da soja",
    "preco_previsto_baseline": "Previsão – modelo de referência", "preco_previsto_linear": "Previsão – modelo linear",
    "preco_previsto_ridge": "Previsão – modelo Ridge", "mes": "Mês", "mês": "Mês", "ano": "Ano",
    "variavel": "Indicador", "variável": "Indicador", "correlacao": "Coeficiente de correlação",
    "correlação": "Coeficiente de correlação", "lag": "Defasagem (meses)", "defasagem": "Defasagem (meses)",
    "coeficiente": "Coeficiente estimado", "pontuacao": "Pontuação dos sinais", "pontuação": "Pontuação dos sinais",
}

def nome_amigavel(nome):
    chave = str(nome).strip()
    if chave in NOMES: return NOMES[chave]
    if chave.lower() in NOMES: return NOMES[chave.lower()]
    texto = re.sub(r"[_\-]+", " ", chave)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:1].upper() + texto[1:]

def normalizar_data(df):
    if df is None or df.empty: return df, None
    candidatos = {"data", "date", "periodo", "período", "mes", "mês", "month"}
    for col in df.columns:
        if str(col).strip().lower() in candidatos:
            raw = df[col].astype(str).str.strip()
            iso = raw.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)
            converted = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
            converted.loc[iso] = pd.to_datetime(raw.loc[iso], errors="coerce", yearfirst=True)
            converted.loc[~iso] = pd.to_datetime(raw.loc[~iso], errors="coerce", dayfirst=True)
            if converted.notna().any():
                out = df.copy(); out[col] = converted
                return out, col
    return df, None


# ----------------------------- LEITURA --------------------------
APP_DIR = Path(__file__).resolve().parent
ROOTS = [
    APP_DIR / "resultados" / "tabelas",
    APP_DIR / "resultados",
    APP_DIR,
]

def localizar_arquivo(nome):
    for root in ROOTS:
        candidate = root / nome
        if candidate.exists() and candidate.is_file(): return candidate
    return None


@st.cache_data(show_spinner=False)
def carregar_csv_flexivel(nome):
    path = localizar_arquivo(nome)
    if not path: return pd.DataFrame()
    for sep in [None, ",", ";", "\t"]:
        try:
            df = pd.read_csv(path, sep=sep, engine="python", encoding="utf-8-sig")
            df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
            if df.shape[1] > 1 or sep is not None: return df
        except Exception: pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def carregar_dados_principais():
    # Prefer the CSV that was verified; avoid silently selecting a stale/invalid parquet.
    nomes_obrigatorios = {
        "data", "soja_internacional_usd_t", "brent_usd_barril",
        "cambio_usd_brl", "fertilizantes_indice"
    }
    for nome in ["dados_consolidados_dashboard.csv", "dados_consolidados_dashboard.parquet"]:
        path = localizar_arquivo(nome)
        if not path:
            continue
        try:
            if path.suffix.lower() == ".parquet":
                df = pd.read_parquet(path)
            else:
                # This dataset is comma-separated. Use the explicit delimiter first.
                df = pd.read_csv(path, sep=",", encoding="utf-8-sig")
            df.columns = [str(c).replace("\ufeff", "").strip().lower() for c in df.columns]
            # Validate before returning: a stale or one-column read must not block fallback.
            if df.empty or not nomes_obrigatorios.issubset(set(df.columns)):
                continue
            datas = pd.to_datetime(df["data"], errors="coerce")
            if datas.notna().sum() == 0:
                continue
            df["data"] = datas
            for col in nomes_obrigatorios - {"data"}:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        except Exception:
            continue
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def carregar_metadata():
    path = localizar_arquivo("metadata_dashboard.json")
    if path:
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: pass
    return {}


@st.cache_data(show_spinner=False)
def carregar_deral():
    """Carrega e normaliza a série mensal de preços do DERAL."""
    path = localizar_arquivo("deral_preco_soja_pr.csv")
    if path is None:
        return pd.DataFrame(columns=["data", "preco_soja_pr"])

    # Testa os separadores mais comuns e remove o BOM do cabeçalho.
    df = pd.DataFrame()
    for sep in [None, ",", ";", "\t"]:
        try:
            tentativa = pd.read_csv(
                path, sep=sep, engine="python", encoding="utf-8-sig"
            )
            tentativa.columns = [
                str(col).replace("\ufeff", "").strip().lower()
                for col in tentativa.columns
            ]
            if {"data", "preco_soja_pr"}.issubset(tentativa.columns):
                df = tentativa
                break
        except Exception:
            continue

    if df.empty:
        return pd.DataFrame(columns=["data", "preco_soja_pr"])

    # Corrige a leitura das datas: datas ISO (AAAA-MM-DD) devem ser lidas
    # sem dayfirst=True, que deslocava meses para janeiro. Formatos brasileiros
    # (DD/MM/AAAA) continuam sendo lidos com dayfirst=True.
    datas_texto = df["data"].astype(str).str.strip()
    mascara_iso = datas_texto.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)
    datas_convertidas = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    datas_convertidas.loc[mascara_iso] = pd.to_datetime(
        datas_texto.loc[mascara_iso], errors="coerce", yearfirst=True
    )
    datas_convertidas.loc[~mascara_iso] = pd.to_datetime(
        datas_texto.loc[~mascara_iso], errors="coerce", dayfirst=True
    )
    df["data"] = datas_convertidas

    # Aceita números no formato 1234.56 ou brasileiro 1.234,56.
    preco = df["preco_soja_pr"].astype(str).str.strip()
    preco = preco.str.replace("R$", "", regex=False).str.replace(" ", "", regex=False)
    tem_virgula = preco.str.contains(",", regex=False)
    preco.loc[tem_virgula] = (
        preco.loc[tem_virgula]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["preco_soja_pr"] = pd.to_numeric(preco, errors="coerce")

    df = df.dropna(subset=["data", "preco_soja_pr"])
    df = df.sort_values("data").drop_duplicates(subset=["data"], keep="last")
    return df[["data", "preco_soja_pr"]].reset_index(drop=True)

def filtrar_periodo(df, inicio, fim):
    if df is None or df.empty: return pd.DataFrame(), None
    out, col_data = normalizar_data(df.copy())
    if col_data and inicio and fim:
        out = out[(out[col_data].dt.date >= inicio) & (out[col_data].dt.date <= fim)]
    return out, col_data

# --------------------------- GRÁFICOS --------------------------
def preparar_figura(fig, altura=360):
    fig.update_layout(
        template="plotly_white", height=altura, margin=dict(l=12, r=14, t=45, b=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", size=11, color="#000000"),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        hoverlabel=dict(bgcolor="white", font_size=11), showlegend=True,
    )
    fig.update_xaxes(showgrid=False, linecolor="#000000", tickfont=dict(color="#000000"), title_font=dict(color="#000000"))
    fig.update_yaxes(gridcolor="#EDF1ED", zeroline=False, tickfont=dict(color="#000000"), title_font=dict(color="#000000"))
    fig.update_layout(legend=dict(font=dict(color="#000000")), title_font=dict(color="#000000"))
    return fig

def titulo_secao(titulo, descricao=None):
    st.markdown(f'<div class="section-heading">{titulo}</div>', unsafe_allow_html=True)
    if descricao: st.markdown(f'<div class="section-caption">{descricao}</div>', unsafe_allow_html=True)

def grafico(df, titulo, altura=360, chave=None, tipo="auto"):
    if df is None or df.empty:
        st.info(f"Não há dados disponíveis para: {titulo}."); return
    data, col_data = normalizar_data(df.copy())
    data = data.dropna(axis=1, how="all")
    # Corrige valores numéricos exportados como texto (decimal brasileiro).
    for c in data.columns:
        if c == col_data: continue
        if data[c].dtype == object:
            txt = data[c].astype(str).str.strip().str.replace(" ", "", regex=False)
            if txt.str.contains(",", regex=False).any():
                if txt.str.contains(r"\.", regex=True).any(): txt = txt.str.replace(".", "", regex=False)
                txt = txt.str.replace(",", ".", regex=False)
            num = pd.to_numeric(txt, errors="coerce")
            if num.notna().sum() >= max(2, int(len(data)*0.5)): data[c] = num
    numericas = data.select_dtypes(include="number").columns.tolist()
    categoricas = [c for c in data.columns if c not in numericas and c != col_data]
    # Matrix correlation: first column contains variable names, rest numeric columns are variables.
    if tipo == "heatmap" or (len(data) == len(numericas) and categoricas and len(numericas) >= 2):
        try:
            index_col = categoricas[0]
            matrix = data.set_index(index_col)[numericas].apply(pd.to_numeric, errors="coerce")
            matrix.index = matrix.index.map(nome_amigavel); matrix.columns = matrix.columns.map(nome_amigavel)
            fig = px.imshow(matrix, text_auto=".2f", aspect="auto", zmin=-1, zmax=1,
                color_continuous_scale=["#B85C4A", "#F7F5EA", "#347653"],
                labels={"color":"Correlação", "x":"Indicador", "y":"Indicador"})
            fig.update_layout(title=None, xaxis_tickangle=-35)
            st.plotly_chart(preparar_figura(fig, max(440, altura)), use_container_width=True, key=chave); return
        except Exception: pass
    # Long-format correlation results: display sorted bars and reference zero.
    if tipo == "heatmap" and numericas:
        ycol = next((c for c in numericas if any(k in c.lower() for k in ["correl", "rho", "coef"])), numericas[-1])
        labels = [c for c in data.columns if c not in numericas and c != col_data]
        if labels:
            labelcol = labels[0]
            plot = data[[labelcol, ycol]].copy().dropna().sort_values(ycol)
            plot[labelcol] = plot[labelcol].astype(str)
            fig = px.bar(plot, x=ycol, y=labelcol, orientation="h", color=ycol,
                color_continuous_scale=["#B85C4A", "#F7F5EA", "#347653"],
                labels={ycol:"Coeficiente", labelcol:"Comparação"})
            fig.update_layout(title=None, coloraxis_showscale=False)
            fig.add_vline(x=0, line_color="#222", line_width=1)
            st.plotly_chart(preparar_figura(fig, max(440, altura)), use_container_width=True, key=chave); return
    if col_data and numericas:
        long = data[[col_data]+numericas].melt(id_vars=col_data, var_name="Indicador", value_name="Valor").dropna()
        long["Indicador"] = long["Indicador"].map(nome_amigavel)
        fig = px.line(long, x=col_data, y="Valor", color="Indicador", labels={col_data:"Período", "Valor":"Valor", "Indicador":"Indicador"})
        fig.update_traces(line=dict(width=2.4)); fig.update_layout(title=None)
        st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
    if numericas and categoricas:
        categoria = categoricas[0]
        if len(numericas) == 1:
            y = numericas[0]; plot = data[[categoria, y]].copy().dropna(subset=[y])
            plot[categoria] = plot[categoria].astype(str)
            fig = px.bar(plot, x=categoria, y=y, labels={categoria:nome_amigavel(categoria), y:nome_amigavel(y)}, color_discrete_sequence=["#4C805B"])
        else:
            plot = data[[categoria]+numericas].melt(id_vars=categoria, var_name="Indicador", value_name="Valor").dropna()
            plot["Indicador"] = plot["Indicador"].map(nome_amigavel)
            fig = px.bar(plot, x=categoria, y="Valor", color="Indicador", barmode="group")
        fig.update_layout(title=None); st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
    if numericas:
        resumo = data[numericas].mean(numeric_only=True).reset_index(); resumo.columns = ["Indicador", "Média"]
        resumo["Indicador"] = resumo["Indicador"].map(nome_amigavel)
        fig = px.bar(resumo, x="Indicador", y="Média", color="Indicador", labels={"Indicador":"Indicador", "Média":"Média"})
        fig.update_layout(title=None); st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
    categoria = data.columns[0]
    freq = data[categoria].astype(str).value_counts().head(15).reset_index(); freq.columns = [nome_amigavel(categoria), "Quantidade"]
    fig = px.bar(freq, x=nome_amigavel(categoria), y="Quantidade", color_discrete_sequence=["#4C805B"])
    fig.update_layout(title=None); st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave)

def mostrar_metricas(df, prefixo):
    if df is None or df.empty:
        st.info(f"Resultados de métricas ({prefixo}) não encontrados no período."); return
    nums = df.select_dtypes(include="number").columns.tolist()
    if not nums:
        st.info("O arquivo de métricas não contém valores numéricos que possam ser exibidos como indicadores."); return
    linha = df.iloc[0]
    # Compact, readable KPI tiles; no raw tables in the dashboard.
    for inicio in range(0, len(nums), 4):
        bloco = nums[inicio:inicio+4]
        cols = st.columns(len(bloco))
        for col, c in zip(cols, bloco):
            val = pd.to_numeric(pd.Series([linha[c]]), errors="coerce").iloc[0]
            with col:
                st.metric(nome_amigavel(c), f"{val:,.3f}" if pd.notna(val) else "—")

# ------------------------- DADOS BASE ---------------------------
df_base = carregar_dados_principais()
metadata = carregar_metadata()
df_deral = carregar_deral()

# Integra o DERAL como série estadual de referência, mantendo as outras variáveis.
if not df_deral.empty:
    if not df_base.empty:
        base_norm, base_date = normalizar_data(df_base)
        if base_date and base_date != "data": base_norm = base_norm.rename(columns={base_date:"data"})
        if "data" in base_norm.columns:
            base_norm["data"] = pd.to_datetime(base_norm["data"], errors="coerce")
            base_norm = base_norm.drop(columns=["preco_soja_pr"], errors="ignore").merge(df_deral, on="data", how="outer")
            df_base = base_norm
        else: df_base = df_deral.copy()
    else: df_base = df_deral.copy()
df_base, coluna_data = normalizar_data(df_base)


# -------------------------- SIDEBAR ----------------------------
with st.sidebar:
    st.markdown("🌱")
    st.markdown('<div class="brand">AgroData PR</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Inteligência e monitoramento<br>do mercado da soja</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div class="side-caption"><b>NAVEGAÇÃO</b></div>', unsafe_allow_html=True)
    pagina = st.radio("Seções", ["🏠 Visão Geral", "📊 Análise Exploratória", "🔗 Correlações e Lags", "⚠️ Sinais de Atenção", "🤖 Modelagem Ridge"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown('<div class="side-caption"><b>PERÍODO</b></div>', unsafe_allow_html=True)
    # Limites fixos do estudo: o usuário não pode selecionar datas fora deste intervalo.
    date_min = date(2000, 1, 1)
    date_max = date(2025, 12, 31)
    date_range = st.date_input(
        "Período (selecione as datas inicial e final)",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        format="DD/MM/YYYY",
        help="Use as datas inicial e final para mudar o período mensal exibido nos gráficos. Limites: 01/01/2000 a 31/12/2025.",
    )
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
        start_date, end_date = date_range[0], date_max
    else:
        start_date, end_date = date_min, date_max
    st.caption(f"Período selecionado: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")
    st.markdown("---")
    st.markdown('<div class="side-caption"><b>ESTÁGIO SUPERVISIONADO</b><br>Deysianne Souza<br>Orientador: Prof. Diego B. Santi<br>UNICENTRO · 2026</div>', unsafe_allow_html=True)

if not df_base.empty and coluna_data:
    df_base = df_base[(df_base[coluna_data].dt.date >= start_date) & (df_base[coluna_data].dt.date <= end_date)]
if not df_deral.empty:
    deral_filtrado = df_deral[(df_deral["data"].dt.date >= start_date) & (df_deral["data"].dt.date <= end_date)]
else: deral_filtrado = pd.DataFrame()

st.markdown('<div class="eyebrow">PAINEL DE INTELIGÊNCIA DO AGRONEGÓCIO</div>', unsafe_allow_html=True)

# ============================ HOME =============================
if pagina == "🏠 Visão Geral":
    st.markdown('<div class="page-title">Painel de Inteligência do Mercado da Soja</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Paraná · DERAL · Análise histórica de janeiro de 2000 a dezembro de 2025</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="hero">'
        '<div class="hero-kicker">AGRODATA PR · INTELIGÊNCIA DE MERCADO</div>'
        '<div class="hero-title">Entenda os movimentos do mercado da soja.</div>'
        '<div class="hero-text">Acompanhe o preço estadual, explore indicadores relacionados e consulte os principais resultados das análises históricas.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # Métricas calculadas a partir do preço DERAL disponível no período filtrado.
    preco_df = deral_filtrado.sort_values("data").copy() if not deral_filtrado.empty else pd.DataFrame()
    if not preco_df.empty:
        preco_df["preco_soja_pr"] = pd.to_numeric(preco_df["preco_soja_pr"], errors="coerce")
        preco_df = preco_df.dropna(subset=["preco_soja_pr"])
    if not preco_df.empty:
        ultimo = float(preco_df["preco_soja_pr"].iloc[-1])
        media_periodo = float(preco_df["preco_soja_pr"].mean())
        primeiro = float(preco_df["preco_soja_pr"].iloc[0])
        variacao_periodo = ((ultimo / primeiro) - 1) * 100 if primeiro else float("nan")
        ultima_data = preco_df["data"].iloc[-1].strftime("%m/%Y")
        total_obs = len(preco_df)
    else:
        ultimo = media_periodo = variacao_periodo = float("nan")
        ultima_data = "Sem dados"
        total_obs = 0

    def formatar_brl(valor):
        if pd.isna(valor):
            return "—"
        return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def formatar_pct(valor):
        if pd.isna(valor):
            return "—"
        return f"{valor:+.1f}%".replace(".", ",")

    kpis = [
        ("ÚLTIMO PREÇO", formatar_brl(ultimo), f"DERAL · {ultima_data}"),
        ("PREÇO MÉDIO", formatar_brl(media_periodo), "Média no período selecionado"),
        ("VARIAÇÃO DO PERÍODO", formatar_pct(variacao_periodo), "Primeiro ao último registro"),
        ("OBSERVAÇÕES", f"{total_obs:,}".replace(",", "."), "Registros mensais disponíveis"),
    ]
    cols = st.columns(4)
    for col, (label, value, note) in zip(cols, kpis):
        with col:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
                unsafe_allow_html=True
            )

    st.write("")
    if preco_df.empty:
        st.warning("Não foram encontrados dados de preço do DERAL para o período selecionado. Confira o arquivo deral_preco_soja_pr.csv.")
    else:
        left, right = st.columns([1.8, 1])
        with left:
            titulo_secao("Evolução do preço da soja no Paraná", "Preço nominal mensal em reais por saca de 60 kg.")
            fig_preco = px.area(
                preco_df, x="data", y="preco_soja_pr",
                labels={"data": "Mês", "preco_soja_pr": "Preço (R$/saca de 60 kg)"}
            )
            fig_preco.update_traces(
                line=dict(color="#286247", width=2.8),
                fillcolor="rgba(62,128,91,0.13)",
                hovertemplate="%{x|%b/%Y}<br>R$ %{y:,.2f}<extra></extra>"
            )
            fig_preco.update_layout(
                title=None,
                yaxis_tickprefix="R$ ",
                xaxis_rangeslider_visible=True
            )
            st.plotly_chart(preparar_figura(fig_preco, 420), use_container_width=True)

        with right:
            titulo_secao("Leitura rápida", "Resumo calculado para o intervalo selecionado.")
            st.markdown(
                f'<div class="insight-card"><div class="insight-label">Preço mais recente</div>'
                f'<div class="insight-number">{formatar_brl(ultimo)}</div>'
                f'<div class="insight-description">Último valor disponível na série estadual.</div></div>',
                unsafe_allow_html=True
            )
            if pd.notna(variacao_periodo):
                direcao = "aumento" if variacao_periodo > 0 else ("redução" if variacao_periodo < 0 else "estabilidade")
                texto_var = f"No intervalo selecionado, o preço apresentou {direcao} de {abs(variacao_periodo):.1f}%.".replace(".", ",")
            else:
                texto_var = "Não há dados suficientes para calcular a variação do período."
            st.markdown(
                f'<div class="note-box">{texto_var} Essa comparação considera o primeiro e o último registro disponíveis e não representa uma previsão.</div>',
                unsafe_allow_html=True
            )
            st.write("")
            st.markdown(
                '<div class="insight-card"><div class="insight-label">Escopo da análise</div>'
                '<div class="insight-number">2000–2025</div>'
                '<div class="insight-description">Série histórica mensal utilizada no estudo.</div></div>',
                unsafe_allow_html=True
            )

        # Comportamento sazonal e variações recentes.
        st.markdown("---")
        col_saz, col_var = st.columns(2)
        with col_saz:
            titulo_secao("Comportamento sazonal", "Preço médio histórico por mês do ano, dentro do período selecionado.")
            saz = preco_df.copy()
            saz["numero_mes"] = saz["data"].dt.month
            meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            perfil = saz.groupby("numero_mes", as_index=False)["preco_soja_pr"].mean()
            perfil["Mês"] = perfil["numero_mes"].map(lambda m: meses[int(m) - 1])
            fig_saz = px.bar(
                perfil, x="Mês", y="preco_soja_pr",
                labels={"preco_soja_pr": "Preço médio (R$/saca)", "Mês": "Mês"}
            )
            fig_saz.update_traces(marker_color="#5B8967", hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
            fig_saz.update_layout(title=None, yaxis_tickprefix="R$ ")
            st.plotly_chart(preparar_figura(fig_saz, 320), use_container_width=True)

        with col_var:
            titulo_secao("Variação mensal do preço", "Percentual de mudança em relação ao mês anterior.")
            variacoes = preco_df[["data", "preco_soja_pr"]].copy()
            variacoes["data"] = pd.to_datetime(variacoes["data"], errors="coerce")
            variacoes["preco_soja_pr"] = pd.to_numeric(variacoes["preco_soja_pr"], errors="coerce")
            variacoes = variacoes.dropna(subset=["data", "preco_soja_pr"]).sort_values("data").reset_index(drop=True)
            variacoes["variacao_mensal"] = variacoes["preco_soja_pr"].pct_change() * 100
            variacoes = variacoes.dropna(subset=["variacao_mensal"]).tail(36)
            if not variacoes.empty:
                variacoes["Direção"] = variacoes["variacao_mensal"].apply(
                    lambda x: "Alta" if x >= 0 else "Queda"
                )
                fig_var = px.bar(
                    variacoes, x="data", y="variacao_mensal", color="Direção",
                    color_discrete_map={"Alta": "#4C805B", "Queda": "#C47762"},
                    labels={"data": "Mês", "variacao_mensal": "Variação (%)"}
                )
                fig_var.update_layout(title=None, legend_title_text="")
                fig_var.add_hline(y=0, line_color="#718078", line_width=1)
                st.plotly_chart(preparar_figura(fig_var, 320), use_container_width=True)
            else:
                st.info("Não há observações suficientes para calcular as variações mensais.")

    # Indicadores de mercado apresentados em índice-base 100 para evitar comparar unidades diferentes.
    st.markdown("---")
    titulo_secao(
        "Indicadores relacionados ao mercado",
        "Séries reescalonadas para base 100 no primeiro mês disponível. O índice permite comparar movimentos, não valores absolutos. A base consolidada disponível para esses indicadores começa em dez/2000."
    )
    # Carrega a base consolidada separadamente da série DERAL para garantir
    # que a junção do preço estadual não interfira na identificação dos indicadores.
    base_ind_raw = carregar_dados_principais()
    base_ind_raw, data_ind = normalizar_data(base_ind_raw)
    if not base_ind_raw.empty and data_ind is None and "data" in base_ind_raw.columns:
        base_ind_raw["data"] = pd.to_datetime(base_ind_raw["data"], errors="coerce")
        data_ind = "data" if base_ind_raw["data"].notna().any() else None
    if not base_ind_raw.empty and data_ind:
        base_ind_raw[data_ind] = pd.to_datetime(base_ind_raw[data_ind], errors="coerce")
        base_ind_raw = base_ind_raw.dropna(subset=[data_ind])
        base_ind_raw = base_ind_raw[
            (base_ind_raw[data_ind].dt.date >= start_date) &
            (base_ind_raw[data_ind].dt.date <= end_date)
        ].sort_values(data_ind)

        if not base_ind_raw.empty:
            st.caption(f"Disponibilidade da base consolidada de indicadores no intervalo: {base_ind_raw[data_ind].min():%m/%Y} a {base_ind_raw[data_ind].max():%m/%Y} ({len(base_ind_raw)} registros). A série DERAL é apresentada separadamente e possui cobertura histórica própria.")

        candidatos = {
            "Preço internacional da soja": ["soja_internacional_usd_t", "soja_internacional_usd"],
            "Câmbio": ["cambio_usd_brl", "cambio_brl_usd", "cambio", "dolar"],
            "Petróleo Brent": ["brent_usd_barril", "brent", "petroleo", "petróleo"],
            "Fertilizantes": ["fertilizantes_indice", "fertilizantes", "indice_fertilizantes", "índice_fertilizantes"],
        }

        # Normaliza valores que podem ter vindo como texto (ex.: "1.234,56").
        def converter_indicador(serie):
            texto = serie.astype(str).str.strip().str.replace(" ", "", regex=False)
            tem_virgula = texto.str.contains(",", regex=False).any()
            tem_ponto = texto.str.contains(r"\.", regex=True).any()
            if tem_virgula and tem_ponto:
                texto = texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            elif tem_virgula:
                texto = texto.str.replace(",", ".", regex=False)
            return pd.to_numeric(texto, errors="coerce")

        colunas_norm = {str(c).strip().lower(): c for c in base_ind_raw.columns}
        series_ind = {}
        for nome, aliases in candidatos.items():
            col_real = next((colunas_norm[a.lower()] for a in aliases if a.lower() in colunas_norm), None)
            if col_real is None:
                continue
            valores = converter_indicador(base_ind_raw[col_real])
            valores = valores.replace([float("inf"), float("-inf")], pd.NA)
            if valores.notna().sum() >= 2:
                series_ind[nome] = valores

        if series_ind:
            base_plot = pd.DataFrame({data_ind: base_ind_raw[data_ind]})
            for nome, valores in series_ind.items():
                primeira = valores.dropna().iloc[0]
                if primeira != 0:
                    base_plot[nome] = (valores / primeira) * 100

            plot_cols = [c for c in series_ind if c in base_plot.columns]
            if plot_cols:
                long_ind = base_plot[[data_ind] + plot_cols].melt(
                    id_vars=data_ind, var_name="Indicador", value_name="Índice (base 100)"
                ).dropna()
                fig_ind = px.line(
                    long_ind, x=data_ind, y="Índice (base 100)", color="Indicador",
                    labels={data_ind: "Período", "Índice (base 100)": "Índice (base 100)"}
                )
                fig_ind.update_traces(line=dict(width=2.3))
                fig_ind.add_hline(y=100, line_dash="dot", line_color="#000000")
                st.plotly_chart(preparar_figura(fig_ind, 350), use_container_width=True)
        else:
            st.warning("Os indicadores foram carregados, mas não possuem valores numéricos suficientes para gerar o gráfico.")
    else:
        st.error("Não foi possível carregar a base consolidada de indicadores ou identificar a coluna de datas.")

    # Destaques fixos dos resultados do estudo completo (não variam com o filtro visual).
    st.markdown("---")
    titulo_secao("Principais achados do estudo", "Resultados estatísticos calculados para a série histórica completa de 2000 a 2025.")
    achado1, achado2, achado3 = st.columns(3)
    with achado1:
        st.markdown(
            '<div class="insight-card"><div class="insight-label">Preço internacional da soja</div>'
            '<div class="insight-number">ρ = 0,49</div>'
            '<div class="insight-description">Associação positiva com a variação do preço estadual, identificada na análise contemporânea.</div></div>',
            unsafe_allow_html=True
        )
    with achado2:
        st.markdown(
            '<div class="insight-card"><div class="insight-label">Câmbio USD/BRL</div>'
            '<div class="insight-number">ρ = 0,32</div>'
            '<div class="insight-description">Associação positiva com a variação do preço estadual, também na defasagem zero.</div></div>',
            unsafe_allow_html=True
        )
    with achado3:
        st.markdown(
            '<div class="insight-card"><div class="insight-label">Interpretação</div>'
            '<div class="insight-number">Exploratória</div>'
            '<div class="insight-description">Correlação não indica causalidade. Os resultados apoiam a análise, não garantem movimentos futuros.</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        '<div class="footer-line">Painel acadêmico desenvolvido para análise histórica do mercado da soja no Paraná · '
        'Dados e resultados do projeto · Atualização conforme os arquivos tratados</div>',
        unsafe_allow_html=True
    )

# ====================== EXPLORATÓRIA ===========================
elif pagina == "📊 Análise Exploratória":
    st.markdown('<div class="page-title">Análise Exploratória</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Estatísticas descritivas, padrões sazonais e variações mensais.</div>', unsafe_allow_html=True)
    st.info("As tabelas desta seção são resultados pré-calculados para a série completa do estudo (jan/2000 a dez/2025). O filtro de período não recalcula essas estatísticas; ele é aplicado aos gráficos temporais da Visão Geral e às séries mensais de sinais e previsões.")
    tab1, tab2, tab3 = st.tabs(["Estatísticas", "Sazonalidade", "Variações"])
    with tab1:
        stats = carregar_csv_flexivel("07_estatisticas_descritivas_niveis.csv")
        titulo_secao("Resumo estatístico", "Escolha uma medida para comparar os indicadores. Cada medida é exibida separadamente para evitar misturar escalas incompatíveis.")
        if not stats.empty and "variavel" in stats.columns:
            medidas = [c for c in ["mean", "50%", "std", "min", "25%", "75%", "max", "coef_variacao_pct"] if c in stats.columns]
            medida_labels = {"mean":"Média", "50%":"Mediana", "std":"Desvio padrão", "min":"Mínimo", "25%":"1º quartil (25%)", "75%":"3º quartil (75%)", "max":"Máximo", "coef_variacao_pct":"Coeficiente de variação (%)"}
            escolha = st.selectbox("Medida estatística", medidas, format_func=lambda c: medida_labels.get(c,c))
            plot = stats[["variavel", escolha]].copy()
            plot[escolha] = pd.to_numeric(plot[escolha], errors="coerce")
            plot = plot.dropna(subset=[escolha]).sort_values(escolha)
            plot["Indicador"] = plot["variavel"].map(nome_amigavel)
            fig = px.bar(plot, x=escolha, y="Indicador", orientation="h", text=plot[escolha].map(lambda v:f"{v:,.2f}"),
                labels={escolha:medida_labels.get(escolha,escolha), "Indicador":"Indicador"}, color_discrete_sequence=["#286247"])
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(title=None, margin=dict(l=10,r=90,t=20,b=30))
            st.plotly_chart(preparar_figura(fig, max(430, 36*len(plot))), use_container_width=True, key="expl_stats_measure")
        else:
            st.info("Arquivo de estatísticas não disponível ou sem estrutura esperada.")
    with tab2:
        saz = carregar_csv_flexivel("07_sazonalidade_mensal.csv")
        titulo_secao("Padrão sazonal médio por mês", "Perfil mensal calculado no conjunto histórico do arquivo sazonal (não é uma série por ano).")
        if not saz.empty and "mes" in saz.columns:
            saz["mes"] = pd.to_numeric(saz["mes"], errors="coerce")
            meses_pt = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
            saz["Mês"] = saz["mes"].map(meses_pt)
            col_opts = {"preco_soja_pr_media":"Preço nominal médio (R$/saca)", "preco_soja_pr_mediana":"Preço nominal mediano (R$/saca)", "preco_soja_real_media":"Preço real médio", "preco_soja_real_mediana":"Preço real mediano", "variacao_preco_media_pct":"Variação média (%)", "variacao_preco_mediana_pct":"Variação mediana (%)"}
            saz_col = st.selectbox("Série sazonal", [c for c in col_opts if c in saz.columns], format_func=lambda c: col_opts[c])
            saz_plot = saz.dropna(subset=[saz_col]).sort_values("mes")
            if not saz_plot.empty:
                fig = px.bar(saz_plot, x="Mês", y=saz_col, text=saz_plot[saz_col].map(lambda v:f"{v:,.2f}"),
                    labels={saz_col:col_opts[saz_col],"Mês":"Mês"}, color_discrete_sequence=["#286247"])
                fig.update_traces(textposition="outside", cliponaxis=False)
                if "variacao" in saz_col: fig.add_hline(y=0, line_color="#111", line_dash="dash")
                fig.update_layout(title=None, margin=dict(t=20,b=30))
                st.plotly_chart(preparar_figura(fig, 430), use_container_width=True, key="expl_seasonal_file")
            else: st.info("A coluna escolhida não possui valores para exibir.")
        else:
            st.info("Arquivo sazonal não encontrado ou não contém a coluna 'mes'.")
    with tab3:
        vari = carregar_csv_flexivel("07_estatisticas_variacoes_mensais.csv")
        titulo_secao("Variações mensais", "Distribuição das variações. A escala usa percentis para não deixar extremos isolados ocultarem os demais indicadores.")
        if not vari.empty and "variavel" in vari.columns:
            needed = [c for c in ["variavel","5%","50%","95%"] if c in vari.columns]
            vplot = vari[needed].copy()
            for c in needed[1:]: vplot[c] = pd.to_numeric(vplot[c], errors="coerce")
            vplot = vplot.dropna(subset=["5%","50%","95%"])
            vplot["Indicador"] = vplot["variavel"].map(nome_amigavel)
            fig = go.Figure()
            for _, row in vplot.iterrows():
                fig.add_trace(go.Scatter(x=[row["5%"], row["95%"]], y=[row["Indicador"]]*2, mode="lines", line=dict(color="#8EAA96",width=5), showlegend=False, hovertemplate="Faixa 5–95%<extra></extra>"))
                fig.add_trace(go.Scatter(x=[row["50%"]], y=[row["Indicador"]], mode="markers+text", marker=dict(color="#204E37",size=10), text=[f"Mediana {row['50%']:.2f}%"], textposition="middle right", showlegend=False, hovertemplate="Mediana: %{x:.2f}%<extra></extra>"))
            fig.add_vline(x=0, line_color="#111", line_dash="dash")
            fig.update_layout(title=None, xaxis_title="Variação mensal (%) — faixa entre percentis 5 e 95", yaxis_title="Indicador", margin=dict(l=20,r=100,t=25,b=45))
            st.plotly_chart(preparar_figura(fig, 460), use_container_width=True, key="expl_variations_range")
            st.caption("A faixa representa o intervalo entre os percentis 5 e 95; o ponto mostra a mediana. Extremos fora da faixa não são ocultados dos cálculos, apenas não são usados para definir a escala visual.")
        else: st.info("Arquivo de variações não encontrado ou sem estrutura esperada.")

# ====================== CORRELAÇÕES/LAGS =======================
elif pagina == "🔗 Correlações e Lags":
    st.markdown('<div class="page-title">Correlações e Defasagens</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Direção e intensidade das relações estatísticas. Correlação não significa causalidade.</div>', unsafe_allow_html=True)
    st.info("As correlações e defasagens são tabelas pré-calculadas para a série completa do estudo. O filtro de período não recalcula os coeficientes.")
    tabs_corr = st.tabs(["Correlação contemporânea", "Variações mensais", "Melhores defasagens", "Lags 0–6 meses"])
    with tabs_corr[0]:
        data = carregar_csv_flexivel("08_correlacoes_niveis.csv")
        titulo_secao("Correlação contemporânea entre níveis", "As barras comparam Pearson e Spearman entre os níveis dos indicadores e o preço estadual. Séries em nível podem compartilhar tendências; interprete também as correlações das variações mensais.")
        if not data.empty and {"variavel_explicativa","pearson_r","spearman_rho"}.issubset(data.columns):
            cdata=data.copy()
            cdata["pearson_r"]=pd.to_numeric(cdata["pearson_r"],errors="coerce")
            cdata["spearman_rho"]=pd.to_numeric(cdata["spearman_rho"],errors="coerce")
            cdata=cdata.dropna(subset=["pearson_r","spearman_rho"])
            cdata["Indicador"]=cdata["variavel_explicativa"].map(nome_amigavel)
            longc=cdata.melt(id_vars="Indicador",value_vars=["pearson_r","spearman_rho"],var_name="Método",value_name="Correlação")
            longc["Método"]=longc["Método"].map({"pearson_r":"Pearson","spearman_rho":"Spearman"})
            fig=px.bar(longc,x="Correlação",y="Indicador",color="Método",barmode="group",orientation="h",text=longc["Correlação"].map(lambda v:f"{v:+.2f}"),color_discrete_sequence=["#79A88B","#24563B"],range_x=[-1,1])
            fig.update_traces(textposition="outside",cliponaxis=False)
            fig.add_vline(x=0,line_color="#111",line_dash="dash")
            fig.update_layout(title=None,margin=dict(l=15,r=45,t=20,b=30),legend_title=None)
            st.plotly_chart(preparar_figura(fig,460),use_container_width=True,key="correlations_levels_bars")
        else: st.info("Arquivo de correlação entre níveis ausente ou com estrutura inesperada.")
    with tabs_corr[1]:
        data_var = carregar_csv_flexivel("08_correlacoes_variacoes_mensais.csv")
        titulo_secao("Correlação entre variações mensais", "Compara as mudanças mensais dos indicadores com a variação do preço estadual. Resultados calculados para o período completo do estudo.")
        if not data_var.empty and {"variavel_explicativa", "pearson_r", "spearman_rho"}.issubset(data_var.columns):
            plot_var = data_var.copy()
            for c in ["pearson_r", "spearman_rho"]:
                plot_var[c] = pd.to_numeric(plot_var[c], errors="coerce")
            plot_var = plot_var.dropna(subset=["pearson_r", "spearman_rho"])
            plot_var["Indicador"] = plot_var["variavel_explicativa"].map(nome_amigavel)
            long_var = plot_var.melt(id_vars="Indicador", value_vars=["pearson_r", "spearman_rho"], var_name="Método", value_name="Correlação")
            long_var["Método"] = long_var["Método"].map({"pearson_r": "Pearson", "spearman_rho": "Spearman"})
            fig_var = px.bar(long_var, x="Correlação", y="Indicador", color="Método", barmode="group", orientation="h", range_x=[-1, 1], color_discrete_sequence=["#79A88B", "#24563B"])
            fig_var.add_vline(x=0, line_color="#111", line_dash="dash")
            fig_var.update_layout(title=None, legend_title=None, margin=dict(l=15, r=35, t=20, b=30))
            st.plotly_chart(preparar_figura(fig_var, 440), use_container_width=True, key="correlations_monthly_changes")
            st.caption("Os coeficientes representam associação entre variações mensais; não demonstram causalidade.")
        else:
            st.info("Arquivo de correlações das variações mensais ausente ou com estrutura inesperada.")

    with tabs_corr[2]:
        best = carregar_csv_flexivel("08_melhores_defasagens_spearman.csv")
        titulo_secao("Melhor lag por indicador", "Mostra a correlação Spearman selecionada e a defasagem correspondente. A linha zero ajuda a separar relações positivas e negativas.")
        if not best.empty and {"variavel_explicativa","spearman_rho","defasagem_meses"}.issubset(best.columns):
            best["spearman_rho"] = pd.to_numeric(best["spearman_rho"], errors="coerce")
            best["defasagem_meses"] = pd.to_numeric(best["defasagem_meses"], errors="coerce")
            best = best.dropna(subset=["spearman_rho","defasagem_meses"]).sort_values("spearman_rho")
            best["Indicador"] = best["variavel_explicativa"].map(nome_amigavel)
            fig = px.bar(best, x="spearman_rho", y="Indicador", orientation="h", color="spearman_rho", color_continuous_scale=["#B85C4A","#F7F5EA","#347653"], range_color=[-1,1], text=best.apply(lambda r:f"ρ={r.spearman_rho:.3f} · lag {int(r.defasagem_meses)}m",axis=1), labels={"spearman_rho":"Spearman ρ","Indicador":"Indicador"})
            fig.update_traces(textposition="outside",cliponaxis=False)
            fig.add_vline(x=0,line_color="#111",line_dash="dash")
            fig.update_layout(title=None,coloraxis_showscale=False,margin=dict(l=20,r=125,t=20,b=35))
            st.plotly_chart(preparar_figura(fig,max(430,42*len(best))),use_container_width=True,key="corr_best_lag_chart")
        else: st.info("O arquivo de melhores defasagens não contém as colunas esperadas.")
    with tabs_corr[3]:
        lag = carregar_csv_flexivel("08_correlacoes_defasagens_0_6_meses.csv")
        titulo_secao("Correlação por defasagem (0 a 6 meses)", "Heatmap com os valores reais de correlação. Selecione o tipo de correlação para comparar os indicadores ao longo dos lags.")
        if not lag.empty and {"variavel_explicativa","defasagem_meses"}.issubset(lag.columns):
            metric_col = st.radio("Correlação", [c for c in ["spearman_rho","pearson_r"] if c in lag.columns], horizontal=True, format_func=lambda c:"Spearman" if c=="spearman_rho" else "Pearson")
            lag["defasagem_meses"] = pd.to_numeric(lag["defasagem_meses"],errors="coerce")
            lag[metric_col] = pd.to_numeric(lag[metric_col],errors="coerce")
            pivot = lag.pivot_table(index="variavel_explicativa",columns="defasagem_meses",values=metric_col,aggfunc="mean")
            pivot = pivot.reindex(columns=range(7))
            pivot.index = [nome_amigavel(i) for i in pivot.index]
            fig = px.imshow(pivot, text_auto=".3f", aspect="auto", zmin=-1,zmax=1,color_continuous_scale=["#B85C4A","#F7F5EA","#347653"],labels={"x":"Defasagem (meses)","y":"Indicador","color":"Correlação"})
            fig.update_layout(title=None,margin=dict(l=20,r=20,t=20,b=30))
            st.plotly_chart(preparar_figura(fig,460),use_container_width=True,key="corr_lag_heatmap")
        else: st.info("Arquivo de correlações por defasagem não encontrado ou sem colunas esperadas.")

# ====================== SINAIS DE ATENÇÃO ======================
elif pagina == "⚠️ Sinais de Atenção":
    st.markdown('<div class="page-title">Sinais de Atenção</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Indicadores exploratórios para acompanhar condições de mercado — não constituem recomendação comercial.</div>', unsafe_allow_html=True)

    resumo = carregar_csv_flexivel("10_resumo_sinais.csv")
    if not resumo.empty:
        r = resumo.iloc[0]
        st.caption(f"Validação original: {r.get('periodo_teste_inicio', '—')} a {r.get('periodo_teste_fim', '—')} · {int(pd.to_numeric(r.get('meses_teste', 0), errors='coerce') or 0)} meses. O resumo refere-se ao teste completo.")
        kpi_specs = [("Sinais identificados", "quantidade_sinais", "{:.0f}"), ("Meses sem sinal", "meses_sem_sinal", "{:.0f}"), ("Cobertura do teste", "cobertura_pct", "{:.1f}%"), ("Acerto entre os sinais", "taxa_acerto_sinais_pct", "{:.1f}%")]
        cols = st.columns(4)
        for col, (label, key, fmt) in zip(cols, kpi_specs):
            val = pd.to_numeric(pd.Series([r.get(key)]), errors="coerce").iloc[0]
            with col:
                st.metric(label, "—" if pd.isna(val) else fmt.format(val))
        st.caption(f"Dos {int(r.get('quantidade_sinais', 0))} sinais emitidos, {int(r.get('numero_acertos', 0))} coincidiram com a direção observada. Foram {int(r.get('sinais_alta', 0))} sinais de alta e {int(r.get('sinais_baixa', 0))} de baixa.")
    else:
        st.warning("O resumo dos sinais não foi encontrado.")

    st.markdown("---")
    regras = carregar_csv_flexivel("10_regras_sinais_atencao.csv")
    titulo_secao("Regras utilizadas", "Indicadores, defasagens e limites de referência estimados no conjunto de treinamento.")
    if not regras.empty:
        regras_exibir = regras.rename(columns={"indicador":"Indicador", "lag_meses":"Defasagem (meses)", "rho_spearman_treino":"Spearman no treino", "p_fdr_bh":"p-valor ajustado (FDR)", "sentido_relacao":"Sentido da relação", "q25_treino":"Limite inferior (Q25)", "q75_treino":"Limite superior (Q75)", "voto_acima_q75":"Voto acima do Q75", "voto_abaixo_q25":"Voto abaixo do Q25"}).copy()
        if "Indicador" in regras_exibir:
            regras_exibir["Indicador"] = regras_exibir["Indicador"].map(nome_amigavel)
        colunas = [c for c in ["Indicador", "Defasagem (meses)", "Spearman no treino", "p-valor ajustado (FDR)", "Sentido da relação", "Limite inferior (Q25)", "Limite superior (Q75)", "Voto acima do Q75", "Voto abaixo do Q25"] if c in regras_exibir.columns]
        st.dataframe(regras_exibir[colunas], use_container_width=True, hide_index=True)
    else:
        st.info("Arquivo de regras não encontrado.")

    st.markdown("---")
    sinais = carregar_csv_flexivel("10_sinais_atencao_mensais.csv")
    titulo_secao("Evolução mensal dos sinais", "A série abaixo respeita o período selecionado na barra lateral.")
    sinais_filtrados, col_data_sinais = filtrar_periodo(sinais, start_date, end_date)
    if not sinais_filtrados.empty and col_data_sinais:
        if "pontuacao" in sinais_filtrados.columns:
            sinais_filtrados["pontuacao"] = pd.to_numeric(sinais_filtrados["pontuacao"], errors="coerce")
            fig_sinais = px.bar(sinais_filtrados, x=col_data_sinais, y="pontuacao", color="sinal", color_discrete_map={"alta":"#4C805B", "baixa":"#C47762", "sem sinal":"#AAB4AC"}, labels={col_data_sinais:"Mês", "pontuacao":"Pontuação", "sinal":"Classificação"})
            fig_sinais.add_hline(y=0, line_color="#333", line_dash="dash")
            fig_sinais.update_layout(title=None, legend_title=None)
            st.plotly_chart(preparar_figura(fig_sinais, 390), use_container_width=True, key="signals_monthly_timeline")
        cols_detail = [c for c in [col_data_sinais, "sinal", "pontuacao", "direcao_real", "acerto_sinal"] if c in sinais_filtrados.columns]
        st.dataframe(sinais_filtrados[cols_detail], use_container_width=True, hide_index=True)
    else:
        st.info("Não há registros de sinais no intervalo selecionado.")
    st.markdown('<div class="note-box">A taxa de acerto é calculada somente entre os meses em que houve emissão de sinal. A cobertura indica a proporção do período de teste em que o mecanismo emitiu algum sinal. O mecanismo é experimental e não deve ser usado isoladamente para decisões comerciais.</div>', unsafe_allow_html=True)

# =========================== RIDGE =============================
elif pagina == "🤖 Modelagem Ridge":
    st.markdown('<div class="page-title">Modelagem Ridge</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Métricas, coeficientes estimados e comparação de previsões no conjunto de teste.</div>', unsafe_allow_html=True)
    metrics = carregar_csv_flexivel("10_metricas_modelagem.csv")
    coefficients = carregar_csv_flexivel("10_coeficientes_ridge.csv")
    predictions = carregar_csv_flexivel("10_previsoes_teste_2020_2025.csv")
    st.info("As métricas resumem o conjunto de teste completo (jan/2020 a dez/2025; 72 observações). O filtro de período altera apenas o gráfico de previsões, não recalcula as métricas.")
    titulo_secao("Desempenho no conjunto de teste", "Escolha um modelo. As métricas de preço (R$ por saca) e de variação mensal (pontos percentuais) são apresentadas separadamente.")
    if not metrics.empty and "modelo" in metrics.columns:
        model_names = metrics["modelo"].dropna().astype(str).tolist()
        selected_model = st.selectbox("Modelo", model_names, index=(model_names.index("Ridge") if "Ridge" in model_names else 0))
        row = metrics[metrics["modelo"].astype(str)==selected_model].iloc[0]
        st.markdown("**Estimativa do preço (R$/saca de 60 kg)**")
        price_metrics = [("mae_preco", "MAE"), ("rmse_preco", "RMSE"), ("mape_preco_pct", "MAPE")]
        price_cards = st.columns(3)
        for col, (key, label) in zip(price_cards, price_metrics):
            val = pd.to_numeric(pd.Series([row.get(key)]), errors="coerce").iloc[0]
            with col:
                st.metric(label, "—" if pd.isna(val) else (f"{val:.2f}%" if key == "mape_preco_pct" else f"R$ {val:.2f}"))
        st.markdown("**Desempenho na variação mensal e direção**")
        variation_metrics = [("mae_variacao_pct_pontos", "MAE variação (p.p.)"), ("rmse_variacao_pct_pontos", "RMSE variação (p.p.)"), ("r2_variacao", "R² variação"), ("acuracia_direcao", "Acurácia direcional"), ("acuracia_balanceada_direcao", "Acurácia balanceada")]
        var_cards = st.columns(5)
        for col, (key, label) in zip(var_cards, variation_metrics):
            val = pd.to_numeric(pd.Series([row.get(key)]), errors="coerce").iloc[0]
            with col:
                shown = "—" if pd.isna(val) else (f"{val:.1%}" if "acuracia" in key else f"{val:.3f}")
                st.metric(label, shown)
        if selected_model == "Ridge":
            alpha = pd.to_numeric(pd.Series([row.get("alpha_ridge")]), errors="coerce").iloc[0]
            st.caption(f"Alpha selecionado na validação temporal: {alpha:g}" if pd.notna(alpha) else "Alpha Ridge não informado.")
    else: st.info("Arquivo de métricas não encontrado ou vazio.")
    st.markdown("---")
    titulo_secao("Coeficientes estimados pelo Ridge", "Magnitude e direção dos coeficientes padronizados. Valores positivos e negativos indicam direções distintas no modelo.")
    if not coefficients.empty and "coeficiente_padronizado_ridge" in coefficients.columns:
        cplot=coefficients.copy()
        cplot["coeficiente_padronizado_ridge"]=pd.to_numeric(cplot["coeficiente_padronizado_ridge"],errors="coerce")
        cplot=cplot.dropna(subset=["coeficiente_padronizado_ridge"])
        cplot["Indicador"] = cplot.apply(lambda r:f"{nome_amigavel(r.get('indicador',''))} · lag {int(r.get('lag_meses',0))}m",axis=1)
        cplot=cplot.sort_values("coeficiente_padronizado_ridge")
        figc=px.bar(cplot,x="coeficiente_padronizado_ridge",y="Indicador",orientation="h",color="coeficiente_padronizado_ridge",color_continuous_scale=["#B85C4A","#F7F5EA","#347653"],text=cplot["coeficiente_padronizado_ridge"].map(lambda v:f"{v:+.3f}"),labels={"coeficiente_padronizado_ridge":"Coeficiente padronizado","Indicador":"Indicador"})
        figc.update_traces(textposition="outside",cliponaxis=False)
        figc.add_vline(x=0,line_color="#111",line_dash="dash")
        figc.update_layout(title=None,coloraxis_showscale=False,margin=dict(l=20,r=70,t=20,b=30))
        st.plotly_chart(preparar_figura(figc,430),use_container_width=True,key="ridge_coefficients_chart")
    else: st.info("Arquivo de coeficientes Ridge ausente ou sem coluna de coeficiente.")
    st.markdown("---")
    titulo_secao("Valores observados e estimados", "Comparação entre preço observado e séries de previsão no período de teste.")
    predictions_filtered, prediction_date = filtrar_periodo(predictions, start_date, end_date)
    if not predictions_filtered.empty:
        expected = ["preco_observado", "preco_previsto_baseline", "preco_previsto_linear", "preco_previsto_ridge"]
        cols = [c for c in expected if c in predictions_filtered.columns]
        if prediction_date and cols:
            long = predictions_filtered[[prediction_date] + cols].melt(id_vars=prediction_date, var_name="Modelo", value_name="Preço")
            long["Modelo"] = long["Modelo"].map(nome_amigavel)
            figp = px.line(long, x=prediction_date, y="Preço", color="Modelo", labels={prediction_date:"Período", "Preço":"Preço"})
            figp.update_traces(line=dict(width=2.4)); figp.update_layout(title="Preço observado e previsões")
            st.plotly_chart(preparar_figura(figp, 420), use_container_width=True)
        else: grafico(predictions_filtered, "Séries de previsão", altura=400, chave="ridge_predictions")
    else: st.info("Arquivo de previsões não encontrado ou sem registros no período selecionado.")

# ---------------------------- FOOTER ----------------------------
st.markdown("---")
st.markdown('<div class="footer-line">AGRODATA PR · Monitoramento e Ciência de Dados no Agronegócio · Estágio Supervisionado · UNICENTRO · 2026</div>', unsafe_allow_html=True)
