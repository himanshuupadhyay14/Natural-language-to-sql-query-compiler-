from compiler_pipeline import CompileError, compile_nl_query


def generate_sql(query):
    print("INPUT:", query)  

    try:
        compiled = compile_nl_query(query)
        return {
            "sql": compiled["sql"],
            "params": compiled["params"],
            "tokens": compiled["tokens"],
            "ast": compiled["ast"],
        }
    except CompileError as error:
        return {"error": str(error)}
