#!/usr/bin/env python3
"""
vc_client.py

An MCP client that:
1. Requests a verifiable credential (VC) from the issuer.
2. Uses the VC to call the MCP agent's 'find_slot' tool.
"""

import requests
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuration
VC_ISSUER_URL = "http://localhost:8000/issue_vc"
MCP_AGENT_COMMAND = "python"
MCP_AGENT_ARGS = ["vc_agent.py"]

# The holder's DID and required permission
HOLDER_DID = "did:example:holder123"
PERMISSIONS = ["calendar.view"]

async def call_mcp_agent(vc: str):
    # Configure the MCP client to launch the agent
    server_params = StdioServerParameters(
        command=MCP_AGENT_COMMAND,
        args=MCP_AGENT_ARGS,
        env=None
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("find_slot", {"verifiable_credential": vc})
            ret = {"ret": json.loads(result.content[0].text)}
            print(json.dumps(ret, indent=4))

def main():
    # Step 1: Request a VC from the issuer
    print("Requesting Verifiable Credential (VC) from issuer...")
    response = requests.post(VC_ISSUER_URL, json={"holder_did": HOLDER_DID, "permissions": PERMISSIONS})
    if response.status_code != 200:
        print("Error obtaining VC:", response.text)
        return
    vc = response.json()["verifiable_credential"]
    print("Received VC:", vc)

    # Step 2: Use the VC to call the MCP agent
    asyncio.run(call_mcp_agent(vc))

if __name__ == "__main__":
    main()
