import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import json
import io
import plotly.express as px

# Carregar chave da API
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carrega os dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()
data["Municipio_UF"] = data["Município"] + " - " + data["UF"]

# Histórico de perguntas
if "historico" not in st.session_state:
    st.session_state["historico"] = []

# Função para buscar resposta do chatbot
def get_bot_response(user_input):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Responda de forma objetiva e clara, extraindo o ESTADO ou MUNICÍPIO da frase abaixo. 
    Se a pergunta for sobre geração de relatório, diga "GERAR_RELATORIO".
    Retorne no seguinte formato JSON (sem explicações):

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

# Função para gerar relatório PDF
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
        linha = f"{row['Município']} - {row['UF']}: {row['Empreendimento']}"
        pdf.multi_cell(0, 10, txt=linha)

    pdf.output("relatorio.pdf")
    st.success("Relatório gerado com sucesso! 📄")
    with open("relatorio.pdf", "rb") as file:
        st.download_button("📥 Baixar Relatório PDF", file, file_name="relatorio.pdf")

# Interface Streamlit
st.markdown("## Assistente virtual do NOVO PAC")

user_input = st.text_input("""O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.  
\n**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**""")

estagio = st.selectbox("Filtrar por estágio da obra:", options=["Todos"] + list(data["Situação"].dropna().unique()))
ordenar_por = st.selectbox("Ordenar por:", options=["Empreendimento", "Código"])

if user_input:
    st.session_state.historico.append(user_input)
    resposta = get_bot_response(user_input)

    if isinstance(resposta, str):
        st.error(resposta)

    elif resposta == "GERAR_RELATORIO":
        st.info("Gerando relatório com todos os dados...")
        gerar_relatorio_pdf("geral", "Todos", data)

    elif isinstance(resposta, dict):
        tipo = resposta.get("tipo")
        valor = resposta.get("valor")

        st.markdown(f"🔍 **Filtro identificado**: **{tipo.title()}** - `{valor}`")

        if tipo == "estado":
            dados_filtrados = data[data["UF"].str.upper() == valor.upper()]
        elif tipo == "municipio":
            dados_filtrados = data[data["Municipio_UF"].str.lower() == valor.lower()]
        else:
            dados_filtrados = pd.DataFrame()

        if estagio != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados["Situação"] == estagio]

        if not dados_filtrados.empty:
            dados_filtrados = dados_filtrados.sort_values(by=ordenar_por)
            st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Situação"]])

            # PDF
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)

            # Excel
            output = io.BytesIO()
            dados_filtrados.to_excel(output, index=False)
            st.download_button("📥 Baixar Excel", output.getvalue(), file_name="relatorio.xlsx")

            # Gráfico
            if "Classificação" in dados_filtrados.columns:
                fig = px.bar(dados_filtrados["Classificação"].value_counts().reset_index(),
                             x="index", y="Classificação",
                             labels={"index": "Classificação", "Classificação": "Quantidade"},
                             title="Distribuição das Obras por Classificação")
                st.plotly_chart(fig)
        else:
            st.warning("Nenhum empreendimento encontrado para esse filtro.")

# Histórico de perguntas
if st.session_state.historico:
    st.markdown("### 💬 Histórico de Perguntas")
    for pergunta in st.session_state.historico[-5:][::-1]:
        st.write("🔸", pergunta)
