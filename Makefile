.PHONY: all oauth_server client agent clean

# Run the OAuth server
oauth_server:
	@echo "Starting OAuth server on port 8000..."
	python -m uvicorn oauth_server:app --reload --port 8000

# Run the client
client:
	@echo "Starting OAuth client on port 9000..."
	python client_with_callback.py &

# Run the MCP agent server
agent:
	@echo "Starting MCP agent server..."
	python calendar_mcp_server.py &

# Stop all background processes
clean:
	@echo "Stopping all running services..."
	@pkill -f "uvicorn oauth_auth_server:app" || true
	@pkill -f "python client_with_callback.py" || true
	@pkill -f "python calendar_mcp_server.py" || true

# Help target
help:
	@echo "Available commands:"
	@echo "  make all          - Start OAuth server and client"
	@echo "  make oauth_server - Start OAuth server only"
	@echo "  make client       - Start OAuth client only"
	@echo "  make agent        - Start MCP agent only"
	@echo "  make clean        - Stop all running services"
