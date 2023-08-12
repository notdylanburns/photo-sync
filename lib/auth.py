from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow


g_session: AuthorizedSession = None


def auth() -> AuthorizedSession:
    global g_session

    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/photoslibrary.readonly"]
    )

    flow.run_local_server()
    g_session = flow.authorized_session()


def get_session(refresh_auth: bool = False):
    if g_session is None or refresh_auth:
        auth()

    return g_session