from sql_chat import get_metadata, DB_PATH, agent_executor

def main():
    user_query = input("How can I help you? ")
    print(get_metadata(DB_PATH))
    response = agent_executor.invoke({"input": user_query})
    print(response)

if __name__ == "__main__":
    main()
