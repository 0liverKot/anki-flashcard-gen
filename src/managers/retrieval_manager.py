import sqlite3
from typing import List, Tuple

from src.db.db import DB
from src.models.embedding_model import EmbeddingModel
from src.schemas import Chunk_Schema

K = 100
MAX_DISTANCE = 0.4

class RetrievalManager:
    def __init__(self, db: DB, model: EmbeddingModel):
        self.db = db
        self.model = model

    # returns distances alongisde chunks if test is true
    def get_chunks(self, prompt: str, test: bool = False) -> List[Chunk_Schema] | List[Tuple[Chunk_Schema, float]]:
        
        embedded_prompt = self.model.embed_prompt(prompt)
        query_vector = sqlite3.Binary(
            embedded_prompt.astype("float32", copy=False).tobytes()
        )

        rows = self.db.cursor.execute(
            """
            SELECT
                source_chunks.chunk_id,
                source_chunks.source_path,
                source_chunks.content,
                source_chunks.embedded_content,
                matches.distance
            FROM vector_full_scan(
                'source_chunks',
                'embedded_content',
                vector_as_f32(?),
                ?
            ) AS matches
            JOIN source_chunks
                ON source_chunks.chunk_id = matches.rowid
            WHERE matches.distance <= ?
            ORDER BY matches.distance ASC
            """,
            (query_vector, K, MAX_DISTANCE),
        ).fetchall()

        results = [
            (
                Chunk_Schema(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    content=content,
                    embedded_content=embedded_content,
                ),
                distance,
            )
            for chunk_id, source_path, content, embedded_content, distance in rows
        ]

        if test:
            return results

        return [chunk for chunk, _ in results]
