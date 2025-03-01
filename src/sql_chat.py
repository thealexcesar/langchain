import logging
import os
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

def get_enhanced_metadata(db_path):
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
                logger.info("SAMPLE DATA: %s", sample_data)
        except Exception as e:
            logger.error("Sample Data Exception:", e)
            pass

        metadata[table_name] = columns
    connection.close()
    return metadata, sample_data


def query_sql(user_query):
    """Execute an SQL query based on the user's question and return an informative response."""
    metadata, sample_data = get_enhanced_metadata(DB_PATH)

    schema_info = "Database structure:\n"
    for table, columns in metadata.items():
        schema_info += f"Table: {table}\n"
        schema_info += "Columns:\n"
        for col in columns:
            schema_info += f"- {col['name']} ({col['type']})\n"

    sample_info = "\nData sample:\n"
    for table, samples in sample_data.items():
        if samples:
            sample_info += f"First line from {table}: {samples[0]}\n"

    planning_prompt = f"""
    {schema_info}
    {sample_info}

    The user's question is: "{user_query}"

    1. Identify which tables and columns are relevant to this query.
    2. Plan how to construct an efficient SQL query.
    3. Describe your plan step by step.
    """

    for attempt in range(5):
        logger.info("Attempt %s to generate SQL query.", attempt+1)
        plan = llm.predict(planning_prompt).strip()
        logger.info("Generated plan: %s", plan)

        sql_prompt = f"""
        {schema_info}
        {sample_info}

        Your plan: {plan}

        Based on the above plan and the database structure, generate an appropriate SQL query to answer: "{user_query}"

        Return ONLY the SQL query, without additional explanations.
        """

        sql_query = llm.predict(sql_prompt).strip()

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()

                cursor.execute(sql_query)
                column_names = [description[0] for description in cursor.description]
                query_result = cursor.fetchall()

                formatted_results = []
                for row in query_result:
                    formatted_row = {}
                    for i, col_name in enumerate(column_names):
                        formatted_row[col_name] = row[i]
                    formatted_results.append(formatted_row)

                if not query_result:
                    logger.warning("The query returned no results.")
                    if attempt < 2:
                        print("No results found. Trying adifferent approach...")
                        planning_prompt +="\nPlease simplify your plan or consider alternative tables."
                        continue
                    return "The query returned no results."

                answer_prompt = f"""
                The user's question was: "{user_query}"
                The SQL query used was: "{sql_query}"

                The results of the query are:
                {formatted_results}

                Please respond to the user's question in a natural and informative way based on these results.
                """

                final_response = llm.predict(answer_prompt).strip()
                return final_response

        except Exception as e:
            logger.error(f"SQL query execution failed: {e}")
            fallback_prompt = f"""
            {schema_info}
            {sample_info}

            The SQL query "{sql_query}" failed with the error: {str(e)}

            Please create an alternative SQL query to answer the question: "{user_query}"
            Make sure to use only existing tables and columns as listed above.
            """

            alternative_query = llm.predict(fallback_prompt).strip()
            logger.info(f"Generated alternative SQL query: {alternative_query}")

            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(alternative_query)
                    query_result = cursor.fetchall()

                    if not query_result:
                        logger.warning("No results could be found for your query.")
                        return "No results could be found for your query."

                    final_response = llm.predict(f"""
                    The user's question was: "{user_query}"
                    The result of the alternative query was: {query_result}

                    Provide a clear answer to the user.
                    """).strip()

                    return final_response
            except Exception as e:
                logger.error(f"Could not execute the alternative query: {e}")
                return "Could not execute the query. Please check if your question is related to the available data."


query_tool = Tool(
    name="SQLQueryTool",
    func=query_sql,
    description="Enhanced tool for querying the database. Provides a more structured approach to finding information."
)

agent_executor = initialize_agent(
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    tools=[query_tool],
    llm=llm,
    verbose=True
)
