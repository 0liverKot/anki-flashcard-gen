import sqlite3

class DB:

    def __init__(self) -> None:
        
        self.sqliteConnection = sqlite3.connect('card_sources.db')
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
