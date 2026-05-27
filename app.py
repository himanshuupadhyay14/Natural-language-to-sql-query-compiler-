from flask import Flask, render_template, request
import sqlite3
import threading
import webbrowser

from query_engine import generate_sql

app = Flask(__name__, template_folder="templates")


def execute_query(sql_query, params=None):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    params = params or []

    try:
        print("SQL:", sql_query, "PARAMS:", params)  
        cursor.execute(sql_query, params)

        if sql_query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        else:
            conn.commit()
            results = [("Operation successful",)]
            columns = ["Status"]
    except Exception as e:
        results = [(str(e),)]
        columns = ["Error"]
    finally:
        conn.close()

    return columns, results


@app.route("/", methods=["GET", "POST"])
def index():
    user_query = ""
    sql_query = ""
    results = []
    columns = []
    tokens = []
    ast_summary = []

    if request.method == "POST":
        user_query = request.form["query"].strip()
        query_data = generate_sql(user_query)

        if query_data.get("error"):
            return render_template(
                "index.html",
                user_query=user_query,
                sql_query="",
                results=[(query_data["error"],)],
                columns=["Error"],
                tokens=[],
                ast_summary=[],
            )

        sql_query = query_data["sql"]
        tokens = query_data.get("tokens", [])
        ast = query_data.get("ast")
        if ast:
            ast_summary = [
                f"action = {ast.action}",
                f"table = {ast.table}",
            ]
            if ast.aggregate:
                ast_summary.append(f"aggregate = {ast.aggregate}")
            if ast.conditions:
                ast_summary.extend(
                    f"condition = {item.column} {item.operator} {item.value}" for item in ast.conditions
                )
            if ast.updates:
                ast_summary.extend(
                    f"update = {item.column} {item.operator} {item.value}" for item in ast.updates
                )
            if ast.insert_values:
                ast_summary.extend(
                    f"insert = {key}: {value}" for key, value in ast.insert_values.items()
                )
        columns, results = execute_query(sql_query, query_data.get("params"))

    return render_template(
        "index.html",
        user_query=user_query,
        sql_query=sql_query,
        results=results,
        columns=columns,
        tokens=tokens,
        ast_summary=ast_summary,
    )


if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    app.run(debug=True, use_reloader=False)

