import os
import json
import psycopg2
from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from config import DB_CONFIG, GOOGLE_OAUTH_CLIENT_ID

app = Flask(__name__)

CREDENTIALS_FILE = "credentials/client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

@app.route("/")
def index():
    # If it has code+state, forward to actual token handler
    if 'code' in request.args and 'state' in request.args:
        return redirect(f"/oauth2callback?code={request.args['code']}&state={request.args['state']}")
    return "✅ OAuth callback server is running."

@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    state = request.args.get("state")  # Discord user ID

    if not code or not state:
        return "Missing code or state", 400

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8080/oauth2callback"  # ← THIS MUST MATCH EXACTLY
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS calendar_tokens (
                    user_id TEXT PRIMARY KEY,
                    token TEXT,
                    refresh_token TEXT,
                    token_uri TEXT,
                    client_id TEXT,
                    client_secret TEXT,
                    scopes TEXT
                )
            """)
            cur.execute("""
                INSERT INTO calendar_tokens (user_id, token, refresh_token, token_uri, client_id, client_secret, scopes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    token = EXCLUDED.token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_uri = EXCLUDED.token_uri,
                    client_id = EXCLUDED.client_id,
                    client_secret = EXCLUDED.client_secret,
                    scopes = EXCLUDED.scopes
            """, (
                state,
                credentials.token,
                credentials.refresh_token,
                credentials.token_uri,
                credentials.client_id,
                credentials.client_secret,
                " ".join(credentials.scopes)
            ))
            conn.commit()

    return "✅ Google Calendar successfully linked. You can return to Discord."

if __name__ == "__main__":
    app.run(port=8080, debug=True)
