import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import json
import re
import unicodedata

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

# Histórico de conversa
if "historico" not in st.session_state:
    st.session_state.historico = []

# 🔄 Agora a função está fora do if!
def interpretar_pergunta(pergunta):
    system_prompt = """
    Você é um assistente inteligente que ajuda a entender perguntas sobre uma base de dados do programa Novo PAC.
    A planilha possui os campos: Eixo, Subeixo, UF, Município, Empreendimento, Modalidade, Classificação, Estágio, Executor.
    O campo "Estágio" pode conter: "Em ação preparatória", "Em licitação / leilão", "Em execução", "Concluído".
    
    Sua tarefa é retornar um JSON com os seguintes campos:
    - municipio
    - uf
    - estagio (com base no significado do usuário: "entregues" = "Concluído")
    - acao ("contar" ou "listar")

    Responda apenas com o JSON.
    """

    response = client.chat.completions.create(  # 👈 Aqui também já está usando o nome certo
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pergunta}
        ]
    )

    try:
        resposta_bruta = response.choices[0].message.content.strip()
        parametros = eval(resposta_bruta)
    except Exception:
        parametros = {"municipio": None, "uf": None, "estagio": None, "acao": "listar"}
    return parametros
        
# Interface de pergunta
pergunta = st.chat_input("Digite sua pergunta:")

# Processar a pergunta
if pergunta:
    st.session_state.historico.append({"role": "user", "content": pergunta})

        # Recupera contexto anterior
    parametros_anteriores = st.session_state.get("parametros_anteriores", {
        "municipio": None,
        "uf": None,
        "estagio": None,
        "acao": None
    })
    
    parametros = interpretar_pergunta(pergunta)
    
    # Mapeamento de estados por nome para sigla
    mapa_estados = {
        "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM", "bahia": "BA",
        "ceará": "CE", "distrito federal": "DF", "espírito santo": "ES", "goiás": "GO",
        "maranhão": "MA", "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
        "pará": "PA", "paraíba": "PB", "paraná": "PR", "pernambuco": "PE", "piauí": "PI",
        "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS",
        "rondônia": "RO", "roraima": "RR", "santa catarina": "SC", "são paulo": "SP",
        "sergipe": "SE", "tocantins": "TO"
    }

    # Converte nome do estado para sigla
    uf_input = parametros.get("uf")
    if uf_input:
        uf_input_lower = uf_input.lower()
        parametros["uf"] = mapa_estados.get(uf_input_lower, uf_input).upper()

    
    # Aplicando a lógica desejada
    if parametros.get("municipio"):
        municipio = parametros["municipio"].lower()
        municipio_uf = data[data["Município"].str.lower() == municipio]["UF"].unique()
    
        # Se encontrarmos a UF correspondente ao município, usamos
        if len(municipio_uf) == 1:
            parametros["uf"] = municipio_uf[0]
        elif len(municipio_uf) > 1:
            parametros["uf"] = municipio_uf[0]  # Pega a primeira se houver mais de uma
    
    elif parametros.get("uf"):
        # Se só veio nova UF, limpa o município anterior
        parametros["municipio"] = None
    
    else:
        # Nenhum novo município ou UF, mantém ambos os anteriores
        parametros["municipio"] = parametros_anteriores.get("municipio")
        parametros["uf"] = parametros_anteriores.get("uf")
    
    # Herdar estágio e ação se não vierem
    for chave in ["estagio", "acao"]:
        if not parametros.get(chave):
            parametros[chave] = parametros_anteriores.get(chave)
    
    # Atualiza o contexto
    st.session_state["parametros_anteriores"] = parametros

    

    # Filtragem dos dados
    dados_filtrados = data.copy()
    if parametros["municipio"]:
        dados_filtrados = dados_filtrados[dados_filtrados["Município"].str.lower() == parametros["municipio"].lower()]
    if parametros["uf"]:
        dados_filtrados = dados_filtrados[dados_filtrados["UF"].str.lower() == parametros["uf"].lower()]
    if parametros["estagio"]:
        dados_filtrados = dados_filtrados[dados_filtrados["Estágio"].str.lower() == parametros["estagio"].lower()]

    # Geração da resposta
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
        if not dados_filtrados.empty:
            st.dataframe(dados_filtrados[["Empreendimento", "Estágio", "Executor", "Município", "UF"]])
            st.session_state.historico.append({"role": "assistant", "content": resposta})

# Histórico de conversa
if st.session_state.historico:
    st.markdown("### 💬 Conversa")
    for msg in st.session_state.historico:
        if msg["role"] == "user":
            st.markdown(f"**🧑 Você:** {msg['content']}")
        elif msg["role"] == "assistant":
            st.markdown(f"**🤖 Assistente:** {msg['content']}")

    # Tabela final (evita repetição da listagem acima)
    if "dados_filtrados" in locals() and not dados_filtrados.empty and parametros["acao"] != "contar":
        st.dataframe(dados_filtrados[["Empreendimento", "Estágio", "Executor", "Município", "UF"]])
