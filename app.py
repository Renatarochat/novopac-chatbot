import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import json
import io

# Chave da API OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carregar dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Inicializar sessão
if "historico" not in st.session_state:
    st.session_state.historico = []

if "ultimo_local" not in st.session_state:
    st.session_state.ultimo_local = {}

# Chatbot que extrai intenção e local
def get_bot_response(user_input):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Extraia se o usuário está perguntando por um Estado, Município ou deseja gerar um relatório.

    Se a pergunta estiver relacionada a um local mencionado anteriormente, retorne tipo "memoria".

    Retorne no seguinte formato JSON (sem explicações):

    {{
      "tipo": "estado" ou "municipio" ou "relatorio" ou "memoria",
      "valor": "nome extraído ou vazio se for relatório ou memória"
    }}

    Pergunta: "{user_input}"
    Último local consultado: "{st.session_state.ultimo_local.get('tipo', '')} - {st.session_state.ultimo_local.get('valor', '')}"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        resultado = json.loads(response.choices[0].message.content)
        return resultado
    except Exception as e:
        return {"tipo": "erro", "valor": str(e)}

# Gerar relatório PDF
def gerar_relatorio_pdf(filtro_tipo, filtro_valor, dados_filtrados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Empreendimentos - NOVO PAC", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Filtro aplicado: {filtro_tipo.title()} - {filtro_valor}", ln=True)
    pdf.cell(200, 10, txt=f"Total de empreendimentos encontrados: {len(dados_filtrados)}", ln=True)
    pdf.ln(10)

    for i, row in dados_filtrados.iterrows():
        linha = f"{row['Município']} - {row['UF']}: {row['Empreendimento']}"
        pdf.multi_cell(0, 10, txt=linha)

    pdf.output("relatorio.pdf")
    with open("relatorio.pdf", "rb") as file:
        st.download_button("📄 Baixar Relatório PDF", file, file_name="relatorio.pdf")

# Gerar Excel
def gerar_excel(dados):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dados.to_excel(writer, index=False)
    st.download_button("📥 Baixar Excel", data=output.getvalue(), file_name="relatorio.xlsx")

# UI do App
st.markdown("## Assistente virtual do NOVO PAC")
st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.

**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**
""")

# Filtro extra (estágio)
estagios_disponiveis = ["Todos"] + sorted(data["Estágio"].dropna().unique().tolist())
estagio = st.selectbox("Filtrar por estágio da obra:", options=estagios_disponiveis)

# Entrada do usuário
user_input = st.text_input("Sua pergunta:")

if user_input:
    resposta = get_bot_response(user_input)
    st.session_state.historico.append(user_input)

    if resposta["tipo"] == "erro":
        st.error(f"Erro: {resposta['valor']}")
    elif resposta["tipo"] == "relatorio":
        gerar_relatorio_pdf("Geral", "Todos", data)
        gerar_excel(data)
    else:
        if resposta["tipo"] == "memoria":
            tipo = st.session_state.ultimo_local.get("tipo")
            valor = st.session_state.ultimo_local.get("valor")
        else:
            tipo = resposta["tipo"]
            valor = resposta["valor"]
            st.session_state.ultimo_local = {"tipo": tipo, "valor": valor}

        st.markdown(f"🔍 **Filtro aplicado**: `{tipo.title()} - {valor}`")

        # Filtro de dados
        if tipo == "estado":
            dados_filtrados = data[data["UF"].str.upper() == valor.upper()]
        elif tipo == "municipio":
            dados_filtrados = data[data["Município"].str.lower() == valor.lower()]
        else:
            dados_filtrados = data.copy()

        if estagio != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados["Estágio"] == estagio]

        if not dados_filtrados.empty:
            st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio"]].sort_values("Empreendimento"))
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)
            gerar_excel(dados_filtrados)
        else:
            st.warning("Nenhum empreendimento encontrado para o filtro selecionado.")

# Histórico de Perguntas
if st.session_state.historico:
    st.markdown("---")
    st.markdown("### 🕘 Histórico de Perguntas")
    for pergunta in st.session_state.historico[::-1]:
        st.markdown(f"- {pergunta}")
