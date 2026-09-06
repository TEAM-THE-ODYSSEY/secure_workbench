import sqlite3
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone

def now():
    return datetime.now(timezone.utc).isoformat()

class SessionStore:
    def __init__(self, db_path="./data/agentic_engine.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS chats("
                      "chat_id TEXT PRIMARY KEY,title TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS messages("
                      "id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id TEXT,"
                      "role TEXT,content TEXT,metadata TEXT,created_at TEXT)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def create_chat(self, title="New Chat"):
        cid, t = str(uuid.uuid4()), now()
        with self._db() as c:
            c.execute("INSERT INTO chats VALUES(?,?,?,?)",(cid,title,t,t))
        return cid

    def exists(self, cid):
        with self._db() as c:
            return c.execute("SELECT 1 FROM chats WHERE chat_id=?",(cid,)).fetchone() is not None

    def add(self,cid,role,content,metadata=None):
        if not self.exists(cid):
            raise ValueError("Unknown chat ID")
        t=now()
        with self._db() as c:
            c.execute("INSERT INTO messages(chat_id,role,content,metadata,created_at) VALUES(?,?,?,?,?)",
                      (cid,role,content,json.dumps(metadata or {}),t))
            c.execute("UPDATE chats SET updated_at=? WHERE chat_id=?",(t,cid))

    def history(self,cid,limit=20):
        with self._db() as c:
            rows=c.execute("SELECT role,content,metadata,created_at FROM messages "
                           "WHERE chat_id=? ORDER BY id DESC LIMIT ?",(cid,limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def chats(self):
        with self._db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM chats ORDER BY updated_at DESC")]
