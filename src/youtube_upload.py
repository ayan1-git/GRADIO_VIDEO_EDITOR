import json
import os
import urllib.parse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

try:
    import google.auth.compute_engine._metadata as _gce_metadata

    _original_get_universe_domain = _gce_metadata.get_universe_domain

    def _patched_get_universe_domain(request):
        try:
            return _original_get_universe_domain(request)
        except Exception:
            return "googleapis.com"

    _gce_metadata.get_universe_domain = _patched_get_universe_domain
except Exception:
    pass


def _load_client_config(client_secrets_file):
    try:
        with open(client_secrets_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Client secrets file is invalid JSON: {client_secrets_file}. "
            f"Error: {e}. Make sure you uploaded the full Google OAuth client JSON, "
            f"not a placeholder or empty file."
        ) from e
    if "installed" in data:
        data = data["installed"]
    return data


def _extract_redirect_uri(client_config):
    redirect_uris = client_config.get("redirect_uris", [])
    if redirect_uris:
        return redirect_uris[0]
    return "http://localhost"


def _extract_code(raw_input):
    raw_input = raw_input.strip()
    if "code=" in raw_input:
        parsed = urllib.parse.urlparse(raw_input)
        params = urllib.parse.parse_qs(parsed.query)
        codes = params.get("code", [])
        if codes:
            return codes[0]
    if len(raw_input) > 20 and " " not in raw_input:
        return raw_input
    return raw_input


def get_authenticated_service(client_secrets_file, token_file="token.json"):
    credentials = None

    if os.path.exists(token_file):
        credentials = Credentials.from_authorized_user_file(token_file)
        if credentials is not None:
            credentials = credentials.with_universe_domain("googleapis.com")

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError:
                credentials = None

        if not credentials:
            client_config = _load_client_config(client_secrets_file)
            redirect_uri = _extract_redirect_uri(client_config)

            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file,
                ["https://www.googleapis.com/auth/youtube.upload"]
            )

            flow.redirect_uri = redirect_uri
            auth_url, _ = flow.authorization_url(
                prompt="consent",
                access_type="offline",
            )
            print("Open this URL in your browser to authorize the app:")
            print(auth_url)
            print("\nAfter approving, Google will redirect to a localhost URL.")
            print("If that page shows an error, copy the FULL redirected URL from your")
            print("browser's address bar and paste it below, or paste just the code.\n")
            raw = input("Paste the authorization URL or code here: ").strip()
            code = _extract_code(raw)
            token = flow.fetch_token(code=code)

            if hasattr(token, "to_json"):
                credentials = token
                with open(token_file, "w") as f:
                    f.write(credentials.to_json())
            else:
                token_dict = dict(token)
                with open(token_file, "w") as f:
                    json.dump(token_dict, f)
                credentials = Credentials(
                    token=token_dict["access_token"],
                    refresh_token=token_dict.get("refresh_token"),
                    token_uri=client_config["token_uri"],
                    client_id=client_config["client_id"],
                    client_secret=client_config["client_secret"],
                    scopes=["https://www.googleapis.com/auth/youtube.upload"],
                )

    if credentials is not None:
        if hasattr(credentials, "with_universe_domain"):
            credentials = credentials.with_universe_domain("googleapis.com")
        else:
            object.__setattr__(credentials, "universe_domain", "googleapis.com")

    return build("youtube", "v3", credentials=credentials)


def upload_video(
    youtube,
    video_path,
    title,
    description="",
    tags=None,
    category_id="22",
    privacy_status="private",
    progress_callback=None,
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/*",
        resumable=True,
        chunksize=2 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status and progress_callback:
            progress_callback(int(status.progress() * 100))

    return response


def upload_to_youtube(
    video_path,
    title,
    description="",
    tags=None,
    category_id="22",
    privacy_status="private",
    client_secrets_file="client_secret.json",
    token_file="token.json",
    progress_callback=None,
):
    youtube = get_authenticated_service(client_secrets_file, token_file)
    response = upload_video(
        youtube,
        video_path,
        title,
        description,
        tags,
        category_id,
        privacy_status,
        progress_callback,
    )
    return response.get("id")
