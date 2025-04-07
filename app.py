import streamlit as st
import pandas as pd
from fpdf import FPDF
from openai import OpenAI
import os

# Configuração da API
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Função para carregar os dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

# Função para gerar PDF
def gerar_pdf(dados_filtrados, tipo, valor):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"Relatório de Empreendimentos - {tipo.title()}: {valor}", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total de empreendimentos: {len(dados_filtrados)}", ln=True)
    pdf.ln(5)

    agrupado = dados_filtrados.groupby(['Eixo', 'Subeixo', 'Modalidade'])

    for (eixo, subeixo, modalidade), grupo in agrupado:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=f"{eixo} / {subeixo} / {modalidade}", ln=True)
        pdf.set_font("Arial", size=10)

        for _, linha in grupo.iterrows():
            texto = f"- {linha['Nome do Empreendimento']} | Estágio: {linha['Estágio']} | Executor: {linha['Executor']}"
            pdf.multi_cell(0, 8, txt=texto)

        pdf.ln(5)

    caminho_pdf = f"relatorio_{tipo}_{valor}.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

# Função que consulta o modelo da OpenAI
def get_bot_response(user_input, data):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Responda de forma objetiva e clara, extraindo o ESTADO ou MUNICÍPIO da frase abaixo. 
    Se a pergunta for sobre geração de relatório, diga "GERAR_RELATORIO".
    Retorne também o tipo de filtro (estado ou municipio).

    Pergunta: "{user_input}"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content

        if "GERAR_RELATORIO" in content.upper():
            return "GERAR_RELATORIO"

        for estado in data['UF'].unique():
            if estado.lower() in user_input.lower():
                return {"tipo": "estado", "valor": estado}

        for municipio in data['Município'].unique():
            if municipio.lower() in user_input.lower():
                return {"tipo": "municipio", "valor": municipio}

        return content

    except Exception as e:
        return f"Erro ao consultar OpenAI: {str(e)}"

# Interface Streamlit
st.set_page_config(page_title="Chatbot NOVO PAC", page_icon="🏗️")
st.title("🏗️ Chatbot - NOVO PAC")

data = carregar_dados()

if "historico" not in st.session_state:
    st.session_state.historico = []

user_input = st.text_input("Digite sua pergunta:")

if user_input:
    resposta = get_bot_response(user_input, data)
    st.session_state.historico.append(("Você", user_input))

    if resposta == "GERAR_RELATORIO":
        if "filtro" in st.session_state:
            tipo = st.session_state["filtro"]["tipo"]
            valor = st.session_state["filtro"]["valor"]
            dados_filtrados = data[data[tipo.title()] == valor]

            if not dados_filtrados.empty:
                caminho_pdf = gerar_pdf(dados_filtrados, tipo, valor)
                with open(caminho_pdf, "rb") as file:
                    st.download_button(
                        label="📥 Baixar Relatório em PDF",
                        data=file,
                        file_name=caminho_pdf,
                        mime="application/pdf",
                    )
                st.success("Relatório gerado com sucesso!")
            else:
                st.warning("Nenhum dado encontrado para esse filtro.")
        else:
            st.warning("Por favor, especifique um estado ou município antes de gerar o relatório.")
    elif isinstance(resposta, dict):
        st.session_state["filtro"] = resposta
        st.markdown(f"🔍 Filtro identificado: **{resposta['tipo'].title()}** - *{resposta['valor']}*")
    else:
        st.session_state.historico.append(("Chatbot", resposta))

# Exibir histórico
for autor, msg in st.session_state.historico:
    st.markdown(f"**{autor}:** {msg}")
