"""Fork-safe, per-process cache of read-only SQLite connections."""

import os
import sqlite3
from typing import Dict, Optional


class SQLiteConnCache:
    """Per-process cache of read-only SQLite connections, keyed by DB path.

    ``sqlite3.Connection`` objects are not fork/pickle-safe, so callers hold only
    a DB *path* and (re)acquire their connection from here. This keeps wrappers
    trivially picklable — they can be sent to a ``ProcessPoolExecutor`` worker
    and will lazily open their own connection in that process on first use. The
    PID guard drops any connections inherited via ``fork`` (they belong to the
    parent and are unsafe to reuse in the child).
    """

    _conns: Dict[str, sqlite3.Connection] = {}
    _pid: Optional[int] = None

    @classmethod
    def get(cls, db_path: str) -> sqlite3.Connection:
        pid = os.getpid()
        if cls._pid != pid:
            cls._conns = {}
            cls._pid = pid
        conn = cls._conns.get(db_path)
        if conn is None:
            conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
            conn.execute("PRAGMA query_only=ON")
            cls._conns[db_path] = conn
        return conn

    @classmethod
    def drop(cls, db_path: str) -> None:
        """Forget (and close) a cached connection, e.g. after the file was rebuilt."""
        if cls._pid != os.getpid():
            return
        conn = cls._conns.pop(db_path, None)
        if conn is not None:
            conn.close()
