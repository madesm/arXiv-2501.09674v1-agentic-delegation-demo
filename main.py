import json
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import jwt

##############################################################################
# CONFIGURATION
##############################################################################

# A hard-coded secret for signing JWTs (NOT for production!)
JWT_SECRET = "MY_SUPER_SECRET_KEY"
JWT_ALGORITHM = "HS256"

# Create a single Flask app to mock all components
app = Flask(__name__)

# In-memory "database" to simulate users, tokens, etc.
FAKE_DB = {
    "users": {
        "alice": {
            "password": "password123",
            "user_id": "u-alice-001",
        },
    },
    "delegations": [],  # store delegated tokens for reference
    "service_data": {
        # Example data that the service might hold about a user
        "u-alice-001": {
            "account_info": "Alice's Account: [Balance: $1234.56]",
            "profile": {"name": "Alice", "email": "alice@example.com"},
        }
    },
}


##############################################################################
# 1. CAP (Consumer Agent Provider) ENDPOINTS
##############################################################################

@app.route("/cap/login", methods=["POST"])
def cap_login():
    """
    Simulate user login to the CAP.
    Expects JSON: {"username": "...", "password": "..."}
    Returns a simple session token (NOT a delegation token) if correct.
    """
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user_record = FAKE_DB["users"].get(username)
    if not user_record or user_record["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401
    
    # For the prototype, let's just return the user_id in a "session token" 
    # with a short expiration.
    payload = {
        "type": "session",
        "user_id": user_record["user_id"],
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return jsonify({"session_token": token})


@app.route("/cap/delegate", methods=["POST"])
def cap_delegate():
    """
    Issues a delegation token to the Delegation Agent on behalf of the user.
    Expects JSON with "session_token" from /cap/login, plus a requested scope.
      e.g. {"session_token": "...", "agent_id": "agent-123", "scope": "READ_ACCOUNT"}
    Returns a signed delegation token.
    """
    data = request.json
    session_token = data.get("session_token")
    agent_id = data.get("agent_id")
    scope = data.get("scope", "READ_ACCOUNT")

    # Validate session token
    try:
        session_payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if session_payload.get("type") != "session":
            return jsonify({"error": "Invalid session token type"}), 400
        user_id = session_payload["user_id"]
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid session token"}), 400

    # Create a delegation token that grants 'scope' to the agent
    delegation_payload = {
        "type": "delegation",
        "iss": "CAP-Prototype",
        "user_id": user_id,
        "agent_id": agent_id,
        "scope": scope,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour from now
    }
    delegation_token = jwt.encode(delegation_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # For reference, store in our in-memory DB
    FAKE_DB["delegations"].append(delegation_token)

    return jsonify({
        "delegation_token": delegation_token
    })


##############################################################################
# 2. DELEGATION AGENT (AI Agent) ENDPOINTS
##############################################################################

@app.route("/agent/command", methods=["POST"])
def agent_command():
    """
    Simulate the Delegation Agent receiving a natural-language command.
    In a real system, you'd parse this with NLP; here, we do a simple example.

    Expects JSON like:
    {
      "delegation_token": "...",
      "command": "Show my account info"
    }
    We then interpret the command, decide which API endpoint to hit on the Service,
    and pass along the delegation token for authentication.
    """
    data = request.json
    delegation_token = data.get("delegation_token")
    command = data.get("command", "").lower()

    # A trivial "intent parsing" (string matching for demonstration)
    if "account info" in command:
        service_endpoint = "/service/account"
    elif "profile" in command:
        service_endpoint = "/service/profile"
    else:
        return jsonify({"error": "Unknown command"}), 400

    # In a real system, we'd make an HTTP request to a separate service.
    # For this prototype, we’ll just forward internally using Flask's test client
    with app.test_client() as client:
        response = client.post(service_endpoint, json={
            "delegation_token": delegation_token
        })
        return (response.data, response.status_code, response.headers.items())


##############################################################################
# 3. SERVICE (CX Portal) ENDPOINTS
##############################################################################

@app.route("/service/account", methods=["POST"])
def service_account():
    """
    Checks delegation token for scope; if valid, returns the user's account info.
    Expects JSON with delegation_token.
    """
    data = request.json
    delegation_token = data.get("delegation_token")

    # Validate delegation token
    try:
        delegation_payload = jwt.decode(delegation_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if delegation_payload.get("type") != "delegation":
            return jsonify({"error": "Invalid delegation token type"}), 400
        if delegation_payload.get("scope") not in ["READ_ACCOUNT", "FULL_ACCESS"]:
            return jsonify({"error": "Insufficient scope"}), 403
        
        user_id = delegation_payload["user_id"]
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Delegation token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid delegation token"}), 400

    # Return the account info from our "database"
    account_info = FAKE_DB["service_data"].get(user_id, {}).get("account_info", "No data found.")
    return jsonify({"account_info": account_info})


@app.route("/service/profile", methods=["POST"])
def service_profile():
    """
    Checks delegation token for scope; if valid, returns the user's profile.
    Expects JSON with delegation_token.
    """
    data = request.json
    delegation_token = data.get("delegation_token")

    # Validate delegation token
    try:
        delegation_payload = jwt.decode(delegation_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if delegation_payload.get("type") != "delegation":
            return jsonify({"error": "Invalid delegation token type"}), 400
        if delegation_payload.get("scope") not in ["READ_PROFILE", "FULL_ACCESS"]:
            return jsonify({"error": "Insufficient scope"}), 403
        
        user_id = delegation_payload["user_id"]
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Delegation token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid delegation token"}), 400

    # Return the profile from our "database"
    profile_info = FAKE_DB["service_data"].get(user_id, {}).get("profile", {})
    return jsonify({"profile": profile_info})


##############################################################################
# MAIN: Run the Flask app (for demonstration)
##############################################################################

if __name__ == "__main__":
    app.run(debug=True, port=5000)
