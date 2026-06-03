import os
import re
import sqlite3
from datetime import date
from groq import Groq
from database import get_connection, SCHEMA, get_rep

# Disallow any SQL that mutates data or reads filesystem
_BLOCKED_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH"
    r"|PRAGMA|VACUUM|REINDEX|LOAD_EXTENSION|sqlite_master)\b",
    re.IGNORECASE,
)

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
6. For sales approach and strategy questions, use the approach_used field in the sales table
   and the outcome field in the visits table to surface patterns.

SQL rules (CRITICAL — follow exactly):
- Always use explicit table aliases and JOIN … ON syntax. Never reference a column with an alias
  that has not been defined in the FROM / JOIN clause of that query.
- When joining sales and visits, use:
    FROM sales s JOIN visits v ON v.store_id = s.store_id AND v.rep_id = s.rep_id
- approach_used values: 'demo', 'discount_offer', 'relationship', 'cold_visit'
- visits.outcome values: 'order_placed', 'follow_up', 'no_order'
- "Best approach" = highest SUM(revenue) or highest rate of outcome='order_placed'
- "Low-performing stores" = store_tier = 'C' OR stores with low recent revenue
- For cross-rep comparisons (manager/admin only), remove the rep_id filter.

Example strategy query (approach with best order rate):
  SELECT s.approach_used,
         COUNT(CASE WHEN v.outcome = 'order_placed' THEN 1 END) * 1.0 / COUNT(*) AS order_rate,
         SUM(s.revenue) AS total_revenue
  FROM sales s
  JOIN visits v ON v.store_id = s.store_id
  WHERE s.rep_id = {rep['rep_id']}
  GROUP BY s.approach_used
  ORDER BY order_rate DESC;
"""


def _clean_sql(raw: str) -> str:
    sql = raw.strip()
    if sql.startswith("```"):
        lines = sql.splitlines()
        sql = "\n".join(l for l in lines if not l.startswith("```")).strip()
    return sql


def _ask_for_sql(question: str, rep: dict, prior_sql: str = None, error: str = None) -> str:
    system = _build_system_prompt(rep)
    if prior_sql and error:
        user_content = (
            f"The following SQLite query failed with error: {error}\n\n"
            f"Broken SQL:\n{prior_sql}\n\n"
            f"Fix the SQL so it is valid SQLite. Remember: always use explicit JOINs with ON clauses "
            f"and never reference an alias that is not defined in the FROM/JOIN clause.\n\n"
            "Return ONLY the corrected raw SQL query, no explanation, no backticks."
        )
    else:
        user_content = (
            f"Generate a single valid SQLite SQL query to answer this question: {question}\n\n"
            "Return ONLY the raw SQL query with no explanation, no markdown, no backticks."
        )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    return _clean_sql(resp.choices[0].message.content)


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


def _is_safe_sql(sql: str) -> bool:
    return sql.strip().upper().startswith("SELECT") and not _BLOCKED_SQL.search(sql)


def _run_sql(sql: str) -> tuple[list, str | None]:
    if not _is_safe_sql(sql):
        return [], "Only SELECT queries are permitted"
    try:
        with get_connection() as conn:
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return rows, None
    except sqlite3.Error as e:
        return [], str(e)


def chat(question: str, rep_id: int) -> dict:
    rep = get_rep(rep_id)
    if not rep:
        return {"answer": "Rep not found.", "query_executed": None, "rep": None}

    sql = _ask_for_sql(question, rep)
    rows, error = _run_sql(sql)

    # One automatic retry with the error fed back to the model
    if error:
        sql = _ask_for_sql(question, rep, prior_sql=sql, error=error)
        rows, error = _run_sql(sql)

    if error:
        answer = (
            "I wasn't able to retrieve that data right now. "
            "Try rephrasing your question or ask something more specific."
        )
    else:
        answer = _ask_for_answer(question, sql, rows, rep)

    return {
        "answer": answer,
        "query_executed": sql,
        "rep": rep,
    }
