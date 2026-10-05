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

# Inicializa as variáveis globais de estado da sessão
if 'relatorio_original' not in st.session_state:
    st.session_state.relatorio_original = None
if 'relatorio_arquivo2_divergente' not in st.session_state:
    st.session_state.relatorio_arquivo2_divergente = None
if 'total_base' not in st.session_state:
    st.session_state.total_base = 0

if 'df_resultado_filtro' not in st.session_state:
    st.session_state.df_resultado_filtro = None
if 'metricas_filtro' not in st.session_state:
    st.session_state.metricas_filtro = None

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
            "Upload da Tabela Base - Data mais Recente (Ano X) (CSV)",
            type=["csv"],
            key="upload_base_modo1"
        )

    with col2:
        arquivo_comparar = st.file_uploader(
            "Upload da Tabela de Comparação - Data mais antiga (Ano X-1) (CSV)",
            type=["csv"],
            key="upload_comp_modo1"
        )

    # Botão de execução fixo na barra lateral
    botao_executar = st.sidebar.button(
        "⚡ Executar Comparação Fiel"
    )

    # Executa a lógica apenas quando o botão for clicado
    if botao_executar:

        if not arquivo_base or not arquivo_comparar:
            st.sidebar.error("Por favor, faça o upload de ambos os arquivos CSV antes de executar.")
        elif not coluna_chave or not coluna_analise:
            st.sidebar.error("Por favor, preencha os nomes de ambas as colunas na barra lateral antes de executar.")
        else:
            with st.spinner("Localizando inscrições e cruzando dados fiscais... Aguarde."):

                # 1. Carrega os arquivos completos como texto
                df_base = pd.read_csv(arquivo_base, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_comp = pd.read_csv(arquivo_comparar, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)

                # Limpa espaços em branco invisíveis nos cabeçalhos
                df_base.columns = df_base.columns.str.strip()
                df_comp.columns = df_comp.columns.str.strip()

                # 2. Validação das colunas
                if coluna_chave not in df_base.columns or coluna_chave not in df_comp.columns:
                    st.error(f"Erro Crítico: A coluna de inscrição '{coluna_chave}' não foi encontrada em um dos arquivos.")
                elif coluna_analise not in df_base.columns or coluna_analise not in df_comp.columns:
                    st.error(f"Erro Crítico: A coluna de valor '{coluna_analise}' não foi encontrada em um dos arquivos.")
                else:

                    # --- PADRONIZAÇÃO DAS CHAVES ---
                    def normalizar_sublote(serie):
                        return (serie.astype(str).str.strip().str.replace(r'[\.\-\/]', '', regex=True).str.lstrip('0'))

                    df_base['CHAVE_ALINHA'] = normalizar_sublote(df_base[coluna_chave])
                    df_comp['CHAVE_ALINHA'] = normalizar_sublote(df_comp[coluna_chave])

                    # --- TRATAMENTO DOS VALORES NUMÉRICOS ---
                    df_base['Valor_Ano_X'] = pd.to_numeric(df_base[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)
                    df_comp['Valor_Ano_X_Menos_1'] = pd.to_numeric(df_comp[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)

                    # 3. Indexa a tabela de comparação (Ano X-1)
                    df_comp_limpo = df_comp.drop_duplicates(subset=['CHAVE_ALINHA'])
                    dict_valores_comp = dict(zip(df_comp_limpo['CHAVE_ALINHA'], df_comp_limpo['Valor_Ano_X_Menos_1']))

                    # 4. Mapeamento Direto para dentro da tabela do Ano X
                    df_base['Valor_Comparar_Antigo'] = df_base['CHAVE_ALINHA'].map(dict_valores_comp)
                    df_base['Localizado_No_Comp'] = df_base['CHAVE_ALINHA'].isin(dict_valores_comp.keys())
                    df_base['Valor_Comparar_Calc_Antigo'] = df_base['Valor_Comparar_Antigo'].fillna(0.0)

                    # 5. Cálculo da variação Real (Sem NP.ABS no numerador para identificar o aumento)
                    v_recente = df_base['Valor_Ano_X'].values
                    v_antigo = df_base['Valor_Comparar_Calc_Antigo'].values

                    ambos_zeros = (v_recente == 0) & (v_antigo == 0)
                    surgiu_no_ano_x = (v_antigo == 0) & (v_recente != 0)
                    zerou_no_ano_x = (v_antigo != 0) & (v_recente == 0)

                    divisao_segura = np.divide(
                        (v_recente - v_antigo),
                        v_antigo,
                        out=np.zeros_like(v_antigo, dtype=float),
                        where=(v_base != 0) & (v_comp != 0)
                    ) * 100.0

                    variacao = np.where(
                        ambos_zeros, 0.0,
                        np.where(surgiu_no_ano_x, 100.0,
                        np.where(zerou_no_ano_x, -100.0, 
                        divisao_segura))
                    )

                    df_base['Variacao_%'] = np.round(variacao, 2)

                    # 6. Identificação das divergências
                    condicao_divergencia = ((np.abs(df_base['Variacao_%']) > margem_limite) | (~df_base['Localizado_No_Comp']))
                    df_resultado = df_base[condicao_divergencia].copy()

                    df_resultado['Ocorrencia'] = np.where(
                        ~df_resultado['Localizado_No_Comp'], "Inscrição ausente no Ano X-1",
                        np.where(df_resultado['Variacao_%'] > 0, "Aumento acima do limite", "Redução acima do limite")
                    )

                    # --- RELATÓRIO 1 ---
                    relatorio_original_gerado = pd.DataFrame({
                        'Inscricao_Sublote': df_resultado[coluna_chave],
                        'Tipo_Inconsistencia': df_resultado['Ocorrencia'],
                        'Valor_Ano_X_Recente': df_resultado['Valor_Ano_X'],
                        'Valor_Ano_X_Menos_1': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Valor_Comparar_Antigo'], "Não Localizado"),
                        'Diferenca_Percentual': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Variacao_%'].astype(str) + "%", "N/A")
                    })

                    # --- RELATÓRIO 2 ---
                    relatorio_arquivo2_divergente_gerado = df_resultado.drop(
                        columns=['CHAVE_ALINHA', 'Valor_Ano_X', 'Valor_Comparar_Antigo', 'Localizado_No_Comp', 'Valor_Comparar_Calc_Antigo', 'Variacao_%', 'Ocorrencia'], 
                        errors='ignore'
                    )

                    # Salva na sessão
                    st.session_state.relatorio_original = relatorio_original_gerado
                    st.session_state.relatorio_arquivo2_divergente = relatorio_arquivo2_divergente_gerado
                    st.session_state.total_base = len(df_base)

    # --- BLOCO DE EXIBIÇÃO E DOWNLOAD MODO 1 ---
    if st.session_state.relatorio_original is not None:
        relatorio_original = st.session_state.relatorio_original
        relatorio_arquivo2_divergente = st.session_state.relatorio_arquivo2_divergente
        total_base = st.session_state.total_base

        if not relatorio_original.empty:
            st.success(f"Análise Concluída! Varremos {total_base} linhas e isolamos {len(relatorio_original)} divergências.")
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                st.subheader("1. Relatório Analítico Calculado")
                
                # --- FUNÇÃO DE FORMATAÇÃO VISUAL (Cores nas Linhas) ---
                def colorir_linhas(row):
                    if row['Tipo_Inconsistencia'] == "Aumento acima do limite":
                        return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row) # Vermelho claro
                    elif row['Tipo_Inconsistencia'] == "Redução acima do limite":
                        return ['background-color: rgba(30, 144, 255, 0.2)'] * len(row) # Azul claro
                    return [''] * len(row)

                # Aplica a estilização visual antes de exibir
                df_estilizado = relatorio_original.head(100).style.apply(colorir_linhas, axis=1)
                st.dataframe(df_estilizado)

                csv_original = relatorio_original.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Relatório Analítico (.csv)",data=csv_original,
                file_name="relatorio_divergencias_temporal.csv",
                mime="text/csv",
                key="btn_download_1"
                )
                with btn_col2:
                st.subheader("2. Linhas Brutas do Ano X (Com erro)")
                st.dataframe(relatorio_arquivo2_divergente.head(100))
                csv_arquivo2 = relatorio_arquivo2_divergente.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                label="📥 Baixar Linhas Extraídas do Ano X (.csv)",
                data=csv_arquivo2,
                file_name="linhas_divergentes_ano_x.csv",
                mime="text/csv",
                key="btn_download_2"
                )
                else:
                st.success(f"Parabéns! Todos os registros foram confrontados e os valores estão consistentes dentro da margem de {margem_limite}%.")
                ============================================================
                MODO 2 - FILTRO POR PARÂMETRO
                ============================================================
                else:
                st.sidebar.subheader("Parâmetros do Filtro")
                coluna_filtro = st.sidebar.text_input("Nome da coluna de análise", value="EXCLUIR").strip()
                parametro_exclusao = st.sidebar.text_input("Parâmetro a excluir", value="sim").strip()
                arquivo_filtro = st.file_uploader(
                "Upload da Tabela para análise (CSV)",
                type=["csv"],
                key="upload_modo2"
                )
                botao_filtrar = st.sidebar.button("⚡ Executar Filtro")
                # Executa o filtro e salva na Session State
                if botao_filtrar:
                if not arquivo_filtro:
                st.sidebar.error("Por favor, faça o upload do arquivo CSV antes de executar.")
                elif not coluna_filtro:
                st.sidebar.error("Por favor, informe o nome da coluna que será analisada.")
                elif not parametro_exclusao:
                st.sidebar.error("Por favor, informe o parâmetro que deverá ser excluído.")
                else:
                with st.spinner("Analisando registros... Aguarde."):
                df_filtro = pd.read_csv(arquivo_filtro, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_filtro.columns = df_filtro.columns.str.strip()
                if coluna_filtro not in df_filtro.columns:
                st.error(f"Erro Crítico: A coluna '{coluna_filtro}' não foi encontrada no arquivo.")
                else:
                valores_coluna = df_filtro[coluna_filtro].astype(str).str.strip().str.lower()
                parametro_comparacao = parametro_exclusao.strip().lower()
                registros_excluir = (valores_coluna == parametro_comparacao)
                df_resultado_filtro_gerado = df_filtro[~registros_excluir].copy()
                # Armazena os dados e métricas no session_state para não sumirem após ações
                st.session_state.df_resultado_filtro = df_resultado_filtro_gerado
                st.session_state.metricas_filtro = {
                "original": len(df_filtro),
                "excluido": registros_excluir.sum(),
                "permanece": len(df_resultado_filtro_gerado)
                }
                # --- BLOCO DE EXIBIÇÃO E DOWNLOAD MODO 2 (Baseado na Session State) ---
                if st.session_state.df_resultado_filtro is not None:
                df_resultado_filtro = st.session_state.df_resultado_filtro
                m = st.session_state.metricas_filtro
                st.success(
                f"Análise concluída! Foram analisados {m['original']} registros, "
                f"{m['excluido']} registros com o parâmetro '{parametro_exclusao}' foram excluídos "
                f"e {m['permanece']} registros permaneceram."
                )
                st.subheader("Registros mantidos")
                st.dataframe(df_resultado_filtro.head(100))
                csv_filtro = df_resultado_filtro.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                label="📥 Baixar Resultado Filtrado (.csv)",
                data=csv_filtro,
                file_name="resultado_filtro_parametro.csv",
                mime="text/csv",
                key="btn_download_filtro"
                )
