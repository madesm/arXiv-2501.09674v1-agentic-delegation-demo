#!/usr/bin/env python3
"""
calendar_mcp_server.py

An MCP server that exposes a 'find_slot' tool. The tool requires an access_token
with scope='calendar.read', validated via the Auth Server's /validate endpoint.

Run: mcp dev calendar_mcp_server.py  (or python calendar_mcp_server.py)
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

# We'll assume your auth server is running on localhost:8000
AUTH_SERVER_URL = "http://localhost:8000/oauth/validate"

# Fake or mocked calendar data
MOCK_CALENDAR = [
    {"start": "2025-03-01T09:00:00", "end": "2025-03-01T10:00:00"},
    {"start": "2025-03-01T11:00:00", "end": "2025-03-01T11:30:00"},
]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CalendarMCP")

mcp = FastMCP("CalendarAgent", description="Demo MCP server requiring an access token to find slots.")


def validate_token(access_token: str) -> dict:
    """
    Validate the given token by calling the Auth Server's /validate endpoint.
    Raise ToolError if invalid or insufficient scope.
    """
    if not access_token:
        logger.warning("Missing access_token")
        raise ToolError("Missing access_token")

    try:
        # Call the auth server
        with httpx.Client() as client:
            response = client.post(f"{AUTH_SERVER_URL}?token={access_token}")
            response.raise_for_status()
            logger.info("Token validation request succeeded.")
            data = response.json()
            logger.debug(f"Token validation response: {data}")
    except httpx.HTTPError as e:
        logger.error(f"Token validation failed: {e}")
        raise ToolError(f"Token validation failed: {e}")

    if not data.get("valid"):
        logger.warning("Invalid or unknown token")
        raise ToolError("Invalid or unknown token")

    payload = data.get("payload", {})
    scope = payload.get("scope", "")
    if "calendar.read" not in scope:
        logger.warning("Token lacks required scope: 'calendar.read'")
        raise ToolError(f"Token lacks required scope: 'calendar.read'")

    return payload


@mcp.tool(name="find_slot")
def find_slot(access_token: str, duration_minutes: int = 30) -> str:
    """
    Finds the next free slot after the last event in our mocked calendar.

    Requires an 'access_token' with scope 'calendar.read'. We call the Auth Server
    to validate the token and scope prior to returning data.
    """
    logger.info("Validating token for find_slot request.")
    validate_token(access_token)
    logger.info("Token validation successful.")

    events = []
    for e in MOCK_CALENDAR:
        start_dt = datetime.fromisoformat(e["start"])
        end_dt = datetime.fromisoformat(e["end"])
        events.append((start_dt, end_dt))
    events.sort(key=lambda x: x[0])

    # naive logic: free time is after the last event
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
    logger.info("Starting Calendar MCP Server...")
    mcp.run()
