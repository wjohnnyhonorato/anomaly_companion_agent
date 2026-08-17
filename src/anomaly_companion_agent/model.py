import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


MODEL_NAME = "gemini-3.5-flash"


def create_model() -> ChatGoogleGenerativeAI:
    """
    Instancia o modelo de linguagem usado pelo Anomaly Companion.

    Returns
    -------
    ChatGoogleGenerativeAI
        Adapter LangChain configurado para o Gemini.

    Raises
    ------
    RuntimeError
        Se ``GEMINI_API_KEY`` não estiver disponível no ambiente.

    Notes
    -----
    Este arquivo concentra a dependência do provider de LLM.
    No ambiente corporativo, a ideia é trocar esta implementação
    por outro adapter, por exemplo ``ChatOpenAI``, sem alterar
    a estrutura do grafo.

    As tools não são vinculadas aqui. O ``bind_tools`` é feito
    em ``graph.py``, porque disponibilizar tools é uma decisão
    do agente/grafo, não do provider.
    """
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada no .env"
        )

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        api_key=api_key,
        temperature=0,
    )
