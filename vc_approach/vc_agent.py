#!/usr/bin/env python3
"""
vc_agent.py

Receives a Verifiable Credential (VC), verifies it, and allows or denies access.
"""

import jwt
import json
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Agent Setup
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Secret for verifying signatures (replace with a real verification key)
ISSUER_SECRET = "super-secret-key"

# Mock calendar
MOCK_CALENDAR = [
    {"start": "2025-03-01T09:00:00", "end": "2025-03-01T10:00:00"},
    {"start": "2025-03-01T11:00:00", "end": "2025-03-01T11:30:00"},
]


class VCRequest(BaseModel):
    verifiable_credential: str


def verify_vc(vc_jwt: str):
    """
    Verify and decode the Verifiable Credential (VC).
    """
    try:
        payload = jwt.decode(vc_jwt, ISSUER_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="VC expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid VC")

    if "calendar.view" not in payload["credentialSubject"]["permissions"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    return payload["credentialSubject"]["id"]


@app.post("/call_agent")
def call_agent(request: VCRequest):
    """
    Endpoint that requires a valid VC before executing actions.
    """
    user_did = verify_vc(request.verifiable_credential)
    logging.info(f"Verified DID: {user_did}")

    # Find next free time slot
    last_end = datetime.fromisoformat(MOCK_CALENDAR[-1]["end"])
    free_start = last_end + timedelta(minutes=15)
    free_end = free_start + timedelta(minutes=30)

    result = {
        "start": free_start.isoformat(timespec="minutes"),
        "end": free_end.isoformat(timespec="minutes"),
    }

    return {"agent_result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
