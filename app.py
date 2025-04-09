import streamlit as st
import pandas as pd
import openai
import os

# Configurações da página
st.set_page_config(page_title="Assistente virtual do NOVO PAC", layout="wide")

# Logo + Título
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.markdown("## **Assistente virtual do NOVO PAC**")

# Descrição
st.write("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. 
Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.
""")

st.markdown("### O que você quer saber sobre o Novo PAC?")
st.write("Quantos empreendimentos tem na sua cidade ou seu estado? Quantos empreendimentos já foram entregues? Digite a sua pergunta:")

# Carregar dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

df = carregar_dados()

# Inicializa histórico da conversa
if "historico" not in st.session_state:
    st.session_state.historico = []

# Função para interpretar pergunta usando GPT
def interpretar_pergunta(pergunta):
    openai.api_key = os.getenv("OPENAI_API_KEY")

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

    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Você é um assistente de análise de dados."},
                  {"role": "user", "content": prompt}]
    )

    import json
    import re

    texto = resposta.choices[0].message['content']
    try:
        json_str = re.search(r"\{.*\}", texto, re.DOTALL).group()
        return json.loads(json_str)
    except:
        return {"acao": "listar", "municipio": None, "uf": None, "estagio": None}

# Caixa de entrada do usuário
pergunta = st.chat_input("Digite sua pergunta aqui:")

if pergunta:
    st.session_state.historico.append({"usuario": pergunta})

    parametros = interpretar_pergunta(pergunta)

    resultado = df.copy()

    if parametros["municipio"]:
        resultado = resultado[resultado["Município"].str.lower() == parametros["municipio"].lower()]
    if parametros["uf"]:
        resultado = resultado[resultado["UF"].str.lower() == parametros["uf"].lower()]
    if parametros["estagio"]:
        resultado = resultado[resultado["Estágio"].str.lower() == parametros["estagio"].lower()]

    if not resultado.empty:
        if parametros["acao"] == "contar":
            st.success(f"Encontramos **{len(resultado)}** empreendimentos com base na sua pergunta.")
        else:
            st.success("Aqui estão os empreendimentos encontrados:")
            st.dataframe(resultado[["Empreendimento", "Estágio", "Executor", "Município", "UF"]].reset_index(drop=True))
    else:
        st.warning("Nenhum dado encontrado com base na sua pergunta.")

    st.session_state.historico.append({"bot": "Resposta apresentada acima."})
