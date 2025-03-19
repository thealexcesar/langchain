import os
import dotenv
from langchain_openai import AzureChatOpenAI
from langchain_groq import ChatGroq

dotenv.load_dotenv()

AZURE = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_version=os.getenv("AZURE_API_VERSION"),
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
)

GROQ = ChatGroq(
    model_name=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY"),
)
