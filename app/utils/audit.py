import json
from typing import Any, Optional

from flask import request

from app.db import get_db, get_cursor


def log_audit(user_id: Optional[str], app_name: str, action: str, success: bool, details: Optional[dict[str, Any]] = None) -> None:
    with get_db() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, app_name, action, success, details, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                app_name,
                action,
                success,
                json.dumps(details or {}),
                request.remote_addr,
                request.headers.get("User-Agent"),
            ),
        )
        conn.commit()
