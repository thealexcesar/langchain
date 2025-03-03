import logging
import os
import re
import sqlite3
import dotenv
from langchain.agents import initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from langchain.tools import Tool

dotenv.load_dotenv()
DB_PATH = "data/temp.db"

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_version=os.getenv("AZURE_API_VERSION"),
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
)

def get_metadata(db_path):
    """Get enhanced metadata from the database, including information about tables and data samples."""
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    metadata = {}
    sample_data = {}

    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [{"name": row[1], "type": row[2]} for row in columns_info]

        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            sample = cursor.fetchall()
            if sample:
                sample_data[table_name] = sample
        except Exception as e:
            logger.error("Sample Data Exception:", e)

        metadata[table_name] = columns
    connection.close()
    return metadata, sample_data

def query_sql(user_query):
    metadata, sample_data = get_metadata(DB_PATH)

    schema_info = "\n".join(
        f"Table: {table}\nColumns: {', '.join(col['name'] for col in columns)}"
        for table, columns in metadata.items()
    )

    sample_info = "\n".join(
        f"First line from {table}: {samples[0]}"
        for table, samples in sample_data.items() if samples
    )

    planning_prompt = f"""
    You are an SQLite expert. Given the database schema and sample data below, generate an efficient SQLite query to answer the user's question.

    Database Schema: {schema_info}
    Sample Data: {sample_info}

    User's question: "{user_query}"
    """

    for attempt in range(3):
        plan = llm.predict(planning_prompt).strip()
        sql_prompt = f"""
        {schema_info}
        {sample_info}

        Your plan: {plan}

        Based on the above plan and the database structure, generate an appropriate SQL query to answer: "{user_query}"

        Return ONLY the SQL query, No pre-amble.
        """

        sql_query = llm.predict(sql_prompt).strip()
        logger.info("\nGenerated query: \n%s", sql_query)
        sql_query = llm.predict(clear_query(sql_prompt)).strip()

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                column_names = [description[0] for description in cursor.description]
                query_result = cursor.fetchall()

                if not query_result:
                    logger.warning("The query returned no results.")
                    if attempt < 4:
                        logger.info("No results found. Trying a different approach...")
                        continue

                formatted_results = []
                for row in query_result:
                    formatted_row = {column_names[i]: row[i] for i in range(len(column_names))}
                    formatted_results.append(formatted_row)

                final_answer = "<<<BEGIN_SQL_RESULTS>>>\n"
                for idx, result in enumerate(formatted_results, start=1):
                    result_str = ", ".join(f"{key}: {value}" for key, value in result.items())
                    final_answer += f"{idx}. {result_str}\n"
                final_answer += "<<<END_SQL_RESULTS>>>\n"
                final_answer += "IMPORTANT: Your final answer MUST include ALL fields shown above in EXACTLY the same format and order.\n"

                return final_answer

        except Exception as e:
            logger.error(f"SQL query execution failed: {e}")
            if attempt < 4:
                logger.info("Attempting an alternative query...")
            else:
                return "Could not execute query. Check you answer and try again."
            continue

    return "Could not execute the query after multiple attempts."


def clear_query(query):
    query = re.sub(r'```sql|```', '', query, flags=re.IGNORECASE)
    query = re.sub(r'--.*$', '', query)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    query = re.sub(r'[^\w\s\(\)=<>\+\-\*,\.]', '', query)
    return query.strip()


query_tool = Tool(
    name="SQLQueryTool",
    func=query_sql,
    description="Enhanced tool for querying the database."
)

agent_executor = initialize_agent(
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    tools=[query_tool],
    llm=llm,
    verbose=True
)

