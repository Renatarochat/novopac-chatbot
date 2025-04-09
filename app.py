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

# Histórico de conversa (oculto)
if "historico" not in st.session_state:
    st.session_state.historico = []

# Função para interpretar a pergunta
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def interpretar_pergunta(pergunta):
    parametros = {
        "municipio": None,
        "uf": None,
        "estagio": None,
        "acao": None
    }

    pergunta_normalizada = remover_acentos(pergunta.lower())

    # Detecta ação (contar ou listar)
    if any(p in pergunta_normalizada for p in ["quantos", "numero", "quantidade", "tem em", "tem quantos"]):
        parametros["acao"] = "contar"
    elif any(p in pergunta_normalizada for p in ["quais", "listar", "mostra", "lista", "exibe"]):
        parametros["acao"] = "listar"

    # Detecta UF (2 letras ou nome por extenso)
    ufs = {
        "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
        "espirito santo": "ES", "goias": "GO", "maranhao": "MA", "mato grosso": "MT", "mato grosso do sul": "MS",
        "minas gerais": "MG", "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE", "piaui": "PI",
        "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS", "rondonia": "RO",
        "roraima": "RR", "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO"
    }

    for nome, sigla in ufs.items():
        if nome in pergunta_normalizada:
            parametros["uf"] = sigla
        elif re.search(rf"\b{sigla.lower()}\b", pergunta_normalizada):
            parametros["uf"] = sigla

    # Detecta município (usa regex para palavras seguidas de "em")
    match_mun = re.search(r"em\s+([a-záéíóúãõâêôç\s]+)", pergunta.lower())
    if match_mun:
        municipio_raw = match_mun.group(1).strip()
        municipio = municipio_raw.split(" ")[0] if "estado" in municipio_raw else municipio_raw
        parametros["municipio"] = municipio.strip()

    # Detecta estágio com base em sinônimos
    if any(p in pergunta_normalizada for p in [
        "nao foram iniciados", "nao iniciado", "nao iniciada", "nao iniciados", "nao iniciadas"
    ]):
        parametros["estagio"] = "em ação preparatória"

    elif any(p in pergunta_normalizada for p in [
        "em andamento", "em obras"
    ]):
        parametros["estagio"] = "em execução"

    elif any(p in pergunta_normalizada for p in [
        "entregues", "finalizados"
    ]):
        parametros["estagio"] = "concluído"

    elif any(p in pergunta_normalizada for p in [
        "em licitacao", "em leilao"
    ]):
        parametros["estagio"] = "em licitação / leilão"

    return parametros

# Interface de pergunta
pergunta = st.chat_input("Digite sua pergunta:")

# Se a pergunta foi feita, processamos a resposta
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
    
    # Converte nome do estado para sigla (se for nome por extenso)
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
        if "dados_filtrados" in locals() and not dados_filtrados.empty and parametros["acao"] != "contar":
            st.dataframe(dados_filtrados[["Empreendimento", "Estágio", "Executor", "Município", "UF"]])
