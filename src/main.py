from .microsoft.auth import authenticate
from .chat import Chat

def main():
    if authenticate():
        Chat().run()
    else:
        exit()       

if __name__ == "__main__":
    main()