import uvicorn
import requests
import secrets
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

app = FastAPI()

# Configuration constants
OAUTH_AUTH_SERVER_URL = "http://localhost:8000"
CLIENT_ID = "demo"
CLIENT_SECRET = "demo-secret"
REDIRECT_URI = "http://localhost:9000/callback"
SCOPE = "calendar.read"
PORT = 9000  # The port we're listening on
MCP_SERVER_COMMAND = "python"
MCP_SERVER_ARGS = ["mcp_server.py"]

# We'll store the access token in a simple global for the demo
access_token_global = None

@app.get("/")
def home():
    """
    Just a quick page to greet the user.
    """
    return HTMLResponse("<h2>OAuth Client Home</h2><p>Use /start to initiate OAuth flow.</p>")

@app.get("/start")
def start_oauth_flow():
    """
    1. Generate the authorization URL
    2. Print or auto-open in browser
    3. Wait for user to login and consent
    """
    auth_url = (
        f"{OAUTH_AUTH_SERVER_URL}/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPE}"
        f"&response_type=code"
    )

    # Optionally auto-open the browser
    webbrowser.open(auth_url)

    return {
        "message": "Please open the following URL in your browser to authorize if it doesn't auto-open.",
        "url": auth_url
    }

@app.get("/callback")
def oauth_callback(request: Request, code: str):
    """
    1. Receive the authorization code here.
    2. Exchange it for an access token.
    3. Store the token in a global variable (for demo).
    4. Optionally call the MCP agent.
    """
    global access_token_global

    # Exchange the code for an access token
    token_endpoint = f"{OAUTH_AUTH_SERVER_URL}/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    resp = requests.post(token_endpoint, json=payload)
    if resp.status_code != 200:
        return HTMLResponse(
            f"<h2>Token exchange failed</h2><p>{resp.text}</p>", status_code=400
        )

    token_data = resp.json()
    access_token_global = token_data["access_token"]

    return HTMLResponse(
        f"<h2>Authorization Successful!</h2>"
        f"<p>Access Token: {access_token_global}</p>"
        f"<p>You can now call <code>/call_agent</code> to test the MCP agent with this token.</p>"
    )

@app.get("/call_agent")
async def call_agent():
    """
    Call the MCP-based agent with the retrieved access token.
    This is just an example usage after OAuth.
    """
    global access_token_global
    if not access_token_global:
        return HTMLResponse("<h2>No access token available.</h2><p>Please authorize first at /start.</p>")

    # Run the MCP agent server in a separate process over stdio
    server_params = StdioServerParameters(
        command=MCP_SERVER_COMMAND,
        args=MCP_SERVER_ARGS,
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Example: call a tool that requires the token
            result = await session.call_tool("find_slot", {"access_token": access_token_global})

    return {"agent_result": result}

def main():
    """
    Run the FastAPI server on port 9000. 
    """
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
