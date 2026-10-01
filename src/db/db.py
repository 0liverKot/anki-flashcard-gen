import sqlite3

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
                combined_embedding BLOB
            )            
            """
        )

        self.cursor.execute(
            """
            SELECT vector_init(
                "card_embeddings",
                "combined_embdedding",
                "dimension=1024,type=FLOAT,distance=COSINE"
            )
            """
        )

