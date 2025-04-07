import streamlit as st
import pandas as pd
import openai
from openai import OpenAI
from fpdf import FPDF
import plotly.express as px
import json
import io

# API do OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Carrega os dados com cache
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Histórico simples de chat
if "historico" not in st.session_state:
    st.session_state.historico = []

# Extrai entidade da pergunta
def get_bot_response(user_input):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Extraia o ESTADO, MUNICÍPIO ou ambos da frase. 
    Se a pergunta for sobre relatório, retorne tipo "relatorio".

    Retorne JSON no formato:
    {{
      "tipo": "estado" ou "municipio" ou "uf_municipio" ou "relatorio",
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
        return json.loads(content)
    except Exception as e:
        return {"tipo": "erro", "valor": str(e)}

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

    for i, row in dados_filtrados.iterrows():
        linha = f"{row['Município']} - {row['UF']}: {row['Empreendimento']}"
        pdf.multi_cell(0, 10, txt=linha)

    pdf.output("relatorio.pdf")
    st.success("Relatório gerado com sucesso! 📄")
    with open("relatorio.pdf", "rb") as file:
        st.download_button("📥 Baixar Relatório PDF", file, file_name="relatorio.pdf")

# Gera Excel
def gerar_excel(dados_filtrados):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dados_filtrados.to_excel(writer, index=False)
    st.download_button("📥 Baixar Excel", output.getvalue(), file_name="dados_novopac.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Interface
st.markdown("## Assistente virtual do NOVO PAC")
st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.  

**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**
""")

user_input = st.text_input("")

if user_input:
    st.session_state.historico.append(user_input)

    resposta = get_bot_response(user_input)
    tipo = resposta.get("tipo")
    valor = resposta.get("valor")

    if tipo == "relatorio":
        gerar_relatorio_pdf("geral", "Todos", data)

    else:
        st.markdown(f"🔍 **Filtro identificado**: **{tipo.title()}** - `{valor}`")

        if tipo == "estado":
            dados_filtrados = data[data["UF"].str.upper() == valor.upper()]
        elif tipo == "municipio":
            dados_filtrados = data[data["Município"].str.lower() == valor.lower()]
        elif tipo == "uf_municipio":
            partes = valor.split("-")
            if len(partes) == 2:
                cidade, uf = partes[0].strip(), partes[1].strip()
                dados_filtrados = data[(data["Município"].str.lower() == cidade.lower()) & (data["UF"].str.upper() == uf.upper())]
            else:
                dados_filtrados = pd.DataFrame()
        else:
            dados_filtrados = pd.DataFrame()

        if not dados_filtrados.empty:
            # Filtros extras
            estagio = st.selectbox("Filtrar por estágio da obra:", options=["Todos"] + list(data["Estágio"].dropna().unique()))
            if estagio != "Todos":
                dados_filtrados = dados_filtrados[dados_filtrados["Estágio"] == estagio]

            # Ordenação
            ordenar_por = st.selectbox("Ordenar por:", options=["Município", "Empreendimento"])
            dados_filtrados = dados_filtrados.sort_values(by=ordenar_por)

            # Tabela
            st.dataframe(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio"]], use_container_width=True)

            # Downloads
            gerar_relatorio_pdf(tipo, valor, dados_filtrados)
            gerar_excel(dados_filtrados)

            # Gráfico
            opcao_grafico = st.selectbox("Visualizar gráfico por:", options=["Modalidade", "Classificação"])
            fig = px.histogram(dados_filtrados, x=opcao_grafico, color=opcao_grafico, title=f"Distribuição por {opcao_grafico}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum empreendimento encontrado.")

# Histórico de perguntas
if st.session_state.historico:
    st.markdown("### 💬 Últimas perguntas:")
    for item in st.session_state.historico[-5:]:
        st.markdown(f"- {item}")
