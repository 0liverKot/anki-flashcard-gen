from .microsoft.auth import authenticate
from .chat import Chat

def main():
    token = authenticate()
    if token == "":
        exit()
    Chat(token).run()

if __name__ == "__main__":
    main()