try:
    from src.microsoft.auth import authenticate
    from src.chat import Chat
except ModuleNotFoundError:
    from microsoft.auth import authenticate
    from chat import Chat

def main():
    if authenticate():
        Chat().run()
    else:
        exit()       

if __name__ == "__main__":
    main()