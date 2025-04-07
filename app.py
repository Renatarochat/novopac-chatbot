import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import json
import io

# Inicializa memória de sessão
if "filtro_atual" not in st.session_state:
    st.session_state.filtro_atual = None

# Chave da API OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carregar dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Interface
st.markdown("## Assistente virtual do NOVO PAC")

user_input = st.text_input("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.  

**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**""")

# Exibir filtro atual + opção para limpar
if st.session_state.filtro_atual:
    st.info(f"📌 Local atual em memória: `{st.session_state.filtro_atual}`")
    if st.button("🧹 Limpar local atual"):
        st.session_state.filtro_atual = None
        st.success("Filtro atual foi limpo. Você pode perguntar sobre outro local.")

# Função para consultar o modelo
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

# Função para gerar PDF
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
    with open("relatorio.pdf", "rb") as file:
        st.download_button("📄 Baixar Relatório em PDF", file, file_name="relatorio.pdf")

# Função para gerar Excel
def gerar_excel(dados):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dados.to_excel(writer, index=False, sheet_name="Empreendimentos")
    st.download_button("📊 Baixar Excel", output.getvalue(), file_name="empreendimentos.xlsx")

# Processa a pergunta
if user_input:
    resposta = get_bot_response(user_input)

    if isinstance(resposta, str):
        if resposta == "GERAR_RELATORIO":
            st.info("Gerando relatório completo...")
            gerar_relatorio_pdf("Geral", "Todos", data)
        else:
            st.error(resposta)
    elif isinstance(resposta, dict):
        tipo = resposta.get("tipo")
        valor = resposta.get("valor")

        if tipo in ["estado", "municipio"]:
            st.session_state.filtro_atual = f"{tipo.title()} - {valor}"

        st.markdown(f"🔍 **Filtro identificado**: **{tipo.title()}** - `{valor}`")

        if tipo == "estado":
            dados_filtrados = data[data["UF"].str.upper() == valor.upper()]
        elif tipo == "municipio":
            dados_filtrados = data[data["Município"].str.lower() == valor.lower()]
        else:
            dados_filtrados = pd.DataFrame()

        # Filtro adicional: estágio da obra
        if not dados_filtrados.empty:
            if "Situação" in dados_filtrados.columns:
                estagios = ["Todos"] + sorted(dados_filtrados["Situação"].dropna().unique())
                estagio = st.selectbox("Filtrar por estágio da obra:", options=estagios)
                if estagio != "Todos":
                    dados_filtrados = dados_filtrados[dados_filtrados["Situação"] == estagio]

            # Ordenação
            ordenar_por = st.selectbox("Ordenar por:", options=["Empreendimento", "Código", "Município"])
            dados_filtrados = dados_filtrados.sort_values(by=ordenar_por)

            # Exibição e exportação
            st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Situação"]])
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)
            gerar_excel(dados_filtrados)
        else:
            st.warning("Nenhum empreendimento encontrado para esse filtro.")
