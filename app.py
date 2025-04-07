import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Assistente virtual do NOVO PAC")

# Carregar dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Histórico de conversa
if "historico" not in st.session_state:
    st.session_state["historico"] = []

# Cabeçalho
st.title("Assistente virtual do NOVO PAC")
st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal...

**Digite sua pergunta para obter mais informações sobre os empreendimentos no Estado ou na sua Cidade:**
""")

# Entrada de pergunta
pergunta = st.text_input("Sua pergunta:")

# Processamento da pergunta
if pergunta:
    pergunta_lower = pergunta.lower()

    municipio = None
    uf = None

    # Buscar município e UF na pergunta (formato: Montes Claros - MG)
    for index, row in data.iterrows():
        cidade = str(row["Município"]).lower()
        estado = str(row["UF"]).lower()
        if cidade in pergunta_lower and estado in pergunta_lower:
            municipio = row["Município"]
            uf = row["UF"]
            break

    # Filtragem
    if municipio and uf:
        dados_filtrados = data[
            (data["Município"] == municipio) & (data["UF"] == uf)
        ]
        
        if not dados_filtrados.empty:
            st.markdown(f"**Filtro aplicado:** Município - `{municipio}` / UF - `{uf}`")
            st.dataframe(dados_filtrados[["Município", "UF", "Empreendimento", "Estágio", "Executor"]], use_container_width=True)
            
            # Botões de exportação
            def gerar_pdf(df):
                return df.to_csv(index=False).encode('utf-8')

            def gerar_excel(df):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Obras')
                return output.getvalue()

            st.download_button("📄 Baixar Relatório PDF", gerar_pdf(dados_filtrados), "relatorio.pdf")
            st.download_button("📥 Baixar Excel", gerar_excel(dados_filtrados), "relatorio.xlsx")

        else:
            st.warning("Nenhum dado encontrado com base na sua pergunta.")

    else:
        st.warning("Não consegui identificar o município e UF na sua pergunta.")

    # Armazenar histórico
    st.session_state["historico"].append(pergunta)

    # Caixa de nova pergunta (reexibe após resposta)
    st.markdown("---")
    st.subheader("🔁 Deseja continuar a conversa?")
    st.rerun()

# Histórico
if st.session_state["historico"]:
    st.markdown("### 🕓 Histórico de Perguntas")
    for item in st.session_state["historico"]:
        st.markdown(f"- {item}")
