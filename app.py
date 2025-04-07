import streamlit as st
import pandas as pd
import openai
from fpdf import FPDF
import io

# Configurações da página
st.set_page_config(page_title="Chatbot - NOVO PAC", layout="centered")

# 🔑 API Key do OpenAI via Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# 📥 Carregar dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# 🤖 Função para gerar resposta do bot
def get_bot_response(user_input):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Extraia da frase abaixo:
    - Se o usuário quer um RELATÓRIO, responda: GERAR_RELATORIO.
    - Caso contrário, diga se ele mencionou um Estado ou um Município.

    Pergunta: "{user_input}"
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = response["choices"][0]["message"]["content"].strip()

    if "GERAR_RELATORIO" in content.upper():
        return "GERAR_RELATORIO"

    for estado in data["UF"].unique():
        if estado.lower() in user_input.lower():
            return {"tipo": "estado", "valor": estado}

    for municipio in data["Município"].unique():
        if municipio.lower() in user_input.lower():
            return {"tipo": "municipio", "valor": municipio}

    return "Desculpe, não encontrei informações suficientes."

# 📄 Função para gerar PDF
def gerar_pdf(filtrado, filtro_tipo, filtro_valor):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    titulo = f"Relatório por {filtro_tipo.title()}: {filtro_valor}"
    pdf.cell(200, 10, txt=titulo, ln=True, align="C")
    pdf.ln(5)

    pdf.cell(200, 10, txt=f"Total de empreendimentos: {len(filtrado)}", ln=True)
    pdf.ln(5)

    # Agrupamento
    agrupado = filtrado.groupby(["Eixo", "Subeixo", "Modalidade"])

    for (eixo, subeixo, modalidade), grupo in agrupado:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt=f"Eixo: {eixo} | Subeixo: {subeixo} | Modalidade: {modalidade}", ln=True)
        pdf.set_font("Arial", size=10)

        for _, row in grupo.iterrows():
            nome = row["Nome do Empreendimento"]
            estagio = row["Estágio"]
            executor = row["Executor"]
            linha = f"- {nome} | Estágio: {estagio} | Executor: {executor}"
            pdf.multi_cell(0, 10, linha)

        pdf.ln(5)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# 💬 Interface do chat
st.title("📊 Chatbot - Empreendimentos do NOVO PAC")

if "chat" not in st.session_state:
    st.session_state.chat = []

user_input = st.text_input("Digite sua pergunta:")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})
    resposta = get_bot_response(user_input)

    if resposta == "GERAR_RELATORIO":
        st.info("Você deseja gerar relatório por Estado ou Município?")
    elif isinstance(resposta, dict):
        filtro_tipo = resposta["tipo"]
        filtro_valor = resposta["valor"]
        filtrado = data[data[filtro_tipo.capitalize()] == filtro_valor]

        if not filtrado.empty:
            st.success(f"Encontrado {len(filtrado)} empreendimentos para {filtro_valor}.")
            pdf_bytes = gerar_pdf(filtrado, filtro_tipo, filtro_valor)
            st.download_button("📥 Baixar Relatório PDF", data=pdf_bytes, file_name=f"relatorio_{filtro_valor}.pdf")
        else:
            st.warning(f"Nenhum dado encontrado para {filtro_valor}.")
    else:
        st.session_state.chat.append({"role": "assistant", "content": resposta})

# Mostrar histórico do chat
st.write("---")
for msg in st.session_state.chat:
    if msg["role"] == "user":
        st.markdown(f"**Você:** {msg['content']}")
    else:
        st.markdown(f"**Assistente:** {msg['content']}")
