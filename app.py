import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

st.set_page_config(page_title="Assistente virtual do NOVO PAC")

# ===============================
# FUNÇÕES AUXILIARES
# ===============================

@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for _, row in dados.iterrows():
        linha = f"{row['Município']} - {row['UF']} | {row['Empreendimento']} | {row['Estágio']}"
        pdf.multi_cell(0, 10, linha)
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

def gerar_excel(dados):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dados.to_excel(writer, index=False)
    output.seek(0)
    return output

# ===============================
# CARREGAR DADOS
# ===============================

data = carregar_dados()

# ===============================
# INTERFACE
# ===============================

st.title("Assistente virtual do NOVO PAC")
st.markdown(
    "O Novo PAC é um programa de investimentos coordenado pelo governo federal...  \n"
    "**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**"
)

# Inicializa histórico se não existir
if "historico" not in st.session_state:
    st.session_state.historico = []

# Pergunta principal
pergunta = st.text_input("Sua pergunta:", key="pergunta_inicial")

# Processa pergunta
if pergunta:
    # Simples análise de localização na pergunta
    filtro_municipio = None
    filtro_uf = None

    for municipio in data["Município"].unique():
        if municipio.lower() in pergunta.lower():
            filtro_municipio = municipio
            break

    for uf in data["UF"].unique():
        if uf.lower() in pergunta.lower():
            filtro_uf = uf
            break

    dados_filtrados = data.copy()

    if filtro_municipio:
        dados_filtrados = dados_filtrados[dados_filtrados["Município"] == filtro_municipio]
    if filtro_uf:
        dados_filtrados = dados_filtrados[dados_filtrados["UF"] == filtro_uf]

    # Monta "resposta"
    if not dados_filtrados.empty:
        st.markdown("#### Resultado:")

        if filtro_municipio:
            st.markdown(f"**Filtro aplicado:** Município = {filtro_municipio}")
        elif filtro_uf:
            st.markdown(f"**Filtro aplicado:** UF = {filtro_uf}")

        st.write(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio"]])
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Baixar Relatório PDF",
                data=gerar_pdf(dados_filtrados),
                file_name="relatorio_novo_pac.pdf"
            )
        with col2:
            st.download_button(
                label="📊 Baixar Excel",
                data=gerar_excel(dados_filtrados),
                file_name="relatorio_novo_pac.xlsx"
            )
    else:
        st.warning("Nenhum dado encontrado com base na sua pergunta.")

    # Armazena no histórico
    st.session_state.historico.append(pergunta)

    # Pergunta de continuação
    nova_pergunta = st.text_input("Tem mais alguma pergunta?", key="nova_pergunta")
    if nova_pergunta:
        st.session_state.historico.append(nova_pergunta)
        st.rerun()

# Histórico abaixo
if st.session_state.historico:
    st.markdown("---")
    st.markdown("### 🕘 Histórico de Perguntas")
    for item in st.session_state.historico:
        st.markdown(f"- {item}")
