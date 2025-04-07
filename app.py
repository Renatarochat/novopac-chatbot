import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import json
from io import BytesIO

# API OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carrega os dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Inicializa histórico de conversa
if "historico" not in st.session_state:
    st.session_state.historico = []

# Função para gerar resposta do chatbot
def get_bot_response(user_input):
    prompt_inicial = """
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Extraia da frase abaixo o ESTADO (UF) ou o MUNICÍPIO. Se a pergunta for para gerar um relatório geral, retorne tipo "relatorio".

    Responda somente neste formato JSON, sem explicações:

    {
      "tipo": "estado" ou "municipio" ou "relatorio",
      "valor": "nome extraído"
    }
    """

    try:
        # Adiciona pergunta atual ao histórico
        st.session_state.historico.append({"role": "user", "content": user_input})

        mensagens = [{"role": "system", "content": prompt_inicial}]
        mensagens += st.session_state.historico[-5:]  # Usa últimas 5 trocas

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=mensagens,
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("{") and content.endswith("}"):
            resultado = json.loads(content)
        else:
            return "Erro: Resposta fora do formato esperado."

        if resultado.get("tipo") == "relatorio":
            return "GERAR_RELATORIO"

        return resultado

    except Exception as e:
        return f"Erro ao consultar OpenAI: {str(e)}"

# Gera relatório PDF
def gerar_relatorio_pdf(filtro_tipo, filtro_valor, dados_filtrados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Empreendimentos - NOVO PAC", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Filtro: {filtro_tipo.title()} - {filtro_valor}", ln=True)
    pdf.cell(200, 10, txt=f"Total de empreendimentos: {len(dados_filtrados)}", ln=True)
    pdf.ln(10)

    for _, row in dados_filtrados.iterrows():
        linha = f"{row['Município']} - {row['UF']}: {row['Empreendimento']} | {row['Executor']} | Estágio: {row['Estágio']}"
        pdf.multi_cell(0, 10, txt=linha)

    pdf.output("relatorio.pdf")
    with open("relatorio.pdf", "rb") as file:
        st.download_button("📥 Baixar PDF", file, file_name="relatorio.pdf")

# Gera Excel
def gerar_excel(dados_filtrados):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        dados_filtrados.to_excel(writer, index=False, sheet_name="Empreendimentos")
    output.seek(0)
    st.download_button("📥 Baixar Excel", output, file_name="relatorio.xlsx")

# Interface inicial
st.markdown("## Assistente virtual do NOVO PAC")
user_input = st.chat_input(
    "O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. "
    "Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.\n\n"
    "**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**"
)

if user_input:
    resposta = get_bot_response(user_input)

    if isinstance(resposta, str) and resposta.startswith("Erro"):
        st.warning(resposta)

    elif resposta == "GERAR_RELATORIO":
        st.info("🔄 Gerando relatório completo...")
        gerar_excel(data)
        gerar_relatorio_pdf("geral", "Todos", data)

    elif isinstance(resposta, dict):
        tipo = resposta.get("tipo")
        valor = resposta.get("valor")

        st.markdown(f"🔍 **Filtro identificado**: **{tipo.title()}** - `{valor}`")

        if tipo == "estado":
            dados_filtrados = data[data["UF"].str.upper() == valor.upper()]
        elif tipo == "municipio":
            dados_filtrados = data[data["Município"].str.lower() == valor.lower()]
        else:
            dados_filtrados = pd.DataFrame()

        if not dados_filtrados.empty:
            st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Executor", "Estágio"]])
            gerar_excel(dados_filtrados)
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)
        else:
            st.warning("Nenhum empreendimento encontrado para esse filtro.")
