from crewai import Agent, Task, Crew, Process
from langchain.tools import Tool

from src.credentials_llm import llm
from src.qa_sql import query_db

tool = Tool(
    name="SQL Query Tool",
    func=query_db,
    description="Execute SQLite queries and return results"
)

agent = Agent(
    role="Database Specialist",
    goal="Execute SQL queries and provide database information",
    backstory="Database specialist executing SQL queries and providing database information",
    tools=[tool],
    verbose=True,
    allow_delegation=True,
    llm=llm
)

task = Task(
    description="Execute an SQL query",
    expected_output="SQL query results",
    tools=[tool],
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
    query = input("How can I help you? ").strip()
    task.description = f"Execute the SQL query: {query}"
    result = crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()
