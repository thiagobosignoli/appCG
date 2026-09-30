import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página web
st.set_page_config(page_title="Comparador de Tabelas Analítico", layout="wide")

st.title("📊 Comparador de Tabelas Analítico (Alta Performance)")
st.write("Suba arquivos CSV com até milhões de linhas e compare valores vinculando as colunas e identificando as divergências entre períodos distintos.")

# Painel de controle lateral fixo
st.sidebar.header("Parâmetros da Análise")
margem_limite = st.sidebar.number_input("Defina a variação máxima aceitável (X%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

# --- NOVAS CAIXAS DE TEXTO PARA OS NOMES DAS COLUNAS ---
coluna_chave = st.sidebar.text_input("Nome da coluna de Inscrição / Chave", value="IDF_SUBLOTE").strip()
coluna_analise = st.sidebar.text_input("Nome da coluna de Valor / Análise", value="VLR_IMPOSTO").strip()

# Campos de Upload na tela principal com os novos labels solicitados
col1, col2 = st.columns(2)
with col1:
    arquivo_base = st.file_uploader("Upload da Tabela Base - Data mais Recente (CSV)", type=["csv"])
with col2:
    arquivo_comparar = st.file_uploader("Upload da Tabela de Comparação - Data mais antiga (CSV)", type=["csv"])

# Inicializa as variáveis de estado para guardar os relatórios na sessão
if 'relatorio_original' not in st.session_state:
    st.session_state.relatorio_original = None
if 'relatorio_arquivo2_divergente' not in st.session_state:
    st.session_state.relatorio_arquivo2_divergente = None
if 'total_base' not in st.session_state:
    st.session_state.total_base = 0

if arquivo_base and arquivo_comparar:
    if st.sidebar.button("⚡ Executar Comparação Fiel"):
        # Garante que o usuário preencheu ambos os campos antes de rodar
        if not coluna_chave or not coluna_analise:
            st.error("Por favor, preencha os nomes de ambas as colunas na barra lateral antes de executar.")
        else:
            with st.spinner("Localizando inscrições e cruzando dados fiscais... Aguarde."):
                
                # 1. Carrega os arquivos completos como texto para preservar a integridade dos dados originais
                df_base = pd.read_csv(arquivo_base, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                df_comp = pd.read_csv(arquivo_comparar, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', dtype=str)
                
                # Limpa espaços em branco invisíveis nos cabeçalhos das colunas
                df_base.columns = df_base.columns.str.strip()
                df_comp.columns = df_comp.columns.str.strip()
                
                # 2. Validação estrita de existência das colunas especificadas
                if coluna_chave not in df_base.columns or coluna_chave not in df_comp.columns:
                    st.error(f"Erro Crítico: A coluna de inscrição '{coluna_chave}' não foi encontrada em um dos arquivos.")
                elif coluna_analise not in df_base.columns or coluna_analise not in df_comp.columns:
                    st.error(f"Erro Crítico: A coluna de valor '{coluna_analise}' não foi encontrada em um dos arquivos.")
                else:
                    
                    # --- PADRONIZAÇÃO DAS CHAVES (Garante o vínculo de '0010' com '10') ---
                    def normalizar_sublote(serie):
                        return serie.astype(str).str.strip().str.replace(r'[\.\-\/]', '', regex=True).str.lstrip('0')

                    df_base['CHAVE_ALINHA'] = normalizar_sublote(df_base[coluna_chave])
                    df_comp['CHAVE_ALINHA'] = normalizar_sublote(df_comp[coluna_chave])
                    
                    # --- TRATAMENTO DOS VALORES NUMÉRICOS ---
                    df_base['Valor_Base_Num'] = pd.to_numeric(df_base[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)
                    df_comp['Valor_Comp_Num'] = pd.to_numeric(df_comp[coluna_analise].str.replace(',', '.', regex=True), errors='coerce').fillna(0.0)
                    
                    # 3. Indexa a tabela de comparação em um dicionário de busca rápida
                    df_comp_limpo = df_comp.drop_duplicates(subset=['CHAVE_ALINHA'])
                    dict_valores_comp = dict(zip(df_comp_limpo['CHAVE_ALINHA'], df_comp_limpo['Valor_Comp_Num']))
                    
                    # 4. Mapeamento Direto (Busca a Inscrição da data mais recente dentro do arquivo da data mais antiga)
                    df_base['Valor_Comparar'] = df_base['CHAVE_ALINHA'].map(dict_valores_comp)
                    df_base['Localizado_No_Comp'] = df_base['CHAVE_ALINHA'].isin(dict_valores_comp.keys())
                    df_base['Valor_Comparar_Calc'] = df_base['Valor_Comparar'].fillna(0.0)
                    
                    # 5. Cálculo Vetorizado da Variação Percentual
                    v_base = df_base['Valor_Base_Num'].values
                    v_comp = df_base['Valor_Comparar_Calc'].values
                    
                    variacao = np.where(
                        v_base != 0,
                        (np.abs(v_comp - v_base) / v_base) * 100,
                        np.where(v_comp != 0, 100.0, 0.0)
                    )
                    df_base['Variacao_%'] = np.round(variacao, 2)
                    
                    # 6. Separa apenas os Erros: Passou de X% OU a inscrição do Arquivo mais recente sumiu no Arquivo mais antigo
                    condicao_divergencia = (df_base['Variacao_%'] > margem_limite) | (~df_base['Localizado_No_Comp'])
                    df_resultado = df_base[condicao_divergencia].copy()
                    
                    # Classifica o tipo de ocorrência encontrada
                    df_resultado['Ocorrencia'] = np.where(
                        df_resultado['Localizado_No_Comp'],
                        "Variação acima do limite estipulado",
                        "Inscrição ausente na Data Mais Antiga"
                    )
                    
                    # --- RELATÓRIO 1: Consolida o seu relatório analítico original com nomenclaturas temporais ---
                    relatorio_original_gerado = pd.DataFrame({
                        'Inscricao_Sublote': df_resultado[coluna_chave],
                        'Tipo_Inconsistencia': df_resultado['Ocorrencia'],
                        'Valor_Data_Recente': df_resultado['Valor_Base_Num'],
                        'Valor_Data_Antiga': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Valor_Comparar'], "Não Localizado"),
                        'Diferenca_Percentual': np.where(df_resultado['Localizado_No_Comp'], df_resultado['Variacao_%'].astype(str) + "%", "N/A")
                    })
                    
                    # --- RELATÓRIO 2: Extração completa das linhas originais da Tabela de Comparação (Data mais antiga) ---
                    chaves_com_erro = df_resultado['CHAVE_ALINHA'].unique()
                    relatorio_arquivo2_divergente_gerado = df_comp[df_comp['CHAVE_ALINHA'].isin(chaves_com_erro)].copy()
                    
                    # Limpa a coluna temporária de alinhamento antes de disponibilizar para download
                    if 'CHAVE_ALINHA' in relatorio_arquivo2_divergente_gerado.columns:
                        relatorio_arquivo2_divergente_gerado = relatorio_arquivo2_divergente_gerado.drop(columns=['CHAVE_ALINHA'])
                    
                    # Salva os resultados no estado da sessão para não sumirem após o download
                    st.session_state.relatorio_original = relatorio_original_gerado
                    st.session_state.relatorio_arquivo2_divergente = relatorio_arquivo2_divergente_gerado
                    st.session_state.total_base = len(df_base)

    # --- BLOCO DE EXIBIÇÃO E DOWNLOAD (Fora do botão, baseado na Session State) ---
    if st.session_state.relatorio_original is not None:
        relatorio_original = st.session_state.relatorio_original
        relatorio_arquivo2_divergente = st.session_state.relatorio_arquivo2_divergente
        total_base = st.session_state.total_base
        
        if not relatorio_original.empty:
            st.success(f"Análise Concluída! Varremos {total_base} linhas e isolamos {len(relatorio_original)} divergências.")
            
            # Layout em colunas para os dois botões ficarem lado a lado
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                st.subheader("1. Relatório Analítico Calculado")
                st.dataframe(relatorio_original.head(100))
                csv_original = relatorio_original.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Relatório Analítico (.csv)",
                    data=csv_original,
                    file_name="relatorio_das_divergencias.csv",
                    mime="text/csv",
                    key="btn_download_1"
                )
                
            with btn_col2:
                st.subheader("2. Linhas Brutas da Data mais antiga")
                st.dataframe(relatorio_arquivo2_divergente.head(100))
                csv_arquivo2 = relatorio_arquivo2_divergente.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Linhas Extraídas Divergentes (.csv)",
                    data=csv_arquivo2,
                    file_name="linhas_divergentes_data_antiga.csv",
                    mime="text/csv",
                    key="btn_download_2"
                )
        else:
            st.success(f"Parabéns! Todos os registros foram confrontados e os valores em '{coluna_analise}' estão consistentes dentro da margem de {margem_limite}%.")
            
