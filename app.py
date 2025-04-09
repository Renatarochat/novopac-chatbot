import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import json
import re

# Inicialização da OpenAI com nova sintaxe
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Página inicial
st.set_page_config(page_title="Assistente Novo PAC")
st.image("logo.png", width=80)

st.markdown("## **Assistente virtual do NOVO PAC**")
st.markdown(
    "O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. "
    "Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais."
)

st.markdown("---")
st.markdown("### O que você quer saber sobre o Novo PAC?")
st.markdown("*Quantos empreendimentos tem na sua cidade ou seu estado? Quantos empreendimentos já foram entregues? Digite a sua pergunta:*")

# Carregar dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Histórico de conversa (oculto)
if "historico" not in st.session_state:
    st.session_state.historico = []

# Função para interpretar a pergunta
def interpretar_pergunta(pergunta):
    prompt = f"""
Você é um assistente que ajuda a filtrar dados de uma planilha de empreendimentos do governo chamada Novo PAC. 
A planilha tem as colunas: Eixo, Subeixo, UF, Município, Empreendimento, Modalidade, Classificação, Estágio, Executor.

O usuário fará perguntas como: 
- "Quantos empreendimentos foram entregues em Belo Horizonte?"
- "Quais empreendimentos estão em andamento no Ceará?"
- "Quero ver a lista de obras concluídas no Rio de Janeiro."

Com base na pergunta abaixo, identifique:

1. Ação: "listar" ou "contar"
2. Município (se houver)
3. UF (se houver)
4. Estágio desejado (Ex: "Concluído", "Em execução", etc.)

Retorne apenas um JSON com os campos: acao, municipio, uf, estagio.

Pergunta: \"{pergunta}\"
"""

    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um assistente de análise de dados."},
            {"role": "user", "content": prompt}
        ]
    )

    texto = resposta.choices[0].message.content
    try:
        json_str = re.search(r"\{.*\}", texto, re.DOTALL).group()
        return json.loads(json_str)
    except:
        return {"acao": "listar", "municipio": None, "uf": None, "estagio": None}

# Interface de pergunta
pergunta = st.chat_input("Digite sua pergunta:")

if pergunta:
    st.session_state.historico.append({"role": "user", "content": pergunta})

    parametros = interpretar_pergunta(pergunta)

    dados_filtrados = data.copy()

    if parametros["municipio"]:
        dados_filtrados = dados_filtrados[dados_filtrados["Município"].str.lower() == parametros["municipio"].lower()]
    if parametros["uf"]:
        dados_filtrados = dados_filtrados[dados_filtrados["UF"].str.lower() == parametros["uf"].lower()]
    if parametros["estagio"]:
        dados_filtrados = dados_filtrados[dados_filtrados["Estágio"].str.lower() == parametros["estagio"].lower()]

    if dados_filtrados.empty:
        resposta = "Não encontrei empreendimentos com os critérios especificados."
    elif parametros["acao"] == "contar":
        resposta = f"Foram encontrados **{len(dados_filtrados)} empreendimentos** com os critérios especificados."
    else:
        resposta = f"Segue a lista de empreendimentos encontrados ({len(dados_filtrados)}):"

    st.markdown(f"**🤖 Resposta:** {resposta}")

    if not dados_filtrados.empty and parametros["acao"] == "listar":
        st.dataframe(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio", "Executor"]])

    st.session_state.historico.append({"role": "assistant", "content": resposta})
