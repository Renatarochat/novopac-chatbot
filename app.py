import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import json
from io import BytesIO

# Carregar chave da API
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carrega os dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Interface principal
st.markdown("## Assistente virtual do NOVO PAC")
st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.  

**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**
""")

# Entrada do usuário
user_input = st.text_input("")

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
        resultado = json.loads(response.choices[0].message.content)
        if resultado.get("tipo") == "relatorio":
            return "GERAR_RELATORIO"
        return resultado

    except Exception as e:
        return f"Erro ao consultar OpenAI: {str(e)}"

# Geração do relatório PDF
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

# Geração de Excel
def gerar_excel(dados_filtrados):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dados_filtrados.to_excel(writer, index=False)
    st.download_button(
        label="📊 Baixar Excel",
        data=output.getvalue(),
        file_name="relatorio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Filtros adicionais
estagio = st.selectbox("Filtrar por estágio da obra:", options=["Todos"] + list(data["Estágio"].dropna().unique()))

# Processamento da pergunta
if user_input:
    resposta = get_bot_response(user_input)

    if isinstance(resposta, str):
        if resposta == "GERAR_RELATORIO":
            gerar_relatorio_pdf("geral", "Todos", data)
            gerar_excel(data)
        else:
            st.error(resposta)

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

        # Filtro adicional por estágio
        if estagio != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados["Estágio"] == estagio]

        if not dados_filtrados.empty:
            # Ordenação (opcional)
            dados_filtrados = dados_filtrados.sort_values(by="Empreendimento")
            st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio"]])

            # Botões de download
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)
            gerar_excel(dados_filtrados)
        else:
            st.warning("Nenhum empreendimento encontrado para esse filtro.")
