from typing import List, Tuple, cast

from src.db.db import DB
from src.managers.retrieval_manager import RetrievalManager
from src.models.embedding_model import EmbeddingModel
from src.models.flashcard_model import FlashcardModel
from src.schemas import Chunk_Schema

from ..microsoft.auth import authenticate


def test():
    
    prompt = input("Enter prompt: ").strip()
    
    db = DB()
    embedding_model = EmbeddingModel()
    retrieval_manager = RetrievalManager(db, embedding_model)
    chunks = cast(List[Chunk_Schema], retrieval_manager.get_chunks(prompt))

    model = FlashcardModel(db, embedding_model)
    context = model.build_context(chunks)
    print(context)
    
if __name__ == "__main__":
    test()