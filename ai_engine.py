import os
import sqlite3
from datetime import date
from groq import Groq
from database import get_connection, SCHEMA, get_rep

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def _build_system_prompt(rep: dict) -> str:
    return f"""You are SaneForce AI, a sales intelligence assistant for field sales reps.

User context:
- Rep: {rep['name']}, Role: {rep['role']}, Territory: {rep['territory']}
- Today's date: {date.today().isoformat()}

Database schema:
{SCHEMA}

Rules:
1. Only answer questions about sales, stores, products, visits, and sales strategies.
2. Scope all queries to the user's rep_id ({rep['rep_id']}) unless their role is 'manager' or 'admin'.
3. Always return a clear, concise English answer. Never show raw SQL to the user.
4. If the data does not support the question, say so clearly. Never fabricate numbers.
5. When relevant, add a short recommendation after the answer.
6. For sales approach questions, analyze the approach_used field in the sales table and correlate with outcomes.
"""


def _ask_for_sql(question: str, rep: dict) -> str:
    system = _build_system_prompt(rep)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Generate a single valid SQLite SQL query to answer this question: {question}\n\n"
                    "Return ONLY the raw SQL query with no explanation, no markdown, no backticks."
                ),
            },
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip().strip("`").strip()


def _ask_for_answer(question: str, sql: str, rows: list, rep: dict) -> str:
    system = _build_system_prompt(rep)
    data_str = str(rows) if rows else "No records found."
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"The user asked: {question}\n\n"
                    f"The SQL query used was: {sql}\n\n"
                    f"The data returned was:\n{data_str}\n\n"
                    "Write a clear, friendly natural language answer. "
                    "Add a short recommendation at the end if relevant."
                ),
            },
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def chat(question: str, rep_id: int) -> dict:
    rep = get_rep(rep_id)
    if not rep:
        return {"answer": "Rep not found.", "query_executed": None}

    sql = _ask_for_sql(question, rep)

    # Strip accidental markdown fences if the model adds them
    if sql.startswith("```"):
        lines = sql.splitlines()
        sql = "\n".join(l for l in lines if not l.startswith("```")).strip()

    rows = []
    error = None
    try:
        with get_connection() as conn:
            cursor = conn.execute(sql)
            rows = [dict(r) for r in cursor.fetchall()]
    except sqlite3.Error as e:
        error = str(e)

    if error:
        answer = (
            f"I had trouble retrieving that data. "
            f"Please try rephrasing your question. (Internal error: {error})"
        )
    else:
        answer = _ask_for_answer(question, sql, rows, rep)

    return {
        "answer": answer,
        "query_executed": sql,
        "rep": rep,
    }
