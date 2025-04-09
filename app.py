import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import json
import re

# Inicialização da OpenAI com nova sintaxe
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configurar a página
st.set_page_config(page_title="Assistente do Novo PAC", layout="wide")

# Layout do cabeçalho
col1, col2 = st.columns([1, 6])

with col1:
    st.image("logo.png", width=300)

with col2:
    st.markdown("<h1 style='margin-bottom: 0; color: #004080;'>Assistente Virtual do <strong>NOVO PAC</strong></h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 18px; margin-top: 0;'>Tire dúvidas sobre obras e empreendimentos do Novo PAC em todo o Brasil.</p>", unsafe_allow_html=True)

st.markdown("---")

# Descrição destacada
st.markdown("""
<div style='background-color: #f0f4f8; padding: 15px; border-radius: 10px;'>
<p style='font-size:16px; margin: 0'>
O <strong>Novo PAC</strong> é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. 
Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.
</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### 📝 O que você quer saber sobre o Novo PAC?")
st.markdown("*Quantos empreendimentos tem na sua cidade ou seu estado? Quantos já foram entregues? Digite sua pergunta abaixo:*")

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

# Se a pergunta foi feita, processamos a resposta
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
        local = ""
        if parametros["municipio"]:
            local = f"na cidade de {parametros['municipio'].title()}"
        elif parametros["uf"]:
            local = f"no estado de {parametros['uf'].upper()}"

        estagio_desc = {
            "concluído": "entregues",
            "em execução": "em execução",
            "em licitação / leilão": "em licitação ou leilão",
            "em ação preparatória": "em fase preparatória"
        }

        tipo_info = estagio_desc.get(parametros["estagio"].lower(), "com os critérios especificados") if parametros["estagio"] else "com os critérios especificados"

        resposta = f"Foram encontrados **{len(dados_filtrados)} empreendimentos {tipo_info} {local}**.".strip()

        st.markdown(f"**🤖 Resposta:** {resposta}")
        st.session_state.historico.append({"role": "assistant", "content": resposta})

    else:
        resposta = f"Segue a lista de empreendimentos encontrados ({len(dados_filtrados)}):"

        st.markdown(f"**🤖 Resposta:** {resposta}")

        if not dados_filtrados.empty and parametros["acao"] != "contar":
            st.dataframe(dados_filtrados[["Empreendimento", "Estágio", "Executor", "Município", "UF"]])
            st.session_state.historico.append({"role": "assistant", "content": resposta})

# Exibe histórico da conversa durante a sessão (sem repetir perguntas anteriores)
if st.session_state.historico:
    st.markdown("### 💬 Conversa")
    for msg in st.session_state.historico:
        if msg["role"] == "user":
            st.markdown(f"**🧑 Você:** {msg['content']}")
        elif msg["role"] == "assistant":
            st.markdown(f"**🤖 Assistente:** {msg['content']}")

    # Mostra a tabela apenas se for uma listagem
    if not dados_filtrados.empty and parametros["acao"] != "contar":
        st.dataframe(dados_filtrados[["Empreendimento", "Estágio", "Executor", "Município", "UF"]])

    st.session_state.historico.append({"role": "assistant", "content": resposta})
