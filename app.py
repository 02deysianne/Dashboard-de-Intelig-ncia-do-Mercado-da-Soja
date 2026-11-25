from pathlib import Path
import json
import unicodedata
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURAÇÕES
# ============================================================

st.set_page_config(
    page_title="AgroData PR | Mercado da Soja",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent

PASTAS_RESULTADOS = [
    BASE_DIR / "resultados",
    BASE_DIR / "resultados" / "tabelas",
    BASE_DIR
]

CORES = {
    "verde": "#247A52",
    "verde_escuro": "#174C36",
    "verde_claro": "#DDEFE5",
    "azul": "#3976A8",
    "laranja": "#D98B32",
    "vermelho": "#C94C4C",
    "cinza": "#68746D",
    "fundo": "#F5F8F6"
}

NOMES_INDICADORES = {
    "soja_internacional_usd_t": "Soja internacional",
    "cambio_usd_brl": "Câmbio USD/BRL",
    "brent_usd_barril": "Petróleo Brent",
    "fertilizantes_indice": "Índice de fertilizantes",
    "exportacao_soja_ton": "Exportações de soja"
}


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F5F8F6;
        color: #203128;
    }

    [data-testid="stSidebar"] {
        background-color: #E8F0EB;
        border-right: 1px solid #D5E1D9;
    }

    [data-testid="stSidebar"] * {
        color: #203128 !important;
    }

    h1, h2, h3 {
        color: #174C36 !important;
    }

    p, label, span, div {
        font-family: Arial, sans-serif;
    }

    [data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #DCE7E0;
        padding: 15px;
        border-radius: 10px;
    }

    [data-testid="stMetricLabel"] {
        color: #53645A !important;
    }

    [data-testid="stMetricValue"] {
        color: #174C36 !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: #203128;
    }

    .stTabs [aria-selected="true"] {
        color: #247A52 !important;
        border-bottom-color: #247A52 !important;
    }

    .aviso {
        background-color: #EAF2ED;
        padding: 13px 16px;
        border-left: 4px solid #247A52;
        border-radius: 6px;
        margin: 10px 0;
        color: #203128;
    }

    .texto-secundario {
        color: #68746D;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_nome(nome):
    """Normaliza nomes de colunas para facilitar a identificação."""
    nome = str(nome).strip().lower()
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    nome = nome.replace(" ", "_").replace("-", "_")
    return nome


def localizar_arquivo(nome):
    """Procura um arquivo nas pastas conhecidas do projeto."""
    for pasta in PASTAS_RESULTADOS:
        caminho = pasta / nome
        if caminho.exists():
            return caminho

    return None


@st.cache_data(show_spinner=False)
def carregar_arquivo(nome):
    """Carrega CSV ou Parquet sem modificar o arquivo original."""
    caminho = localizar_arquivo(nome)

    if caminho is None:
        return pd.DataFrame()

    try:
        if caminho.suffix.lower() == ".parquet":
            df = pd.read_parquet(caminho)
        else:
            try:
                df = pd.read_csv(caminho, sep=None, engine="python")
            except Exception:
                df = pd.read_csv(caminho, encoding="latin1")

        df.columns = [str(c).strip() for c in df.columns]
        return df

    except Exception as erro:
        st.warning(f"Não foi possível carregar {nome}: {erro}")
        return pd.DataFrame()


def carregar_primeiro(nomes):
    """Carrega o primeiro arquivo existente de uma lista."""
    for nome in nomes:
        df = carregar_arquivo(nome)
        if not df.empty:
            return df

    return pd.DataFrame()


def encontrar_coluna(df, alternativas):
    """Encontra uma coluna considerando variações de nomes."""
    if df.empty:
        return None

    mapa = {
        normalizar_nome(coluna): coluna
        for coluna in df.columns
    }

    for alternativa in alternativas:
        chave = normalizar_nome(alternativa)
        if chave in mapa:
            return mapa[chave]

    return None


def converter_data(df, alternativas=None):
    """Identifica e converte a coluna de data."""
    if df.empty:
        return df

    alternativas = alternativas or [
        "data", "date", "mes", "data_referencia"
    ]

    coluna = encontrar_coluna(df, alternativas)

    if coluna:
        df = df.copy()
        df[coluna] = pd.to_datetime(
            df[coluna],
            errors="coerce"
        )
        df = df.dropna(subset=[coluna])
        df = df.sort_values(coluna)

        if coluna != "data":
            df = df.rename(columns={coluna: "data"})

    return df


def converter_numerico(df, colunas):
    """Converte as colunas indicadas para valores numéricos."""
    df = df.copy()

    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce"
            )

    return df


def formatar_numero(valor, casas=2):
    if pd.isna(valor):
        return "—"

    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor):
    if pd.isna(valor):
        return "—"

    return f"{valor:.2f}%".replace(".", ",")


def grafico_vazio(mensagem):
    st.info(mensagem)


def coluna_preco(df, tipo="nominal"):
    """Identifica a coluna de preço nominal ou real."""
    if tipo == "real":
        alternativas = [
            "preco_soja_real",
            "preco_real",
            "preco_corrigido",
            "preco_soja_pr_real",
            "preco_real_dez_2025"
        ]
    else:
        alternativas = [
            "preco_soja_pr",
            "preco_soja_nominal",
            "preco_nominal",
            "preco_deral",
            "preco"
        ]

    return encontrar_coluna(df, alternativas)


def adicionar_media_movel(df, coluna, janela=12):
    """Calcula média móvel apenas para visualização exploratória."""
    resultado = df.copy()

    if coluna in resultado.columns:
        resultado["media_movel_12"] = (
            resultado[coluna]
            .rolling(window=janela, min_periods=janela)
            .mean()
        )

    return resultado


def titulo_secao(titulo, descricao=None):
    st.subheader(titulo)

    if descricao:
        st.caption(descricao)


# ============================================================
# CARREGAMENTO DOS DADOS
# ============================================================

@st.cache_data(show_spinner="Carregando resultados do projeto...")
def carregar_dados():
    dados = carregar_primeiro([
        "dados_consolidados_dashboard.parquet",
        "dados_consolidados_dashboard.csv"
    ])

    deral = carregar_arquivo("deral_preco_soja_pr.csv")

    if deral.empty:
        deral = dados.copy()

    dados = converter_data(dados)
    deral = converter_data(deral)

    return dados, deral


dados, deral = carregar_dados()

estatisticas = carregar_arquivo(
    "07_estatisticas_descritivas_niveis.csv"
)

sazonalidade = carregar_arquivo(
    "07_sazonalidade_mensal.csv"
)

variacoes = carregar_arquivo(
    "07_estatisticas_variacoes_mensais.csv"
)

corr_niveis = carregar_arquivo(
    "08_correlacoes_niveis.csv"
)

corr_variacoes = carregar_arquivo(
    "08_correlacoes_variacoes_mensais.csv"
)

melhores_lags = carregar_arquivo(
    "08_melhores_defasagens_spearman.csv"
)

lags_0_6 = carregar_arquivo(
    "08_correlacoes_defasagens_0_6_meses.csv"
)

sinais_resumo = carregar_arquivo(
    "10_resumo_sinais.csv"
)

regras_sinais = carregar_arquivo(
    "10_regras_sinais_atencao.csv"
)

sinais_mensais = carregar_arquivo(
    "10_sinais_atencao_mensais.csv"
)

metricas_modelagem = carregar_arquivo(
    "10_metricas_modelagem.csv"
)

coeficientes = carregar_arquivo(
    "10_coeficientes_ridge.csv"
)

previsoes = carregar_arquivo(
    "10_previsoes_teste_2020_2025.csv"
)

metadata = carregar_arquivo("metadata_dashboard.json")

if dados.empty and deral.empty:
    st.error(
        "Não foram encontrados os dados do projeto. "
        "Verifique se a pasta resultados está no mesmo diretório do app.py."
    )
    st.stop()


# ============================================================
# PREPARAÇÃO DAS BASES
# ============================================================

if not dados.empty:
    dados = converter_data(dados)

    dados = converter_numerico(
        dados,
        list(NOMES_INDICADORES.keys())
    )

if not deral.empty:
    deral = converter_data(deral)

    col_preco_nominal = coluna_preco(deral, "nominal")
    col_preco_real = coluna_preco(deral, "real")

    if col_preco_nominal:
        deral[col_preco_nominal] = pd.to_numeric(
            deral[col_preco_nominal],
            errors="coerce"
        )

    if col_preco_real:
        deral[col_preco_real] = pd.to_numeric(
            deral[col_preco_real],
            errors="coerce"
        )


# ============================================================
# FILTROS GERAIS
# ============================================================

datas_disponiveis = []

for base in [dados, deral]:
    if not base.empty and "data" in base.columns:
        datas_disponiveis.extend(
            base["data"].dropna().tolist()
        )

if datas_disponiveis:
    data_minima = min(datas_disponiveis).date()
    data_maxima = max(datas_disponiveis).date()
else:
    data_minima = pd.Timestamp("2000-01-01").date()
    data_maxima = pd.Timestamp("2025-12-31").date()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("# 🌱 AgroData PR")
    st.caption("Monitoramento do mercado da soja")

    st.divider()

    pagina = st.radio(
        "Navegação",
        [
            "🏠 Visão Geral",
            "📊 Análise Exploratória",
            "🔗 Correlações e Defasagens",
            "⚠️ Sinais de Atenção",
            "🤖 Modelagem e Validação"
        ]
    )

    st.divider()

    st.markdown("### Período de visualização")

    periodo = st.date_input(
        "Selecione o intervalo",
        value=(data_minima, data_maxima),
        min_value=data_minima,
        max_value=data_maxima
    )

    if isinstance(periodo, tuple) and len(periodo) == 2:
        data_inicio, data_fim = periodo
    else:
        data_inicio = data_minima
        data_fim = data_maxima


def filtrar_periodo(df):
    if df.empty or "data" not in df.columns:
        return df

    inicio = pd.Timestamp(data_inicio)
    fim = pd.Timestamp(data_fim) + pd.Timedelta(days=1)

    return df[
        (df["data"] >= inicio) &
        (df["data"] < fim)
    ].copy()


dados_filtrados = filtrar_periodo(dados)
deral_filtrado = filtrar_periodo(deral)


# ============================================================
# 1. VISÃO GERAL
# ============================================================

if pagina == "🏠 Visão Geral":

    st.title("Visão Geral do Mercado da Soja")
    st.caption(
        "Acompanhamento do preço estadual e dos principais indicadores "
        "relacionados ao mercado da soja."
    )

    st.markdown(
        """
        <div class="aviso">
        O painel utiliza resultados previamente processados. "
        "As visualizações não recalculam as análises estatísticas "
        "ou os modelos durante a navegação.
        </div>
        """,
        unsafe_allow_html=True
    )

    tipo_preco = st.radio(
        "Tipo de preço da soja",
        ["Nominal", "Corrigido pelo IPCA"],
        horizontal=True
    )

    tipo = "real" if tipo_preco == "Corrigido pelo IPCA" else "nominal"

    coluna_preco_selecionada = coluna_preco(deral_filtrado, tipo)

    if coluna_preco_selecionada:
        serie_preco = deral_filtrado[
            ["data", coluna_preco_selecionada]
        ].dropna()

        serie_preco = serie_preco.rename(
            columns={coluna_preco_selecionada: "preco"}
        )

        total_registros = len(serie_preco)

        ultimo_preco = (
            serie_preco["preco"].iloc[-1]
            if total_registros > 0 else np.nan
        )

        primeiro_preco = (
            serie_preco["preco"].iloc[0]
            if total_registros > 0 else np.nan
        )

        variacao_total = (
            ((ultimo_preco / primeiro_preco) - 1) * 100
            if pd.notna(primeiro_preco)
            and primeiro_preco != 0
            and pd.notna(ultimo_preco)
            else np.nan
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Registros da série estadual",
            total_registros
        )

        c2.metric(
            "Último preço disponível",
            f"R$ {formatar_numero(ultimo_preco)}"
        )

        c3.metric(
            "Variação no período",
            formatar_percentual(variacao_total)
        )

        st.markdown("### Evolução do preço da soja no Paraná")

        serie_preco["media_movel"] = (
            serie_preco["preco"]
            .rolling(12, min_periods=12)
            .mean()
        )

        fig_preco = go.Figure()

        fig_preco.add_trace(
            go.Scatter(
                x=serie_preco["data"],
                y=serie_preco["preco"],
                mode="lines",
                name=f"Preço {tipo_preco.lower()}",
                line=dict(color=CORES["verde"], width=2.5)
            )
        )

        fig_preco.add_trace(
            go.Scatter(
                x=serie_preco["data"],
                y=serie_preco["media_movel"],
                mode="lines",
                name="Média móvel de 12 meses",
                line=dict(
                    color=CORES["laranja"],
                    width=2,
                    dash="dash"
                )
            )
        )

        fig_preco.update_layout(
            template="plotly_white",
            height=430,
            xaxis_title="Data",
            yaxis_title="Preço (R$/saca de 60 kg)",
            hovermode="x unified",
            legend_title=""
        )

        st.plotly_chart(fig_preco, use_container_width=True)

        if tipo == "real":
            st.caption(
                "Preço corrigido pelo IPCA, em valores de dezembro de 2025."
            )

    else:
        grafico_vazio(
            "Não foi encontrada uma coluna de preço compatível "
            "com a seleção. Verifique os nomes das colunas da base DERAL."
        )

    st.divider()

    st.markdown("### Comparação dos indicadores de mercado")

    if not dados_filtrados.empty:

        indicadores = [
            coluna for coluna in NOMES_INDICADORES
            if coluna in dados_filtrados.columns
        ]

        if indicadores:
            dados_grafico = dados_filtrados[
                ["data"] + indicadores
            ].copy()

            # Reescala para base 100, preservando as unidades originais
            # nos arquivos e permitindo comparação visual das trajetórias.
            dados_base100 = dados_grafico[["data"]].copy()

            for coluna in indicadores:
                serie = dados_grafico[coluna].dropna()

                if len(serie) > 0 and serie.iloc[0] != 0:
                    primeiro_valor = serie.iloc[0]

                    dados_base100[coluna] = (
                        dados_grafico[coluna] /
                        primeiro_valor * 100
                    )

            fig_indicadores = go.Figure()

            for coluna in indicadores:
                fig_indicadores.add_trace(
                    go.Scatter(
                        x=dados_base100["data"],
                        y=dados_base100[coluna],
                        mode="lines",
                        name=NOMES_INDICADORES[coluna]
                    )
                )

            fig_indicadores.update_layout(
                template="plotly_white",
                height=430,
                xaxis_title="Data",
                yaxis_title="Índice (base 100)",
                hovermode="x unified",
                legend_title=""
            )

            st.plotly_chart(
                fig_indicadores,
                use_container_width=True
            )

            quantidade_indicadores = (
                dados_grafico[indicadores]
                .dropna(how="all")
                .shape[0]
            )

            st.caption(
                f"A comparação apresenta {quantidade_indicadores} "
                "registros com pelo menos um indicador disponível. "
                "As séries foram reescaladas para base 100."
            )

            st.caption(
                "A base integrada dos indicadores possui disponibilidade "
                "a partir de dezembro de 2000, totalizando 301 registros. "
                "A série estadual DERAL possui 312 meses, de janeiro de "
                "2000 a dezembro de 2025. A diferença decorre da cobertura "
                "temporal das bases e não representa, por si só, perda "
                "de registros."
            )

        else:
            grafico_vazio(
                "Não foram encontradas as colunas dos indicadores "
                "na base consolidada."
            )

    else:
        grafico_vazio("A base consolidada não está disponível.")


# ============================================================
# 2. ANÁLISE EXPLORATÓRIA
# ============================================================

elif pagina == "📊 Análise Exploratória":

    st.title("Análise Exploratória")
    st.caption(
        "Estatísticas descritivas, comportamento temporal, sazonalidade "
        "e variações do preço da soja."
    )

    aba1, aba2, aba3, aba4 = st.tabs([
        "Estatísticas descritivas",
        "Sazonalidade",
        "Médias móveis",
        "Variações e extremos"
    ])

    with aba1:
        titulo_secao(
            "Estatísticas descritivas",
            "Resumo estatístico das variáveis utilizadas no projeto."
        )

        if not estatisticas.empty:
            st.dataframe(
                estatisticas,
                use_container_width=True,
                hide_index=True
            )
        else:
            grafico_vazio(
                "Arquivo 07_estatisticas_descritivas_niveis.csv "
                "não encontrado."
            )

    with aba2:
        titulo_secao(
            "Sazonalidade mensal",
            "Comportamento médio e mediano das variáveis ao longo dos meses."
        )

        if not sazonalidade.empty:

            coluna_mes = encontrar_coluna(
                sazonalidade,
                ["mes", "mes_numero", "month"]
            )

            coluna_media = encontrar_coluna(
                sazonalidade,
                [
                    "preco_soja_nominal_media",
                    "preco_nominal_media",
                    "preco_media",
                    "media_preco"
                ]
            )

            coluna_mediana = encontrar_coluna(
                sazonalidade,
                [
                    "preco_soja_nominal_mediana",
                    "preco_nominal_mediana",
                    "preco_mediana",
                    "mediana_preco"
                ]
            )

            if coluna_mes and coluna_media:
                fig_sazonalidade = go.Figure()

                fig_sazonalidade.add_trace(
                    go.Bar(
                        x=sazonalidade[coluna_mes],
                        y=sazonalidade[coluna_media],
                        name="Preço médio"
                    )
                )

                if coluna_mediana:
                    fig_sazonalidade.add_trace(
                        go.Scatter(
                            x=sazonalidade[coluna_mes],
                            y=sazonalidade[coluna_mediana],
                            name="Preço mediano",
                            mode="lines+markers",
                            line=dict(
                                color=CORES["laranja"],
                                width=2
                            )
                        )
                    )

                fig_sazonalidade.update_layout(
                    template="plotly_white",
                    height=400,
                    xaxis_title="Mês",
                    yaxis_title="Preço da soja (R$/saca)",
                    hovermode="x unified"
                )

                st.plotly_chart(
                    fig_sazonalidade,
                    use_container_width=True
                )

            st.dataframe(
                sazonalidade,
                use_container_width=True,
                hide_index=True
            )

        else:
            grafico_vazio(
                "Arquivo de sazonalidade não encontrado."
            )

    with aba3:
        titulo_secao(
            "Médias móveis",
            "A média móvel de 12 meses suaviza oscilações de curto prazo "
            "e facilita a observação da tendência."
        )

        if not deral_filtrado.empty:
            col_preco = coluna_preco(deral_filtrado, "nominal")

            if col_preco:
                df_mm = deral_filtrado[
                    ["data", col_preco]
                ].dropna().copy()

                df_mm = df_mm.rename(
                    columns={col_preco: "preco"}
                )

                df_mm = adicionar_media_movel(
                    df_mm,
                    "preco",
                    janela=12
                )

                fig_mm = go.Figure()

                fig_mm.add_trace(
                    go.Scatter(
                        x=df_mm["data"],
                        y=df_mm["preco"],
                        name="Preço nominal",
                        mode="lines",
                        line=dict(
                            color=CORES["azul"],
                            width=1.5
                        )
                    )
                )

                fig_mm.add_trace(
                    go.Scatter(
                        x=df_mm["data"],
                        y=df_mm["media_movel_12"],
                        name="Média móvel de 12 meses",
                        mode="lines",
                        line=dict(
                            color=CORES["laranja"],
                            width=2.5
                        )
                    )
                )

                fig_mm.update_layout(
                    template="plotly_white",
                    height=430,
                    xaxis_title="Data",
                    yaxis_title="Preço (R$/saca de 60 kg)",
                    hovermode="x unified"
                )

                st.plotly_chart(
                    fig_mm,
                    use_container_width=True
                )

                st.caption(
                    "A média móvel é uma ferramenta de suavização "
                    "visual. Ela não representa uma previsão."
                )

            else:
                grafico_vazio(
                    "Coluna de preço nominal não identificada."
                )
        else:
            grafico_vazio(
                "Série de preços não disponível para o período."
            )

    with aba4:
        titulo_secao(
            "Variações e valores extremos",
            "Distribuição das variações mensais e identificação exploratória "
            "de observações extremas."
        )

        if not variacoes.empty:
            st.dataframe(
                variacoes,
                use_container_width=True,
                hide_index=True
            )

        if not deral_filtrado.empty:
            col_preco = coluna_preco(deral_filtrado, "nominal")

            if col_preco:
                df_extremos = deral_filtrado[
                    ["data", col_preco]
                ].dropna().copy()

                df_extremos["variacao_pct"] = (
                    df_extremos[col_preco].pct_change() * 100
                )

                valores = df_extremos["variacao_pct"].dropna()

                if len(valores) >= 5:
                    q1 = valores.quantile(0.25)
                    q3 = valores.quantile(0.75)
                    iqr = q3 - q1

                    limite_inferior = q1 - 1.5 * iqr
                    limite_superior = q3 + 1.5 * iqr

                    df_extremos["extremo"] = (
                        (df_extremos["variacao_pct"] < limite_inferior) |
                        (df_extremos["variacao_pct"] > limite_superior)
                    )

                    fig_extremos = px.scatter(
                        df_extremos.dropna(
                            subset=["variacao_pct"]
                        ),
                        x="data",
                        y="variacao_pct",
                        color="extremo",
                        color_discrete_map={
                            True: CORES["vermelho"],
                            False: CORES["azul"]
                        },
                        labels={
                            "data": "Data",
                            "variacao_pct": "Variação mensal (%)",
                            "extremo": "Valor extremo"
                        },
                        title="Variações mensais e observações extremas"
                    )

                    fig_extremos.update_layout(
                        template="plotly_white",
                        height=400
                    )

                    st.plotly_chart(
                        fig_extremos,
                        use_container_width=True
                    )

                    st.caption(
                        "Os valores extremos foram identificados "
                        "exploratoriamente pelo critério do intervalo "
                        "interquartil (1,5 × IQR). Isso não significa "
                        "que sejam erros nos dados."
                    )

                    extremos = df_extremos[
                        df_extremos["extremo"] == True
                    ]

                    st.markdown("#### Observações classificadas como extremas")

                    st.dataframe(
                        extremos[
                            ["data", col_preco, "variacao_pct"]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )


# ============================================================
# 3. CORRELAÇÕES E DEFASAGENS
# ============================================================

elif pagina == "🔗 Correlações e Defasagens":

    st.title("Correlações e Defasagens")
    st.caption(
        "Associações entre os indicadores de mercado e o comportamento "
        "do preço da soja."
    )

    st.markdown(
        """
        As correlações indicam o grau de associação entre variáveis.
        Elas não demonstram causalidade. As defasagens representam
        deslocamentos temporais avaliados nas análises do projeto.
        """
    )

    aba1, aba2, aba3 = st.tabs([
        "Correlações",
        "Melhores defasagens",
        "Mapa de defasagens"
    ])

    with aba1:

        st.markdown("### Correlações em níveis")

        if not corr_niveis.empty:

            st.dataframe(
                corr_niveis,
                use_container_width=True,
                hide_index=True
            )

            coluna_rho = encontrar_coluna(
                corr_niveis,
                ["spearman_rho", "rho_spearman", "spearman"]
            )

            coluna_indicador = encontrar_coluna(
                corr_niveis,
                ["indicador", "variavel", "variavel_independente"]
            )

            if coluna_rho and coluna_indicador:
                df_plot = corr_niveis.copy()

                df_plot[coluna_rho] = pd.to_numeric(
                    df_plot[coluna_rho],
                    errors="coerce"
                )

                df_plot = df_plot.dropna(
                    subset=[coluna_rho]
                )

                fig_corr = px.bar(
                    df_plot,
                    x=coluna_indicador,
                    y=coluna_rho,
                    color=coluna_rho,
                    color_continuous_scale="RdYlGn",
                    labels={
                        coluna_rho: "Spearman (ρ)",
                        coluna_indicador: "Indicador"
                    },
                    title="Correlação de Spearman"
                )

                fig_corr.update_layout(
                    template="plotly_white",
                    height=400
                )

                st.plotly_chart(
                    fig_corr,
                    use_container_width=True
                )

            # Só classifica significância se o arquivo trouxer p-valor.
            coluna_p = encontrar_coluna(
                corr_niveis,
                [
                    "p_fdr_bh",
                    "p_valor_ajustado",
                    "p_adjusted",
                    "p_value_adjusted",
                    "p_valor",
                    "p_value"
                ]
            )

            if coluna_p:
                st.info(
                    "O arquivo contém uma coluna de p-valor. "
                    "A interpretação da significância deve considerar "
                    "se o valor é bruto ou ajustado por FDR."
                )
            else:
                st.warning(
                    "O arquivo de correlações não apresenta p-valores "
                    "ou valores ajustados identificáveis. Portanto, "
                    "esta tela apresenta a intensidade das associações, "
                    "mas não classifica as correlações como estatisticamente "
                    "significativas."
                )

        else:
            grafico_vazio(
                "Arquivo de correlações em níveis não encontrado."
            )

        st.divider()

        st.markdown("### Correlações das variações mensais")

        if not corr_variacoes.empty:
            st.dataframe(
                corr_variacoes,
                use_container_width=True,
                hide_index=True
            )
        else:
            grafico_vazio(
                "Arquivo de correlações das variações mensais "
                "não encontrado."
            )

    with aba2:

        st.markdown("### Melhores defasagens identificadas")

        if not melhores_lags.empty:

            st.dataframe(
                melhores_lags,
                use_container_width=True,
                hide_index=True
            )

            coluna_indicador = encontrar_coluna(
                melhores_lags,
                ["indicador", "variavel"]
            )

            coluna_lag = encontrar_coluna(
                melhores_lags,
                ["defasagem_meses", "lag_meses", "lag"]
            )

            coluna_rho = encontrar_coluna(
                melhores_lags,
                ["spearman_rho", "rho_spearman"]
            )

            if coluna_indicador and coluna_lag and coluna_rho:

                df_lag = melhores_lags.copy()

                df_lag[coluna_lag] = pd.to_numeric(
                    df_lag[coluna_lag],
                    errors="coerce"
                )

                df_lag[coluna_rho] = pd.to_numeric(
                    df_lag[coluna_rho],
                    errors="coerce"
                )

                df_lag = df_lag.dropna(
                    subset=[coluna_lag, coluna_rho]
                )

                fig_lag = px.bar(
                    df_lag,
                    x=coluna_indicador,
                    y=coluna_rho,
                    color=coluna_lag,
                    color_continuous_scale="Viridis",
                    labels={
                        coluna_rho: "Spearman (ρ)",
                        coluna_lag: "Defasagem (meses)",
                        coluna_indicador: "Indicador"
                    },
                    title="Correlação nas melhores defasagens"
                )

                fig_lag.update_layout(
                    template="plotly_white",
                    height=400
                )

                st.plotly_chart(
                    fig_lag,
                    use_container_width=True
                )

            st.caption(
                "Uma defasagem com maior correlação representa uma "
                "associação temporal mais forte dentro dos intervalos "
                "avaliados. Não significa que o indicador cause "
                "a variação futura do preço."
            )

        else:
            grafico_vazio(
                "Arquivo de melhores defasagens não encontrado."
            )

    with aba3:

        st.markdown("### Correlações entre os lags de 0 a 6 meses")

        if not lags_0_6.empty:

            st.dataframe(
                lags_0_6,
                use_container_width=True,
                hide_index=True
            )

            coluna_lag = encontrar_coluna(
                lags_0_6,
                ["defasagem_meses", "lag_meses", "lag"]
            )

            coluna_indicador = encontrar_coluna(
                lags_0_6,
                ["indicador", "variavel"]
            )

            coluna_rho = encontrar_coluna(
                lags_0_6,
                ["spearman_rho", "rho_spearman"]
            )

            if coluna_lag and coluna_indicador and coluna_rho:

                tabela = lags_0_6.copy()

                tabela[coluna_lag] = pd.to_numeric(
                    tabela[coluna_lag],
                    errors="coerce"
                )

                tabela[coluna_rho] = pd.to_numeric(
                    tabela[coluna_rho],
                    errors="coerce"
                )

                matriz = tabela.pivot_table(
                    index=coluna_indicador,
                    columns=coluna_lag,
                    values=coluna_rho,
                    aggfunc="mean"
                )

                if not matriz.empty:
                    fig_heat = go.Figure(
                        data=go.Heatmap(
                            z=matriz.values,
                            x=matriz.columns.astype(str),
                            y=matriz.index.astype(str),
                            colorscale="RdYlGn",
                            zmid=0,
                            colorbar=dict(title="Spearman ρ")
                        )
                    )

                    fig_heat.update_layout(
                        template="plotly_white",
                        title="Mapa de calor das correlações",
                        xaxis_title="Defasagem (meses)",
                        yaxis_title="Indicador",
                        height=420
                    )

                    st.plotly_chart(
                        fig_heat,
                        use_container_width=True
                    )

        else:
            grafico_vazio(
                "Arquivo de correlações com defasagens não encontrado."
            )


# ============================================================
# 4. SINAIS DE ATENÇÃO
# ============================================================

elif pagina == "⚠️ Sinais de Atenção":

    st.title("Sinais de Atenção")
    st.caption(
        "Acompanhamento experimental de condições associadas "
        "a movimentos do preço da soja."
    )

    st.markdown(
        """
        <div class="aviso">
        Os sinais são exploratórios. Não representam recomendações
        de compra ou venda e não devem ser interpretados como
        previsões determinísticas do preço da soja.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Indicadores resumidos
    cobertura = 52.78
    acerto = 47.37
    sinais_emitidos = 38
    meses_teste = 72

    if not sinais_resumo.empty:

        primeira_linha = sinais_resumo.iloc[0]

        col_cobertura = encontrar_coluna(
            sinais_resumo,
            ["cobertura_pct"]
        )

        col_acerto = encontrar_coluna(
            sinais_resumo,
            ["taxa_acerto_sinais_pct"]
        )

        col_qtd = encontrar_coluna(
            sinais_resumo,
            ["quantidade_sinais"]
        )

        col_meses = encontrar_coluna(
            sinais_resumo,
            ["meses_teste"]
        )

        if col_cobertura:
            cobertura = pd.to_numeric(
                primeira_linha[col_cobertura],
                errors="coerce"
            )

        if col_acerto:
            acerto = pd.to_numeric(
                primeira_linha[col_acerto],
                errors="coerce"
            )

        if col_qtd:
            sinais_emitidos = primeira_linha[col_qtd]

        if col_meses:
            meses_teste = primeira_linha[col_meses]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Meses avaliados",
        str(meses_teste)
    )

    c2.metric(
        "Cobertura dos sinais",
        formatar_percentual(cobertura)
    )

    c3.metric(
        "Taxa de acerto",
        formatar_percentual(acerto)
    )

    st.caption(
        "Resultado documentado para o teste de janeiro de 2020 "
        "a dezembro de 2025: 38 sinais em 72 meses, com cobertura "
        "de 52,78% e taxa de acerto de 47,37%."
    )

    st.divider()

    st.markdown("### Comparação entre sinais e comportamento observado")

    if not sinais_mensais.empty:

        df_sinais = converter_data(
            sinais_mensais.copy()
        )

        col_sinal = encontrar_coluna(
            df_sinais,
            ["sinal"]
        )

        col_direcao = encontrar_coluna(
            df_sinais,
            ["direcao_real", "direcao_observada"]
        )

        col_acerto = encontrar_coluna(
            df_sinais,
            ["acerto_sinal", "acerto"]
        )

        col_pontuacao = encontrar_coluna(
            df_sinais,
            ["pontuacao", "pontuação", "score"]
        )

        if col_sinal and col_direcao and "data" in df_sinais.columns:

            df_comparacao = df_sinais.copy()

            # Classificação textual para facilitar a leitura.
            df_comparacao["sinal_texto"] = (
                df_comparacao[col_sinal]
                .fillna("Sem sinal")
                .astype(str)
            )

            df_comparacao["direcao_texto"] = (
                df_comparacao[col_direcao]
                .fillna("Não informada")
                .astype(str)
            )

            fig_comparacao = go.Figure()

            fig_comparacao.add_trace(
                go.Scatter(
                    x=df_comparacao["data"],
                    y=df_comparacao["sinal_texto"],
                    mode="markers",
                    name="Sinal emitido",
                    marker=dict(
                        size=9,
                        color=CORES["azul"]
                    )
                )
            )

            fig_comparacao.add_trace(
                go.Scatter(
                    x=df_comparacao["data"],
                    y=df_comparacao["direcao_texto"],
                    mode="markers",
                    name="Direção observada",
                    marker=dict(
                        size=9,
                        color=CORES["laranja"],
                        symbol="diamond"
                    )
                )
            )

            fig_comparacao.update_layout(
                template="plotly_white",
                height=420,
                title="Sinal emitido versus direção observada",
                xaxis_title="Data",
                yaxis_title="Classificação",
                hovermode="x unified"
            )

            st.plotly_chart(
                fig_comparacao,
                use_container_width=True
            )

            if col_acerto:
                st.markdown("#### Resultado dos sinais")

                df_resultado = df_comparacao.copy()

                df_resultado[col_acerto] = (
                    df_resultado[col_acerto]
                    .astype(str)
                )

                st.dataframe(
                    df_resultado[
                        [
                            coluna for coluna in [
                                "data",
                                col_sinal,
                                col_direcao,
                                col_acerto
                            ]
                            if coluna in df_resultado.columns
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

        elif col_pontuacao and "data" in df_sinais.columns:

            df_sinais[col_pontuacao] = pd.to_numeric(
                df_sinais[col_pontuacao],
                errors="coerce"
            )

            fig_pontuacao = px.line(
                df_sinais,
                x="data",
                y=col_pontuacao,
                title="Pontuação mensal do mecanismo de sinais",
                labels={
                    "data": "Data",
                    col_pontuacao: "Pontuação"
                }
            )

            fig_pontuacao.update_layout(
                template="plotly_white",
                height=400
            )

            st.plotly_chart(
                fig_pontuacao,
                use_container_width=True
            )

        else:
            st.warning(
                "Não foram identificadas todas as colunas necessárias "
                "para comparar sinal emitido e direção observada."
            )

        if col_pontuacao:
            st.markdown("#### Pontuação mensal")

            fig_score = px.line(
                df_sinais,
                x="data",
                y=col_pontuacao,
                labels={
                    "data": "Data",
                    col_pontuacao: "Pontuação"
                }
            )

            fig_score.update_layout(
                template="plotly_white",
                height=350
            )

            st.plotly_chart(
                fig_score,
                use_container_width=True
            )

    else:
        grafico_vazio(
            "Arquivo de sinais mensais não encontrado."
        )

    st.divider()

    st.markdown("### Indicadores selecionados pelas regras")

    if not regras_sinais.empty:
        st.dataframe(
            regras_sinais,
            use_container_width=True,
            hide_index=True
        )
    else:
        grafico_vazio(
            "Arquivo de regras dos sinais não encontrado."
        )

    st.markdown("### Limitações dos sinais")

    st.markdown(
        """
        - A taxa de acerto observada no teste foi inferior a 50%.
        - A cobertura indica que o mecanismo não emitiu sinal em todos
          os meses avaliados.
        - As regras foram construídas a partir de relações históricas
          e limites estimados no período de treinamento.
        - Correlação não comprova causalidade.
        - Mudanças nas condições do mercado podem reduzir a utilidade
          das regras ao longo do tempo.
        - O mecanismo não considera todas as variáveis locais que
          influenciam o preço da soja, como frete, prêmio de exportação,
          custos portuários, estoques e condições climáticas regionais.

        Portanto, os sinais devem ser utilizados apenas como recurso
        complementar de monitoramento.
        """
    )


# ============================================================
# 5. MODELAGEM E VALIDAÇÃO
# ============================================================

elif pagina == "🤖 Modelagem e Validação":

    st.title("Modelagem e Validação")
    st.caption(
        "Comparação dos modelos avaliados no projeto e análise "
        "dos resultados obtidos no período de teste."
    )

    st.markdown(
        """
        Os resultados apresentados foram calculados previamente.
        Esta seção permite comparar o desempenho dos modelos sem
        executar novamente o treinamento durante a navegação.
        """
    )

    aba1, aba2, aba3 = st.tabs([
        "Métricas dos modelos",
        "Observado versus estimado",
        "Coeficientes Ridge"
    ])

    with aba1:

        st.markdown("### Comparação das métricas")

        if not metricas_modelagem.empty:

            st.dataframe(
                metricas_modelagem,
                use_container_width=True,
                hide_index=True
            )

            coluna_modelo = encontrar_coluna(
                metricas_modelagem,
                ["modelo"]
            )

            coluna_rmse = encontrar_coluna(
                metricas_modelagem,
                ["rmse_preco", "rmse_variacao_pct_pontos"]
            )

            if coluna_modelo and coluna_rmse:

                df_metricas = metricas_modelagem.copy()

                df_metricas[coluna_rmse] = pd.to_numeric(
                    df_metricas[coluna_rmse],
                    errors="coerce"
                )

                fig_metricas = px.bar(
                    df_metricas,
                    x=coluna_modelo,
                    y=coluna_rmse,
                    color=coluna_modelo,
                    title="Comparação do RMSE",
                    labels={
                        coluna_modelo: "Modelo",
                        coluna_rmse: "RMSE"
                    }
                )

                fig_metricas.update_layout(
                    template="plotly_white",
                    height=400,
                    showlegend=False
                )

                st.plotly_chart(
                    fig_metricas,
                    use_container_width=True
                )

            st.info(
                "MAE, RMSE, MAPE, R² e acurácia direcional avaliam "
                "dimensões diferentes do desempenho. A interpretação "
                "deve considerar o conjunto das métricas."
            )

        else:
            grafico_vazio(
                "Arquivo de métricas da modelagem não encontrado."
            )

    with aba2:

        st.markdown("### Preço observado versus estimado")

        if not previsoes.empty:

            df_prev = converter_data(
                previsoes.copy()
            )

            coluna_observado = encontrar_coluna(
                df_prev,
                ["preco_observado", "observado"]
            )

            coluna_baseline = encontrar_coluna(
                df_prev,
                ["preco_previsto_baseline", "baseline"]
            )

            coluna_linear = encontrar_coluna(
                df_prev,
                ["preco_previsto_linear", "linear"]
            )

            coluna_ridge = encontrar_coluna(
                df_prev,
                ["preco_previsto_ridge", "ridge"]
            )

            if "data" in df_prev.columns and coluna_observado:

                fig_prev = go.Figure()

                fig_prev.add_trace(
                    go.Scatter(
                        x=df_prev["data"],
                        y=df_prev[coluna_observado],
                        name="Observado",
                        mode="lines",
                        line=dict(
                            color=CORES["verde_escuro"],
                            width=2.5
                        )
                    )
                )

                if coluna_baseline:
                    fig_prev.add_trace(
                        go.Scatter(
                            x=df_prev["data"],
                            y=df_prev[coluna_baseline],
                            name="Baseline",
                            mode="lines"
                        )
                    )

                if coluna_linear:
                    fig_prev.add_trace(
                        go.Scatter(
                            x=df_prev["data"],
                            y=df_prev[coluna_linear],
                            name="Regressão Linear",
                            mode="lines"
                        )
                    )

                if coluna_ridge:
                    fig_prev.add_trace(
                        go.Scatter(
                            x=df_prev["data"],
                            y=df_prev[coluna_ridge],
                            name="Ridge",
                            mode="lines"
                        )
                    )

                fig_prev.update_layout(
                    template="plotly_white",
                    height=450,
                    title="Comparação das previsões no período de teste",
                    xaxis_title="Data",
                    yaxis_title="Preço / variação conforme arquivo de origem",
                    hovermode="x unified"
                )

                st.plotly_chart(
                    fig_prev,
                    use_container_width=True
                )

                st.caption(
                    "A unidade do eixo vertical acompanha a variável "
                    "registrada no arquivo de previsões. Consulte as "
                    "métricas para identificar a variável-alvo utilizada."
                )

            st.dataframe(
                previsoes,
                use_container_width=True,
                hide_index=True
            )

        else:
            grafico_vazio(
                "Arquivo de previsões do período de teste não encontrado."
            )

    with aba3:

        st.markdown("### Coeficientes do modelo Ridge")

        if not coeficientes.empty:

            st.dataframe(
                coeficientes,
                use_container_width=True,
                hide_index=True
            )

            coluna_variavel = encontrar_coluna(
                coeficientes,
                ["variavel", "indicador", "feature"]
            )

            coluna_coef = encontrar_coluna(
                coeficientes,
                ["coeficiente", "coef", "valor"]
            )

            if coluna_variavel and coluna_coef:

                df_coef = coeficientes.copy()

                df_coef[coluna_coef] = pd.to_numeric(
                    df_coef[coluna_coef],
                    errors="coerce"
                )

                fig_coef = px.bar(
                    df_coef,
                    x=coluna_variavel,
                    y=coluna_coef,
                    color=coluna_coef,
                    color_continuous_scale="RdYlGn",
                    title="Coeficientes Ridge",
                    labels={
                        coluna_variavel: "Variável",
                        coluna_coef: "Coeficiente"
                    }
                )

                fig_coef.update_layout(
                    template="plotly_white",
                    height=400
                )

                st.plotly_chart(
                    fig_coef,
                    use_container_width=True
                )

        else:
            grafico_vazio(
                "Arquivo de coeficientes Ridge não encontrado."
            )

    st.divider()

    st.markdown("### Interpretação dos resultados")

    st.markdown(
        """
        Os resultados do projeto indicam capacidade explicativa limitada
        dos modelos avaliados. No período de teste de 2020 a 2025, o modelo
        Ridge apresentou RMSE de 6,95 e R² de 0,054 para a variação mensal
        do preço.

        Esses resultados não sustentam o uso do modelo como previsão
        determinística do preço da soja. Sua contribuição deve ser
        interpretada como parte da avaliação exploratória das relações
        entre os indicadores e o comportamento do mercado.
        """
    )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "AgroData PR | Análise de Indicadores de Mercado e Defasagens "
    "Temporais para Monitoramento do Preço da Soja no Paraná."
)

st.caption(
    "Fonte: bases públicas tratadas e resultados estatísticos "
    "previamente processados no projeto."
)
