import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página web
st.set_page_config(page_title="Comparador de Tabelas Gigantes", layout="wide")

st.title("📊 Comparador de Tabelas Analítico (Alta Performance)")
st.write("Suba arquivos CSV com até milhões de linhas e compare valores com margem percentual.")

# Painel de controle lateral para as configurações
st.sidebar.header("Configurações do Filtro")
margem_limite = st.sidebar.number_input("Defina o limite de variação aceitável (X%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
coluna_chave = st.sidebar.text_input("Nome da Coluna Identificadora (ex: ID, CPF, Chave)", value="ID")

# Campos de Upload na tela principal
col1, col2 = st.columns(2)
with col1:
    arquivo_base = st.file_uploader("Upload da Tabela Base (CSV)", type=["csv"])
with col2:
    arquivo_comparar = st.file_uploader("Upload da Tabela de Comparação (CSV)", type=["csv"])

if arquivo_base and arquivo_comparar:
    with st.spinner("Processando e cruzando tabelas na velocidade do Python... Aguarde."):
        # Carrega os CSVs na memória de forma otimizada
        df_base = pd.read_csv(arquivo_base, dtype={coluna_chave: str})
        df_comp = pd.read_csv(arquivo_comparar, dtype={coluna_chave: str})
        
        # Faz o cruzamento (Merge) das duas tabelas usando a coluna chave
        df_junto = pd.merge(df_base, df_comp, on=coluna_chave, suffixes=('_Base', '_Comp'))
        
        # Identifica as colunas numéricas comuns que precisam ser comparadas
        colunas_base = [col for col in df_base.columns if col != coluna_chave and col in df_comp.columns]
        
        if len(colunas_base) == 0:
            st.error("Não foram encontradas colunas com nomes idênticos para comparação entre os arquivos.")
        else:
            linhas_divergentes = []
            
            # Varre as 15 colunas matematicamente de forma vetorizada (Rápido!)
            for col in colunas_base:
                c_base = f"{col}_Base"
                c_comp = f"{col}_Comp"
                
                # Converte para numérico ignorando erros de texto
                df_junto[c_base] = pd.to_numeric(df_junto[c_base], errors='coerce').fillna(0)
                df_junto[c_comp] = pd.to_numeric(df_junto[c_comp], errors='coerce').fillna(0)
                
                # Calcula a variação percentual absoluta
                # Evita divisão por zero se a base for 0
                df_junto[f'Var_{col}_%'] = np.where(
                    df_junto[c_base] != 0,
                    (abs(df_junto[c_comp] - df_junto[c_base]) / df_junto[c_base]) * 100,
                    np.where(df_junto[c_comp] != 0, 100.0, 0.0) # Se base=0 e comp!=0, variação é 100%
                )
            
            # Filtra apenas as linhas onde PELO MENOS UMA das colunas passou do limite X%
            condicoes = [df_junto[f'Var_{col}_%'] > margem_limite for col in colunas_base]
            mascara_divergencias = np.logical_or.reduce(condicoes)
            
            df_resultado = df_junto[mascara_divergencias]
            
            # Exibe o painel de resultados na tela
            st.success(f"Análise Concluída! Das {len(df_junto)} linhas cruzadas, encontramos {len(df_resultado)} linhas que divergiram mais do que {margem_limite}%.")
            
            # Mostra uma amostra das primeiras linhas divergentes
            st.subheader("Amostra das Linhas Divergentes")
            st.dataframe(df_resultado.head(100)) # Exibe as primeiras 100 linhas na tela de forma interativa
            
            # Botão para exportar o relatório inteiro de divergências de volta para CSV
            csv_resultado = df_resultado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Relatório Completo de Divergências (.csv)",
                data=csv_resultado,
                file_name="relatorio_divergencias.csv",
                mime="text/csv"
            )
