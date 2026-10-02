from ..microsoft.auth import authenticate
from ..microsoft import onenote_service

def test():
    token = authenticate()
    notes_metadata = onenote_service.getPages(token)
    print(notes_metadata)

if __name__ == "__main__":
    test()