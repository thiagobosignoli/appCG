import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página web
st.set_page_config(page_title="Comparador de Tabelas Analítico", layout="wide")

st.title("📊 Comparador de Tabelas Analítico (High Performance)")
st.write("Vincula as linhas através da coluna de identificação e processa filtros e cruzamentos avançados de acordo com os parâmetros definidos.")

# Painel de controle lateral fixo
st.sidebar.header("Parâmetros da Análise")

# --- ESCOLHA DO TIPO DE ANÁLISE ---
tipo_analise = st.sidebar.radio(
    "Tipo de análise:",
    [
        "Comparação por percentual (%)",
        "Filtro por Parâmetro (Sim/Não)",
        "Excluir por Valor Até (Teto)",
        "Excluir por Data de atualização (ano)",
        "Excluir por Arquivo de Benefícios"
    ],
    key="tipo_analise_global"
)

# --- SISTEMA ANTISOBREPOSIÇÃO: DETECTOR DE MUDANÇAS DE INPUT ---
def verificar_e_limpar_estado(chave_atual, valor_atual):
    if f"prev_{chave_atual}" not in st.session_state:
        st.session_state[f"prev_{chave_atual}"] = valor_atual
    elif st.session_state[f"prev_{chave_atual}"] != valor_atual:
        st.session_state[f"prev_{chave_atual}"] = valor_atual
        for k in ["relatorio_original", "relatorio_arquivo2_divergente", "total_base", "df_resultado_filtro", "metricas_filtro", "df_resultado_valor", "metricas_valor", "df_resultado_ano", "metricas_ano", "df_resultado_beneficios", "metricas_beneficios"]:
            if k in st.session_state:
                st.session_state[k] = None

# Monitora mudança de tipo de análise
verificar_e_limpar_estado("tipo_analise", tipo_analise)

# Inicializa as variáveis globais de estado da sessão
for k in ["relatorio_original", "relatorio_arquivo2_divergente", "total_base", "df_resultado_filtro", "metricas_filtro", "df_resultado_valor", "metricas_valor", "df_resultado_ano", "metricas_ano", "df_resultado_beneficios", "metricas_beneficios"]:
    if k not in st.session_state:
        st.session_state[k] = None
        
# ============================================================
# MODO 1 - COMPARAÇÃO POR PERCENTUAL (Com Faixa de Exclusão)
# ============================================================
if tipo_analise == "Comparação por percentual (%)":

    st.sidebar.subheader("Faixa de Exclusão Percentual")
    col_inf, col_sup = st.sidebar.columns(2)
    with col_inf:
        limite_inferior = st.number_input("Limite Inferior (X%)", min_value=0.0, max_value=100.0, value=4.0, step=0.1)
    with col_sup:
        limite_superior = st.number_input("Limite Superior (Y%)", min_value=0.0, max_value=100.0, value=4.6, step=0.1)

    incluir_novas = st.sidebar.checkbox(
        "Incluir novas inscrições (Inexistentes no Ano Anterior)", 
        value=False,
        help="Se marcado, mantém na tabela final os registros novos que não possuem histórico no passado."
    )

    coluna_chave = st.sidebar.text_input("Nome da coluna de Inscrição / Chave", value="NUM_INSCRICAO").strip()
    coluna_analise = st.sidebar.text_input("Nome da coluna de Valor / Análise", value="VLR_IMPOSTO").strip()

    col1, col2 = st.columns(2)
    with col1:
        arquivo_base = st.file_uploader("Upload da Tabela Base - Data mais Recente (CSV)", type=["csv"], key="upload_base_modo1")
    with col2:
        arquivo_comparar = st.file_uploader("Upload da Tabela de Comparação - Data mais antiga (CSV)", type=["csv"], key="upload_comp_modo1")

    botao_executar = st.sidebar.button("⚡ Executar Comparação Fiel")

    if botao_executar:
        if not arquivo_base or not arquivo_comparar:
            st.sidebar.error("Por favor, faça o upload de ambos os arquivos CSV antes de executar.")
        elif limite_inferior > limite_superior:
            st.sidebar.error("Erro: O Limite Inferior não pode ser maior do que o Limite Superior.")
        elif not coluna_chave or not coluna_analise:
            st.sidebar.error("Por favor, preencha os nomes de ambas as colunas na barra lateral.")
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

                    df_base['Valor_Ano'] = pd.to_numeric(df_base[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)
                    df_comp['Valor_Ano_Menos_1'] = pd.to_numeric(df_comp[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)

                    df_comp_limpo = df_comp.drop_duplicates(subset=['CHAVE_ALINHA'])
                    dict_valores_comp = dict(zip(df_comp_limpo['CHAVE_ALINHA'], df_comp_limpo['Valor_Ano_Menos_1']))

                    df_base['Valor_Comparar_Antigo'] = df_base['CHAVE_ALINHA'].map(dict_valores_comp)
                    df_base['Localizado_No_Comp'] = df_base['CHAVE_ALINHA'].isin(dict_valores_comp.keys())
                    df_base['Valor_Comparar_Calc_Antigo'] = df_base['Valor_Comparar_Antigo'].fillna(0.0)

                    v_recente = df_base['Valor_Ano'].values
                    v_antigo = df_base['Valor_Comparar_Calc_Antigo'].values

                    ambos_zeros = (v_recente == 0) & (v_antigo == 0)
                    surgiu_no_ano_x = (v_antigo == 0) & (v_recente != 0)
                    zerou_no_ano_x = (v_antigo != 0) & (v_recente == 0)

                    divisao_segura = np.divide((v_recente - v_antigo), v_antigo, out=np.zeros_like(v_antigo, dtype=float), where=(v_recente != 0) & (v_antigo != 0)) * 100.0
                    variacao = np.where(ambos_zeros, 0.0, np.where(surgiu_no_ano_x, 100.0, np.where(zerou_no_ano_x, -100.0, divisao_segura)))

                    df_base['Variacao_%'] = np.round(variacao, 2)
                    variacao_absoluta = np.abs(df_base['Variacao_%'])

                    esta_na_faixa_exclusao = (variacao_absoluta >= limite_inferior) & (variacao_absoluta <= limite_superior)

                    if incluir_novas:
                        condicao_manter = (~esta_na_faixa_exclusao & df_base['Localizado_No_Comp']) | (~df_base['Localizado_No_Comp'])
                    else:
                        condicao_manter = ~esta_na_faixa_exclusao & df_base['Localizado_No_Comp']

                    df_resultado = df_base[condicao_manter].copy()

                    df_resultado['Ocorrencia'] = np.where(
                        ~df_resultado['Localizado_No_Comp'], "Inscrição Nova (Sem histórico no Ano Anterior)",
                        np.where(df_resultado['Variacao_%'] == 0, "Valores Idênticos",
                        np.where(df_resultado['Variacao_%'] > 0, "Aumento Aceito (Fora da Faixa)", "Redução Aceita (Fora da Faixa)"))
                    )

                    relatorio_original_gerado = pd.DataFrame({
                        'Inscricao_Sublote': df_resultado[coluna_chave],
                        'Tipo_Inconsistencia': df_resultado['Ocorrencia'],
                        'Valor_Ano_Recente': df_resultado['Valor_Ano'],
                        'Valor_Ano_Antigo': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Valor_Comparar_Antigo'], "Inexistente"),
                        'Diferenca_Percentual': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Variacao_%'].astype(str) + "%", "N/A")
                    })

                    relatorio_arquivo2_divergente_gerado = df_resultado.drop(
                        columns=['CHAVE_ALINHA', 'Valor_Ano', 'Valor_Comparar_Antigo', 'Localizado_No_Comp', 'Valor_Comparar_Calc_Antigo', 'Variacao_%', 'Ocorrencia'], 
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
                st.download_button(label="📥 Baixar Linhas Validadas do Ano Recente (.csv)", data=csv_arquivo2, file_name="linhas_validadas_ano_Recente.csv", mime="text/csv", key="btn_download_2")
        else:
            st.warning("Atenção: Nenhum registro atendeu aos critérios de consistência estipulados.")

# ============================================================
# MODO 2 - FILTRO POR PARÂMETRO (Sim/Não)
# ============================================================
elif tipo_analise == "Filtro por Parâmetro (Sim/Não)":
    st.sidebar.subheader("Parâmetros do Filtro")
    coluna_filtro = st.sidebar.text_input("Nome da coluna de análise", value="FLG_HOUVE_DEPRECIACAO").strip()
    parametro_exclusao = st.sidebar.text_input("Parâmetro a excluir", value="S").strip()

    arquivo_filtro = st.file_uploader("Upload da Tabela para análise (CSV)", type=["csv"], key="upload_modo2")
    if arquivo_filtro:
        verificar_e_limpar_estado("file_modo2", arquivo_filtro.name)
        
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
    coluna_valor_teto = st.sidebar.text_input("Nome da coluna de valor", value="VLR_VENAL_IMOVEL_TRIB").strip()
    teto_num = st.sidebar.number_input("Excluir valores até (R$)", min_value=0.0, value=90000.0, step=1000.0)

    arquivo_teto = st.file_uploader("Upload da Tabela para análise (CSV)", type=["csv"], key="upload_modo3")
    if arquivo_teto:
        verificar_e_limpar_estado("file_modo3", arquivo_teto.name)
         
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
                    df_resultado_teto_gerado = df_teto[~registros_excluir].copy()

                    st.session_state.df_resultado_valor = df_resultado_teto_gerado
                    st.session_state.metricas_valor = {"original": len(df_teto), "excluido": registros_excluir.sum(), "permanece": len(df_resultado_teto_gerado)}

    if st.session_state.df_resultado_valor is not None:
        df_resultado_valor = st.session_state.df_resultado_valor
        m = st.session_state.metricas_valor
        st.success(f"Filtro aplicado! Analisados {m['original']} registros, excluídos {m['excluido']} registros com valor até R$ {teto_num:,.2f}.")
        st.subheader("Registros com valores acima do teto mantidos")
        st.dataframe(df_resultado_valor.head(100))

        csv_filtro = df_resultado_valor.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(label="📥 Baixar Tabela Filtrada por Valor (.csv)", data=csv_filtro, file_name="resultado_filtro_teto.csv", mime="text/csv", key="btn_download_teto")

# ============================================================
# MODO 4 - EXCLUIR POR ANO (DATA dd/mm/aaaa)
# ============================================================
elif tipo_analise == "Excluir por Data de atualização (ano)":
    st.sidebar.subheader("Parâmetros de Data")
    coluna_data = st.sidebar.text_input("Nome da coluna de data (dd/mm/aaaa)", value="DTA_ULTIMA_ATUALIZACAO").strip()
    ano_excluir = st.sidebar.text_input("Digitar o Ano a excluir (aaaa)", value="2026").strip()

    arquivo_data = st.file_uploader("Upload da Tabela para análise (CSV)", type=["csv"], key="upload_modo4")
    if arquivo_data:
        verificar_e_limpar_estado("file_modo4", arquivo_data.name)
        
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
                    anos_extraidos = df_data[coluna_data].astype(str).str.strip().str.slice(-4)
                    registros_excluir = (anos_extraidos == ano_excluir)
                    df_resultado_data_gerado = df_data[~registros_excluir].copy()

                    st.session_state.df_resultado_ano = df_resultado_data_gerado
                    st.session_state.metricas_ano = {"original": len(df_data), "excluido": registros_excluir.sum(), "permanece": len(df_resultado_data_gerado)}

    if st.session_state.df_resultado_ano is not None:
        df_resultado_ano = st.session_state.df_resultado_ano
        m = st.session_state.metricas_ano
        st.success(f"Filtro de data concluído! Analisados {m['original']} registros, excluídos {m['excluido']} registros pertencentes ao ano de {ano_excluir}.")
        st.subheader("Registros mantidos (Anos restantes)")
        st.dataframe(df_resultado_ano.head(100))

        csv_filtro = df_resultado_ano.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(label="📥 Baixar Tabela Filtrada por Ano (.csv)", data=csv_filtro, file_name="resultado_filtro_ano.csv", mime="text/csv", key="btn_download_ano")

# ============================================================
# MODO 5 - EXCLUIR POR ARQUIVO DE BENEFÍCIOS
# ============================================================
else:
    st.sidebar.subheader("Parâmetros de Benefícios")
    coluna_chave_beneficio = st.sidebar.text_input("Nome da coluna de Inscrição / Chave", value="NUM_INSCRICAO", key="chave_beneficios").strip()

    col1, col2 = st.columns(2)
    with col1:
        arquivo_recente = st.file_uploader("Upload da Tabela do Ano Corrente (CSV)", type=["csv"], key="upload_recente_modo5")
    with col2:
        arquivo_beneficios = st.file_uploader("Upload da Tabela de Benefícios (CSV)", type=["csv"], key="upload_beneficios_modo5")

    if arquivo_recente:
        verificar_e_limpar_estado("file_modo5", arquivo_recente.name)

    botao_beneficios = st.sidebar.button("⚡ Executar Expurgo de Benefícios")

    if botao_beneficios:
        if not arquivo_recente or not arquivo_beneficios:
            st.sidebar.error("Por favor, faça o upload de ambos os arquivos CSV antes de executar.")
        elif not coluna_chave_beneficio:
            st.sidebar.error("Por favor, insira o nome da coluna de identificação na barra lateral.")
        else:
            with st.spinner("Cruzando inscrições com a base de benefícios... Aguarde."):
                df_rec = pd.read_csv(arquivo_recente, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_ben = pd.read_csv(arquivo_beneficios, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)

                df_rec.columns = df_rec.columns.str.strip()
                df_ben.columns = df_ben.columns.str.strip()

                if coluna_chave_beneficio not in df_rec.columns or coluna_chave_beneficio not in df_ben.columns:
                    st.error(f"Erro Crítico: A coluna de inscrição '{coluna_chave_beneficio}' não foi encontrada em um dos arquivos.")
                else:
                    def normalizar_sublote(serie):
                        return (serie.astype(str).str.strip().str.replace(r'[\.\-\/]', '', regex=True).str.lstrip('0'))

                    df_rec['CHAVE_ALINHA'] = normalizar_sublote(df_rec[coluna_chave_beneficio])
                    df_ben['CHAVE_ALINHA'] = normalizar_sublote(df_ben[coluna_chave_beneficio])

                    chaves_beneficios = set(df_ben['CHAVE_ALINHA'].dropna().unique())
                    registros_excluir = df_rec['CHAVE_ALINHA'].isin(chaves_beneficios)
                    
                    df_resultado_beneficios_gerado = df_rec[~registros_excluir].copy()

                    if 'CHAVE_ALINHA' in df_resultado_beneficios_gerado.columns:
                        df_resultado_beneficios_gerado = df_resultado_beneficios_gerado.drop(columns=['CHAVE_ALINHA'])

                    st.session_state.df_resultado_beneficios = df_resultado_beneficios_gerado
                    st.session_state.metricas_beneficios = {
                        "original": len(df_rec),
                        "excluido": registros_excluir.sum(),
                        "permanece": len(df_resultado_beneficios_gerado)
                    }

    if st.session_state.df_resultado_beneficios is not None:
        df_resultado_beneficios = st.session_state.df_resultado_beneficios
        m = st.session_state.metricas_beneficios
        st.success(f"Expurgo Concluído! Analisados {m['original']} registros da tabela corrente. Foram localizados e excluídos {m['excluido']} registros constantes no arquivo de benefícios.")
        st.subheader("Tabela do Ano Corrente Filtrada (Sem Beneficiários)")
        st.dataframe(df_resultado_beneficios.head(100))

        csv_beneficios = df_resultado_beneficios.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(label="📥 Baixar Tabela Filtrada (.csv)", data=csv_beneficios, file_name="tabela_sem_beneficios.csv", mime="text/csv", key="btn_download_beneficios")
