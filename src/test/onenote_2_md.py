from pathlib import Path

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

    notebook_structure = onenote_service.getAllNoteBookStructure(token, notes_metadata[0])

    page_content = onenote_service.get_notebook_page_content(token, notebook_structure)
    
    page = page_content.values()
    output_path = Path(__file__).with_name("output.md")
    output_path.write_text("\n\n".join(page), encoding="utf-8")
    print(page)

    chunks = content_to_chunks(page_content)
    
    counter = 0
    for chunk in chunks:
        counter += 1
        print(f"Chunk: {counter}\n")
        print(f"Source Path: {chunk.source_path}")
        print(f"Content: {chunk.content}\n")

if __name__ == "__main__":
    test()