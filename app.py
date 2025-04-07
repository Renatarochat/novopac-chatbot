import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import json
import io

# Inicializa cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carrega dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Função para entender a pergunta
def get_bot_response(user_input):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Extraia o ESTADO ou MUNICÍPIO da frase abaixo. 
    Se a pergunta for sobre geração de relatório, diga "GERAR_RELATORIO".
    Retorne o seguinte JSON:

    {{
      "tipo": "estado" ou "municipio" ou "relatorio",
      "valor": "nome extraído"
    }}

    Pergunta: "{user_input}"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        content = response.choices[0].message.content
        resultado = json.loads(content)

        if resultado.get("tipo") == "relatorio":
            return "GERAR_RELATORIO"

        return resultado

    except Exception as e:
        return f"Erro ao consultar OpenAI: {str(e)}"

# Gera PDF
def gerar_relatorio_pdf(filtro_tipo, filtro_valor, dados_filtrados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Empreendimentos - NOVO PAC", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Filtro aplicado: {filtro_tipo.title()} - {filtro_valor}", ln=True)
    pdf.cell(200, 10, txt=f"Total de empreendimentos encontrados: {len(dados_filtrados)}", ln=True)
    pdf.ln(10)

    for _, row in dados_filtrados.iterrows():
        linha = f"{row['Município']} - {row['UF']}: {row['Empreendimento']} - Estágio: {row['Estágio']}"
        pdf.multi_cell(0, 10, txt=linha)

    pdf.output("relatorio.pdf")
    with open("relatorio.pdf", "rb") as file:
        st.download_button("📄 Baixar Relatório PDF", file, file_name="relatorio.pdf")

# Gera Excel
def gerar_excel(dados_filtrados):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dados_filtrados.to_excel(writer, index=False, sheet_name="Empreendimentos")
    output.seek(0)
    st.download_button("📥 Baixar Excel", output, file_name="relatorio.xlsx")

# Interface
st.markdown("## Assistente virtual do NOVO PAC")

# Introdução com quebra de linha e negrito
st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.  

**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**
""")

# Filtro de estágio da obra
estagios = ["Todos"] + sorted(data["Estágio"].dropna().unique().tolist())
estagio = st.selectbox("Filtrar por estágio da obra:", options=estagios)

# Histórico de perguntas
if "historico" not in st.session_state:
    st.session_state.historico = []

user_input = st.text_input("Sua pergunta:")

if user_input:
    st.session_state.historico.append(user_input)
    resposta = get_bot_response(user_input)

    if isinstance(resposta, str):
        st.error(resposta)

    elif resposta == "GERAR_RELATORIO":
        st.info("Gerando relatório com todos os dados...")
        dados_filtrados = data.copy()
        if estagio != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados["Estágio"] == estagio]
        st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio"]])
        gerar_relatorio_pdf("Geral", "Todos", dados_filtrados)
        gerar_excel(dados_filtrados)

    elif isinstance(resposta, dict):
        tipo = resposta.get("tipo")
        valor = resposta.get("valor")
        st.markdown(f"🔎 **Filtro aplicado**: `{tipo.title()} - {valor}`")

        if tipo == "estado":
            dados_filtrados = data[data["UF"].str.upper() == valor.upper()]
        elif tipo == "municipio":
            dados_filtrados = data[data["Município"].str.lower() == valor.lower()]
        else:
            dados_filtrados = pd.DataFrame()

        if estagio != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados["Estágio"] == estagio]

        if not dados_filtrados.empty:
            st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio"]])
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)
            gerar_excel(dados_filtrados)
        else:
            st.warning("Nenhum empreendimento encontrado para esse filtro.")

# Mostrar histórico
if st.session_state.historico:
    st.markdown("### 💬 Histórico de Perguntas")
    for pergunta in reversed(st.session_state.historico[-5:]):
        st.markdown(f"- {pergunta}")
