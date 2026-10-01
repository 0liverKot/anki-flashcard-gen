import msal, requests 

CLIENT_ID = "feca8ef7-e597-476c-bede-94418b68ab4b"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Notes.Read", "Notes.Read.All"]

def authenticate() -> bool: 
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    # check for cached token
    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        print("Microsoft Authentication Required")
        result = app.acquire_token_interactive(scopes=SCOPES)

    if "access_token" in result:
        r = requests.get(
            "https://graph.microsoft.com/v1.0/me/onenote/notebooks",
            headers={"Authorization": f"Bearer {result['access_token']}"}
        )
        return True
    else: 
        print(result.get("error"), result.get("error_description"))
        return False