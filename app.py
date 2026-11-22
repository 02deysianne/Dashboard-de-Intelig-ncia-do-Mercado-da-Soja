# ============================================================
# AGRODATA PR | Dashboard de monitoramento e análise da soja
# Versão integrada e aprimorada - Streamlit + Plotly
# ============================================================
import os
import json
import re
import unicodedata
from pathlib import Path

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
section[data-testid="stSidebar"] * {color:#000000 !important;}
section[data-testid="stSidebar"] [data-testid="stDateInput"] input {
 color:#203128 !important; background:white !important; -webkit-text-fill-color:#203128 !important;
}
.brand {font-size:25px;font-weight:800;letter-spacing:-.8px;color:white;}
.brand-sub,.side-caption {color:#C8D9CD !important;font-size:11px;line-height:1.5;}
.eyebrow {color:#47745A;text-transform:uppercase;font-weight:800;letter-spacing:1.5px;font-size:10px;margin-bottom:6px;}
.page-title {font-weight:800;color:#183C30;letter-spacing:-.7px;font-size:30px;margin:0;}
.page-subtitle {color:#718078;font-size:13px;margin:4px 0 16px;}
.hero {background:linear-gradient(115deg,#173D32 0%,#286247 68%,#477D55 100%);border-radius:16px;padding:21px 24px;color:white;margin:2px 0 18px;}
.hero-kicker {color:#D5E6D8;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;font-weight:800;}
.hero-title {color:white;font-size:24px;font-weight:800;margin:6px 0;}
.hero-text {color:#E0ECE2;font-size:12px;max-width:800px;}
.kpi-card {background:white;border:1px solid #E5EBE5;border-radius:13px;padding:14px 16px;min-height:95px;box-shadow:0 3px 12px rgba(28,55,39,.035);}
.kpi-label {color:#7B8980;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;}
.kpi-value {color:#193F31;font-size:23px;font-weight:800;margin-top:7px;line-height:1.15;}
.kpi-note {color:#849087;font-size:10px;margin-top:4px;}
.section-heading {color:#214635;font-size:17px;font-weight:800;margin:7px 0 2px;}
.section-caption {color:#7B8980;font-size:11px;margin-bottom:10px;}
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
            convertido = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if convertido.notna().any():
                out = df.copy(); out[col] = convertido
                return out, col
    return df, None


# ----------------------------- LEITURA --------------------------
ROOTS = [Path("resultados/tabelas"), Path("resultados"), Path(".")]

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
            df = pd.read_csv(path, sep=sep, engine="python")
            if df.shape[1] > 1 or sep is not None: return df
        except Exception: pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def carregar_dados_principais():
    for nome in ["dados_consolidados_dashboard.parquet", "dados_consolidados_dashboard.csv"]:
        path = localizar_arquivo(nome)
        if not path: continue
        try:
            if path.suffix.lower() == ".parquet": return pd.read_parquet(path)
            for sep in [None, ",", ";", "\t"]:
                try:
                    df = pd.read_csv(path, sep=sep, engine="python")
                    if not df.empty: return df
                except Exception: pass
        except Exception: pass
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
    path = localizar_arquivo("deral_preco_soja_pr.csv")
    if not path: return pd.DataFrame()
    try:
        df = pd.read_csv(path, sep=None, engine="python")
        if "data" in df.columns: df["data"] = pd.to_datetime(df["data"], errors="coerce", dayfirst=True)
        if "preco_soja_pr" in df.columns: df["preco_soja_pr"] = pd.to_numeric(df["preco_soja_pr"], errors="coerce")
        if {"data", "preco_soja_pr"}.issubset(df.columns):
            return df.dropna(subset=["data", "preco_soja_pr"]).sort_values("data")
    except Exception: pass
    return pd.DataFrame()

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
        font=dict(family="DM Sans", size=11, color="#526158"),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        hoverlabel=dict(bgcolor="white", font_size=11), showlegend=True,
    )
    fig.update_xaxes(showgrid=False, linecolor="#E5EBE5", tickfont=dict(color="#78867D"))
    fig.update_yaxes(gridcolor="#EDF1ED", zeroline=False, tickfont=dict(color="#78867D"))
    return fig

def titulo_secao(titulo, descricao=None):
    st.markdown(f'<div class="section-heading">{titulo}</div>', unsafe_allow_html=True)
    if descricao: st.markdown(f'<div class="section-caption">{descricao}</div>', unsafe_allow_html=True)

def grafico(df, titulo, altura=360, chave=None, tipo="auto"):
    if df is None or df.empty:
        st.info(f"Não há dados disponíveis para: {titulo}."); return
    data, col_data = normalizar_data(df.copy())
    data = data.dropna(axis=1, how="all")
    numericas = data.select_dtypes(include="number").columns.tolist()
    categoricas = [c for c in data.columns if c not in numericas and c != col_data]
    # Matriz de correlação (coluna inicial categórica com nomes de variáveis)
    if tipo == "heatmap" or (tipo == "auto" and len(numericas) >= 2 and len(data) == len(numericas) and categoricas):
        try:
            categ = categoricas[0]
            mat = data.set_index(categ)[numericas]
            if mat.shape[0] and mat.shape[1]:
                fig = px.imshow(mat, text_auto=".2f", aspect="auto", color_continuous_scale=["#B85C4A", "#F7F5EA", "#347653"], labels={"color":"Correlação"})
                fig.update_layout(title=titulo)
                st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
        except Exception: pass
    if col_data and numericas:
        long = data[[col_data]+numericas].melt(id_vars=col_data, var_name="Indicador", value_name="Valor")
        long["Indicador"] = long["Indicador"].map(nome_amigavel)
        fig = px.line(long, x=col_data, y="Valor", color="Indicador", labels={col_data:"Período", "Valor":"Valor", "Indicador":"Indicador"})
        fig.update_traces(line=dict(width=2.2)); fig.update_layout(title=titulo)
        st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
    if numericas and categoricas:
        categoria = categoricas[0]
        if len(numericas) == 1:
            y = numericas[0]; plot = data[[categoria, y]].copy()
            plot[categoria] = plot[categoria].astype(str); plot[y] = pd.to_numeric(plot[y], errors="coerce")
            plot = plot.dropna(subset=[y])
            fig = px.bar(plot, x=categoria, y=y, color=categoria, labels={categoria:nome_amigavel(categoria), y:nome_amigavel(y)})
        else:
            plot = data[[categoria]+numericas].melt(id_vars=categoria, var_name="Indicador", value_name="Valor")
            plot["Indicador"] = plot["Indicador"].map(nome_amigavel)
            fig = px.bar(plot, x=categoria, y="Valor", color="Indicador", barmode="group", labels={categoria:nome_amigavel(categoria), "Valor":"Valor", "Indicador":"Indicador"})
        fig.update_layout(title=titulo)
        st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
    if numericas:
        resumo = data[numericas].mean(numeric_only=True).reset_index()
        resumo.columns = ["Indicador", "Média"]
        resumo["Indicador"] = resumo["Indicador"].map(nome_amigavel)
        fig = px.bar(resumo, x="Indicador", y="Média", color="Indicador", labels={"Indicador":"Indicador", "Média":"Média"})
        fig.update_layout(title=titulo)
        st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave); return
    coluna = data.columns[0]
    freq = data[coluna].astype(str).value_counts().head(20).reset_index()
    freq.columns = [nome_amigavel(coluna), "Quantidade"]
    fig = px.bar(freq, x=nome_amigavel(coluna), y="Quantidade", color=nome_amigavel(coluna))
    fig.update_layout(title=titulo)
    st.plotly_chart(preparar_figura(fig, altura), use_container_width=True, key=chave)

def mostrar_metricas(df, prefixo):
    if df is None or df.empty:
        st.info(f"Arquivo de métricas ({prefixo}) não encontrado ou vazio."); return
    nums = df.select_dtypes(include="number").columns.tolist()
    if not nums:
        st.dataframe(df, use_container_width=True, hide_index=True); return
    linha = df.iloc[0]
    cols = st.columns(min(len(nums), 4))
    for i, c in enumerate(nums[:4]):
        val = pd.to_numeric(pd.Series([linha[c]]), errors="coerce").iloc[0]
        with cols[i]: st.metric(nome_amigavel(c), f"{val:,.3f}" if pd.notna(val) else "—")
    if len(df) > 1 or len(nums) > 4:
        st.dataframe(df, use_container_width=True, hide_index=True)

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
            base_norm["data"] = pd.to_datetime(base_norm["data"], errors="coerce", dayfirst=True)
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
    pagina = st.radio("Seções", [" Visão Geral", " Análise Exploratória", " Correlações e Lags", " Sinais de Atenção", " Modelagem Ridge"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown('<div class="side-caption"><b>PERÍODO</b></div>', unsafe_allow_html=True)
    valid_dates = df_base[coluna_data].dropna() if coluna_data and not df_base.empty else pd.Series(dtype="datetime64[ns]")
    if len(valid_dates):
        date_min, date_max = valid_dates.min().date(), valid_dates.max().date()
    else: date_min, date_max = pd.Timestamp("2000-01-01").date(), pd.Timestamp.today().date()
    date_range = st.date_input("Intervalo", value=(date_min, date_max), min_value=date_min, max_value=date_max, format="DD/MM/YYYY")
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2: start_date, end_date = date_range
    elif isinstance(date_range, (tuple, list)) and len(date_range) == 1: start_date, end_date = date_range[0], date_max
    else: start_date, end_date = date_min, date_max
    st.markdown("---")
    st.markdown('<div class="side-caption"><b>ESTÁGIO SUPERVISIONADO</b><br>Deysianne Souza<br>Orientador: Prof. Diego B. Santi<br>UNICENTRO · 2026</div>', unsafe_allow_html=True)

if not df_base.empty and coluna_data:
    df_base = df_base[(df_base[coluna_data].dt.date >= start_date) & (df_base[coluna_data].dt.date <= end_date)]
if not df_deral.empty:
    deral_filtrado = df_deral[(df_deral["data"].dt.date >= start_date) & (df_deral["data"].dt.date <= end_date)]
else: deral_filtrado = pd.DataFrame()

st.markdown('<div class="eyebrow">PAINEL DE INTELIGÊNCIA DO AGRONEGÓCIO</div>', unsafe_allow_html=True)

# ============================ HOME =============================
if pagina == " Visão Geral":
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
        "Séries reescalonadas para base 100 no primeiro mês disponível. O índice permite comparar movimentos, não os valores absolutos."
    )
    if not df_base.empty and coluna_data:
        candidatos = {
            "Preço internacional da soja": ["soja_internacional_usd_t", "soja_internacional_usd"],
            "Câmbio": ["cambio_brl_usd", "cambio_usd_brl", "cambio", "dolar"],
            "Petróleo Brent": ["brent", "petroleo", "petróleo"],
            "Fertilizantes": ["fertilizantes", "indice_fertilizantes", "índice_fertilizantes"],
        }
        colunas_indice = []
        nomes_indice = {}
        colunas_existentes = {str(c).lower(): c for c in df_base.columns}
        for nome, aliases in candidatos.items():
            achou = next((colunas_existentes[a.lower()] for a in aliases if a.lower() in colunas_existentes), None)
            if achou and pd.api.types.is_numeric_dtype(df_base[achou]):
                colunas_indice.append(achou)
                nomes_indice[achou] = nome
        if colunas_indice:
            base_ind = df_base[[coluna_data] + colunas_indice].copy().sort_values(coluna_data)
            linhas = []
            for coluna in colunas_indice:
                serie = pd.to_numeric(base_ind[coluna], errors="coerce")
                validos = serie.dropna()
                if len(validos) >= 2 and validos.iloc[0] != 0:
                    base_ind[nomes_indice[coluna]] = (serie / validos.iloc[0]) * 100
                    linhas.append(nomes_indice[coluna])
            if linhas:
                longo_ind = base_ind[[coluna_data] + linhas].melt(
                    id_vars=coluna_data, var_name="Indicador", value_name="Índice (base 100)"
                ).dropna()
                fig_ind = px.line(
                    longo_ind, x=coluna_data, y="Índice (base 100)", color="Indicador",
                    labels={coluna_data: "Período", "Índice (base 100)": "Índice (base 100)"}
                )
                fig_ind.update_traces(line=dict(width=2.3))
                fig_ind.add_hline(y=100, line_dash="dot", line_color="#9AA69D")
                st.plotly_chart(preparar_figura(fig_ind, 350), use_container_width=True)
            else:
                st.info("Os indicadores disponíveis não possuem valores suficientes para formar índices comparáveis.")
        else:
            st.info("Não foram identificadas, na base carregada, colunas numéricas dos indicadores de mercado esperados.")
    else:
        st.info("A base consolidada com indicadores não está disponível para montar a comparação.")

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
elif pagina == " Análise Exploratória":
    st.markdown('<div class="page-title">Análise Exploratória</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Estatísticas descritivas, padrões sazonais e variações mensais.</div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Estatísticas", "Sazonalidade", "Variações"])
    file_specs = [("07_estatisticas_descritivas_niveis.csv", "Resumo estatístico das variáveis"), ("07_sazonalidade_mensal.csv", "Padrão sazonal médio por mês"), ("07_estatisticas_variacoes_mensais.csv", "Comportamento das variações mensais")]
    for tab, (file_name, description) in zip([tab1, tab2, tab3], file_specs):
        with tab:
            data = carregar_csv_flexivel(file_name)
            filtered, _ = filtrar_periodo(data, start_date, end_date)
            titulo_secao(description, f"Arquivo: {file_name}")
            if not filtered.empty: st.dataframe(filtered, use_container_width=True, hide_index=True)
            grafico(filtered, description, altura=400, chave=f"expl_{file_name}")


# ====================== CORRELAÇÕES/LAGS =======================
elif pagina == " Correlações e Lags":
    st.markdown('<div class="page-title">Correlações e Defasagens</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Relações contemporâneas e defasadas entre indicadores, incluindo defasagens de 0 a 6 meses.</div>', unsafe_allow_html=True)
    corr_files = [("08_correlacoes_niveis.csv", "Matriz de correlação entre os indicadores", "heatmap"), ("08_melhores_defasagens_spearman.csv", "Melhores defasagens — Spearman", "auto"), ("08_correlacoes_defasagens_0_6_meses.csv", "Correlações por defasagem de 0 a 6 meses", "auto")]
    for idx, (fname, heading, chart_type) in enumerate(corr_files):
        data = carregar_csv_flexivel(fname)
        titulo_secao(heading, f"Resultado da análise: {fname}")
        if not data.empty: st.dataframe(data, use_container_width=True, hide_index=True)
        grafico(data, heading, altura=390, chave=f"corr_{idx}", tipo=chart_type)
        if idx < len(corr_files)-1: st.markdown("---")

# ====================== SINAIS DE ATENÇÃO ======================
elif pagina == " Sinais de Atenção":
    st.markdown('<div class="page-title">Sinais de Atenção</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Monitoramento a partir das regras e indicadores calculados no projeto.</div>', unsafe_allow_html=True)
    signal_files = [("10_resumo_sinais.csv", "Resumo dos sinais identificados"), ("10_regras_sinais_atencao.csv", "Critérios e regras de disparo"), ("10_sinais_atencao_mensais.csv", "Evolução mensal dos sinais")]
    for idx, (fname, heading) in enumerate(signal_files):
        data = carregar_csv_flexivel(fname)
        filtered, _ = filtrar_periodo(data, start_date, end_date)
        titulo_secao(heading, f"Arquivo: {fname}")
        if not filtered.empty: st.dataframe(filtered, use_container_width=True, hide_index=True)
        grafico(filtered, heading, altura=370, chave=f"signals_{idx}")
        if idx < len(signal_files)-1: st.markdown("---")

# =========================== RIDGE =============================
elif pagina == " Modelagem Ridge":
    st.markdown('<div class="page-title">Modelagem Ridge</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Métricas, coeficientes estimados e comparação de previsões no conjunto de teste.</div>', unsafe_allow_html=True)
    metrics = carregar_csv_flexivel("10_metricas_modelagem.csv")
    coefficients = carregar_csv_flexivel("10_coeficientes_ridge.csv")
    predictions = carregar_csv_flexivel("10_previsoes_teste_2020_2025.csv")
    titulo_secao("Indicadores de desempenho", "Métricas registradas no arquivo de resultados do modelo.")
    mostrar_metricas(metrics, "modelo Ridge")
    st.markdown("---")
    titulo_secao("Coeficientes estimados pelo Ridge", "Valores dos coeficientes conforme o resultado calculado.")
    if not coefficients.empty: st.dataframe(coefficients, use_container_width=True, hide_index=True)
    grafico(coefficients, "Coeficientes do modelo Ridge", altura=380, chave="ridge_coefficients")
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
        st.dataframe(predictions_filtered, use_container_width=True, hide_index=True)
    else: st.info("Arquivo de previsões não encontrado ou sem registros no período selecionado.")

# ---------------------------- FOOTER ----------------------------
st.markdown("---")
st.markdown('<div class="footer-line">AGRODATA PR · Monitoramento e Ciência de Dados no Agronegócio · Estágio Supervisionado · UNICENTRO · 2026</div>', unsafe_allow_html=True)
