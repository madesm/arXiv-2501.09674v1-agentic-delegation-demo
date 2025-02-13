#!/usr/bin/env python3
"""
vc_issuer.py

Issues a Verifiable Credential (VC) granting delegation.
Run:
    uvicorn vc_issuer:app --reload --port 8000
"""

import jwt
import time
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Hardcoded secret key for signing the VC (do not use in production)
ISSUER_SECRET = "super-secret-key"

# Template for the credential
CREDENTIAL_TEMPLATE = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential", "DelegationCredential"],
    "issuer": "did:example:issuer",
    "credentialSubject": {
        "id": None,  # Holder's DID
        "permissions": []  # e.g. ["calendar.view"]
    },
    "issuanceDate": None,
    "expirationDate": None,
    "proof": {}
}

class VCRequest(BaseModel):
    holder_did: str
    permissions: list

@app.post("/issue_vc")
def issue_vc(request: VCRequest):
    now = int(time.time())
    expiry = now + 3600  # VC valid for 1 hour

    # Prepare the credential
    vc = CREDENTIAL_TEMPLATE.copy()
    vc["credentialSubject"]["id"] = request.holder_did
    vc["credentialSubject"]["permissions"] = request.permissions
    vc["issuanceDate"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    vc["expirationDate"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry))
    
    # Sign the VC using JWT
    signed_vc = jwt.encode(vc, ISSUER_SECRET, algorithm="HS256")
    return {"verifiable_credential": signed_vc}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
