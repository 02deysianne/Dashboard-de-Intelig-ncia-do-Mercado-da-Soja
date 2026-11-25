# ============================================================
# AGRODATA PR
# Análise de Indicadores de Mercado e Defasagens Temporais
# para Monitoramento do Preço da Soja no Paraná
# ============================================================

from pathlib import Path
import json
import re
import unicodedata
import math

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ============================================================
# 1. CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="AgroData PR | Mercado da Soja",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

PASTA_APP = Path(__file__).resolve().parent
PASTAS_RESULTADOS = [
    PASTA_APP / "resultados",
    PASTA_APP / "resultados" / "tabelas",
    PASTA_APP
]

CORES = {
    "verde": "#16845B",
    "verde_claro": "#DDF3E9",
    "azul": "#2878B5",
    "azul_escuro": "#17466D",
    "laranja": "#E69B35",
    "vermelho": "#D9534F",
    "roxo": "#8064A2",
    "cinza": "#6B7280"
}

TEMA_GRAFICO = "plotly_white"


# ============================================================
# 2. ESTILO
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #F5F8F7;
    }

    section[data-testid="stSidebar"] {
        background-color: #153F35;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] [data-baseweb="select"] {
        color: #202020 !important;
        background-color: white !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #202020 !important;
    }

    h1, h2, h3 {
        color: #174D3B;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #E2EAE6;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    .subtitulo {
        color: #64748B;
        font-size: 15px;
        margin-top: -10px;
    }

    .caixa-info {
        background-color: #EAF4EF;
        border-left: 5px solid #16845B;
        padding: 14px;
        border-radius: 7px;
        margin: 10px 0 20px 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. FUNÇÕES DE NORMALIZAÇÃO E LEITURA
# ============================================================

def normalizar_coluna(nome):
    """Padroniza nomes de colunas, removendo acentos e espaços."""

    nome = str(nome).strip().lower()

    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(
        caractere for caractere in nome
        if not unicodedata.combining(caractere)
    )

    nome = re.sub(r"[^a-z0-9]+", "_", nome)
    nome = re.sub(r"_+", "_", nome)

    return nome.strip("_")


def converter_valor_numerico(valor):
    """Converte valores numéricos com vírgula decimal ou símbolos."""

    if pd.isna(valor):
        return np.nan

    if isinstance(valor, (int, float, np.number)):
        return float(valor)

    texto = str(valor).strip()

    if texto.lower() in ["", "nan", "none", "-", "—", "null"]:
        return np.nan

    texto = texto.replace("R$", "")
    texto = texto.replace("US$", "")
    texto = texto.replace("$", "")
    texto = texto.replace("%", "")
    texto = texto.replace(" ", "")

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")

    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except (ValueError, TypeError):
        return np.nan


def ler_csv(caminho):
    """Lê CSV tentando diferentes codificações e separadores."""

    separadores = [",", ";", "\t", None]
    codificacoes = ["utf-8-sig", "latin1", "cp1252"]

    melhor_df = None
    melhor_pontuacao = -1

    for codificacao in codificacoes:
        for separador in separadores:
            try:
                df = pd.read_csv(
                    caminho,
                    sep=separador,
                    encoding=codificacao,
                    engine="python",
                    on_bad_lines="skip"
                )

                if df.empty:
                    continue

                df.columns = [
                    normalizar_coluna(coluna)
                    for coluna in df.columns
                ]

                pontuacao = len(df.columns)

                if pontuacao > melhor_pontuacao:
                    melhor_df = df.copy()
                    melhor_pontuacao = pontuacao

            except Exception:
                continue

    if melhor_df is None:
        return pd.DataFrame()

    # Converte colunas que aparentam ser numéricas.
    for coluna in melhor_df.columns:
        if melhor_df[coluna].dtype == "object":
            convertida = melhor_df[coluna].apply(
                converter_valor_numerico
            )

            proporcao = convertida.notna().mean()

            if proporcao >= 0.60:
                melhor_df[coluna] = convertida

    return melhor_df


def localizar_arquivo(nome):
    """Procura um arquivo nas pastas de resultados."""

    for pasta in PASTAS_RESULTADOS:
        caminho = pasta / nome

        if caminho.exists():
            return caminho

    return None


def carregar_resultado(nome):
    """Carrega CSV ou Parquet, priorizando Parquet."""

    nome_base = Path(nome).stem

    parquet = localizar_arquivo(nome_base + ".parquet")
    csv = localizar_arquivo(nome_base + ".csv")

    try:
        if parquet:
            return pd.read_parquet(parquet)

        if csv:
            return ler_csv(csv)

    except Exception as erro:
        st.warning(f"Não foi possível carregar {nome}: {erro}")

    return pd.DataFrame()


def carregar_metadata():
    caminho = localizar_arquivo("metadata_dashboard.json")

    if caminho is None:
        return {}

    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception:
        return {}


def encontrar_coluna(df, alternativas):
    """Encontra uma coluna a partir de uma lista de nomes possíveis."""

    if df.empty:
        return None

    colunas = list(df.columns)

    for alternativa in alternativas:
        nome = normalizar_coluna(alternativa)

        if nome in colunas:
            return nome

    for coluna in colunas:
        for alternativa in alternativas:
            nome = normalizar_coluna(alternativa)

            if nome in coluna:
                return coluna

    return None


def normalizar_data(df):
    """Identifica e converte a coluna de data."""

    if df.empty:
        return df

    coluna_data = encontrar_coluna(
        df,
        [
            "data", "date", "periodo", "mes", "month",
            "data_referencia", "data_referencia_mes",
            "mes_referencia", "ano_mes"
        ]
    )

    if coluna_data is None:
        return df

    df = df.copy()

    datas = pd.to_datetime(
        df[coluna_data],
        errors="coerce",
        dayfirst=True
    )

    # Trata datas no formato YYYYMM.
    if datas.notna().sum() == 0:
        texto = df[coluna_data].astype(str).str.replace(
            r"\.0$", "", regex=True
        )

        datas = pd.to_datetime(
            texto,
            format="%Y%m",
            errors="coerce"
        )

    # Trata datas no formato YYYY-MM.
    if datas.notna().sum() == 0:
        datas = pd.to_datetime(
            df[coluna_data].astype(str) + "-01",
            errors="coerce"
        )

    df["data"] = datas

    return df.dropna(subset=["data"]).sort_values("data")


def filtrar_periodo(df, inicio, fim):
    if df.empty or "data" not in df.columns:
        return df

    return df[
        (df["data"] >= pd.Timestamp(inicio))
        & (df["data"] <= pd.Timestamp(fim))
    ].copy()


def colunas_numericas(df, excluir=None):
    if df.empty:
        return []

    excluir = excluir or []

    return [
        coluna for coluna in df.select_dtypes(include=np.number).columns
        if coluna not in excluir
    ]


def nome_legivel(nome):
    return str(nome).replace("_", " ").strip().title()


def formatar_numero(valor, casas=2):
    if pd.isna(valor):
        return "—"

    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mostrar_metricas(df, coluna):
    if df.empty or coluna not in df.columns:
        st.info("Não há dados suficientes para calcular os indicadores.")
        return

    serie = pd.to_numeric(df[coluna], errors="coerce").dropna()

    if serie.empty:
        st.info("A coluna selecionada não possui valores numéricos.")
        return

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Valor mais recente", formatar_numero(serie.iloc[-1]))
    c2.metric("Média", formatar_numero(serie.mean()))
    c3.metric("Mínimo", formatar_numero(serie.min()))
    c4.metric("Máximo", formatar_numero(serie.max()))


def mostrar_grafico(fig, altura=430):
    fig.update_layout(
        template=TEMA_GRAFICO,
        height=altura,
        margin=dict(l=20, r=20, t=65, b=35),
        hovermode="x unified",
        legend_title_text="Indicadores"
    )

    st.plotly_chart(fig, use_container_width=True)


def baixar_csv(df, nome_arquivo, chave):
    if df.empty:
        return

    arquivo = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="⬇️ Baixar dados deste gráfico",
        data=arquivo,
        file_name=nome_arquivo,
        mime="text/csv",
        key=chave
    )


def aviso_sem_dados(nome):
    st.info(
        f"Não foram encontrados dados suficientes para apresentar "
        f"o gráfico de {nome}. Verifique se o arquivo correspondente "
        f"está na pasta `resultados`."
    )


# ============================================================
# 4. CARREGAMENTO DAS BASES
# ============================================================

@st.cache_data
def carregar_bases():
    dados = carregar_resultado("dados_consolidados_dashboard")

    if dados.empty:
        dados = carregar_resultado("dados_consolidados")

    dados = normalizar_data(dados)

    deral = carregar_resultado("deral_preco_soja_pr")

    # Trata DERAL no formato mensal longitudinal.
    if not deral.empty:
        deral = normalizar_data(deral)

        coluna_preco = encontrar_coluna(
            deral,
            [
                "preco_soja_pr", "preco_soja", "preco",
                "valor", "valor_sc", "preco_sc_60kg"
            ]
        )

        if coluna_preco and coluna_preco != "preco_soja_pr":
            deral = deral.rename(
                columns={coluna_preco: "preco_soja_pr"}
            )

        # Trata DERAL no formato original: ANO + JAN...DEZ.
        if "data" not in deral.columns:
            coluna_ano = encontrar_coluna(
                deral, ["ano", "year"]
            )

            meses = {
                "jan": 1, "janeiro": 1,
                "fev": 2, "fevereiro": 2,
                "mar": 3, "marco": 3,
                "abr": 4, "abril": 4,
                "mai": 5, "maio": 5,
                "jun": 6, "junho": 6,
                "jul": 7, "julho": 7,
                "ago": 8, "agosto": 8,
                "set": 9, "setembro": 9,
                "out": 10, "outubro": 10,
                "nov": 11, "novembro": 11,
                "dez": 12, "dezembro": 12
            }

            if coluna_ano:
                colunas_meses = {
                    coluna: meses[coluna]
                    for coluna in deral.columns
                    if coluna in meses
                }

                if colunas_meses:
                    deral[coluna_ano] = pd.to_numeric(
                        deral[coluna_ano], errors="coerce"
                    )

                    deral = deral.dropna(subset=[coluna_ano])

                    deral_longo = deral.melt(
                        id_vars=[coluna_ano],
                        value_vars=list(colunas_meses.keys()),
                        var_name="mes",
                        value_name="preco_soja_pr"
                    )

                    deral_longo["numero_mes"] = (
                        deral_longo["mes"].map(colunas_meses)
                    )

                    deral_longo["data"] = pd.to_datetime(
                        dict(
                            year=deral_longo[coluna_ano].astype(int),
                            month=deral_longo["numero_mes"],
                            day=1
                        ),
                        errors="coerce"
                    )

                    deral_longo["preco_soja_pr"] = (
                        deral_longo["preco_soja_pr"].apply(
                            converter_valor_numerico
                        )
                    )

                    deral = deral_longo[
                        ["data", "preco_soja_pr"]
                    ].dropna()

    arquivos = {
        "estatisticas": "07_estatisticas_descritivas_niveis",
        "sazonalidade": "07_sazonalidade_mensal",
        "variacoes": "07_estatisticas_variacoes_mensais",
        "correlacoes_niveis": "08_correlacoes_niveis",
        "correlacoes_variacoes": "08_correlacoes_variacoes_mensais",
        "melhores_lags": "08_melhores_defasagens_spearman",
        "lags": "08_correlacoes_defasagens_0_6_meses",
        "resumo_sinais": "10_resumo_sinais",
        "regras_sinais": "10_regras_sinais_atencao",
        "sinais": "10_sinais_atencao_mensais",
        "metricas_modelagem": "10_metricas_modelagem",
        "coeficientes": "10_coeficientes_ridge",
        "previsoes": "10_previsoes_teste_2020_2025"
    }

    resultados = {
        chave: normalizar_data(carregar_resultado(arquivo))
        for chave, arquivo in arquivos.items()
    }

    return dados, deral, resultados, carregar_metadata()


df, df_deral, resultados, metadata = carregar_bases()


# ============================================================
# 5. IDENTIFICAÇÃO DAS COLUNAS PRINCIPAIS
# ============================================================

COLUNAS_INDICADORES = {
    "Preço da soja internacional": [
        "soja_internacional_usd_t", "soja_usd_t",
        "preco_soja_usd_t", "soja_internacional"
    ],
    "Petróleo Brent": [
        "brent_usd_barril", "brent", "petroleo_brent",
        "preco_brent"
    ],
    "Câmbio dólar/real": [
        "cambio_usd_brl", "usd_brl", "dolar",
        "taxa_cambio", "cambio"
    ],
    "Índice de fertilizantes": [
        "fertilizantes_indice", "indice_fertilizantes",
        "fertilizantes", "fertilizer_index"
    ]
}

COLUNAS_PRECO_REAL = [
    "preco_soja_real", "preco_soja_pr_real",
    "preco_real", "preco_corrigido_ipca",
    "preco_soja_corrigido_ipca"
]

COLUNAS_PRECO_NOMINAL = [
    "preco_soja_pr", "preco_soja", "preco_nominal",
    "preco_soja_nominal", "preco"
]

coluna_preco_real = encontrar_coluna(df, COLUNAS_PRECO_REAL)
coluna_preco_nominal = encontrar_coluna(df, COLUNAS_PRECO_NOMINAL)

colunas_indicadores_encontradas = {}

for nome, alternativas in COLUNAS_INDICADORES.items():
    coluna = encontrar_coluna(df, alternativas)

    if coluna:
        colunas_indicadores_encontradas[nome] = coluna


# ============================================================
# 6. MENU LATERAL
# ============================================================

st.sidebar.markdown("# 🌱 AgroData PR")
st.sidebar.caption("Monitoramento do mercado da soja no Paraná")

pagina = st.sidebar.radio(
    "Navegação",
    [
        "📊 Visão Geral",
        "🔎 Análise Exploratória",
        "🔗 Correlações e Defasagens",
        "🚦 Sinais de Atenção",
        "🤖 Modelagem e Validação"
    ]
)

st.sidebar.divider()

if not df.empty and "data" in df.columns:
    data_min = df["data"].min().date()
    data_max = df["data"].max().date()

    periodo = st.sidebar.date_input(
        "Período de análise",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max
    )

    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
    else:
        inicio, fim = data_min, data_max

    df_periodo = filtrar_periodo(df, inicio, fim)

else:
    inicio, fim = None, None
    df_periodo = df.copy()

st.sidebar.divider()
st.sidebar.caption("Projeto de estágio curricular")


# ============================================================
# 7. FUNÇÕES DE GRÁFICOS
# ============================================================

def grafico_serie_temporal(base, coluna, titulo, eixo_y=None):
    if base.empty or coluna not in base.columns or "data" not in base.columns:
        aviso_sem_dados(titulo)
        return

    dados = base[["data", coluna]].copy()
    dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")
    dados = dados.dropna()

    if dados.empty:
        aviso_sem_dados(titulo)
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dados["data"],
        y=dados[coluna],
        mode="lines",
        name=nome_legivel(coluna),
        line=dict(color=CORES["verde"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(22,132,91,0.08)"
    ))

    fig.update_layout(
        title=titulo,
        xaxis_title="Período",
        yaxis_title=eixo_y or nome_legivel(coluna)
    )

    mostrar_grafico(fig)


def grafico_comparacao_indicadores(base, colunas):
    disponiveis = [
        coluna for coluna in colunas
        if coluna in base.columns
    ]

    if base.empty or not disponiveis or "data" not in base.columns:
        aviso_sem_dados("comparação dos indicadores")
        return

    dados = base[["data"] + disponiveis].copy()

    # Índice 100 para permitir comparação de escalas diferentes.
    normalizados = []

    for coluna in disponiveis:
        serie = pd.to_numeric(dados[coluna], errors="coerce")
        primeiro = serie.dropna().iloc[0] if serie.notna().any() else np.nan

        if pd.notna(primeiro) and primeiro != 0:
            dados[coluna + "_indice"] = (serie / primeiro) * 100
            normalizados.append(coluna + "_indice")

    if not normalizados:
        aviso_sem_dados("comparação dos indicadores")
        return

    longo = dados.melt(
        id_vars="data",
        value_vars=normalizados,
        var_name="indicador",
        value_name="indice"
    )

    longo["indicador"] = (
        longo["indicador"]
        .str.replace("_indice", "", regex=False)
        .map(nome_legivel)
    )

    fig = px.line(
        longo,
        x="data",
        y="indice",
        color="indicador",
        title="Evolução comparativa dos indicadores — índice base 100"
    )

    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="gray",
        annotation_text="Base 100"
    )

    fig.update_yaxes(title="Índice (base 100)")
    fig.update_xaxes(title="Período")

    mostrar_grafico(fig)


def grafico_distribuicao(base, coluna, titulo):
    if base.empty or coluna not in base.columns:
        aviso_sem_dados(titulo)
        return

    valores = pd.to_numeric(base[coluna], errors="coerce").dropna()

    if valores.empty:
        aviso_sem_dados(titulo)
        return

    fig = px.histogram(
        x=valores,
        nbins=30,
        marginal="box",
        title=titulo,
        labels={"x": nome_legivel(coluna), "y": "Frequência"}
    )

    mostrar_grafico(fig)


def grafico_boxplot(base, coluna, titulo):
    if base.empty or coluna not in base.columns:
        aviso_sem_dados(titulo)
        return

    valores = pd.to_numeric(base[coluna], errors="coerce").dropna()

    if valores.empty:
        aviso_sem_dados(titulo)
        return

    fig = px.box(
        y=valores,
        points="outliers",
        title=titulo,
        labels={"y": nome_legivel(coluna)}
    )

    mostrar_grafico(fig)


def grafico_matriz_correlacao(base, colunas, titulo):
    disponiveis = [
        coluna for coluna in colunas
        if coluna in base.columns
    ]

    if len(disponiveis) < 2:
        aviso_sem_dados(titulo)
        return

    dados = base[disponiveis].apply(
        pd.to_numeric, errors="coerce"
    )

    matriz = dados.corr(method="spearman")

    fig = px.imshow(
        matriz,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu",
        origin="lower",
        title=titulo,
        labels=dict(
            x="Indicadores",
            y="Indicadores",
            color="Correlação"
        )
    )

    mostrar_grafico(fig, altura=550)


def grafico_colunas(df_base, coluna_x, coluna_y, titulo, eixo_y=None):
    if df_base.empty:
        aviso_sem_dados(titulo)
        return

    if coluna_x not in df_base.columns or coluna_y not in df_base.columns:
        aviso_sem_dados(titulo)
        return

    dados = df_base.copy()
    dados[coluna_y] = pd.to_numeric(
        dados[coluna_y], errors="coerce"
    )
    dados = dados.dropna(subset=[coluna_y])

    if dados.empty:
        aviso_sem_dados(titulo)
        return

    fig = px.bar(
        dados,
        x=coluna_x,
        y=coluna_y,
        title=titulo,
        labels={
            coluna_x: nome_legivel(coluna_x),
            coluna_y: eixo_y or nome_legivel(coluna_y)
        },
        text_auto=".2f"
    )

    mostrar_grafico(fig)


# ============================================================
# 8. CABEÇALHO
# ============================================================

st.title("🌱 Monitoramento do Mercado da Soja — Paraná")

st.markdown(
    '<p class="subtitulo">Análise de indicadores de mercado, '
    'comportamento dos preços, correlações, defasagens temporais '
    'e sinais de atenção.</p>',
    unsafe_allow_html=True
)

if df.empty:
    st.warning(
        "A base principal não foi localizada ou não pôde ser lida. "
        "Verifique os arquivos na pasta `resultados`."
    )


# ============================================================
# 9. VISÃO GERAL
# ============================================================

if pagina == "📊 Visão Geral":

    st.header("Visão Geral do Mercado")

    st.markdown(
        "Acompanhe a evolução do preço da soja no Paraná e observe "
        "como os principais indicadores de mercado se comportaram "
        "ao longo do período selecionado."
    )

    preco_escolhido = None

    opcoes_preco = {}

    if coluna_preco_nominal:
        opcoes_preco["Preço nominal"] = coluna_preco_nominal

    if coluna_preco_real:
        opcoes_preco["Preço corrigido pelo IPCA"] = coluna_preco_real

    if opcoes_preco:
        escolha = st.radio(
            "Tipo de preço apresentado",
            list(opcoes_preco.keys()),
            horizontal=True
        )

        preco_escolhido = opcoes_preco[escolha]

        if escolha == "Preço corrigido pelo IPCA":
            st.caption(
                "Valores apresentados conforme a série real disponível "
                "na base. Confira a documentação da base para identificar "
                "o mês de referência utilizado na correção."
            )
        else:
            st.caption(
                "Preço nominal: valores sem correção monetária pelo IPCA."
            )

    if preco_escolhido:
        mostrar_metricas(df_periodo, preco_escolhido)

        grafico_serie_temporal(
            df_periodo,
            preco_escolhido,
            "Evolução do preço da soja no Paraná",
            "Preço por saca (conforme unidade da base)"
        )

        baixar_csv(
            df_periodo[["data", preco_escolhido]].dropna(),
            "preco_soja_periodo.csv",
            "download_preco_geral"
        )

    elif not df_deral.empty and "preco_soja_pr" in df_deral.columns:
        deral_periodo = filtrar_periodo(df_deral, inicio, fim)

        mostrar_metricas(deral_periodo, "preco_soja_pr")

        grafico_serie_temporal(
            deral_periodo,
            "preco_soja_pr",
            "Evolução do preço da soja no Paraná — DERAL"
        )

    else:
        aviso_sem_dados("preço da soja")

    st.divider()
    st.subheader("Comparação dos indicadores de mercado")

    colunas_comparacao = list(colunas_indicadores_encontradas.values())

    if preco_escolhido:
        colunas_comparacao = [preco_escolhido] + colunas_comparacao

    grafico_comparacao_indicadores(
        df_periodo,
        colunas_comparacao
    )

    st.divider()
    st.subheader("Comportamento mensal do preço")

    sazonalidade = resultados["sazonalidade"]

    if not sazonalidade.empty:
        coluna_mes = encontrar_coluna(
            sazonalidade, ["mes", "mes_numero", "mes_nome"]
        )

        coluna_media = encontrar_coluna(
            sazonalidade,
            ["media", "preco_medio", "media_preco", "media_mensal"]
        )

        if coluna_mes and coluna_media:
            grafico_colunas(
                sazonalidade,
                coluna_mes,
                coluna_media,
                "Sazonalidade mensal do preço da soja",
                "Preço médio"
            )
        else:
            st.info(
                "O arquivo de sazonalidade foi encontrado, mas suas "
                "colunas não foram identificadas automaticamente."
            )
    else:
        aviso_sem_dados("sazonalidade mensal")

    st.markdown("""
    <div class="caixa-info">
    <b>Como interpretar:</b> a evolução do preço mostra a trajetória
    histórica da soja. A comparação em índice base 100 permite observar
    se os indicadores cresceram ou diminuíram proporcionalmente,
    mesmo quando possuem unidades de medida diferentes.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 10. ANÁLISE EXPLORATÓRIA
# ============================================================

elif pagina == "🔎 Análise Exploratória":

    st.header("Análise Exploratória dos Dados")

    st.markdown(
        "Explore a distribuição dos valores, a variação mensal, "
        "a sazonalidade e a presença de observações extremas."
    )

    opcoes = {}

    for nome, coluna in colunas_indicadores_encontradas.items():
        opcoes[nome] = coluna

    if coluna_preco_nominal:
        opcoes["Preço da soja nominal"] = coluna_preco_nominal

    if coluna_preco_real:
        opcoes["Preço da soja corrigido pelo IPCA"] = coluna_preco_real

    if not opcoes:
        st.warning("Não foram identificadas colunas numéricas para análise.")
    else:
        indicador_nome = st.selectbox(
            "Selecione o indicador para explorar",
            list(opcoes.keys())
        )

        indicador = opcoes[indicador_nome]

        st.subheader(f"Comportamento de {indicador_nome}")

        grafico_serie_temporal(
            df_periodo,
            indicador,
            f"Evolução temporal — {indicador_nome}"
        )

        c1, c2 = st.columns(2)

        with c1:
            grafico_distribuicao(
                df_periodo,
                indicador,
                f"Distribuição dos valores — {indicador_nome}"
            )

        with c2:
            grafico_boxplot(
                df_periodo,
                indicador,
                f"Dispersão e possíveis valores extremos — {indicador_nome}"
            )

        st.divider()
        st.subheader("Estatísticas descritivas")

        estatisticas = resultados["estatisticas"]

        if not estatisticas.empty:
            coluna_indicador = encontrar_coluna(
                estatisticas,
                ["indicador", "variavel", "serie", "nome"]
            )

            coluna_media = encontrar_coluna(
                estatisticas, ["media", "mean"]
            )

            coluna_mediana = encontrar_coluna(
                estatisticas, ["mediana", "median"]
            )

            coluna_desvio = encontrar_coluna(
                estatisticas,
                ["desvio_padrao", "desvio", "std"]
            )

            coluna_cv = encontrar_coluna(
                estatisticas,
                ["cv", "coeficiente_variacao"]
            )

            if coluna_indicador:
                linha = estatisticas[
                    estatisticas[coluna_indicador].astype(str)
                    .str.contains(
                        normalizar_coluna(indicador),
                        case=False,
                        na=False
                    )
                ]

                if linha.empty:
                    linha = estatisticas[
                        estatisticas[coluna_indicador].astype(str)
                        .str.contains(
                            indicador_nome.split()[0],
                            case=False,
                            na=False
                        )
                    ]

                if not linha.empty:
                    linha = linha.iloc[0]

                    metricas = [
                        ("Média", coluna_media),
                        ("Mediana", coluna_mediana),
                        ("Desvio padrão", coluna_desvio),
                        ("Coeficiente de variação", coluna_cv)
                    ]

                    colunas_metricas = st.columns(4)

                    for i, (rotulo, coluna) in enumerate(metricas):
                        if coluna:
                            valor = converter_valor_numerico(linha[coluna])
                            colunas_metricas[i].metric(
                                rotulo,
                                formatar_numero(valor)
                            )
                else:
                    st.info(
                        "Não foi encontrada uma linha correspondente "
                        "ao indicador selecionado no arquivo estatístico."
                    )
            else:
                st.info(
                    "O arquivo de estatísticas não possui uma coluna "
                    "de identificação reconhecida."
                )
        else:
            aviso_sem_dados("estatísticas descritivas")

    st.divider()
    st.subheader("Variações mensais")

    variacoes = resultados["variacoes"]

    if not variacoes.empty:
        coluna_indicador_var = encontrar_coluna(
            variacoes, ["indicador", "variavel", "serie", "nome"]
        )

        coluna_variacao = encontrar_coluna(
            variacoes,
            [
                "variacao_percentual", "variacao_pct",
                "variacao_mensal_pct", "variacao"
            ]
        )

        if coluna_variacao:
            if coluna_indicador_var:
                indicador_var = st.selectbox(
                    "Indicador das variações",
                    sorted(
                        variacoes[coluna_indicador_var]
                        .dropna().astype(str).unique()
                    ),
                    key="indicador_variacoes"
                )

                dados_var = variacoes[
                    variacoes[coluna_indicador_var].astype(str)
                    == indicador_var
                ].copy()
            else:
                dados_var = variacoes.copy()

            coluna_data_var = encontrar_coluna(
                dados_var, ["data", "periodo", "mes"]
            )

            if coluna_data_var:
                dados_var = normalizar_data(dados_var)

                if "data" in dados_var.columns:
                    fig = px.bar(
                        dados_var,
                        x="data",
                        y=coluna_variacao,
                        title="Variação percentual mensal",
                        labels={
                            "data": "Período",
                            coluna_variacao: "Variação (%)"
                        }
                    )

                    fig.add_hline(y=0, line_dash="dash")
                    mostrar_grafico(fig)
                else:
                    aviso_sem_dados("variações mensais")
            else:
                grafico_colunas(
                    dados_var,
                    dados_var.columns[0],
                    coluna_variacao,
                    "Variação mensal"
                )
        else:
            aviso_sem_dados("variações mensais")
    else:
        aviso_sem_dados("variações mensais")

    st.markdown("""
    <div class="caixa-info">
    <b>Interpretação:</b> a média representa o comportamento central
    dos valores; a mediana reduz a influência de observações extremas;
    o desvio padrão indica dispersão; e o coeficiente de variação
    permite avaliar a variabilidade relativa da série.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 11. CORRELAÇÕES E DEFASAGENS
# ============================================================

elif pagina == "🔗 Correlações e Defasagens":

    st.header("Correlações e Defasagens Temporais")

    st.markdown(
        "Esta seção investiga a relação entre o preço da soja e os "
        "indicadores de mercado, incluindo a possibilidade de que "
        "determinados movimentos ocorram antes de alterações no preço."
    )

    base_corr = resultados["correlacoes_niveis"]

    st.subheader("Correlação entre os indicadores")

    if not base_corr.empty:
        coluna_indicador = encontrar_coluna(
            base_corr, ["indicador", "variavel", "serie", "nome"]
        )

        coluna_corr = encontrar_coluna(
            base_corr,
            ["spearman", "correlacao_spearman", "correlacao", "rho"]
        )

        if coluna_indicador and coluna_corr:
            dados_corr = base_corr.copy()
            dados_corr[coluna_corr] = pd.to_numeric(
                dados_corr[coluna_corr], errors="coerce"
            )
            dados_corr = dados_corr.dropna(subset=[coluna_corr])

            fig = px.bar(
                dados_corr.sort_values(coluna_corr),
                x=coluna_corr,
                y=coluna_indicador,
                orientation="h",
                color=coluna_corr,
                color_continuous_scale="RdBu",
                range_color=[-1, 1],
                title="Força e direção da correlação de Spearman",
                labels={
                    coluna_corr: "Correlação de Spearman",
                    coluna_indicador: "Indicador"
                },
                text_auto=".2f"
            )

            fig.add_vline(x=0, line_dash="dash", line_color="black")
            fig.add_vline(x=0.5, line_dash="dot", line_color="gray")
            fig.add_vline(x=-0.5, line_dash="dot", line_color="gray")

            mostrar_grafico(fig)
        else:
            # Quando o arquivo já estiver em formato de matriz.
            colunas = colunas_numericas(base_corr)

            if len(colunas) >= 2:
                grafico_matriz_correlacao(
                    base_corr,
                    colunas,
                    "Matriz de correlação"
                )
            else:
                aviso_sem_dados("correlações")
    else:
        # Calcula uma matriz exploratória diretamente da base.
        colunas = list(colunas_indicadores_encontradas.values())

        if coluna_preco_nominal:
            colunas.insert(0, coluna_preco_nominal)

        grafico_matriz_correlacao(
            df_periodo,
            colunas,
            "Matriz exploratória de correlação de Spearman"
        )

    st.divider()
    st.subheader("Correlação das variações mensais")

    base_variacoes_corr = resultados["correlacoes_variacoes"]

    if not base_variacoes_corr.empty:
        coluna_indicador = encontrar_coluna(
            base_variacoes_corr,
            ["indicador", "variavel", "serie", "nome"]
        )

        coluna_corr = encontrar_coluna(
            base_variacoes_corr,
            ["spearman", "correlacao_spearman", "correlacao", "rho"]
        )

        if coluna_indicador and coluna_corr:
            grafico_colunas(
                base_variacoes_corr,
                coluna_indicador,
                coluna_corr,
                "Correlação entre as variações mensais"
            )
        else:
            st.info(
                "Não foi possível identificar automaticamente "
                "as colunas do arquivo de correlações das variações."
            )
    else:
        aviso_sem_dados("correlações das variações")

    st.divider()
    st.subheader("Análise das defasagens de 0 a 6 meses")

    base_lags = resultados["lags"]

    if not base_lags.empty:
        coluna_lag = encontrar_coluna(
            base_lags, ["lag", "defasagem", "meses", "defasagem_meses"]
        )

        coluna_corr = encontrar_coluna(
            base_lags,
            ["spearman", "correlacao_spearman", "correlacao", "rho"]
        )

        coluna_indicador = encontrar_coluna(
            base_lags,
            ["indicador", "variavel", "serie", "nome"]
        )

        if coluna_lag and coluna_corr:
            base_plot = base_lags.copy()
            base_plot[coluna_lag] = pd.to_numeric(
                base_plot[coluna_lag], errors="coerce"
            )
            base_plot[coluna_corr] = pd.to_numeric(
                base_plot[coluna_corr], errors="coerce"
            )
            base_plot = base_plot.dropna(
                subset=[coluna_lag, coluna_corr]
            )

            if coluna_indicador:
                opcoes_lag = sorted(
                    base_plot[coluna_indicador]
                    .dropna().astype(str).unique()
                )

                escolhido = st.selectbox(
                    "Indicador para visualizar as defasagens",
                    opcoes_lag
                )

                base_plot = base_plot[
                    base_plot[coluna_indicador].astype(str) == escolhido
                ]

            fig = px.line(
                base_plot.sort_values(coluna_lag),
                x=coluna_lag,
                y=coluna_corr,
                markers=True,
                title="Correlação por defasagem temporal",
                labels={
                    coluna_lag: "Defasagem (meses)",
                    coluna_corr: "Correlação de Spearman"
                }
            )

            fig.update_traces(
                line=dict(color=CORES["azul"], width=3),
                marker=dict(size=10)
            )

            fig.add_hline(y=0, line_dash="dash")
            fig.update_xaxes(dtick=1)

            mostrar_grafico(fig)
        else:
            aviso_sem_dados("defasagens")
    else:
        aviso_sem_dados("defasagens de 0 a 6 meses")

    st.divider()
    st.subheader("Melhores defasagens identificadas")

    melhores = resultados["melhores_lags"]

    if not melhores.empty:
        coluna_indicador = encontrar_coluna(
            melhores, ["indicador", "variavel", "serie", "nome"]
        )

        coluna_lag = encontrar_coluna(
            melhores,
            ["melhor_lag", "lag", "defasagem", "defasagem_meses"]
        )

        coluna_corr = encontrar_coluna(
            melhores,
            ["spearman", "correlacao_spearman", "correlacao", "rho"]
        )

        if coluna_indicador and coluna_lag:
            fig = px.bar(
                melhores,
                x=coluna_indicador,
                y=coluna_lag,
                color=coluna_corr if coluna_corr else coluna_lag,
                text=coluna_lag,
                title="Defasagem com melhor resultado por indicador",
                labels={
                    coluna_indicador: "Indicador",
                    coluna_lag: "Melhor defasagem (meses)"
                }
            )

            mostrar_grafico(fig)
        else:
            aviso_sem_dados("melhores defasagens")
    else:
        aviso_sem_dados("melhores defasagens")

    st.markdown("""
    <div class="caixa-info">
    <b>Como interpretar as defasagens:</b> uma defasagem de zero mês
    representa uma relação no mesmo período. Uma defasagem positiva
    indica que o indicador foi deslocado em relação ao preço da soja,
    conforme a convenção utilizada no processamento. A interpretação
    final deve considerar a definição de lag adotada nos notebooks.
    <br><br>
    <b>Importante:</b> correlação indica associação estatística,
    não comprova causalidade nem garante capacidade de previsão.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 12. SINAIS DE ATENÇÃO
# ============================================================

elif pagina == "🚦 Sinais de Atenção":

    st.header("Sinais de Atenção do Mercado")

    st.markdown(
        "Visualize os indicadores classificados como sinais de atenção, "
        "as regras estatísticas utilizadas e o comportamento dos sinais "
        "ao longo do tempo."
    )

    resumo = resultados["resumo_sinais"]
    regras = resultados["regras_sinais"]
    sinais = resultados["sinais"]

    st.subheader("Resumo dos sinais")

    if not resumo.empty:
        coluna_tipo = encontrar_coluna(
            resumo,
            ["sinal", "tipo_sinal", "classificacao", "categoria", "status"]
        )

        coluna_quantidade = encontrar_coluna(
            resumo,
            ["quantidade", "total", "frequencia", "contagem", "n"]
        )

        if coluna_tipo and coluna_quantidade:
            resumo[coluna_quantidade] = pd.to_numeric(
                resumo[coluna_quantidade], errors="coerce"
            )

            fig = px.pie(
                resumo.dropna(subset=[coluna_quantidade]),
                names=coluna_tipo,
                values=coluna_quantidade,
                hole=0.45,
                title="Distribuição dos sinais identificados"
            )

            mostrar_grafico(fig)
        else:
            st.info(
                "O arquivo de resumo foi encontrado, mas não foi possível "
                "identificar suas colunas de categoria e quantidade."
            )
    else:
        aviso_sem_dados("resumo dos sinais")

    st.divider()
    st.subheader("Regras estatísticas dos sinais")

    if not regras.empty:
        coluna_indicador = encontrar_coluna(
            regras, ["indicador", "variavel", "serie", "nome"]
        )

        coluna_lag = encontrar_coluna(
            regras, ["lag", "defasagem", "melhor_lag"]
        )

        coluna_corr = encontrar_coluna(
            regras,
            ["spearman", "rho", "correlacao", "correlacao_spearman"]
        )

        coluna_p = encontrar_coluna(
            regras,
            ["p_ajustado", "p_valor_ajustado", "pvalue_ajustado",
             "p_valor_fdr", "p_fdr", "p_valor"]
        )

        if coluna_indicador and coluna_lag:
            regras_plot = regras.copy()
            regras_plot[coluna_lag] = pd.to_numeric(
                regras_plot[coluna_lag], errors="coerce"
            )

            fig = px.bar(
                regras_plot,
                x=coluna_indicador,
                y=coluna_lag,
                color=coluna_corr if coluna_corr else coluna_lag,
                text=coluna_lag,
                title="Defasagem utilizada nas regras por indicador",
                labels={
                    coluna_indicador: "Indicador",
                    coluna_lag: "Defasagem (meses)"
                }
            )

            mostrar_grafico(fig)

        if coluna_corr:
            regras_plot = regras.copy()
            regras_plot[coluna_corr] = pd.to_numeric(
                regras_plot[coluna_corr], errors="coerce"
            )

            if coluna_indicador:
                fig = px.bar(
                    regras_plot,
                    x=coluna_corr,
                    y=coluna_indicador,
                    orientation="h",
                    color=coluna_corr,
                    color_continuous_scale="RdBu",
                    range_color=[-1, 1],
                    title="Intensidade e direção da associação",
                    labels={
                        coluna_corr: "Correlação de Spearman",
                        coluna_indicador: "Indicador"
                    }
                )

                fig.add_vline(x=0, line_dash="dash")
                mostrar_grafico(fig)

        if coluna_p:
            regras_plot = regras.copy()
            regras_plot[coluna_p] = pd.to_numeric(
                regras_plot[coluna_p], errors="coerce"
            )

            regras_plot = regras_plot[
                regras_plot[coluna_p] > 0
            ].copy()

            if not regras_plot.empty:
                regras_plot["-log10(p)"] = regras_plot[coluna_p].apply(
                    lambda valor: -math.log10(valor)
                    if valor > 0 else np.nan
                )

                eixo = coluna_indicador or regras_plot.columns[0]

                fig = px.bar(
                    regras_plot,
                    x=eixo,
                    y="-log10(p)",
                    title="Evidência estatística após ajuste de significância",
                    labels={
                        eixo: "Indicador",
                        "-log10(p)": "Força da evidência estatística"
                    }
                )

                fig.add_hline(
                    y=-math.log10(0.05),
                    line_dash="dash",
                    line_color=CORES["vermelho"],
                    annotation_text="Referência p = 0,05"
                )

                mostrar_grafico(fig)

    else:
        aviso_sem_dados("regras dos sinais")

    st.divider()
    st.subheader("Evolução dos sinais ao longo do tempo")

    if not sinais.empty:
        sinais = normalizar_data(sinais)

        coluna_tipo = encontrar_coluna(
            sinais,
            ["sinal", "tipo_sinal", "classificacao", "categoria", "status"]
        )

        coluna_indicador = encontrar_coluna(
            sinais, ["indicador", "variavel", "serie", "nome"]
        )

        coluna_score = encontrar_coluna(
            sinais,
            ["score", "pontuacao", "intensidade", "valor_sinal"]
        )

        if "data" in sinais.columns:
            sinais_plot = filtrar_periodo(sinais, inicio, fim)

            if coluna_tipo:
                contagem = (
                    sinais_plot.groupby(
                        ["data", coluna_tipo]
                    ).size().reset_index(name="quantidade")
                )

                fig = px.bar(
                    contagem,
                    x="data",
                    y="quantidade",
                    color=coluna_tipo,
                    title="Quantidade de sinais por período",
                    labels={
                        "data": "Período",
                        "quantidade": "Quantidade de sinais"
                    }
                )

                mostrar_grafico(fig)

            if coluna_indicador:
                contagem_indicador = (
                    sinais_plot.groupby(coluna_indicador)
                    .size().reset_index(name="quantidade")
                    .sort_values("quantidade", ascending=True)
                )

                fig = px.bar(
                    contagem_indicador,
                    x="quantidade",
                    y=coluna_indicador,
                    orientation="h",
                    title="Indicadores com maior frequência de sinais",
                    labels={
                        "quantidade": "Quantidade de ocorrências",
                        coluna_indicador: "Indicador"
                    },
                    text="quantidade"
                )

                mostrar_grafico(fig)

            if coluna_score:
                sinais_plot[coluna_score] = pd.to_numeric(
                    sinais_plot[coluna_score], errors="coerce"
                )

                fig = px.scatter(
                    sinais_plot,
                    x="data",
                    y=coluna_score,
                    color=coluna_tipo if coluna_tipo else None,
                    hover_data=[coluna_indicador]
                    if coluna_indicador else None,
                    title="Intensidade dos sinais ao longo do tempo",
                    labels={
                        "data": "Período",
                        coluna_score: "Intensidade"
                    }
                )

                mostrar_grafico(fig)

        else:
            st.info(
                "O arquivo de sinais foi localizado, mas não foi "
                "reconhecida uma coluna de data."
            )

        # Comparação com o preço DERAL, quando as datas coincidirem.
        if (
            not df_deral.empty
            and "data" in df_deral.columns
            and "preco_soja_pr" in df_deral.columns
            and "data" in sinais.columns
        ):
            st.subheader("Sinais em relação ao preço observado")

            preco = df_deral[["data", "preco_soja_pr"]].copy()
            preco["preco_soja_pr"] = pd.to_numeric(
                preco["preco_soja_pr"], errors="coerce"
            )

            sinais_data = sinais.copy()

            if coluna_score:
                sinais_data[coluna_score] = pd.to_numeric(
                    sinais_data[coluna_score], errors="coerce"
                )

                sinais_agrupados = (
                    sinais_data.groupby("data")[coluna_score]
                    .mean().reset_index()
                )

                comparacao = preco.merge(
                    sinais_agrupados,
                    on="data",
                    how="inner"
                )

                if not comparacao.empty:
                    fig = make_subplots(specs=[[{"secondary_y": True}]])

                    fig.add_trace(
                        go.Scatter(
                            x=comparacao["data"],
                            y=comparacao["preco_soja_pr"],
                            mode="lines",
                            name="Preço da soja — DERAL",
                            line=dict(color=CORES["verde"], width=2.5)
                        ),
                        secondary_y=False
                    )

                    fig.add_trace(
                        go.Bar(
                            x=comparacao["data"],
                            y=comparacao[coluna_score],
                            name="Intensidade média dos sinais",
                            opacity=0.35,
                            marker_color=CORES["laranja"]
                        ),
                        secondary_y=True
                    )

                    fig.update_layout(
                        title="Preço observado e intensidade dos sinais"
                    )

                    fig.update_yaxes(
                        title_text="Preço da soja",
                        secondary_y=False
                    )

                    fig.update_yaxes(
                        title_text="Intensidade dos sinais",
                        secondary_y=True
                    )

                    mostrar_grafico(fig)

    else:
        aviso_sem_dados("sinais mensais")

    st.markdown("""
    <div class="caixa-info">
    <b>Interpretação:</b> os sinais de atenção funcionam como mecanismos
    de monitoramento de condições identificadas nas séries históricas.
    Eles não representam previsões garantidas de alta ou queda do preço.
    A leitura deve considerar a intensidade, a frequência, a defasagem
    e a evidência estatística de cada indicador.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 13. MODELAGEM E VALIDAÇÃO
# ============================================================

elif pagina == "🤖 Modelagem e Validação":

    st.header("Modelagem e Validação")

    st.markdown(
        "Apresente os resultados da modelagem Ridge, os indicadores "
        "de desempenho, os coeficientes estimados e a comparação entre "
        "os valores observados e estimados no conjunto de teste."
    )

    metricas = resultados["metricas_modelagem"]
    coeficientes = resultados["coeficientes"]
    previsoes = resultados["previsoes"]

    st.subheader("Desempenho da modelagem")

    if not metricas.empty:
        coluna_metrica = encontrar_coluna(
            metricas,
            ["metrica", "indicador", "nome", "medida"]
        )

        coluna_valor = encontrar_coluna(
            metricas,
            ["valor", "resultado", "score", "metrica_valor"]
        )

        if coluna_metrica and coluna_valor:
            metricas_plot = metricas.copy()
            metricas_plot[coluna_valor] = pd.to_numeric(
                metricas_plot[coluna_valor], errors="coerce"
            )

            metricas_plot = metricas_plot.dropna(
                subset=[coluna_valor]
            )

            if not metricas_plot.empty:
                fig = px.bar(
                    metricas_plot,
                    x=coluna_metrica,
                    y=coluna_valor,
                    color=coluna_metrica,
                    text_auto=".3f",
                    title="Métricas de desempenho do modelo Ridge",
                    labels={
                        coluna_metrica: "Métrica",
                        coluna_valor: "Valor"
                    }
                )

                mostrar_grafico(fig)

                colunas_metricas = st.columns(
                    min(4, len(metricas_plot))
                )

                for i, (_, linha) in enumerate(
                    metricas_plot.head(4).iterrows()
                ):
                    colunas_metricas[i].metric(
                        str(linha[coluna_metrica]),
                        formatar_numero(linha[coluna_valor], 4)
                    )
        else:
            st.info(
                "Não foi possível identificar as colunas de métrica "
                "e valor no arquivo de modelagem."
            )
    else:
        aviso_sem_dados("métricas da modelagem")

    st.divider()
    st.subheader("Importância dos coeficientes")

    if not coeficientes.empty:
        coluna_variavel = encontrar_coluna(
            coeficientes,
            ["variavel", "indicador", "feature", "nome", "variavel_modelo"]
        )

        coluna_coef = encontrar_coluna(
            coeficientes,
            ["coeficiente", "coef", "valor", "peso"]
        )

        if coluna_variavel and coluna_coef:
            coef_plot = coeficientes.copy()
            coef_plot[coluna_coef] = pd.to_numeric(
                coef_plot[coluna_coef], errors="coerce"
            )

            coef_plot = coef_plot.dropna(subset=[coluna_coef])
            coef_plot = coef_plot.sort_values(coluna_coef)

            fig = px.bar(
                coef_plot,
                x=coluna_coef,
                y=coluna_variavel,
                orientation="h",
                color=coluna_coef,
                color_continuous_scale="RdBu",
                title="Coeficientes estimados pelo modelo Ridge",
                labels={
                    coluna_coef: "Coeficiente",
                    coluna_variavel: "Indicador"
                },
                text_auto=".4f"
            )

            fig.add_vline(x=0, line_dash="dash", line_color="black")

            mostrar_grafico(fig)
        else:
            aviso_sem_dados("coeficientes Ridge")
    else:
        aviso_sem_dados("coeficientes Ridge")

    st.divider()
    st.subheader("Valores observados e estimados")

    if not previsoes.empty:
        previsoes = normalizar_data(previsoes)

        coluna_real = encontrar_coluna(
            previsoes,
            [
                "valor_real", "preco_real", "observado",
                "y_real", "preco_observado", "real"
            ]
        )

        coluna_previsto = encontrar_coluna(
            previsoes,
            [
                "valor_previsto", "previsao", "previsto",
                "y_previsto", "preco_previsto", "predito"
            ]
        )

        if coluna_real and coluna_previsto:
            previsoes[coluna_real] = pd.to_numeric(
                previsoes[coluna_real], errors="coerce"
            )

            previsoes[coluna_previsto] = pd.to_numeric(
                previsoes[coluna_previsto], errors="coerce"
            )

            previsoes_plot = previsoes.dropna(
                subset=[coluna_real, coluna_previsto]
            ).copy()

            if "data" in previsoes_plot.columns:
                previsoes_plot = previsoes_plot.sort_values("data")

                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=previsoes_plot["data"],
                    y=previsoes_plot[coluna_real],
                    mode="lines",
                    name="Preço observado",
                    line=dict(color=CORES["azul"], width=2.5)
                ))

                fig.add_trace(go.Scatter(
                    x=previsoes_plot["data"],
                    y=previsoes_plot[coluna_previsto],
                    mode="lines",
                    name="Preço estimado",
                    line=dict(
                        color=CORES["laranja"],
                        width=2.5,
                        dash="dash"
                    )
                ))

                fig.update_layout(
                    title="Comparação entre valores observados e estimados",
                    xaxis_title="Período",
                    yaxis_title="Preço da soja"
                )

                mostrar_grafico(fig)

            else:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=list(range(len(previsoes_plot))),
                    y=previsoes_plot[coluna_real],
                    mode="lines+markers",
                    name="Observado"
                ))

                fig.add_trace(go.Scatter(
                    x=list(range(len(previsoes_plot))),
                    y=previsoes_plot[coluna_previsto],
                    mode="lines+markers",
                    name="Estimado"
                ))

                fig.update_layout(
                    title="Valores observados e estimados no conjunto de teste",
                    xaxis_title="Observações do conjunto de teste",
                    yaxis_title="Preço da soja"
                )

                mostrar_grafico(fig)

            # Gráfico dos erros de previsão.
            previsoes_plot["erro"] = (
                previsoes_plot[coluna_real]
                - previsoes_plot[coluna_previsto]
            )

            eixo_x = (
                previsoes_plot["data"]
                if "data" in previsoes_plot.columns
                else list(range(len(previsoes_plot)))
            )

            fig = px.bar(
                x=eixo_x,
                y=previsoes_plot["erro"],
                title="Erro entre o valor observado e o estimado",
                labels={
                    "x": "Período ou observação",
                    "y": "Erro (observado − estimado)"
                }
            )

            fig.add_hline(y=0, line_dash="dash", line_color="black")
            mostrar_grafico(fig)

            # Dispersão observado x estimado.
            fig = px.scatter(
                previsoes_plot,
                x=coluna_real,
                y=coluna_previsto,
                title="Relação entre valores observados e estimados",
                labels={
                    coluna_real: "Valor observado",
                    coluna_previsto: "Valor estimado"
                },
                trendline="ols"
            )

            minimo = min(
                previsoes_plot[coluna_real].min(),
                previsoes_plot[coluna_previsto].min()
            )

            maximo = max(
                previsoes_plot[coluna_real].max(),
                previsoes_plot[coluna_previsto].max()
            )

            fig.add_trace(go.Scatter(
                x=[minimo, maximo],
                y=[minimo, maximo],
                mode="lines",
                name="Referência ideal",
                line=dict(color="gray", dash="dash")
            ))

            mostrar_grafico(fig)

        else:
            st.info(
                "O arquivo de previsões foi encontrado, mas as colunas "
                "de valores observados e estimados não foram identificadas."
            )
    else:
        aviso_sem_dados("previsões do conjunto de teste")

    st.markdown("""
    <div class="caixa-info">
    <b>Como interpretar:</b> os coeficientes Ridge indicam a contribuição
    estimada de cada variável dentro do modelo ajustado, considerando
    a escala e o tratamento utilizados. A comparação entre valores
    observados e estimados permite avaliar visualmente o comportamento
    do modelo no conjunto de teste. As métricas devem ser interpretadas
    em conjunto, e não isoladamente.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 14. RODAPÉ E DIAGNÓSTICO
# ============================================================

st.divider()

with st.expander("Informações sobre os dados carregados"):

    arquivos_verificados = [
        "dados_consolidados_dashboard.csv / .parquet",
        "deral_preco_soja_pr.csv",
        "07_estatisticas_descritivas_niveis.csv",
        "07_sazonalidade_mensal.csv",
        "07_estatisticas_variacoes_mensais.csv",
        "08_correlacoes_niveis.csv",
        "08_correlacoes_variacoes_mensais.csv",
        "08_melhores_defasagens_spearman.csv",
        "08_correlacoes_defasagens_0_6_meses.csv",
        "10_resumo_sinais.csv",
        "10_regras_sinais_atencao.csv",
        "10_sinais_atencao_mensais.csv",
        "10_metricas_modelagem.csv",
        "10_coeficientes_ridge.csv",
        "10_previsoes_teste_2020_2025.csv"
    ]

    st.write("**Status da base principal:**")

    if df.empty:
        st.error("Base principal não carregada.")
    else:
        st.success(
            f"Base principal carregada: {len(df):,} registros "
            f"e {len(df.columns)} colunas."
        )

        if "data" in df.columns:
            st.write(
                f"Período disponível: {df['data'].min():%m/%Y} "
                f"até {df['data'].max():%m/%Y}."
            )

    st.write("**Arquivos de resultados:**")

    for arquivo in arquivos_verificados:
        nome = Path(arquivo).stem

        if nome == "dados_consolidados_dashboard":
            carregado = not df.empty
        elif nome == "deral_preco_soja_pr":
            carregado = not df_deral.empty
        else:
            chave = {
                "07_estatisticas_descritivas_niveis": "estatisticas",
                "07_sazonalidade_mensal": "sazonalidade",
                "07_estatisticas_variacoes_mensais": "variacoes",
                "08_correlacoes_niveis": "correlacoes_niveis",
                "08_correlacoes_variacoes_mensais": "correlacoes_variacoes",
                "08_melhores_defasagens_spearman": "melhores_lags",
                "08_correlacoes_defasagens_0_6_meses": "lags",
                "10_resumo_sinais": "resumo_sinais",
                "10_regras_sinais_atencao": "regras_sinais",
                "10_sinais_atencao_mensais": "sinais",
                "10_metricas_modelagem": "metricas_modelagem",
                "10_coeficientes_ridge": "coeficientes",
                "10_previsoes_teste_2020_2025": "previsoes"
            }.get(nome)

            carregado = (
                chave is not None
                and not resultados[chave].empty
            )

        if carregado:
            st.write(f"✅ {arquivo}")
        else:
            st.write(f"⚠️ {arquivo} — não localizado ou vazio")

    st.caption(
        "Os gráficos são construídos a partir dos arquivos processados "
        "disponíveis na pasta resultados. A ausência de um arquivo ou "
        "de uma coluna necessária pode impedir a exibição do gráfico "
        "correspondente."
    )

st.caption(
    "AgroData PR | Projeto de análise de indicadores de mercado "
    "e monitoramento do preço da soja no Paraná."
)
