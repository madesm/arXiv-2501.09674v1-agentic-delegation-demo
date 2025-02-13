#!/usr/bin/env python3
"""
vc_mcp_server.py

An MCP server that exposes a 'find_slot' tool. The tool requires a verifiable credential (VC)
granting the 'calendar.view' permission. The VC is verified locally using a shared secret.
Run: mcp dev vc_mcp_server.py  (or python vc_mcp_server.py)
"""

import json
import logging
from datetime import datetime, timedelta

import jwt
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CalendarMCP")

# Secret for verifying VC signatures (replace with a real key in production)
ISSUER_SECRET = "super-secret-key"

# Fake or mocked calendar data
MOCK_CALENDAR = [
    {"start": "2025-03-01T09:00:00", "end": "2025-03-01T10:00:00"},
    {"start": "2025-03-01T11:00:00", "end": "2025-03-01T11:30:00"},
]

# Set up the MCP server
mcp = FastMCP(
    "CalendarAgent",
    description="Demo MCP server requiring a verifiable credential (VC) to find slots."
)

def verify_vc(vc_jwt: str) -> str:
    """
    Verify and decode the Verifiable Credential (VC).
    Returns the holder's DID if verification is successful.
    Raises ToolError on failure.
    """
    if not vc_jwt:
        logger.warning("Missing verifiable credential")
        raise ToolError("Missing verifiable credential")
    try:
        payload = jwt.decode(vc_jwt, ISSUER_SECRET, algorithms=["HS256"])
        logger.info("VC verification succeeded.")
        logger.debug(f"VC payload: {payload}")
    except jwt.ExpiredSignatureError:
        logger.warning("VC expired")
        raise ToolError("VC expired")
    except jwt.InvalidTokenError:
        logger.error("Invalid VC")
        raise ToolError("Invalid VC")

    # Check that the VC grants the required permission
    permissions = payload.get("credentialSubject", {}).get("permissions", [])
    if "calendar.view" not in permissions:
        logger.warning("VC lacks required permission: 'calendar.view'")
        raise ToolError("VC lacks required permission: 'calendar.view'")

    return payload.get("credentialSubject", {}).get("id", "unknown")

@mcp.tool(name="find_slot")
def find_slot(verifiable_credential: str, duration_minutes: int = 30) -> str:
    """
    Finds the next free slot after the last event in our mocked calendar.

    Requires a verifiable credential (VC) that grants 'calendar.view' permission.
    """
    logger.info("Verifying VC for find_slot request.")
    holder_did = verify_vc(verifiable_credential)
    logger.info(f"Verified holder DID: {holder_did}")

    # Process calendar events
    events = []
    for e in MOCK_CALENDAR:
        start_dt = datetime.fromisoformat(e["start"])
        end_dt = datetime.fromisoformat(e["end"])
        events.append((start_dt, end_dt))
    events.sort(key=lambda x: x[0])

    # Naive logic: free time is after the last event
    last_end = events[-1][1]
    free_start = last_end + timedelta(minutes=15)
    free_end = free_start + timedelta(minutes=duration_minutes)

    result = {
        "start": free_start.isoformat(timespec="minutes"),
        "end": free_end.isoformat(timespec="minutes"),
    }
    logger.info(f"Returning free slot: {result}")
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    logger.info("Starting Calendar MCP Server with VC-based delegation...")
    mcp.run()
