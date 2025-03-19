from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from credentials_llm import AZURE
from qa_sql import query_db

tool = Tool(
    name="query",
    func=query_db,
    description="Run SQL queries and return results"
)

agent = initialize_agent(
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    tools=[tool],
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
