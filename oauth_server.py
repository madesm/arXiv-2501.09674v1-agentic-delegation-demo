"""
oauth_auth_server.py

A toy OAuth 2.0 server using FastAPI, implementing a minimal Authorization Code flow:
- /oauth/authorize to get an authorization code
- /oauth/token to exchange code for an access token

This is for demonstration only. DO NOT use this in production without
adding proper security, PKCE, refresh tokens, real user login, etc.

Run:
  uvicorn oauth_auth_server:app --reload --port 8000
Then test the flow:

  1. GET /oauth/authorize?client_id=demo&redirect_uri=http://localhost:9000/callback
       &scope=calendar.read&response_type=code
  2. "Log in" with the toy user (alice / password123)
  3. Approve the scope.
  4. Auth server redirects to the client's redirect_uri?code=ABC123
  5. The client exchanges the code at /oauth/token to get an access_token.
"""

import time
import secrets
import jwt
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

##############################################################################
# CONFIG
##############################################################################

app = FastAPI(title="Toy OAuth 2.0 Server")
templates = Jinja2Templates(directory="templates")  # You can store an HTML template in "./templates" if desired

JWT_SECRET = "MY_SUPER_SECRET_KEY"   # Hard-coded, do NOT use in production
JWT_ALGORITHM = "HS256"

# In-memory store of codes, tokens, user sessions
AUTHORIZATION_CODES = {}
ACCESS_TOKENS = {}
USER_SESSIONS = {}  # e.g. session_id -> user_id

# Minimal user database
FAKE_USERS_DB = {
    "alice": {"password": "password123", "user_id": "u-alice-001"}
}

# Minimal client registry
FAKE_CLIENTS = {
    "demo": {
        "client_secret": "demo-secret",
        "redirect_uris": {"http://localhost:9000/callback"}
    }
}

##############################################################################
# DATA MODELS
##############################################################################

class TokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str
    code: str
    redirect_uri: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    scope: str
    expires_in: int

##############################################################################
# HTML TEMPLATES (Minimal inline; you may prefer external .html files)
##############################################################################

LOGIN_FORM = """
<html>
  <body>
    <h2>Login</h2>
    <form method="POST">
      Username: <input type="text" name="username" /><br />
      Password: <input type="password" name="password" /><br />
      <button type="submit">Login</button>
    </form>
  </body>
</html>
"""

CONSENT_FORM = """
<html>
  <body>
    <h2>Consent</h2>
    <p>User: {user_id}</p>
    <p>Client: {client_id}</p>
    <p>Scope: {scope}</p>
    <form method="POST">
      <button type="submit" name="approve" value="yes">Approve</button>
      <button type="submit" name="approve" value="no">Deny</button>
    </form>
  </body>
</html>
"""

##############################################################################
# UTILS
##############################################################################

def create_access_token(user_id: str, scope: str, expires_in: int = 3600) -> str:
    """
    Create a signed JWT with the given user_id and scope. Expires in 1 hour by default.
    """
    now = int(time.time())
    payload = {
        "sub": user_id,
        "scope": scope,
        "iat": now,
        "exp": now + expires_in
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

##############################################################################
# ENDPOINTS
##############################################################################

@app.get("/oauth/authorize")
def authorize_get(
    request: Request,
    client_id: str,
    redirect_uri: str,
    scope: str = "calendar.read",
    response_type: str = "code"
):
    """
    Step 1: Authorize endpoint (GET).
    Example:
      GET /oauth/authorize?client_id=demo&redirect_uri=http://localhost:9000/callback&scope=calendar.read&response_type=code
    - Checks if client_id is valid, redirect_uri is registered, etc.
    - If user not logged in, show login form.
    - If user is logged in, prompt for consent.
    """
    # Validate client
    client_info = FAKE_CLIENTS.get(client_id)
    if not client_info:
        raise HTTPException(status_code=400, detail="Unknown client_id")
    if redirect_uri not in client_info["redirect_uris"]:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")

    # Check if user session is established
    session_id = request.cookies.get("session_id")
    user_id = USER_SESSIONS.get(session_id) if session_id else None

    if not user_id:
        # Show login form
        return HTMLResponse(content=LOGIN_FORM)

    # User is logged in, show consent page
    return HTMLResponse(
        content=CONSENT_FORM.format(user_id=user_id, client_id=client_id, scope=scope)
    )


@app.post("/oauth/authorize")
def authorize_post(
    request: Request,
    client_id: str,
    redirect_uri: str,
    scope: str = "calendar.read",
    response_type: str = "code",
    approve: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None)
):
    """
    Step 1 (continued):
    - If user posted login form, validate credentials, set session, then redirect to GET /oauth/authorize again.
    - If user posted consent form, either issue auth code or deny.
    """
    # Validate client again
    client_info = FAKE_CLIENTS.get(client_id)
    if not client_info or redirect_uri not in client_info["redirect_uris"]:
        raise HTTPException(status_code=400, detail="Invalid client or redirect")

    # Check if user is just logging in
    if username and password:
        user = FAKE_USERS_DB.get(username)
        if not user or user["password"] != password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create a session
        session_id = secrets.token_urlsafe(16)
        USER_SESSIONS[session_id] = user["user_id"]

        response = RedirectResponse(
            url=f"/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type={response_type}",
            status_code=302
        )
        # Set session cookie
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response

    # If user posted consent form
    session_id = request.cookies.get("session_id")
    user_id = USER_SESSIONS.get(session_id)
    if not user_id:
        # Not logged in
        return HTMLResponse(content=LOGIN_FORM)

    if approve != "yes":
        # Denied
        return HTMLResponse("<h1>Access Denied</h1>")

    # Approved -> issue authorization code
    code = secrets.token_urlsafe(16)
    AUTHORIZATION_CODES[code] = {
        "user_id": user_id,
        "scope": scope,
        "client_id": client_id,
        "expires_at": time.time() + 300  # code valid for 5 min
    }

    # Redirect back to client with code
    return RedirectResponse(url=f"{redirect_uri}?code={code}", status_code=302)


@app.post("/oauth/token", response_model=TokenResponse)
def token_exchange(data: TokenRequest):
    """
    Step 2: Token exchange endpoint
    POST /oauth/token
    {
      "client_id": "...",
      "client_secret": "...",
      "grant_type": "authorization_code",
      "code": "...",
      "redirect_uri": "... or optional"
    }
    Returns an access_token (JWT).
    """
    # Validate client
    client_info = FAKE_CLIENTS.get(data.client_id)
    if not client_info:
        raise HTTPException(status_code=400, detail="Unknown client_id")
    if client_info["client_secret"] != data.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client secret")
    if data.grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")

    # Retrieve code info
    code_info = AUTHORIZATION_CODES.get(data.code)
    if not code_info:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    if code_info["client_id"] != data.client_id:
        raise HTTPException(status_code=400, detail="Mismatched client_id in code")
    if time.time() > code_info["expires_at"]:
        raise HTTPException(status_code=400, detail="Authorization code expired")

    # If everything is valid, generate access token
    user_id = code_info["user_id"]
    scope = code_info["scope"]

    # Remove code from store (one-time use)
    del AUTHORIZATION_CODES[data.code]

    # Create JWT
    expires_in = 3600
    access_token = create_access_token(user_id, scope, expires_in)
    ACCESS_TOKENS[access_token] = True

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "scope": scope,
        "expires_in": expires_in
    }

##############################################################################
# UTILITY ENDPOINT (OPTIONAL) for token validation
##############################################################################

@app.post("/oauth/validate")
def validate(token: str):
    """
    Optional endpoint to validate or introspect a token (like /introspect).
    GET /oauth/validate?token=...
    """
    if token not in ACCESS_TOKENS:
        raise HTTPException(status_code=401, detail="Unknown or revoked token")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"valid": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

##############################################################################
# RUN
##############################################################################
# In dev:
#   uvicorn oauth_auth_server:app --reload --port 8000
##############################################################################
