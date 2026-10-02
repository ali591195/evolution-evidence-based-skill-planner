from app.db import get_conn


def create_user(name: str, email: str, password_hash: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO users (name, email, password_hash) "
            "VALUES (%s, %s, %s) RETURNING id",
            (name, email, password_hash),
        ).fetchone()
    return str(row[0])


def get_by_email(email: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = %s", (email,)
        ).fetchone()
    return {"id": str(row[0]), "password_hash": row[1]} if row else None


def get_by_id(user_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    return {"id": str(row[0]), "name": row[1], "email": row[2]} if row else None