import streamlit as st
import pandas as pd
import openai

# Configurações da página
st.set_page_config(page_title="Assistente Virtual do NOVO PAC")
st.image("logo.png", width=360)
st.markdown("## **Assistente virtual do NOVO PAC**")
st.markdown("""
O Novo PAC é um programa de investimentos coordenado pelo governo federal, em parceria com o setor privado, estados, municípios e movimentos sociais. 
Todo o esforço conjunto é para acelerar o crescimento econômico e a inclusão social, gerando emprego e renda, e reduzindo desigualdades sociais e regionais.
""")

# Pergunta do usuário
st.markdown("#### O que você quer saber sobre o Novo PAC?")
st.markdown("Quantos empreendimentos tem na sua cidade ou seu estado? Quantos empreendimentos já foram entregues? Digite a sua pergunta:")

# Carregar dados
@st.cache_data
def carregar_dados():
    return pd.read_excel("novopac.xlsx")

data = carregar_dados()

# Inicializar histórico
if "historico" not in st.session_state:
    st.session_state.historico = []

# Caixa de entrada
pergunta = st.text_input("Digite sua pergunta:")

# Função para interpretar pergunta
def interpretar_pergunta(pergunta):
    system_prompt = """
Você é um assistente inteligente que ajuda a entender perguntas sobre uma base de dados do programa Novo PAC.
A planilha possui os campos: Eixo, Subeixo, UF, Município, Empreendimento, Modalidade, Classificação, Estágio, Executor.
O campo "Estágio" pode conter: "Em ação preparatória", "Em licitação / leilão", "Em execução", "Concluído".

Sua tarefa é retornar um JSON com os seguintes campos:
- municipio
- uf
- estagio (com base no significado do usuário: "entregues" = "Concluído")
- acao ("contar" ou "listar")

Responda apenas com o JSON.
    """

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pergunta}
        ]
    )

    try:
        resposta_bruta = response.choices[0].message.content.strip()
        parametros = eval(resposta_bruta)
    except Exception:
        parametros = {"municipio": None, "uf": None, "estagio": None, "acao": "listar"}
    return parametros

# Processar pergunta
if pergunta:
    st.session_state.historico.append({"role": "user", "content": pergunta})

    parametros = interpretar_pergunta(pergunta)
    dados_filtrados = data.copy()

    if parametros["municipio"]:
        dados_filtrados = dados_filtrados[dados_filtrados["Município"].str.lower() == parametros["municipio"].lower()]
    if parametros["uf"]:
        dados_filtrados = dados_filtrados[dados_filtrados["UF"].str.lower() == parametros["uf"].lower()]
    if parametros["estagio"]:
        dados_filtrados = dados_filtrados[dados_filtrados["Estágio"].str.lower() == parametros["estagio"].lower()]

    if dados_filtrados.empty:
        resposta = "Não encontrei empreendimentos com os critérios especificados."
    elif parametros["acao"] == "contar":
        local = []
        if parametros["municipio"]:
            local.append(f"na cidade de {parametros['municipio'].title()}")
        if parametros["uf"]:
            local.append(f"no estado de {parametros['uf'].upper()}")
        local_str = " ".join(local)
        estagio_str = f"{parametros['estagio'].lower()}" if parametros["estagio"] else ""
        resposta = f"Foram encontrados **{len(dados_filtrados)} empreendimentos {estagio_str} {local_str}**."
    else:
        resposta = f"Segue a lista de empreendimentos encontrados ({len(dados_filtrados)}):"

    st.markdown(f"**🤖 Resposta:** {resposta}")
    st.session_state.historico.append({"role": "assistant", "content": resposta})

    if not dados_filtrados.empty and parametros["acao"] != "contar":
        st.dataframe(dados_filtrados[["Empreendimento", "Estágio", "Executor", "Município", "UF"]])

# Exibir histórico (não visível para usuário, mas disponível para debug)
# for mensagem in st.session_state.historico:
#     st.write(mensagem["role"], ":", mensagem["content"])
