import os
import sqlite3
import time
import dotenv
from langchain.agents import initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from langchain.tools import Tool

dotenv.load_dotenv()
DB_PATH = "data/temp.db"

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_version=os.getenv("AZURE_API_VERSION"),
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
)

def get_metadata(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    metadata = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        metadata[table_name] = columns

    connection.close()
    return metadata

generate_sql_tool = Tool(
    name="SQLQueryGenerator",
    func=lambda query: generate_sql_agent(query, get_metadata(DB_PATH)),
    description="Generates an SQL query based on the user's request and the database structure.",
)

def generate_sql_agent(user_query, metadata):
    prompt = f"""
    You are an SQL expert. The database contains the following tables and columns:
    {metadata}
    Generate a valid SQL query to answer the following question:
    "{user_query}"
    """
    sql_query = llm.predict(prompt).strip()
    return sql_query

generate_sql_tool = Tool(
    name="SQLQueryGenerator",
    func=lambda query: generate_sql_agent(query, get_metadata(DB_PATH)),
    description="Generates an SQL query based on the user's request and the database structure.",
)

def is_query_relevant(user_query, metadata, max_attempts=3, timeout=1) -> bool:
    attempts = 0
    while attempts < max_attempts:
        prompt = f"""
        You are an AI assistant analyzing a database. Below is the schema:
        {metadata}

        The user asked: "{user_query}"

        Check if the database has the necessary tables and columns to answer the question.
        Respond with only "YES" if it can be answered using the available data, otherwise respond with only "NO".
        """
        response = llm.predict(prompt).strip().upper()
        is_relevant = response == "YES"
        print(f"\nAttempt {attempts+1}: It's relevant: {is_relevant}")

        if is_relevant:
            return True

        attempts += 1
        time.sleep(timeout)

    return False

def query_database(user_query, max_attempts=3):
    metadata = get_metadata(DB_PATH)

    if not is_query_relevant(user_query, metadata):
        return "The database does not contain enough information to answer your question."

    attempts = 0
    while attempts < max_attempts:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                sql_prompt = f"""
                    You are an AI SQL assistant for an SQLite database. The database has the following metadata: {metadata}.
                    You can only query the tables and columns listed in the metadata.
                    Generate an SQL query to answer the following question: "{user_query}."
                    """
                sql_query = llm.predict(sql_prompt).strip()
                print(f"Generated SQL Query (Attempt {attempts+1}): {sql_query}")

                cursor.execute(sql_query)
                query_result = cursor.fetchall()

                if not query_result:
                    attempts += 1
                    print("No data found. Retrying...\n")
                    continue

                result_prompt = f"""
                    The user asked: "{user_query}"
                    The database query returned: "{query_result}"

                    Convert this result into a clear and natural language answer for the user.
                    """
                final_response = llm.predict(result_prompt).strip()
                return final_response

        except Exception as e:
            print(f"Error executing query (Attempt {attempts+1}): {e}")
            attempts += 1

    return "I tried multiple queries but couldn't find relevant data."

query_tool = Tool(
    name="DatabaseQueryTool",
    func=query_database,
    description="Use this tool to execute SQL queries in the database. Provide a natural language query."
)

agent_executor = initialize_agent(
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    tools=[query_tool],
    llm=llm,
    verbose=True
)

