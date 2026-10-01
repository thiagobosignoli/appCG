import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página web
st.set_page_config(page_title="Comparador de Tabelas Analítico", layout="wide")

st.title("📊 Comparador de Tabelas Analítico (Alta Performance)")
st.write("Vincula as linhas através da coluna de identificação e identifica divergências na coluna de valor entre períodos distintos.")

# Painel de controle lateral fixo
st.sidebar.header("Parâmetros da Análise")

# --- ESCOLHA DO TIPO DE ANÁLISE ---
tipo_analise = st.sidebar.radio(
    "Tipo de análise:",
    [
        "Comparação por percentual (%)",
        "Filtro por Parâmetro"
    ]
)

# ============================================================
# MODO 1 - COMPARAÇÃO POR PERCENTUAL
# ============================================================

if tipo_analise == "Comparação por percentual (%)":

    margem_limite = st.sidebar.number_input(
        "Defina a variação máxima aceitável (X%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.5
    )

    # Caixas de texto para os nomes das colunas
    coluna_chave = st.sidebar.text_input(
        "Nome da coluna de Inscrição / Chave",
        value="NUM_INSCRICAO"
    ).strip()

    coluna_analise = st.sidebar.text_input(
        "Nome da coluna de Valor / Análise",
        value="VLR_IMPOSTO"
    ).strip()

    # Campos de Upload na tela principal
    col1, col2 = st.columns(2)

    with col1:
        arquivo_base = st.file_uploader(
            "Upload da Tabela Base - Data mais Recente (CSV)",
            type=["csv"]
        )

    with col2:
        arquivo_comparar = st.file_uploader(
            "Upload da Tabela de Comparação - Data mais antiga (CSV)",
            type=["csv"]
        )

    # Botão de execução fixo na barra lateral
    botao_executar = st.sidebar.button(
        "⚡ Executar Comparação Fiel"
    )

    # Inicializa as variáveis de estado
    if 'relatorio_original' not in st.session_state:
        st.session_state.relatorio_original = None

    if 'relatorio_arquivo2_divergente' not in st.session_state:
        st.session_state.relatorio_arquivo2_divergente = None

    if 'total_base' not in st.session_state:
        st.session_state.total_base = 0

    # Executa a lógica apenas quando o botão for clicado
    if botao_executar:

        if not arquivo_base or not arquivo_comparar:

            st.sidebar.error(
                "Por favor, faça o upload de ambos os arquivos CSV antes de executar."
            )

        elif not coluna_chave or not coluna_analise:

            st.sidebar.error(
                "Por favor, preencha os nomes de ambas as colunas na barra lateral antes de executar."
            )

        else:

            with st.spinner(
                "Localizando inscrições e cruzando dados fiscais... Aguarde."
            ):

                # 1. Carrega os arquivos completos como texto
                df_base = pd.read_csv(
                    arquivo_base,
                    sep=None,
                    engine='python',
                    encoding='utf-8-sig',
                    on_bad_lines='skip',
                    dtype=str
                )

                df_comp = pd.read_csv(
                    arquivo_comparar,
                    sep=None,
                    engine='python',
                    encoding='utf-8-sig',
                    on_bad_lines='skip',
                    dtype=str
                )

                # Limpa espaços em branco invisíveis nos cabeçalhos
                df_base.columns = df_base.columns.str.strip()
                df_comp.columns = df_comp.columns.str.strip()

                # 2. Validação das colunas
                if (
                    coluna_chave not in df_base.columns
                    or coluna_chave not in df_comp.columns
                ):

                    st.error(
                        f"Erro Crítico: A coluna de inscrição "
                        f"'{coluna_chave}' não foi encontrada em um dos arquivos."
                    )

                elif (
                    coluna_analise not in df_base.columns
                    or coluna_analise not in df_comp.columns
                ):

                    st.error(
                        f"Erro Crítico: A coluna de valor "
                        f"'{coluna_analise}' não foi encontrada em um dos arquivos."
                    )

                else:

                    # --- PADRONIZAÇÃO DAS CHAVES ---
                    def normalizar_sublote(serie):
                        return (
                            serie.astype(str)
                            .str.strip()
                            .str.replace(r'[\.\-\/]', '', regex=True)
                            .str.lstrip('0')
                        )

                    df_base['CHAVE_ALINHA'] = normalizar_sublote(
                        df_base[coluna_chave]
                    )

                    df_comp['CHAVE_ALINHA'] = normalizar_sublote(
                        df_comp[coluna_chave]
                    )

                    # --- TRATAMENTO DOS VALORES NUMÉRICOS ---
                    df_base['Valor_Base_Num'] = pd.to_numeric(
                        df_base[coluna_analise]
                        .str.replace(',', '.', regex=True),
                        errors='coerce'
                    ).fillna(0.0)

                    df_comp['Valor_Comp_Num'] = pd.to_numeric(
                        df_comp[coluna_analise]
                        .str.replace(',', '.', regex=True),
                        errors='coerce'
                    ).fillna(0.0)

                    # 3. Indexa a tabela de comparação
                    df_comp_limpo = df_comp.drop_duplicates(
                        subset=['CHAVE_ALINHA']
                    )

                    dict_valores_comp = dict(
                        zip(
                            df_comp_limpo['CHAVE_ALINHA'],
                            df_comp_limpo['Valor_Comp_Num']
                        )
                    )

                    # 4. Mapeamento Direto
                    df_base['Valor_Comparar'] = df_base[
                        'CHAVE_ALINHA'
                    ].map(dict_valores_comp)

                    df_base['Localizado_No_Comp'] = df_base[
                        'CHAVE_ALINHA'
                    ].isin(dict_valores_comp.keys())

                    df_base['Valor_Comparar_Calc'] = df_base[
                        'Valor_Comparar'
                    ].fillna(0.0)

                    # 5. Cálculo da variação
                    v_base = df_base['Valor_Base_Num'].values
                    v_comp = df_base['Valor_Comparar_Calc'].values

                    # Ambas as tabelas são zero
                    ambos_zeros = (
                        (v_base == 0) &
                        (v_comp == 0)
                    )

                    # Uma das tabelas é zero e a outra não
                    um_deles_zero = (
                        ((v_base == 0) & (v_comp != 0)) |
                        ((v_base != 0) & (v_comp == 0))
                    )

                    # Divisão segura
                    divisao_segura = np.divide(
                        np.abs(v_comp - v_base),
                        v_base,
                        out=np.zeros_like(
                            v_base,
                            dtype=float
                        ),
                        where=(
                            (v_base != 0) &
                            (v_comp != 0)
                        )
                    ) * 100.0

                    # Consolida a regra matemática
                    variacao = np.where(
                        ambos_zeros,
                        0.0,
                        np.where(
                            um_deles_zero,
                            100.0,
                            divisao_segura
                        )
                    )

                    df_base['Variacao_%'] = np.round(
                        variacao,
                        2
                    )

                    # 6. Identificação das divergências
                    condicao_divergencia = (
                        (df_base['Variacao_%'] > margem_limite) |
                        (~df_base['Localizado_No_Comp'])
                    )

                    df_resultado = df_base[
                        condicao_divergencia
                    ].copy()

                    # Classifica o tipo de ocorrência
                    df_resultado['Ocorrencia'] = np.where(
                        df_resultado['Localizado_No_Comp'],
                        "Variação acima do limite estipulado",
                        "Inscrição ausente na Data Mais Antiga"
                    )

                    # --- RELATÓRIO 1 ---
                    relatorio_original_gerado = pd.DataFrame({
                        'Inscricao_Sublote':
                            df_resultado[coluna_chave],

                        'Tipo_Inconsistencia':
                            df_resultado['Ocorrencia'],

                        'Valor_Data_Recente':
                            df_resultado['Valor_Base_Num'],

                        'Valor_Data_Antiga':
                            np.where(
                                df_resultado['Localizado_No_Comp'],
                                df_resultado['Valor_Comparar'],
                                "Não Localizado"
                            ),

                        'Diferenca_Percentual':
                            np.where(
                                df_resultado['Localizado_No_Comp'],
                                df_resultado['Variacao_%'].astype(str) + "%",
                                "N/A"
                            )
                    })

                    # --- RELATÓRIO 2 ---
                    chaves_com_erro = df_resultado[
                        'CHAVE_ALINHA'
                    ].unique()

                    relatorio_arquivo2_divergente_gerado = df_comp[
                        df_comp['CHAVE_ALINHA'].isin(
                            chaves_com_erro
                        )
                    ].copy()

                    # Remove coluna temporária
                    if 'CHAVE_ALINHA' in relatorio_arquivo2_divergente_gerado.columns:

                        relatorio_arquivo2_divergente_gerado = (
                            relatorio_arquivo2_divergente_gerado
                            .drop(
                                columns=['CHAVE_ALINHA']
                            )
                        )

                    # Salva os resultados na sessão
                    st.session_state.relatorio_original = (
                        relatorio_original_gerado
                    )

                    st.session_state.relatorio_arquivo2_divergente = (
                        relatorio_arquivo2_divergente_gerado
                    )

                    st.session_state.total_base = len(
                        df_base
                    )


    # --- BLOCO DE EXIBIÇÃO E DOWNLOAD ---
    if st.session_state.relatorio_original is not None:

        relatorio_original = (
            st.session_state.relatorio_original
        )

        relatorio_arquivo2_divergente = (
            st.session_state.relatorio_arquivo2_divergente
        )

        total_base = (
            st.session_state.total_base
        )

        if not relatorio_original.empty:

            st.success(
                f"Análise Concluída! "
                f"Varremos {total_base} linhas e "
                f"isolamos {len(relatorio_original)} divergências."
            )

            btn_col1, btn_col2 = st.columns(2)

            # Relatório 1
            with btn_col1:

                st.subheader(
                    "1. Relatório Analítico Calculado"
                )

                st.dataframe(
                    relatorio_original.head(100)
                )

                csv_original = (
                    relatorio_original
                    .to_csv(
                        index=False,
                        sep=';',
                        encoding='utf-8-sig'
                    )
                    .encode('utf-8-sig')
                )

                st.download_button(
                    label="📥 Baixar Relatório Analítico (.csv)",
                    data=csv_original,
                    file_name="relatorio_divergencias_temporal.csv",
                    mime="text/csv",
                    key="btn_download_1"
                )

            # Relatório 2
            with btn_col2:

                st.subheader(
                    "2. Linhas Brutas da Data mais antiga"
                )

                st.dataframe(
                    relatorio_arquivo2_divergente.head(100)
                )

                csv_arquivo2 = (
                    relatorio_arquivo2_divergente
                    .to_csv(
                        index=False,
                        sep=';',
                        encoding='utf-8-sig'
                    )
                    .encode('utf-8-sig')
                )

                st.download_button(
                    label="📥 Baixar Linhas Extraídas da Data Antiga (.csv)",
                    data=csv_arquivo2,
                    file_name="linhas_divergentes_data_antiga.csv",
                    mime="text/csv",
                    key="btn_download_2"
                )

        else:

            st.success(
                f"Parabéns! Todos os registros foram confrontados "
                f"e os valores estão consistentes dentro da margem "
                f"de {margem_limite}%."
            )


# ============================================================
# MODO 2 - FILTRO POR PARÂMETRO
# ============================================================

else:

    st.sidebar.subheader(
        "Parâmetros do Filtro"
    )

    # Nome da coluna que será analisada
    coluna_filtro = st.sidebar.text_input(
        "Nome da coluna de análise",
        value="EXCLUIR"
    ).strip()

    # Parâmetro que deverá ser excluído
    parametro_exclusao = st.sidebar.text_input(
        "Parâmetro a excluir",
        value="sim"
    ).strip()

    # Upload do arquivo
    arquivo_filtro = st.file_uploader(
        "Upload da Tabela para análise (CSV)",
        type=["csv"]
    )

    # Botão de execução
    botao_filtrar = st.sidebar.button(
        "⚡ Executar Filtro"
    )

    # Executa o filtro
    if botao_filtrar:

        if not arquivo_filtro:

            st.sidebar.error(
                "Por favor, faça o upload do arquivo CSV antes de executar."
            )

        elif not coluna_filtro:

            st.sidebar.error(
                "Por favor, informe o nome da coluna que será analisada."
            )

        elif not parametro_exclusao:

            st.sidebar.error(
                "Por favor, informe o parâmetro que deverá ser excluído."
            )

        else:

            with st.spinner(
                "Analisando registros... Aguarde."
            ):

                # Carrega o arquivo
                df_filtro = pd.read_csv(
                    arquivo_filtro,
                    sep=None,
                    engine='python',
                    encoding='utf-8-sig',
                    on_bad_lines='skip',
                    dtype=str
                )

                # Limpa os cabeçalhos
                df_filtro.columns = (
                    df_filtro.columns.str.strip()
                )

                # Verifica se a coluna existe
                if coluna_filtro not in df_filtro.columns:

                    st.error(
                        f"Erro Crítico: A coluna "
                        f"'{coluna_filtro}' não foi encontrada no arquivo."
                    )

                else:

                    # Padroniza os valores para comparação
                    valores_coluna = (
                        df_filtro[coluna_filtro]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                    )

                    # Parâmetro informado pelo usuário
                    parametro_comparacao = (
                        parametro_exclusao
                        .strip()
                        .lower()
                    )

                    # Identifica os registros que possuem
                    # exatamente o parâmetro informado
                    registros_excluir = (
                        valores_coluna ==
                        parametro_comparacao
                    )

                    # Mantém todos os registros que NÃO
                    # possuem o parâmetro informado
                    df_resultado_filtro = df_filtro[
                        ~registros_excluir
                    ].copy()

                    # Quantidades
                    total_original = len(
                        df_filtro
                    )

                    total_excluido = (
                        registros_excluir.sum()
                    )

                    total_resultado = len(
                        df_resultado_filtro
                    )

                    # Mensagem de resultado
                    st.success(
                        f"Análise concluída! "
                        f"Foram analisados {total_original} registros, "
                        f"{total_excluido} registros com o parâmetro "
                        f"'{parametro_exclusao}' foram excluídos "
                        f"e {total_resultado} registros permaneceram."
                    )

                    # Exibe o resultado
                    st.subheader(
                        "Registros mantidos"
                    )

                    st.dataframe(
                        df_resultado_filtro.head(100)
                    )

                    # Prepara CSV
                    csv_filtro = (
                        df_resultado_filtro
                        .to_csv(
                            index=False,
                            sep=';',
                            encoding='utf-8-sig'
                        )
                        .encode('utf-8-sig')
                    )

                    # Botão de download
                    st.download_button(
                        label="📥 Baixar Resultado Filtrado (.csv)",
                        data=csv_filtro,
                        file_name="resultado_filtro_parametro.csv",
                        mime="text/csv",
                        key="btn_download_filtro"
                    )
