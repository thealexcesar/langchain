import os
import dotenv
from langchain_openai import AzureChatOpenAI
from crewai import Agent, Task, Crew, Process
from langchain.tools import Tool
from pydantic import BaseModel, Field
import sqlite3
from sqlalchemy import create_engine, inspect

dotenv.load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_version=os.getenv("AZURE_API_VERSION"),
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
)

class SQLQueryToolParameters(BaseModel):
    query: str = Field(..., description="SQL query to execute.")

def query_db_tool(query: str):
    db_path = "../data/temp.db"
    return query_db(query, db_path)

sql_query_tool = Tool(
    name="SQL Query Tool",
    func=query_db_tool,
    description="Execute SQL queries and return results",
    args_schema=SQLQueryToolParameters
)

def query_db(query: str, db_path: str):
    query = query.strip()
    schema_info = get_schema_info(db_path)

    if not query.lower().startswith(('select', 'show', 'with')):
        return [{"Error": f"Invalid query. Only SELECT queries allowed.", "Schema": schema_info}]

    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = connection.cursor()
        cursor.execute(query)

        column_names = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        formatted_results = []
        for row in results:
            formatted_row = {column_names[i]: row[i] for i in range(len(column_names))}
            formatted_results.append(formatted_row)

        connection.close()

        if formatted_results:
            formatted_results[0]["_schema_info"] = schema_info
        else:
            formatted_results = [{"_schema_info": schema_info, "message": "Query executed successfully, but returned no results."}]
        return formatted_results
    except sqlite3.OperationalError as e:
        if "readonly database" in str(e).lower():
            return [{"error": "Security Error: Attempt to modify database detected.", "_schema_info": schema_info}]
        return [{"error": f"Database error: {str(e)}", "_schema_info": schema_info}]
    except Exception as e:
        return [{"error": f"Execution error: {str(e)}", "_schema_info": schema_info}]

def get_schema_info(db_path):
    if not os.path.exists(db_path):
        return {"Error": "Database file not found."}

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            return {"Error": "No tables found in the database."}

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

agent = Agent(
    role="Database Specialist",
    goal="Execute SQL queries and provide database information",
    backstory="Database specialist executing SQL queries and providing database information",
    tools=[sql_query_tool],
    verbose=True,
    allow_delegation=True,
    llm=llm
)

task = Task(
    description="Execute an SQL query",
    expected_output="SQL query results",
    tools=[sql_query_tool],
    agent=agent
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    process=Process.sequential,
    cache=True,
    max_rpm=100,
    share_crew=True
)

def main():
    query = input("How can I assist you? ").strip()
    task.description = f"Execute the SQL query: {query}"
    result = crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()
