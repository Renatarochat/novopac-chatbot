import streamlit as st
import pandas as pd
import openai
import json
from fpdf import FPDF

# Configurar a chave da OpenAI (vinda do secrets do Streamlit Cloud)
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- Funções ---

# Carrega os dados do Excel
@st.cache_data
def carregar_dados():
    df = pd.read_excel("novopac.xlsx")
    return df

# Chat com o modelo da OpenAI
def interpretar_comando(user_input):
    prompt = f"""
Você é um assistente que responde perguntas sobre empreendimentos do NOVO PAC com base em uma tabela.

Analise a frase do usuário e retorne um JSON com as seguintes chaves:
- "acao": pode ser "responder" ou "gerar_relatorio"
- "tipo_filtro": "estado", "municipio" ou null
- "valor": o nome do estado ou município (sem acento), ou null

Responda APENAS com o JSON. Sem explicações.

Frase do usuário: "{user_input}"
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response["choices"][0]["message"]["content"]
        resultado = json.loads(content)
        return resultado

    except Exception as e:
        return {"erro": str(e)}

# Gera o relatório em PDF
def gerar_pdf(filtro_tipo, filtro_valor, dados_filtrados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    titulo = f"Relatório - {filtro_tipo.capitalize()}: {filtro_valor}"
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')
    pdf.cell(200, 10, txt=f"Total de empreend
