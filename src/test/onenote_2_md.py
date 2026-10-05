from pathlib import Path

from src.db.db import DB
from src.managers.source_manager import SourceManager
from src.models.embedding_model import EmbeddingModel

from ..microsoft.auth import authenticate
from ..microsoft import onenote_service
from .. parsers.notebook_content_to_chunks import content_to_chunks


def test():
    token = authenticate()
    if token == "":
        print("Issue authenticating")
        exit()

    notes_metadata = onenote_service.getNoteBookMetadata(token)

    if not notes_metadata:
        print("Test Result: Error getting notebook meta data")
        exit()

    SourceManager(DB(), EmbeddingModel()).add_notebook(token, notes_metadata[0])

if __name__ == "__main__":
    test()