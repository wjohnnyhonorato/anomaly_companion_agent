# Importa o Chainlit, responsável pela interface de chat.
import chainlit as cl

# Representa uma mensagem enviada por uma pessoa no padrão LangChain.
from langchain_core.messages import HumanMessage

# Importa a função que constrói e compila nosso grafo LangGraph.
from anomaly_companion_agent.graph import create_graph


# O grafo é criado uma vez, quando a aplicação Chainlit inicia.
# Ele será reutilizado sempre que o usuário enviar uma mensagem.
graph = create_graph()


# Este decorator registra uma função para o evento:
# "uma nova conversa foi iniciada".
@cl.on_chat_start
async def on_chat_start():
    """Executa quando o usuário abre uma nova conversa."""

    # Cria uma mensagem do assistente e a envia para a interface.
    await cl.Message(
        content=(
            "Olá! Sou o Anomaly Companion. "
            "Informe uma anomalia para investigação."
        )
    ).send()


# Este decorator registra uma função para o evento:
# "o usuário enviou uma mensagem".
@cl.on_message
async def on_message(message: cl.Message):
    """Recebe uma mensagem e a envia para o LangGraph."""

    initial_state = {
        "messages": [
            HumanMessage(content=message.content)
        ]
    }

    execution_config = {
        "callbacks": [
            cl.LangchainCallbackHandler()
        ]
    }

    result = await graph.ainvoke(
        initial_state,
        config=execution_config,
    )

    final_message = result["messages"][-1]

    # Use .text, e não .content.
    answer_text = final_message.text

    await cl.Message(
        content=answer_text
    ).send()