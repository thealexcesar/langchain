from operator import itemgetter
import os
import dotenv
from langchain.agents import AgentExecutor, tool
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain.tools import StructuredTool
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
import dotenv

dotenv.load_dotenv()

@tool()
def sql_to_llm_tool(uuid: str, question: str, table_columns_desc: str, metadata: dict | None = None):
    """Tool to convert SQL queries into LLM-compatible questions, enabling users.

    extract meaningful insights from SQLite databases based on 
    specified table and column descriptions and metadata.
    """
    try:
        sqlite_path = "data/temp.db"
    except:
        raise ValueError("Error to get file database.")


class QA_SQL:
    def __init__(self, sqlite_path: str, question: str, template: str, metadata: dict | None = None):
        self.__sqlite_path = sqlite_path
        self.__question = question
        self.__template = template
        self.__metadata = metadata or {}

    def extract_schema_and_query_llm(self):

        db = SQLDatabase.from_uri(f"sqlite:///{self.__sqlite_path}")
        api_key = os.getenv("AZURE_API_KEY")
        azure_deployment = os.getenv("AZURE_DEPLOYMENT")
        api_version = os.getenv("AZURE_API_VERSION")
        azure_endpoint = os.getenv("AZURE_ENDPOINT")

        if not all([api_key, azure_deployment, api_version, azure_endpoint]):
            raise ValueError("Certifique-se de que todas as credenciais do Azure OpenAI estão definidas no arquivo .env.")

        llm = AzureChatOpenAI(
            azure_deployment=azure_deployment,
            api_version=api_version,
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            temperature=0.0,
        )


        write_query = create_sql_query_chain(llm, db)
        execute_query = QuerySQLDataBaseTool(db=db)
        write_execute_chain = write_query | execute_query
        
        try:
            result = write_execute_chain.invoke({
                "question": f"{self.__template} | do not limit the query: {self.__question}"
            })
            
            answer_prompt = PromptTemplate.from_template(
                """Given the following user question, corresponding SQL query, 
                and SQL result, answer the user question with precision.
                
                Question: {question}
                SQL Query: {query}
                SQL Result: {result}
                Metadata: {metadata}
                Answer: """
            )
            
            answer = answer_prompt | llm | StrOutputParser()
            chain = RunnablePassthrough.assign(
                query=write_query
            ).assign(
                result=itemgetter("query") | execute_query
            ) | answer
            
            response = chain.invoke({
                "question": f"{self.__template} | de acordo com '{self.__question}' gerar uma mensagem amigavel",
                "metadata": self.__metadata
            })
            return response
            
        except Exception:
            try:
                query = write_query.invoke({
                    "question": f"{self.__template} | de acordo com '{self.__question}' gerar uma mensagem amigavel",
                    "metadata": self.__metadata
                })
                db.run(query)
                msg = HumanMessage(
                    content=f"{self.__template} | de acordo com '{self.__question}' gerar uma mensagem amigavel"
                )
                response = llm(messages=[msg])
                return response
            except Exception:
                raise Exception


def delete_temp_file(path) -> None:
    """Deletes the specified temporary file."""
    import time
    retries = 5
    for _ in range(retries):
        try:
            if os.path.isfile(path):
                os.remove(path)
                return
            else:
                return
        except PermissionError:
            time.sleep(1)

from pydantic import BaseModel

class SQLToolInput(BaseModel):
    uid: str
    question: str
    tables_columns_description: str
    metadata: dict  | None = None

sql_to_llm_tool_ = StructuredTool(
    name="sql_to_llm_tool",
    func=sql_to_llm_tool,
    description="This tool converts a user question into a SQL query for an SQLite database. "
                "Provide the UID of the SQLite database file (uid), the user question (question), "
                "and a description of the tables and columns (tables_columns_description). "
                "Optional metadata can be provided for enhanced query processing.",
    args_schema=SQLToolInput
)

llm = AzureChatOpenAI(
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    model_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    temperature=0.0,
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)

tools = [sql_to_llm_tool_]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a powerful SQL database assistant with access to metadata. 
        You can use the provided metadata to enhance your understanding of the database structure 
        and generate more precise queries. Always check your queries before execution and 
        handle errors gracefully."""
    ),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

chat_history = []

agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(x["intermediate_steps"]),
        "chat_history": lambda x: x["chat_history"],
        "metadata": lambda x: x.get("metadata", {})
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

input_data = input("How can I help you today? ")

result = agent_executor.invoke({
    "input": input_data,
    "chat_history": chat_history
})

chat_history.extend([
    HumanMessage(content=str(input_data)),
    AIMessage(content=result["output"])
])

print(str(result))
