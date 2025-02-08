import asyncio
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

###############################################################################
# CONFIGURATION & LOGGING
###############################################################################

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Configuration:
    """Manages configuration and environment variables for the MCP client."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.load_env()
        self.access_token = os.getenv("ACCESS_TOKEN")

    @staticmethod
    def load_env() -> None:
        """Load environment variables from .env file."""
        load_dotenv()

    def get_access_token(self) -> str:
        """Retrieve the stored access token or prompt the user."""
        if self.access_token:
            return self.access_token
        return input("Enter your access token: ").strip()


###############################################################################
# MCP CLIENT WRAPPER
###############################################################################

class MCPClient:
    """Handles connecting to an MCP server and executing tools."""

    def __init__(self, server_command: str, server_args: list[str]) -> None:
        self.server_command = server_command
        self.server_args = server_args
        self.session: ClientSession | None = None

    async def initialize(self) -> None:
        """Initialize the connection to the MCP server."""
        server_params = StdioServerParameters(command=self.server_command, args=self.server_args)

        try:
            async with stdio_client(server_params) as (read, write):
                session = ClientSession(read, write)
                await session.initialize()
                self.session = session
        except Exception as e:
            logging.error(f"Failed to connect to MCP server: {e}")
            raise

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on the MCP server."""
        if not self.session:
            raise RuntimeError("MCP session is not initialized.")

        tools_response = await self.session.list_tools()
        tools = []

        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                tools.extend(item[1])

        return tools

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute an MCP tool with the given arguments."""
        if not self.session:
            raise RuntimeError("MCP session is not initialized.")

        logging.info(f"Calling tool '{tool_name}' with args: {arguments}")
        result = await self.session.call_tool(tool_name, arguments)
        return result

    async def cleanup(self) -> None:
        """Close the MCP session properly."""
        if self.session:
            await self.session.close()
            self.session = None


###############################################################################
# CHAT INTERFACE
###############################################################################

class ChatSession:
    """Handles user input and interaction with the MCP tools."""

    def __init__(self, mcp_client: MCPClient, config: Configuration) -> None:
        self.mcp_client = mcp_client
        self.config = config

    async def start_chat(self) -> None:
        """Main interactive chat session."""
        await self.mcp_client.initialize()

        # List available tools
        tools = await self.mcp_client.list_tools()
        available_tools = {tool.name: tool for tool in tools}
        logging.info(f"Available MCP tools: {list(available_tools.keys())}")

        while True:
            try:
                user_input = input("\n[USER] ").strip().lower()
                if user_input in ["quit", "exit"]:
                    logging.info("Exiting chat.")
                    break

                if "what times am i free" in user_input:
                    await self.handle_find_slot(available_tools)
                else:
                    print("[ASSISTANT] I didn't understand that. Try asking about free times.")

            except KeyboardInterrupt:
                logging.info("\nExiting chat.")
                break
            except Exception as e:
                logging.error(f"Error: {e}")

    async def handle_find_slot(self, available_tools: dict[str, Any]) -> None:
        """Handles calling the `find_slot` tool to check available calendar times."""
        tool_name = "find_slot"
        if tool_name not in available_tools:
            print("[ASSISTANT] The 'find_slot' tool is not available on this server.")
            return

        access_token = self.config.get_access_token()
        duration = input("Enter the meeting duration in minutes (default 30): ").strip()
        duration_minutes = int(duration) if duration.isdigit() else 30

        tool_arguments = {
            "access_token": access_token,
            "duration_minutes": duration_minutes
        }

        result = await self.mcp_client.execute_tool(tool_name, tool_arguments)

        print(f"\n[ASSISTANT] The next free slot is:\n{result}\n")


###############################################################################
# MAIN FUNCTION
###############################################################################

async def main() -> None:
    """Start the MCP client and chat session."""
    config = Configuration()

    # Set the command to run the MCP server (adjust to match your setup)
    server_command = "python"
    server_args = ["demo.py"]

    mcp_client = MCPClient(server_command, server_args)
    chat_session = ChatSession(mcp_client, config)

    await chat_session.start_chat()


if __name__ == "__main__":
    asyncio.run(main())
