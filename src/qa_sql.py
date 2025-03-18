import os
import sqlite3
from sqlalchemy import create_engine, inspect

def query_db(query):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data/temp.db')
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
        print("\nSchema: ", formatted_results)
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
