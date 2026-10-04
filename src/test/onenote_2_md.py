from ..microsoft.auth import authenticate
from ..microsoft import onenote_service

def test():
    token = authenticate()
    if token == "":
        print("Issue authenticating")
        exit()

    notes_metadata = onenote_service.getNoteBookMetadata(token)

    if not notes_metadata:
        print("Test Result: Error getting notebook meta data")
        exit()

    notebook_structure = onenote_service.getAllNoteBookStructure(
        token,
        notes_metadata[0],
    )
    print(notebook_structure)

if __name__ == "__main__":
    test()