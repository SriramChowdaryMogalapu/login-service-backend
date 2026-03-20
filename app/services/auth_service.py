from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db import get_db, get_cursor
from app.utils.security import hash_value


def get_authorized_app(app_name: str) -> Optional[dict]:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            "SELECT app_name, client_secret_hash FROM authorized_apps WHERE app_name = %s AND is_active = true",
            (app_name,),
        )
        return cur.fetchone()


def get_user_by_email(email: str) -> Optional[dict]:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute("SELECT * FROM users WHERE UPPER(email) = UPPER(%s) AND is_active = true", (email.strip(),))
        return cur.fetchone()


def get_user_by_id(user_id: str) -> Optional[dict]:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute("SELECT * FROM users WHERE id = %s AND is_active = true", (user_id,))
        return cur.fetchone()


def create_user(email: str, password_hash: str, full_name: str) -> str:
    normalized_email = email.strip().upper()
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, super_user)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (normalized_email, password_hash, full_name, False),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row["id"])


def create_user_with_role(email: str, password_hash: str, full_name: str, super_user: bool = False) -> str:
    normalized_email = email.strip().upper()
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, super_user)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (normalized_email, password_hash, full_name, super_user),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row["id"])


def create_authorized_app(app_name: str, client_secret_hash: str) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        try:
            cur.execute(
                """
                INSERT INTO authorized_apps (app_name, client_secret_hash, is_active)
                VALUES (%s, %s, true)
                """,
                (app_name, client_secret_hash),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def store_refresh_token(user_id: str, app_name: str, refresh_jti: str, expires_delta: timedelta, ip_address: str, user_agent: str) -> None:
    expires_at = datetime.now(timezone.utc) + expires_delta
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            INSERT INTO refresh_tokens (user_id, app_name, token_hash, expires_at, ip_address, device_info)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, app_name, hash_value(refresh_jti), expires_at, ip_address, user_agent),
        )
        conn.commit()


def revoke_refresh_tokens_for_user(user_id: str, app_name: str) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            "UPDATE refresh_tokens SET revoked = true WHERE user_id = %s AND app_name = %s",
            (user_id, app_name),
        )
        conn.commit()


def revoke_refresh_token_jti(user_id: str, app_name: str, refresh_jti: str) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked = true
            WHERE user_id = %s AND app_name = %s AND token_hash = %s
            """,
            (user_id, app_name, hash_value(refresh_jti)),
        )
        conn.commit()


def is_refresh_token_active(user_id: str, app_name: str, refresh_jti: str) -> bool:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            SELECT id
            FROM refresh_tokens
            WHERE user_id = %s
              AND app_name = %s
              AND token_hash = %s
              AND revoked = false
              AND expires_at > NOW()
            """,
            (user_id, app_name, hash_value(refresh_jti)),
        )
        return cur.fetchone() is not None


def create_password_reset(user_id: str, token: str, expires_at: datetime) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (user_id, hash_value(token), expires_at),
        )
        conn.commit()


def get_valid_password_reset_user_id(token: str) -> Optional[str]:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            SELECT user_id
            FROM password_resets
            WHERE token_hash = %s AND expires_at > NOW() AND used = false
            """,
            (hash_value(token),),
        )
        row = cur.fetchone()
        return str(row["user_id"]) if row else None


def mark_password_reset_used(token: str) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute("UPDATE password_resets SET used = true WHERE token_hash = %s", (hash_value(token),))
        conn.commit()


def update_user_password(user_id: str, password_hash: str) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
        conn.commit()


def update_user_mpin(user_id: str, mpin_hash: str) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute("UPDATE users SET mpin_hash = %s WHERE id = %s", (mpin_hash, user_id))
        conn.commit()


def update_user_super_user(user_id: str, super_user: bool) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute("UPDATE users SET super_user = %s WHERE id = %s", (super_user, user_id))
        conn.commit()
