from typing import List, Tuple, cast

from src.db.db import DB
from src.managers.retrieval_manager import RetrievalManager
from src.models.embedding_model import EmbeddingModel
from src.schemas import Chunk_Schema

from ..microsoft.auth import authenticate


def test():
    
    prompt = input("Enter prompt: ").strip()
    chunks = cast(List[Tuple[Chunk_Schema, float]], RetrievalManager(DB(), EmbeddingModel()).get_chunks(prompt, test=True))

    counter = 0
    for chunk, distance in chunks:
        counter += 1
        print(f"Chunk: {counter} with Distance: {distance}\n")
        print(chunk.content)
        print("____________________________")

if __name__ == "__main__":
    test()