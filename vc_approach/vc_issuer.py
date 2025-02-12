#!/usr/bin/env python3
"""
vc_issuer.py

Issues a Verifiable Credential (VC) granting delegation.
"""

import jwt
import json
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Hardcoded private key (Replace this in production)
ISSUER_SECRET = "super-secret-key"

# Credential Schema
CREDENTIAL_TEMPLATE = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1"
    ],
    "type": ["VerifiableCredential", "DelegationCredential"],
    "issuer": "did:example:issuer",
    "credentialSubject": {
        "id": None,  # Holder DID
        "permissions": []  # Actions granted
    },
    "issuanceDate": None,
    "expirationDate": None,
    "proof": {}  # Signature
}


class VCRequest(BaseModel):
    holder_did: str
    permissions: list


@app.post("/issue_vc")
def issue_vc(request: VCRequest):
    """
    Issues a Verifiable Credential (VC) with the requested permissions.
    """
    now = int(time.time())
    expiry = now + 3600  # 1 hour validity

    # Create VC
    vc = CREDENTIAL_TEMPLATE.copy()
    vc["credentialSubject"]["id"] = request.holder_did
    vc["credentialSubject"]["permissions"] = request.permissions
    vc["issuanceDate"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    vc["expirationDate"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry))

    # Sign VC using JWT
    signed_vc = jwt.encode(vc, ISSUER_SECRET, algorithm="HS256")
    return {"verifiable_credential": signed_vc}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
