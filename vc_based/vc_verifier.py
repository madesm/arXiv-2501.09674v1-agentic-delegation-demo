"""
vc_verifier.py

Contains helper functions to verify a Verifiable Credential (VC).
"""

import jwt
from fastapi import HTTPException

# Must match the issuer's secret
ISSUER_SECRET = "super-secret-key"

def verify_vc(vc_jwt: str) -> str:
    """
    Verifies and decodes the given VC (JWT).
    Returns the holder's DID if the VC is valid and grants the required permission.
    Raises HTTPException if verification fails.
    """
    try:
        payload = jwt.decode(vc_jwt, ISSUER_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="VC expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid VC")

    permissions = payload.get("credentialSubject", {}).get("permissions", [])
    if "calendar.view" not in permissions:
        raise HTTPException(status_code=403, detail="VC lacks required permission: calendar.view")
    return payload.get("credentialSubject", {}).get("id", "unknown")
