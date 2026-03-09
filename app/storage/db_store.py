import sqlite3
from pathlib import Path

DB_PATH = Path("data/repoir.db")


class DBStore:
    """
    Single SQLite database for all structured storage:
    - objects table    : file metadata (one row per ingested file)
    - chunks FTS5 table: chunk text with built-in BM25 keyword search
    - vectors table    : FAISS integer ID → chunk_id mapping
    """
    
    def __init__(self, user_id: str = "default"):
        # Create a private folder for each user
        self.user_dir = Path(f"data/users/{user_id}")
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.user_dir / "repoir.db"
        
        # Increased timeout to 20s to prevent locking timeouts during heavy syncs
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=20.0)
        self.conn.row_factory = sqlite3.Row
        
        # High concurrency settings (WAL mode allows readers to read while writers write)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS objects (
                object_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                source      TEXT NOT NULL, -- original filename or URL
                type        TEXT NOT NULL, -- 'document', 'image', 'url', 'text'
                file_type   TEXT,          -- '.pdf', '.png', 'url'
                file_path   TEXT,          -- path in data/objects/ or GDrive file_id
                file_size   INTEGER DEFAULT 0, -- Size in bytes
                chunk_count INTEGER DEFAULT 0,
                thumbnail_url TEXT,        -- GDrive thumbnail link
                icon_url TEXT,             -- GDrive file type icon
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                action      TEXT NOT NULL, -- 'UPLOAD', 'RENAME', 'DELETE', 'CATEGORIZE'
                details     TEXT,
                timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS jobs (
                job_id  TEXT PRIMARY KEY,
                status  TEXT, -- 'processing', 'completed', 'failed'
                details TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                chunk_id    UNINDEXED,
                object_id   UNINDEXED,
                chunk_index UNINDEXED,
                chunk_text,
                tokenize = 'porter ascii'
            );

            CREATE TABLE IF NOT EXISTS vectors (
                vector_id   INTEGER PRIMARY KEY,
                chunk_id    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS categories (
                category_id   TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                description   TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS category_mappings (
                category_id   TEXT,
                object_id     TEXT,
                is_confirmed  INTEGER DEFAULT 0, -- 0 for AI matched, 1 for user confirmed
                PRIMARY KEY (category_id, object_id),
                FOREIGN KEY (category_id) REFERENCES categories(category_id),
                FOREIGN KEY (object_id) REFERENCES objects(object_id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()

        # --- Migrations: safely add new columns to existing DBs ---
        migrations = [
            "ALTER TABLE objects ADD COLUMN icon_url TEXT",
        ]
        for migration in migrations:
            try:
                self.conn.execute(migration)
                self.conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore

    # ── Object (file) operations ───────────────────────────────────────────

    def store_object(self, object_id: str, user_id: str, source: str,
                     type_: str, file_type: str, file_path: str | None,
                     chunk_count: int, file_size: int = 0, thumbnail_url: str = None, icon_url: str = None):
        self.conn.execute(
            "INSERT OR REPLACE INTO objects (object_id, user_id, source, type, file_type, file_path, chunk_count, file_size, thumbnail_url, icon_url) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (object_id, user_id, source, type_, file_type, file_path, chunk_count, file_size, thumbnail_url, icon_url)
        )
        self.conn.commit()

    def get_objects_by_ids(self, object_ids: list[str]) -> list[dict]:
        """Fetch file metadata for a list of object_ids. Deduplicates automatically."""
        seen = set()
        results = []
        for oid in object_ids:
            if oid in seen:
                continue
            row = self.conn.execute(
                "SELECT * FROM objects WHERE object_id = ?", (oid,)
            ).fetchone()
            if row:
                results.append(dict(row))
                seen.add(oid)
        return results

    # ── Chunk (text) operations ────────────────────────────────────────────

    def store_chunks(self, object_id: str, chunks: list[str]):
        """
        Store chunk texts for BM25 keyword search.

        Args:
            object_id: The parent file's object ID
            chunks:    List of chunk text strings (in order)
        """
        data = [
            (f"{object_id}_chunk_{i}", object_id, i, text)
            for i, text in enumerate(chunks)
        ]
        self.conn.executemany(
            "INSERT INTO chunks (chunk_id, object_id, chunk_index, chunk_text) VALUES (?,?,?,?)",
            data
        )
        self.conn.commit()

    def keyword_search(self, query: str, k: int = 50) -> list[str]:
        """
        BM25 keyword search over all chunk texts.
        SQLite FTS5 uses BM25 ranking natively (ORDER BY rank).

        Returns a ranked list of chunk_ids.
        """
        # FTS5 query: escape the query to prevent syntax errors
        safe_query = " ".join(
            f'"{word}"' for word in query.split() if word.strip()
        )
        if not safe_query:
            return []

        try:
            rows = self.conn.execute(
                "SELECT chunk_id FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
                (safe_query, k)
            ).fetchall()
            return [r["chunk_id"] for r in rows]
        except sqlite3.OperationalError:
            # Malformed FTS query — fall back gracefully
            return []

    # ── Vector → Chunk mapping operations ─────────────────────────────────

    def get_next_vector_id(self) -> int:
        """Returns the next available FAISS vector integer ID."""
        # Use FAISS to get the actual running total of vectors.
        # This prevents ID collisions if database rows are deleted.
        from app.storage.faiss_store import FAISSStore
        fs = FAISSStore(user_id=self.user_dir.name)
        return fs.total_vectors()

    def store_vectors(self, start_id: int, chunk_ids: list[str]):
        """Map sequential FAISS vector IDs to chunk_ids."""
        data = [(start_id + i, cid) for i, cid in enumerate(chunk_ids)]
        self.conn.executemany("INSERT INTO vectors VALUES (?,?)", data)
        self.conn.commit()

    def get_chunk_id_by_vector(self, vector_id: int) -> str | None:
        row = self.conn.execute(
            "SELECT chunk_id FROM vectors WHERE vector_id = ?", (vector_id,)
        ).fetchone()
        return row["chunk_id"] if row else None

    def get_chunk_text_by_vector(self, vector_id: int) -> str | None:
        """Fetches the actual text content of a chunk via its vector ID."""
        chunk_id = self.get_chunk_id_by_vector(vector_id)
        if not chunk_id:
            return None
        row = self.conn.execute(
            "SELECT chunk_text FROM chunks WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        return row["chunk_text"] if row else None


    def close(self):
        self.conn.close()

    def update_job_status(self, job_id: str, status: str, details: str = ""):
        self.conn.execute(
            "INSERT OR REPLACE INTO jobs (job_id, status, details) VALUES (?, ?, ?)",
            (job_id, status, details)
        )
        self.conn.commit()

    def get_job_status(self, job_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

        # ── Category & Listing Operations ─────────────────────────────────

    def list_all_objects(self, category_id: str | None = None) -> list[dict]:
        """List all objects, optionally filtered by category."""
        if category_id:
            query = """
                SELECT o.* FROM objects o
                JOIN category_mappings m ON o.object_id = m.object_id
                WHERE m.category_id = ?
            """
            rows = self.conn.execute(query, (category_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM objects").fetchall()
        return [dict(r) for r in rows]

    def create_category(self, category_id: str, name: str, description: str):
        self.conn.execute(
            "INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
            (category_id, name, description)
        )
        self.conn.commit()

    def get_all_categories(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM categories").fetchall()
        return [dict(r) for r in rows]

    def map_files_to_category(self, category_id: str, object_ids: list[str]):
        data = [(category_id, oid) for oid in object_ids]
        self.conn.executemany(
            "INSERT OR IGNORE INTO category_mappings (category_id, object_id) VALUES (?, ?)",
            data
        )
        self.conn.commit()

    def delete_object(self, object_id: str):
        """Cleanly remove an object and all its associated data."""
        self.conn.execute("DELETE FROM objects WHERE object_id = ?", (object_id,))
        self.conn.execute("DELETE FROM chunks WHERE object_id = ?", (object_id,))
        self.conn.execute("DELETE FROM category_mappings WHERE object_id = ?", (object_id,))
        # Note: Mapping to chunk_ids in vectors table stays, but since 
        # objects/chunks entries are gone, it will be ignored by search.
        self.conn.commit()

    def rename_object(self, object_id: str, new_name: str):
        """Updates the display name (source) of an object."""
        self.conn.execute(
            "UPDATE objects SET source = ? WHERE object_id = ?",
            (new_name, object_id)
        )
        self.conn.commit()

    def update_object_cloud_info(self, object_id: str, file_path: str, thumbnail_url: str = None, icon_url: str = None):
        """Atomically links a GDrive file ID and thumbnail to an existing object."""
        self.conn.execute(
            "UPDATE objects SET file_path = ?, thumbnail_url = ?, icon_url = ? WHERE object_id = ?",
            (file_path, thumbnail_url, icon_url, object_id)
        )
        self.conn.commit()

    def delete_category(self, category_id: str):
        """Removes a virtual category and its file associations."""
        self.conn.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
        self.conn.execute("DELETE FROM category_mappings WHERE category_id = ?", (category_id,))
        self.conn.commit()

    # ── Analytics & Activity Log ──────────────────────────────────────

    def log_activity(self, user_id: str, action: str, details: str = ""):
        """Logs a user action (UPLOAD, RENAME, DELETE, etc.)"""
        self.conn.execute(
            "INSERT INTO activity_log (user_id, action, details) VALUES (?, ?, ?)",
            (user_id, action, details)
        )
        self.conn.commit()

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        """Fetches the most recent user actions."""
        rows = self.conn.execute(
            "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_storage_stats(self) -> dict:
        """Calculates total files and storage size grouped by type."""
        query = """
            SELECT type, COUNT(*) as count, SUM(file_size) as size 
            FROM objects 
            GROUP BY type
        """
        rows = self.conn.execute(query).fetchall()
        
        stats = {}
        for r in rows:
            stats[r["type"]] = {
                "count": r["count"],
                "total_size_bytes": r["size"] or 0
            }
        return stats

