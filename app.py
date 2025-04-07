import openai

openai.api_key = st.secrets["OPENAI_API_KEY"]

def get_bot_response(user_input, data):
    prompt = f"""
    Você é um assistente que responde sobre empreendimentos do NOVO PAC com base em uma tabela.

    Responda de forma objetiva e clara, extraindo o ESTADO ou MUNICÍPIO da frase abaixo. 
    Se a pergunta for sobre geração de relatório, diga "GERAR_RELATORIO".
    Retorne também o tipo de filtro (estado ou municipio).

    Pergunta: "{user_input}"
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response["choices"][0]["message"]["content"]

        if "GERAR_RELATORIO" in content.upper():
            return "GERAR_RELATORIO"

        for estado in data['UF'].unique():
            if estado.lower() in user_input.lower():
                return {"tipo": "estado", "valor": estado}

        for municipio in data['Município'].unique():
            if municipio.lower() in user_input.lower():
                return {"tipo": "municipio", "valor": municipio}

        return content

    except Exception as e:
        return f"Erro ao consultar OpenAI: {str(e)}"
