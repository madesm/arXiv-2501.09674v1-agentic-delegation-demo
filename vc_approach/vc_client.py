#!/usr/bin/env python3
"""
vc_client.py

Requests a Verifiable Credential (VC) from the issuer, then presents it to the agent.
"""

import requests
import json

VC_ISSUER_URL = "http://localhost:8000/issue_vc"
VC_AGENT_URL = "http://localhost:9000/call_agent"

HOLDER_DID = "did:example:holder123"
PERMISSIONS = ["calendar.view"]

# Step 1: Request a VC from the issuer
print("Requesting Verifiable Credential (VC)...")
response = requests.post(VC_ISSUER_URL, json={"holder_did": HOLDER_DID, "permissions": PERMISSIONS})

if response.status_code != 200:
    print("Error obtaining VC:", response.text)
    exit(1)

vc = response.json()["verifiable_credential"]
print("Received Verifiable Credential:", vc)

# Step 2: Use the VC to call the agent
print("\nCalling agent with VC...")
agent_response = requests.post(VC_AGENT_URL, json={"verifiable_credential": vc})

if agent_response.status_code != 200:
    print("Agent denied access:", agent_response.text)
    exit(1)

print("Agent Response:", json.dumps(agent_response.json(), indent=2))
