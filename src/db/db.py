import sqlite3
from pathlib import Path
import sys

import sqlite_vector


def load_vector_extension(connection: sqlite3.Connection) -> None:
    binary_name = {
        "win32": "vector.dll",
        "darwin": "vector.dylib",
        "linux": "vector.so",
    }.get(sys.platform)
    if binary_name is None:
        raise OSError(f"Unsupported platform for sqlite-vector: {sys.platform}")

    extension_path = Path(sqlite_vector.__file__).parent / "binaries" / binary_name

    if not extension_path.is_file():
        raise FileNotFoundError(
            f"sqlite-vector extension was not found at {extension_path}"
        )

    connection.enable_load_extension(True)
    try:
        connection.load_extension(str(extension_path))
    finally:
        connection.enable_load_extension(False)

class DB:

    def __init__(self) -> None:
        
        self.sqliteConnection = sqlite3.connect('card_sources.db', check_same_thread=False)
        self.cursor = self.sqliteConnection.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS card_sources (
                card_id INTEGER PRIMARY KEY,
                source_document TEXT NOT NULL,
                source_section TEXT NOT NULL,
                source_excerpt TEXT NOT NULL,
                source_hash TEXT NOT NULL
            )
            """
        )
        self.sqliteConnection.commit()

class VectorDB:

    def __init__(self) -> None:

        self.sqliteConnection = sqlite3.connect('card_embeddings.db', check_same_thread=False)
        load_vector_extension(self.sqliteConnection)
        self.cursor = self.sqliteConnection.cursor()

        # combined embedding stores both question and answer in the following format:
        # Question: <question>
        # Answer: <answer>
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS card_embeddings (
                rowid INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                combined_embedding BLOB NOT NULL
            )            
            """
        )

        self.cursor.execute(
            """
            SELECT vector_init(
                'card_embeddings',
                'combined_embedding',
                'dimension=1024,type=FLOAT32,distance=COSINE'
            )
            """
        )
