from ..microsoft.auth import authenticate
from ..microsoft import onenote_service

def test():
    token = authenticate()
    notes_metadata = onenote_service.getNoteBookMetadata(token)

    if not notes_metadata:
        print("Test Result: Error getting notebook meta data")

    sections = onenote_service.getAllNoteBookSections(token, notes_metadata[0])
    print(sections)

if __name__ == "__main__":
    test()