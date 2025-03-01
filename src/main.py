from sql_chat import agent_executor

def main():
    user_query = input("How can I help you? ")
    response = agent_executor.invoke({"input": user_query})
    print(response)

if __name__ == "__main__":
    main()
