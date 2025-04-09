import streamlit as st
import pandas as pd
import openai

# Configurações da página
st.set_page_config(page_title="Assistente virtual do NOVO PAC", layout="wide")

# Carregar dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

df = carregar_dados()

# Dicionário de sinônimos para o estágio
estagios_sinonimos = {
    "concluído": ["concluído", "finalizado", "entregue", "entregues", "pronto", "prontos"],
    "em execução": ["em execução", "andamento", "executando", "fazendo"],
    "em licitação / leilão": ["em licitação", "em leilão", "licitando", "leiloando"],
    "em ação preparatória": ["ação preparatória", "planejamento", "preparação", "não iniciado", "parado", "paralisado"]
}

# Função para mapear palavras-chave da pergunta para estágio
def identificar_estagio(pergunta):
    pergunta = pergunta.lower()
    for estagio, palavras in estagios_sinonimos.items():
        for palavra in palavras:
            if palavra in pergunta:
                return estagio
    return None

# Extrair município ou estado da pergunta
def extrair_local(pergunta):
    for uf in df['UF'].unique():
        if uf.lower() in pergunta.lower():
            return None, uf.upper()
    for municipio in df['Município'].unique():
        if municipio.lower() in pergunta.lower():
            return municipio, None
    return None, None

# Interface
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.markdown("## **Assistente virtual do NOVO PAC**")

st.write("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. 
Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.
""")

st.markdown("### O que você quer saber sobre o Novo PAC?")
st.write("Quantos empreendimentos tem na sua cidade ou seu estado? Quantos empreendimentos já foram entregues? Digite a sua pergunta:")

# Inicializa histórico
if "historico" not in st.session_state:
    st.session_state.historico = []

# Entrada do usuário
pergunta = st.chat_input("Digite sua pergunta aqui:")

if pergunta:
    st.session_state.historico.append({"usuario": pergunta})

    # Identificação dos parâmetros
    municipio, uf = extrair_local(pergunta)
    estagio = identificar_estagio(pergunta)

    resultado = df.copy()

    if municipio:
        resultado = resultado[resultado["Município"].str.lower() == municipio.lower()]
    elif uf:
        resultado = resultado[resultado["UF"].str.lower() == uf.lower()]

    if estagio:
        resultado = resultado[resultado["Estágio"].str.lower() == estagio.lower()]

    # Resposta
    if not resultado.empty:
        if "quantos" in pergunta.lower():
            st.success(f"Encontramos **{len(resultado)}** empreendimentos com base na sua pergunta.")
        else:
            st.success("Aqui estão os empreendimentos encontrados:")
        st.dataframe(resultado[["Empreendimento", "Estágio", "Executor"]].reset_index(drop=True))
    else:
        st.warning("Nenhum dado encontrado com base na sua pergunta.")

    st.session_state.historico.append({"bot": "Resposta apresentada acima."})
