import streamlit as st
import pandas as pd
from openai import OpenAI
import json

# Configuração da página
st.set_page_config(page_title="Assistente virtual do NOVO PAC")

# Chave da API
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carregar os dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Mostrar título e descrição
col1, col2 = st.columns([1, 8])
with col1:
    st.image("logo.png", width=80)  # Substitua por sua logo
with col2:
    st.markdown("### **Assistente virtual do NOVO PAC**")

st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.
""")

st.markdown("#### O que você quer saber sobre o Novo PAC?")
st.markdown("Quantos empreendimentos tem na sua cidade ou seu estado? Quantos empreendimentos já foram entregues? Digite a sua pergunta:")

# Inicializar histórico
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# Função de interpretação via OpenAI
def interpretar_pergunta(pergunta, historico):
    prompt = f"""
Você é um assistente de dados do Novo PAC. Baseando-se em perguntas como:

- "Quantos empreendimentos têm em Belo Horizonte?"
- "Quais foram entregues em SP?"
- "Me mostre os empreendimentos em Montes Claros"

Identifique a intenção do usuário e devolva um JSON com:

- tipo: "listar", "contar", ou "desconhecido"
- filtro: "municipio" ou "estado"
- valor: nome do estado ou município
- estagio (opcional): se ele pedir por estágio como "entregue", "em andamento" etc.

Formato de saída:
{{
  "tipo": "listar" | "contar" | "desconhecido",
  "filtro": "estado" | "municipio",
  "valor": "Minas Gerais",
  "estagio": "Concluída" (opcional)
}}

Histórico da conversa:
{json.dumps(historico[-5:])}

Pergunta: "{pergunta}"
"""

    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return json.loads(resposta.choices[0].message.content)

# Função para processar a pergunta
def responder(pergunta):
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    interpretado = interpretar_pergunta(pergunta, st.session_state.mensagens)

    tipo = interpretado.get("tipo")
    filtro = interpretado.get("filtro")
    valor = interpretado.get("valor")
    estagio = interpretado.get("estagio")

    df = data.copy()

    # Aplicar filtros
    if filtro == "estado":
        df = df[df["UF"].str.lower() == valor.lower()]
    elif filtro == "municipio":
        df = df[df["Município"].str.lower() == valor.lower()]

    if estagio:
        df = df[df["Estágio"].str.contains(estagio, case=False, na=False)]

    # Geração da resposta
    if df.empty:
        resposta_texto = "Nenhum empreendimento encontrado com esses critérios."
    elif tipo == "contar":
        resposta_texto = f"🔎 Foram encontrados **{len(df)}** empreendimentos para **{valor}**."
    elif tipo == "listar":
        resposta_texto = f"🔎 Lista de empreendimentos encontrados em **{valor}**:"
    else:
        resposta_texto = "Desculpe, não entendi exatamente a sua pergunta. Tente reformular."

    st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
    st.markdown(resposta_texto)

    # Mostrar tabela se tipo for listar
    if tipo == "listar" and not df.empty:
        st.dataframe(df[["Empreendimento", "Estágio", "Executor"]].reset_index(drop=True))

# Entrada de texto interativa
pergunta = st.chat_input("Digite sua pergunta sobre os empreendimentos do Novo PAC")

if pergunta:
    responder(pergunta)
