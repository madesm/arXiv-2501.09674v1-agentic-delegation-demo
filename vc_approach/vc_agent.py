#!/usr/bin/env python3
"""
vc_agent.py

An MCP server (CalendarAgent) that exposes a 'find_slot' tool.
The tool requires a verifiable credential (VC) granting 'calendar.view' permission.
Run: mcp dev vc_agent.py  (or python vc_agent.py)
"""

import json
import logging
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from vc_verifier import verify_vc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CalendarMCP")

# Mocked calendar data
MOCK_CALENDAR = [
    {"start": "2025-03-01T09:00:00", "end": "2025-03-01T10:00:00"},
    {"start": "2025-03-01T11:00:00", "end": "2025-03-01T11:30:00"},
]

# Set up the MCP server
mcp = FastMCP("CalendarAgent", description="MCP server requiring a VC to find calendar slots.")

@mcp.tool(name="find_slot")
def find_slot(verifiable_credential: str, duration_minutes: int = 30) -> str:
    """
    Finds the next free slot after the last event.
    Requires a VC (as a JWT) that grants the 'calendar.view' permission.
    """
    logger.info("Verifying VC for find_slot request.")
    holder_did = verify_vc(verifiable_credential)
    logger.info(f"Verified holder DID: {holder_did}")

    # Process the mocked calendar events
    events = []
    for e in MOCK_CALENDAR:
        start_dt = datetime.fromisoformat(e["start"])
        end_dt = datetime.fromisoformat(e["end"])
        events.append((start_dt, end_dt))
    events.sort(key=lambda x: x[0])

    # Simple logic: free time is after the last event plus a 15-minute buffer
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
