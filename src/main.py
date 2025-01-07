import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("A chave da API (OPENAI_API_KEY) não foi encontrada no arquivo .env.")

llm = ChatOpenAI(
    # model="gpt-4o-mini",
    model="gpt-3.5-turbo",
    temperature=0.7,
    openai_api_key=api_key
)

question = input("O que deseja saber? ")

try:
    response = llm.predict(question)
    print("Resposta:", response)
except Exception as e:
    print(f"Erro ao obter resposta: {e}")
