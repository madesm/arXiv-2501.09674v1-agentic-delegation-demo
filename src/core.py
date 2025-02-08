import jwt
import datetime
import requests

# Secret key for signing delegation tokens (in production, use a secure key store)
JWT_SECRET = "MY_SECRET_KEY"
JWT_ALGORITHM = "HS256"

class DelegationToken:
    """Handles creation and validation of delegation tokens."""
    
    @staticmethod
    def create_token(user_id, agent_id, scope, expiration_hours=1):
        payload = {
            "iss": "CAP",
            "user_id": user_id,
            "agent_id": agent_id,
            "scope": scope,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_hours),
            "iat": datetime.datetime.utcnow(),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def validate_token(token):
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return decoded
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}

class APIClient:
    """Handles API requests with error handling."""
    
    @staticmethod
    def post(url, data):
        try:
            response = requests.post(url, json=data)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
