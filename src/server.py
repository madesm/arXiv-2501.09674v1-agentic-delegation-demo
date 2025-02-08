#!/usr/bin/env python
"""
Minimal single-file example of:
- OAuth 2.0 style delegation with Flask (port 5000)
- MCP server with calendar/time tools (FastMCP)

Usage:
  1) Install dependencies:
       pip install flask mcp
  2) Run this file:
       python mcp_calendar_oauth.py

     This will:
       - Start the Flask OAuth server on port 5000
       - Also run the MCP server in the same process (stdio).

  3) In a browser, simulate an OAuth 2 flow:
       http://localhost:5000/oauth/authorize?client_id=demo&redirect_uri=http://127.0.0.1:5000/callback&scope=calendar.read&response_type=code

     You'll be prompted for "username" (e.g. alice) and "password" (password123) 
     then asked for "consent" to grant "calendar.read" scope to the client.

     The server will redirect to:
       http://example.org/callback?code=XYZ

  4) Exchange authorization code for access_token:
     POST /oauth/token
       Content-Type: application/json
       {
         "client_id": "demo",
         "client_secret": "demo-secret",
         "grant_type": "authorization_code",
         "code": "<CODE_FROM_STEP_3>"
       }

     Response:
       {
         "access_token": "...",
         "token_type": "Bearer",
         "scope": "calendar.read",
         "expires_in": 3600
       }

  5) Use the access token to call MCP tools such as `find_slot`:
     - In the MCP Inspector or Claude Desktop, call:
         Tool: "find_slot"
         Arguments: {"access_token":"<your_token>", "duration_minutes":45}

     Or `get_current_time` / `convert_time` similarly.

NOTE: This is purely for demonstration. Real OAuth flows are more involved (PKCE, 
secure client secrets, user management, etc.).
"""

import os
import threading
import secrets
import time
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Optional, Dict

from flask import Flask, request, redirect, session, url_for, jsonify
from flask import render_template_string

import jwt

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

##############################################################################
# CONFIG
##############################################################################

app = Flask(__name__)
app.secret_key = "NOT_A_GOOD_SECRET_IN_PRODUCTION"

JWT_SECRET = "MY_SUPER_SECRET_KEY"   # For signing access tokens (toy example)
JWT_ALGORITHM = "HS256"

# Minimal "database"
FAKE_USERS = {
    "alice": {
        "password": "password123",
        "user_id": "u-alice-001"
    }
}

# Minimal OAuth client registry
FAKE_CLIENTS = {
    "demo": {
        "client_secret": "demo-secret",
        "redirect_uris": {"http://example.org/callback"},  # permitted redirect
    }
}

# Temp storage for OAuth codes and tokens
AUTHORIZATION_CODES: Dict[str, dict[str, Any]] = {}
ACCESS_TOKENS: Dict[str, dict[str, Any]] = {}

##############################################################################
# MCP SERVER: CALENDAR/TIME DEMO
##############################################################################

mcp = FastMCP(
    "Calendar OAuth Demo",
    description="MCP server with OAuth-based delegation for a toy calendar/time system."
)

MOCKED_CALENDAR = [
    {"start": "2025-03-01T09:00:00", "end": "2025-03-01T10:00:00"},
    {"start": "2025-03-01T11:00:00", "end": "2025-03-01T11:30:00"},
]


def validate_access_token(access_token: str, required_scope: str) -> dict:
    """
    Decode and validate an OAuth2 access_token with the required scope.
    Raises ToolError if invalid or insufficient scope.
    """
    # Check if we have it in our in-memory "DB"
    token_info = ACCESS_TOKENS.get(access_token)
    if not token_info:
        raise ToolError("Invalid or unknown access_token")

    # Check expiry
    if time.time() > token_info["expires_at"]:
        raise ToolError("Access token expired")

    # Check scope
    scope = token_info["scope"]
    if required_scope not in scope.split():
        raise ToolError(f"Insufficient scope. Needed: {required_scope}, got: {scope}")

    return token_info


@mcp.tool(
    name="find_slot",
    description="Find the next free calendar slot (in minutes). Requires OAuth2 token with scope=calendar.read."
)
def find_slot_tool(access_token: str, duration_minutes: int = 30) -> str:
    """
    Example usage in MCP:
      call_tool("find_slot", {
        "access_token":"<token>",
        "duration_minutes":45
      })
    """
    validate_access_token(access_token, "calendar.read")

    # Very naive logic: next free time after the last event in MOCKED_CALENDAR
    events = []
    for e in MOCKED_CALENDAR:
        start_dt = datetime.fromisoformat(e["start"])
        end_dt = datetime.fromisoformat(e["end"])
        events.append((start_dt, end_dt))
    events.sort(key=lambda x: x[0])

    last_end = events[-1][1]
    new_slot_start = last_end + timedelta(minutes=15)
    new_slot_end = new_slot_start + timedelta(minutes=duration_minutes)

    result = {
        "start": new_slot_start.isoformat(timespec="minutes"),
        "end": new_slot_end.isoformat(timespec="minutes"),
    }
    return json.dumps(result, indent=2)


@mcp.tool(
    name="get_current_time",
    description="Get the current time in a given timezone. Requires OAuth2 token with scope=calendar.read."
)
def get_current_time_tool(access_token: str, timezone: str = "UTC") -> str:
    validate_access_token(access_token, "calendar.read")

    zone = _get_zoneinfo(timezone)
    now = datetime.now(zone)
    result = {
        "timezone": timezone,
        "datetime": now.isoformat(timespec="seconds"),
        "is_dst": bool(now.dst()),
    }
    return json.dumps(result, indent=2)


@mcp.tool(
    name="convert_time",
    description="Convert a time from one timezone to another. Requires OAuth2 token with scope=calendar.read."
)
def convert_time_tool(access_token: str, source_timezone: str, time_str: str, target_timezone: str) -> str:
    validate_access_token(access_token, "calendar.read")

    source_zone = _get_zoneinfo(source_timezone)
    target_zone = _get_zoneinfo(target_timezone)

    try:
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        raise ToolError("Invalid time format. Expect HH:MM (24-hour)")

    now = datetime.now(source_zone)
    source_dt = datetime(
        now.year, now.month, now.day,
        parsed_time.hour, parsed_time.minute,
        tzinfo=source_zone
    )
    target_dt = source_dt.astimezone(target_zone)

    source_offset = source_dt.utcoffset() or timedelta()
    target_offset = target_dt.utcoffset() or timedelta()
    hour_diff = (target_offset - source_offset).total_seconds() / 3600

    if hour_diff.is_integer():
        diff_str = f"{hour_diff:+.1f}h"
    else:
        diff_str = f"{hour_diff:+.2f}".rstrip("0").rstrip(".") + "h"

    result = {
        "source": {
            "timezone": source_timezone,
            "datetime": source_dt.isoformat(timespec="seconds"),
            "is_dst": bool(source_dt.dst()),
        },
        "target": {
            "timezone": target_timezone,
            "datetime": target_dt.isoformat(timespec="seconds"),
            "is_dst": bool(target_dt.dst()),
        },
        "time_difference": diff_str,
    }
    return json.dumps(result, indent=2)


def _get_zoneinfo(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception as e:
        raise ToolError(f"Invalid timezone '{tz_name}': {e}")


##############################################################################
# OAUTH 2.0 - MINIMAL ENDPOINTS
##############################################################################

@app.route("/")
def index():
    return "<h1>MCP OAuth Demo</h1><p>See /oauth/authorize, /oauth/token, etc.</p>"

@app.route("/oauth/authorize")
def oauth_authorize():
    """
    Step 1 (typical OAuth):
      GET /oauth/authorize?client_id=demo&redirect_uri=...&scope=calendar.read&response_type=code
    We ask the user to log in, then prompt for consent. If granted, we generate an auth code.
    """
    client_id = request.args.get("client_id", "")
    redirect_uri = request.args.get("redirect_uri", "")
    scope = request.args.get("scope", "")
    response_type = request.args.get("response_type", "")

    # Basic checks
    if client_id not in FAKE_CLIENTS:
        return "Unknown client_id", 400
    if redirect_uri not in FAKE_CLIENTS[client_id]["redirect_uris"]:
        return "Invalid redirect_uri", 400
    if response_type != "code":
        return "Invalid response_type", 400

    # Save these in session so we can come back after login
    session["client_id"] = client_id
    session["redirect_uri"] = redirect_uri
    session["scope"] = scope

    # If user not logged in, go to "login page"
    if "logged_in_user" not in session:
        return redirect(url_for("login_page"))

    # If user is logged in, ask for consent
    user_id = session["logged_in_user"]
    return render_template_string("""
    <h1>Consent</h1>
    <p>User {{user_id}} is logged in.</p>
    <p>Client "{{client_id}}" requests scope "{{scope}}". Grant access?</p>
    <form method="POST" action="{{url_for('confirm_consent')}}">
      <button type="submit" name="approve" value="yes">Approve</button>
      <button type="submit" name="approve" value="no">Deny</button>
    </form>
    """, user_id=user_id, client_id=client_id, scope=scope)

@app.route("/login_page", methods=["GET", "POST"])
def login_page():
    """
    A mock login page. Typically you'd have a real form with user & pass.
    """
    if request.method == "GET":
        return """
        <h1>Login</h1>
        <form method="POST">
          <label>Username: <input name="username"></label><br>
          <label>Password: <input name="password" type="password"></label><br>
          <button type="submit">Login</button>
        </form>
        """
    else:
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # Validate
        user_record = FAKE_USERS.get(username)
        if not user_record or user_record["password"] != password:
            return "Invalid credentials", 401
        session["logged_in_user"] = user_record["user_id"]
        # redirect back to /oauth/authorize to continue
        return redirect(url_for("oauth_authorize"))

@app.route("/confirm_consent", methods=["POST"])
def confirm_consent():
    """
    After user sees the consent page, either Approve or Deny.
    If approved, we generate an authorization code.
    """
    if request.form.get("approve") != "yes":
        return "User denied consent", 403

    user_id = session["logged_in_user"]
    client_id = session["client_id"]
    redirect_uri = session["redirect_uri"]
    scope = session["scope"]

    # Generate a random auth code
    auth_code = secrets.token_urlsafe(32)
    AUTHORIZATION_CODES[auth_code] = {
        "user_id": user_id,
        "client_id": client_id,
        "scope": scope,
        "expires_at": time.time() + 300,  # 5min
    }

    # Redirect back to client
    return redirect(f"{redirect_uri}?code={auth_code}")

@app.route("/oauth/token", methods=["POST"])
def oauth_token():
    """
    Step 2 (typical OAuth):
      POST /oauth/token
      { client_id, client_secret, grant_type=authorization_code, code=..., ... }

    Returns { access_token, token_type, scope, expires_in }
    """
    data = request.json or {}
    client_id = data.get("client_id", "")
    client_secret = data.get("client_secret", "")
    grant_type = data.get("grant_type", "")
    code = data.get("code", "")

    # Validate
    if client_id not in FAKE_CLIENTS:
        return jsonify({"error":"invalid_client_id"}), 400
    if FAKE_CLIENTS[client_id]["client_secret"] != client_secret:
        return jsonify({"error":"invalid_client_secret"}), 400
    if grant_type != "authorization_code":
        return jsonify({"error":"invalid_grant_type"}), 400

    code_info = AUTHORIZATION_CODES.get(code)
    if not code_info:
        return jsonify({"error":"invalid_code"}), 400
    if code_info["client_id"] != client_id:
        return jsonify({"error":"mismatched_client"}), 400
    if time.time() > code_info["expires_at"]:
        return jsonify({"error":"code_expired"}), 400

    # All good, generate access_token
    user_id = code_info["user_id"]
    scope = code_info["scope"]
    access_token = secrets.token_urlsafe(32)
    expires_in = 3600
    ACCESS_TOKENS[access_token] = {
        "user_id": user_id,
        "scope": scope,
        "expires_at": time.time() + expires_in
    }

    # Remove the auth code from store (typical once-used)
    del AUTHORIZATION_CODES[code]

    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "scope": scope,
        "expires_in": expires_in
    })

##############################################################################
# COMBINED APP + MCP RUN
##############################################################################

def run_flask():
    # By default, Flask uses port 5000
    print("Starting Flask OAuth server on http://127.0.0.1:5000")
    app.run(debug=False, port=5000)

if __name__ == "__main__":
    # 1) Start the Flask OAuth server in a separate thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # 2) Run the MCP server (which listens via stdio or SSE by default)
    print("Starting MCP server. Use `mcp dev mcp_calendar_oauth.py` or connect with Claude Desktop.")
    mcp.run()
