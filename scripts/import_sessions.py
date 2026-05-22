#!/usr/bin/env python3
"""
Import session_*.json files in /opt/data/sessions into the Hermes
state.db (sessions + messages tables). Idempotent — uses INSERT OR
REPLACE on the sessions row; deletes prior messages for the session
before re-inserting so re-runs don't duplicate.

Usage:
    docker exec hermes /opt/hermes/.venv/bin/python /opt/data/import_sessions.py [SESSION_ID...]

With no args, imports all session_2026*.json. With args, imports only
the specified IDs (the prefix `session_` is optional).
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def _to_epoch(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return datetime.fromisoformat(str(v)).timestamp()


SESSIONS_DIR = Path("/opt/data/sessions")
DB_PATH = "/opt/data/state.db"


def _normalize_content(content):
    """Hermes content can be a str OR a list of parts (text + tool_use). Persist as TEXT."""
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _import_one(conn: sqlite3.Connection, json_path: Path) -> tuple[str, int]:
    with json_path.open() as f:
        data = json.load(f)

    file_id = json_path.stem.removeprefix("session_")
    msgs = data.get("messages", [])
    n_msgs = len(msgs)
    tool_calls = sum(1 for m in msgs if m.get("tool_calls"))
    started = _to_epoch(data.get("session_start"))
    ended = _to_epoch(data.get("last_updated")) or started
    duration_per_msg = (ended - started) / max(n_msgs, 1)

    title = ""
    first_user = next((m for m in msgs if m.get("role") == "user"), None)
    if first_user:
        c = first_user.get("content")
        if isinstance(c, list):
            c = next((p.get("text", "") for p in c if p.get("type") == "text"), "")
        body = (c or "")[:90]
        # sessions.title has a UNIQUE constraint; prefix with start time so
        # that splits of the same parent conversation don't collide.
        # Use the snapshot timestamp embedded in the file_id rather than
        # session_start — splits of the same parent share session_start.
        try:
            snap = datetime.strptime(file_id[:15], "%Y%m%d_%H%M%S")
            prefix = snap.strftime("%m-%d %H:%M")
        except ValueError:
            prefix = file_id[:13]
        title = f"[{prefix}] {body}"

    base_url = data.get("base_url") or ""
    billing_provider = (
        "anthropic" if "anthropic" in base_url
        else "openrouter" if "openrouter" in base_url
        else "openai" if "openai" in base_url
        else None
    )

    conn.execute("DELETE FROM messages WHERE session_id = ?", (file_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (file_id,))
    conn.execute(
        """
        INSERT INTO sessions (
            id, source, model, system_prompt,
            started_at, ended_at, message_count, tool_call_count,
            billing_provider, billing_base_url, title
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_id,
            data.get("platform") or "cli",
            data.get("model"),
            data.get("system_prompt"),
            started,
            ended,
            n_msgs,
            tool_calls,
            billing_provider,
            base_url or None,
            title,
        ),
    )

    for i, m in enumerate(msgs):
        ts = started + duration_per_msg * i
        conn.execute(
            """
            INSERT INTO messages (
                session_id, role, content,
                tool_call_id, tool_calls, tool_name,
                timestamp, finish_reason, reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                m.get("role"),
                _normalize_content(m.get("content")),
                m.get("tool_call_id"),
                json.dumps(m["tool_calls"], ensure_ascii=False) if m.get("tool_calls") else None,
                m.get("tool_name"),
                ts,
                m.get("finish_reason"),
                m.get("reasoning"),
            ),
        )

    return file_id, n_msgs


def main(argv: list[str]) -> int:
    wanted = {a.removeprefix("session_").removesuffix(".json") for a in argv} if argv else None

    files = sorted(SESSIONS_DIR.glob("session_2026*.json"))
    if wanted is not None:
        files = [f for f in files if f.stem.removeprefix("session_") in wanted]

    if not files:
        print("No matching session files found.")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    for f in files:
        try:
            sid, n = _import_one(conn, f)
            print(f"  ✓ imported {sid} ({n} messages)")
        except Exception as e:
            print(f"  ✗ {f.name}: {type(e).__name__}: {e}")

    conn.commit()
    print()
    s = conn.execute("SELECT count(*) FROM sessions").fetchone()[0]
    m = conn.execute("SELECT count(*) FROM messages").fetchone()[0]
    fts = conn.execute("SELECT count(*) FROM messages_fts").fetchone()[0]
    print(f"DB now has: {s} sessions, {m} messages, {fts} indexed in FTS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
