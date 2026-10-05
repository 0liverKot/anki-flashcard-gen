from typing import Dict, List
import hashlib
import json
import sqlite3

from src.microsoft import onenote_service
from src.models.embedding_model import EmbeddingModel

from ..db.db import DB
from .. parsers.notebook_content_to_chunks import content_to_chunks
from ..type_aliases import SourceFile
from ..schemas import Card, Card_Source_Schema, Chunk_Schema, NotebookData

class SourceManager:
    def __init__(self, db: DB, embedding_model: EmbeddingModel) -> None:
        self.db = db
        self.model = embedding_model

    def get_current_source_dict(self) -> SourceFile:
        rows = self.db.cursor.execute(
            "SELECT source_path, content FROM source_chunks"
        ).fetchall()
        return [
            {"source": source_path, "content": content}
            for source_path, content in rows
        ]


    def get_current_source_json(self) -> str:
        return json.dumps(self.get_current_source_dict())


    def is_source_valid(self, source: str, debug=False) -> bool:
        exists = self.db.cursor.execute(
            """
            SELECT 1
            FROM source_chunks
            WHERE source_path = ?
            LIMIT 1
            """,
            (source,),
        ).fetchone()
        if exists:
            return True

        if debug:
            for source_path in self.get_current_source_dict():
                print(source_path.get("source"))
                print(source)
                print("\n")
        return False
    

    def hash_excerpt(self, excerpt: str | None) -> str:
        if not excerpt:
            return ""
        
        return hashlib.sha256(
            excerpt.encode("utf-8")
        ).hexdigest()


    def add_card_sources(self, cards: List[Card], card_ids: List[int]):

        def create_card_source(card: Card, id: int) -> Card_Source_Schema | None:
            source = self.db.cursor.execute(
                """
                SELECT content
                FROM source_chunks
                WHERE source_path = ?
                LIMIT 1
                """,
                (card.source,),
            ).fetchone()
            if source is None:
                return None

            source_excerpt = source[0]

            return Card_Source_Schema(
                card_id=id,
                source_path=card.source,
                source_excerpt=source_excerpt,
                source_hash=self.hash_excerpt(source_excerpt)
            )
        rows = []
        for card, card_id in zip(cards, card_ids):
            card_source = create_card_source(card, card_id)

            if card_source is None:
                continue
                
            rows.append((
                card_source.card_id,
                card_source.source_path,
                card_source.source_excerpt,
                card_source.source_hash
            ))


        self.db.cursor.executemany(
            """
            INSERT INTO card_sources (
            card_id,
            source_path,
            source_excerpt,
            source_hash
            ) 
            VALUES (?, ?, ?, ?)""",
            rows)
        self.db.sqliteConnection.commit()

    
    def synchronise(self) -> List[int]:
        unsynced = []
        for card_id, source_path, source_hash in (
            self.db.cursor.execute(
                """
                SELECT card_id, source_path, source_hash
                FROM card_sources
                """
            ).fetchall()
        ):
            source = self.db.cursor.execute(
                """
                SELECT content
                FROM source_chunks
                WHERE source_path = ?
                LIMIT 1
                """,
                (source_path,),
            ).fetchone()
            if source is None or self.hash_excerpt(source[0]) != source_hash:
                unsynced.append(card_id)

        return unsynced
        

    def get_card_sources(self):
        card_sources = self.db.cursor.execute("""
                SELECT card_id, source_path, source_hash
            FROM card_sources        
            """).fetchall()
        return card_sources
    

    def get_source_paths(self, ids: List[int]) -> Dict[int, str]:
        placeholders = ",".join("?" for _ in ids)

        rows = self.db.cursor.execute(f"""
            SELECT card_id, source_path
            FROM card_sources
            WHERE card_id IN ({placeholders})
            """,
            ids).fetchall()
        
        return {card_id: source_path for card_id, source_path in rows}
    

    def get_sources(self, source_paths: Dict[int, str]) -> Dict[int, str]:
        if not source_paths:
            return {}

        rows = self.db.cursor.execute(
            f"""
            SELECT source_path, content
            FROM source_chunks
            WHERE source_path IN ({
                ",".join("?" for _ in source_paths)
            })
            """,
            list(source_paths.values()),
        ).fetchall()
        content_by_path = dict(rows)
        return {
            card_id: content_by_path[path]
            for card_id, path in source_paths.items()
            if path in content_by_path
        }
    

    def update_sources(self, ids: List[int], cards: List[Card]) -> None:
        for id, card in zip(ids, cards):
            source = self.db.cursor.execute(
                """
                SELECT content
                FROM source_chunks
                WHERE source_path = ?
                LIMIT 1
                """,
                (card.source,),
            ).fetchone()
            if source is None:
                raise ValueError(f"Source chunk not found: {card.source}")

            source_excerpt = source[0]
            hashed_source_exerpt = self.hash_excerpt(source_excerpt)

            self.db.cursor.execute(
                """
                UPDATE card_sources
                SET source_excerpt = ?, source_hash = ? 
                WHERE card_id = ?                
                """,
                (source_excerpt, hashed_source_exerpt, id)
            )
            self.db.sqliteConnection.commit()


    def add_notebook(self, token: str, notebook: NotebookData):
        notebook_structure = onenote_service.getAllNoteBookStructure(token, notebook)
        notebook_page_content = onenote_service.get_notebook_page_content(
            token,
            notebook_structure,
        )
        chunks = content_to_chunks(notebook_page_content)
        stored_content = dict(
            self.db.cursor.execute(
                "SELECT source_path, content FROM source_chunks"
            ).fetchall()
        )
        current_paths = {chunk.source_path for chunk in chunks}
        notebook_prefix = f"{notebook.displayName} > "
        stale_paths = [
            path
            for path in stored_content
            if path.startswith(notebook_prefix) and path not in current_paths
        ]
        changed_chunks = [
            chunk
            for chunk in chunks
            if stored_content.get(chunk.source_path) != chunk.content
        ]
        embedded_chunks = self.model.embed_content(changed_chunks)

        self.db.cursor.execute(
            """
            INSERT OR REPLACE INTO notebooks (
                notebook_id,
                structure,
                last_modified
            )
            VALUES (?, ?, ?)
            """,
            (
                notebook.id,
                notebook_structure.model_dump_json(),
                str(notebook.lastModifiedDateTime),
            ),
        )
        self.db.sqliteConnection.commit()
        self.db.cursor.executemany(
            "DELETE FROM source_chunks WHERE source_path = ?",
            [(path,) for path in stale_paths],
        )
        self.add_chunks(embedded_chunks)


    def add_chunks(self, chunks: List[Chunk_Schema]) -> None:
        existing_paths = {
            row[0]
            for row in self.db.cursor.execute(
                "SELECT source_path FROM source_chunks"
            ).fetchall()
        }

        for chunk in chunks:
            values = (chunk.content, sqlite3.Binary(chunk.embedded_content))
            
            # sources for a chunk are unique
            # check if new chunks already exist, if so update
            if chunk.source_path in existing_paths:
                self.db.cursor.execute(
                    """
                    UPDATE source_chunks
                    SET content = ?, embedded_content = vector_as_f32(?)
                    WHERE source_path = ?
                    """,
                    (*values, chunk.source_path),
                )
            else:
                self.db.cursor.execute(
                    """
                    INSERT INTO source_chunks (
                        source_path,
                        content,
                        embedded_content
                    )
                    VALUES (?, ?, vector_as_f32(?))
                    """,
                    (chunk.source_path, *values),
                )
        self.db.sqliteConnection.commit()