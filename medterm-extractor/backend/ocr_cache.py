"""Persistent cache for OCR results keyed by the uploaded image bytes."""

import hashlib
import os
import sqlite3
from contextlib import contextmanager


class OCRCache:
    def __init__(self, database_path):
        self.database_path = database_path
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ocr_results (
                    image_hash TEXT PRIMARY KEY,
                    raw_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def image_hash(image_bytes):
        return hashlib.sha256(image_bytes).hexdigest()

    def get(self, image_bytes):
        image_hash = self.image_hash(image_bytes)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT raw_text FROM ocr_results WHERE image_hash = ?",
                (image_hash,),
            ).fetchone()
        return row[0] if row else None

    def put(self, image_bytes, raw_text):
        image_hash = self.image_hash(image_bytes)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ocr_results (image_hash, raw_text)
                VALUES (?, ?)
                ON CONFLICT(image_hash) DO UPDATE SET
                    raw_text = excluded.raw_text,
                    created_at = CURRENT_TIMESTAMP
                """,
                (image_hash, raw_text),
            )
