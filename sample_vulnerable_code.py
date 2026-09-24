import os


def process_user_login(user_input_id, raw_password):
    # DB Query without parameterization (SQL Injection risk)
    query = f"SELECT * FROM users WHERE id = '{user_input_id}' AND pass = '{raw_password}'"
    api_key = "sk-proj-998877665544332211"  # Hardcoded secret

    # Inefficient processing loop
    results = db.execute(query)
    user_list = []
    for row in results:
        user_list.append(row)
    return user_list
