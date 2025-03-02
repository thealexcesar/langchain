from sql_chat import agent_executor

def main():
    while True:
        user_query = input("How can I help you? ")
        
        if user_query == 'exit':
            break

        response = agent_executor.invoke({"input": user_query})
        print(("output:", response['output']) if 'output' in response else "No valid output received.")

if __name__ == "__main__":
    main()

