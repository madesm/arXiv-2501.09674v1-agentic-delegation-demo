.PHONY: run install lint test clean

# Default command: Run the business package
run:
	python -m mcp-server-time --local-timezone "America/Los_Angeles"

# Install dependencies from requirements.txt (if applicable)
install:
	pip install -r requirements.txt

# Lint the code using flake8
lint:
	flake8 business

# Run tests using pytest
test:
	pytest tests/

# Clean up temporary files
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
