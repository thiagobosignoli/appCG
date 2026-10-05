import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página web
st.set_page_config(page_title="Comparador de Tabelas Analítico", layout="wide")

st.title("📊 Comparador de Tabelas Analítico (Alta Performance)")
st.write("Vincula as linhas através da coluna de identificação e processa filtros e cruzamentos avançados de acordo com os parâmetros definidos.")

# Painel de controle lateral fixo
st.sidebar.header("Parâmetros da Análise")

# --- ESCOLHA DO TIPO DE ANÁLISE (Com os novos botões solicitados) ---
tipo_analise = st.sidebar.radio(
    "Tipo de análise:",
    [
        "Comparação por percentual (%)",
        "Filtro por Parâmetro (Sim/Não)",
        "Excluir por Valor Até (Teto)",
        "Excluir por Ano (Data)"
    ]
)

# Inicializa as variáveis globais de estado da sessão para reter dados nos downloads
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
# MODO 1 - COMPARAÇÃO POR PERCENTUAL (Com Faixa de Exclusão)
# ============================================================
if tipo_analise == "Comparação por percentual (%)":

    # Divisão em duas caixas de texto/número na mesma linha para os limites
    col_inf, col_sup = st.sidebar.columns(2)
    with col_inf:
        limite_inferior = st.number_input("Limite Inferior (X%)", min_value=0.0, max_value=100.0, value=4.0, step=0.1)
    with col_sup:
        limite_superior = st.number_input("Limite Superior (Y%)", min_value=0.0, max_value=100.0, value=4.6, step=0.1)

    # Filtro checkbox para inscrições novas
    incluir_novas = st.sidebar.checkbox(
        "Incluir inscrições novas (Inexistentes no Ano X-1)", 
        value=True,
        help="Se marcado, mantém na tabela final os registros novos que não possuem histórico no passado."
    )

    # Caixas de texto para os nomes das colunas
    coluna_chave = st.sidebar.text_input("Nome da coluna de Inscrição / Chave", value="NUM_INSCRICAO").strip()
    coluna_analise = st.sidebar.text_input("Nome da coluna de Valor / Análise", value="VLR_IMPOSTO").strip()

    # Campos de Upload na tela principal
    col1, col2 = st.columns(2)
    with col1:
        arquivo_base = st.file_uploader("Upload da Tabela Base - Data mais Recente (CSV)", type=["csv"], key="upload_base_modo1")
    with col2:
        arquivo_comparar = st.file_uploader("Upload da Tabela de Comparação - Data mais antiga (CSV)", type=["csv"], key="upload_comp_modo1")

    # Botão de execução fixo na barra lateral
    botao_executar = st.sidebar.button("⚡ Executar Comparação Fiel")

    if botao_executar:
        if limite_inferior > limite_superior:
            st.sidebar.error("Erro: O limite inferior não pode ser maior do que o limite superior.")
        elif not arquivo_base or not arquivo_comparar:
            st.sidebar.error("Por favor, faça o upload de ambos os arquivos CSV antes de executar.")
        elif not coluna_chave or not coluna_analise:
            st.sidebar.error("Por favor, preencha os nomes de ambas as colunas na barra lateral antes de executar.")
        else:
            with st.spinner("Localizando inscrições e cruzando dados fiscais... Aguarde."):
                df_base = pd.read_csv(arquivo_base, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_comp = pd.read_csv(arquivo_comparar, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)

                df_base.columns = df_base.columns.str.strip()
                df_comp.columns = df_comp.columns.str.strip()

                if coluna_chave not in df_base.columns or coluna_chave not in df_comp.columns:
                    st.error(f"Erro Crítico: A coluna de inscrição '{coluna_chave}' não foi encontrada em um dos arquivos.")
                elif coluna_analise not in df_base.columns or coluna_analise not in df_comp.columns:
                    st.error(f"Erro Crítico: A coluna de valor '{coluna_analise}' não foi encontrada em um dos arquivos.")
                else:
                    def normalizar_sublote(serie):
                        return (serie.astype(str).str.strip().str.replace(r'[\.\-\/]', '', regex=True).str.lstrip('0'))

                    df_base['CHAVE_ALINHA'] = normalizar_sublote(df_base[coluna_chave])
                    df_comp['CHAVE_ALINHA'] = normalizar_sublote(df_comp[coluna_chave])

                    df_base['Valor_Ano_X'] = pd.to_numeric(df_base[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)
                    df_comp['Valor_Ano_X_Menos_1'] = pd.to_numeric(df_comp[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)

                    df_comp_limpo = df_comp.drop_duplicates(subset=['CHAVE_ALINHA'])
                    dict_valores_comp = dict(zip(df_comp_limpo['CHAVE_ALINHA'], df_comp_limpo['Valor_Ano_X_Menos_1']))

                    df_base['Valor_Comparar_Antigo'] = df_base['CHAVE_ALINHA'].map(dict_valores_comp)
                    df_base['Localizado_No_Comp'] = df_base['CHAVE_ALINHA'].isin(dict_valores_comp.keys())
                    df_base['Valor_Comparar_Calc_Antigo'] = df_base['Valor_Comparar_Antigo'].fillna(0.0)

                    v_recente = df_base['Valor_Ano_X'].values
                    v_antigo = df_base['Valor_Comparar_Calc_Antigo'].values

                    ambos_zeros = (v_recente == 0) & (v_antigo == 0)
                    surgiu_no_ano_x = (v_antigo == 0) & (v_recente != 0)
                    zerou_no_ano_x = (v_antigo != 0) & (v_recente == 0)

                    divisao_segura = np.divide(
                        (v_recente - v_antigo),
                        v_antigo,
                        out=np.zeros_like(v_antigo, dtype=float),
                        where=(v_recente != 0) & (v_antigo != 0)
                    ) * 100.0

                    variacao = np.where(
                        ambos_zeros, 0.0,
                        np.where(surgiu_no_ano_x, 100.0,
                        np.where(zerou_no_ano_x, -100.0, 
                        divisao_segura))
                    )

                    df_base['Variacao_%'] = np.round(variacao, 2)
                    variacao_absoluta = np.abs(df_base['Variacao_%'])

                    # Regra Atualizada: EXCLUI as linhas que estiverem DENTRO da faixa definida (ex: de 4.0 a 4.6)
                    esta_na_faixa_exclusao = (variacao_absoluta >= limite_inferior) & (variacao_absoluta <= limite_superior)

                    if incluir_novas:
                        condicao_manter = (~esta_na_faixa_exclusao & df_base['Localizado_No_Comp']) | (~df_base['Localizado_No_Comp'])
                    else:
                        condicao_manter = ~esta_na_faixa_exclusao & df_base['Localizado_No_Comp']

                    df_resultado = df_base[condicao_manter].copy()

                    df_resultado['Ocorrencia'] = np.where(
                        ~df_resultado['Localizado_No_Comp'], "Inscrição Nova (Sem histórico no Ano X-1)",
                        np.where(df_resultado['Variacao_%'] == 0, "Valores Idênticos",
                        np.where(df_resultado['Variacao_%'] > 0, "Aumento Aceito (Fora da Faixa)", "Redução Aceita (Fora da Faixa)"))
                    )

                    relatorio_original_gerado = pd.DataFrame({
                        'Inscricao_Sublote': df_resultado[coluna_chave],
                        'Tipo_Inconsistencia': df_resultado['Ocorrencia'],
                        'Valor_Ano_Recente': df_resultado['Valor_Ano_X'],
                        'Valor_Ano_Antigo': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Valor_Comparar_Antigo'], "Inexistente"),
                        'Diferenca_Percentual': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Variacao_%'].astype(str) + "%", "N/A")
                    })

                    relatorio_arquivo2_divergente_gerado = df_resultado.drop(
                        columns=['CHAVE_ALINHA', 'Valor_Ano_X', 'Valor_Comparar_Antigo', 'Localizado_No_Comp', 'Valor_Comparar_Calc_Antigo', 'Variacao_%', 'Ocorrencia'], 
                        errors='ignore'
                    )

                    st.session_state.relatorio_original = relatorio_original_gerado
                    st.session_state.relatorio_arquivo2_divergente = relatorio_arquivo2_divergente_gerado
                    st.session_state.total_base = len(df_base)

    if st.session_state.relatorio_original is not None:
        relatorio_original = st.session_state.relatorio_original
        relatorio_arquivo2_divergente = st.session_state.relatorio_arquivo2_divergente
        total_base = st.session_state.total_base

        if not relatorio_original.empty:
            st.success(f"Análise Concluída! Varremos {total_base} linhas e mantivemos {len(relatorio_original)} registros (excluindo os contidos na faixa de {limite_inferior}% a {limite_superior}%).")
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                st.subheader("1. Relatório Analítico Consistente")
                def colorir_linhas(row):
                    if "Inscrição Nova" in row['Tipo_Inconsistencia']:
                        return ['background-color: rgba(255, 165, 0, 0.15)'] * len(row)
                    elif "Aceito" in row['Tipo_Inconsistencia']:
                        return ['background-color: rgba(76, 175, 80, 0.1)'] * len(row)
                    return [''] * len(row)

                df_estilizado = relatorio_original.head(100).style.apply(colorir_linhas, axis=1)
                st.dataframe(df_estilizado)

                csv_original = relatorio_original.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(label="📥 Baixar Relatório Consistente (.csv)", data=csv_original, file_name="relatorio_registros_consistentes.csv", mime="text/csv", key="btn_download_1")
                
            with btn_col2:
                st.subheader("2. Linhas Brutas do Ano X (Validadas)")
                st.dataframe(relatorio_arquivo2_divergente.head(100))
                csv_arquivo2 = relatorio_arquivo2_divergente.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(label="📥 Baixar Linhas Validadas do Ano Recente (.csv)", data=csv_arquivo2, file_name="linhas_validadas_ano_x.csv", mime="text/csv", key="btn_download_2")
        else:
            st.success("Atenção: Nenhum registro atendeu aos critérios de consistência estipulados.")

# ============================================================
# MODO 2 - FILTRO POR PARÂMETRO (Sim/Não)
# ============================================================
elif tipo_analise == "Filtro por Parâmetro (Sim/Não)":
    st.sidebar.subheader("Parâmetros do Filtro")
    coluna_filtro = st.sidebar.text_input("Nome da coluna de análise", value="EXCLUIR").strip()
    parametro_exclusao = st.sidebar.text_input("Parâmetro a excluir", value="sim").strip()

    arquivo_filtro = st.file_uploader("Upload da Tabela para análise (CSV)", type=["csv"], key="upload_modo2")
    botao_filtrar = st.sidebar.button("⚡ Executar Filtro")

    if botao_filtrar:
        if not arquivo_filtro or not coluna_filtro or not parametro_exclusao:
            st.sidebar.error("Por favor, certifique-se de que carregou o arquivo e preencheu todos os campos.")
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

                    st.session_state.df_resultado_filtro = df_resultado_filtro_gerado
                    st.session_state.metricas_filtro = {"original": len(df_filtro), "excluido": registros_excluir.sum(), "permanece": len(df_resultado_filtro_gerado)}

    if st.session_state.df_resultado_filtro is not None:
        df_resultado_filtro = st.session_state.df_resultado_filtro
        m = st.session_state.metricas_filtro
        st.success(f"Análise concluída! Foram analisados {m['original']} registros, {m['excluido']} registros com o parâmetro '{parametro_exclusao}' foram excluídos.")
        st.subheader("Registros mantidos")
        st.dataframe(df_resultado_filtro.head(100))

        csv_filtro = df_resultado_filtro.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(label="📥 Baixar Resultado Filtrado (.csv)", data=csv_filtro, file_name="resultado_filtro_parametro.csv", mime="text/csv", key="btn_download_filtro")

# ============================================================
# MODO 3 - EXCLUIR POR VALOR ATÉ (TETO NUMÉRICO)
# ============================================================
elif tipo_analise == "Excluir por Valor Até (Teto)":
    st.sidebar.subheader("Parâmetros do Teto")
    coluna_valor_teto = st.sidebar.text_input("Nome da coluna de valor", value="VLR_IMPOSTO").strip()
    teto_num = st.sidebar.number_input("Excluir valores até (R$)", min_value=0.0, value=90000.0, step=1000.0)

    arquivo_teto = st.file_uploader("Upload da Tabela para análise (CSV)", type=["csv"], key="upload_modo3")
    botao_teto = st.sidebar.button("⚡ Executar Filtro de Teto")

    if botao_teto:
        if not arquivo_teto or not coluna_valor_teto:
            st.sidebar.error("Por favor, preencha a coluna de valor e carregue o arquivo.")
        else:
            with st.spinner("Analisando limites financeiros... Aguarde."):
                df_teto = pd.read_csv(arquivo_teto, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_teto.columns = df_teto.columns.str.strip()

                if coluna_valor_teto not in df_teto.columns:
                    st.error(f"Erro Crítico: A coluna '{coluna_valor_teto}' não foi encontrada.")
                else:
                    valores_num = pd.to_numeric(df_teto[coluna_valor_teto].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)
                    registros_excluir = (valores_num <= teto_num)
                    df_resultado_teto = df_teto[~registros_excluir].copy()

                    st.session_state.df_resultado_filtro = df_resultado_teto
                    st.session_state.metricas_filtro = {"original": len(df_teto), "excluido": registros_excluir.sum(), "permanece": len(df_resultado_teto)}

    if st.session_state.df_resultado_filtro is not None and tipo_analise == "Excluir por Valor Até (Teto)":
        df_resultado_filtro = st.session_state.df_resultado_filtro
        m = st.session_state.metricas_filtro
        st.success(f"Filtro aplicado! Analisados {m['original']} registros, excluídos {m['excluido']} registros com valor até R$ {teto_num:,.2f}.")
        st.subheader("Registros com valores acima do teto mantidos")
        st.dataframe(df_resultado_filtro.head(100))

        csv_filtro = df_resultado_filtro.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(label="📥 Baixar Tabela Filtrada por Teto (.csv)", data=csv_filtro, file_name="resultado_filtro_teto.csv", mime="text/csv", key="btn_download_teto")

# ============================================================
# MODO 4 - EXCLUIR POR ANO (DATA dd/mm/aaaa)
# ============================================================
else:
    st.sidebar.subheader("Parâmetros de Data")
    coluna_data = st.sidebar.text_input("Nome da coluna de data (dd/mm/aaaa)", value="DTA_ULTIMA_ATUALIZACAO").strip()
    ano_excluir = st.sidebar.text_input("Digitar o Ano a excluir (aaaa)", value="2026").strip()

    arquivo_data = st.file_uploader("Upload da Tabela para análise (CSV)", type=["csv"], key="upload_modo4")
    botao_data = st.sidebar.button("⚡ Executar Filtro por Ano")

    if botao_data:
        if not arquivo_data or not coluna_data or not ano_excluir:
            st.sidebar.error("Por favor, preencha todos os campos e carregue o arquivo.")
        else:
            with st.spinner("Filtrando datas temporais... Aguarde."):
                df_data = pd.read_csv(arquivo_data, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_data.columns = df_data.columns.str.strip()

                if coluna_data not in df_data.columns:
                    st.error(f"Erro Crítico: A coluna '{coluna_data}' não foi encontrada.")
                else:
                    # Extrai os últimos 4 dígitos no formato dd/mm/aaaa para isolar o ano
                    anos_extraidos = df_data[coluna_data].astype(str).str.strip().str.slice(-4)
                    registros_excluir = (anos_extraidos == ano_excluir)
                    df_resultado_data = df_data[~registros_excluir].copy()

                    st.session_state.df_resultado_filtro = df_resultado_data
                    st.session_state.metricas_filtro = {"original": len(df_data), "excluido": registros_excluir.sum(), "permanece": len(df_resultado_data)}

    if st.session_state.df_resultado_filtro is not None and tipo_analise == "Excluir por Ano (Data)":
        df_resultado_filtro = st.session_state.df_resultado_filtro
        m = st.session_state.metricas_filtro
        st.success(f"Filtro temporal concluído! Analisados {m['original']} registros, excluídos {m['excluido']} registros pertencentes ao ano de {ano_excluir}.")
        st.subheader("Registros mantidos (Anos restantes)")
        st.dataframe(df_resultado_filtro.head(100))

        csv_filtro = df_resultado_filtro.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(label="📥 Baixar Tabela Filtrada por Ano (.csv)", data=csv_filtro, file_name="resultado_filtro_ano.csv", mime="text/csv", key="btn_download_ano")
