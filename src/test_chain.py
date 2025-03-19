import os
import sqlite3
from langchain.agents import Tool, AgentType, initialize_agent
from langchain_core.pydantic_v1 import BaseModel, Field
from sqlalchemy import create_engine, inspect
from credentials_llm import AZURE
import dotenv

dotenv.load_dotenv()


class QueryArgsClass(BaseModel):
    sql_query: str = Field(description="SQL query to execute")

def sql_query_func(query):

    db_path = "data/temp.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    metadata = None
    try:
        cursor.execute(query)
        column_names = [description[0] for description in cursor.description]
        results = cursor.fetchall()

        formatted_results = []
        for row in results:
            formatted_row = {column_names[i]: row[i] for i in range(len(column_names))}
            formatted_results.append(formatted_row)
        metadata = get_schema_info(db_path)

        if formatted_results:
            formatted_results[0]["_metadata"] = metadata
        else:
            formatted_results = [{"_metadata": metadata, "message": "Query executed successfully, but returned no results."}]
        return formatted_results

    except sqlite3.Error as e:
        return [{"error": f"Database error: {str(e)}", "_metadata": metadata}]
    finally:
        conn.close()


def get_schema_info(db_path):
    if not os.path.exists(db_path):
        return {"Error": "Database file not found."}

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            return {"Error": "No tables found in database."}

        schema_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema_info[table] = {
                "columns": [column['name'] for column in columns],
                "primary_keys": inspector.get_pk_constraint(table)['constrained_columns'],
                "foreign_keys": inspector.get_foreign_keys(table)
            }
        return schema_info
    except Exception as e:
        return {"error": f"Schema extraction error: {str(e)}."}



sql_tool = Tool(
    name="sql_query",
    func=sql_query_func,
    description="Execute SQL queries against SQLite database",
    args_schema=QueryArgsClass
)


agent = initialize_agent(
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    tools=[sql_tool],
    llm=AZURE,
    handle_parsing_errors=True,
    verbose=True
)


def main():
    query = input("How can I help you? ").strip()
    try:
        result = agent.invoke({"input": query})
        print(f"LLM output: {result['output']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
