#!/bin/bash

# GitHub MCP Setup Script
# This script helps set up and run the GitHub MCP server

# Check if Python is installed
if ! command -v python &> /dev/null
then
    echo "Python could not be found. Please install Python 3.9 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ])
then
    echo "Python 3.9 or higher is required. Found Python $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Determine the activate script based on OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    ACTIVATE_SCRIPT=".venv/Scripts/activate"
else
    # Unix-like
    ACTIVATE_SCRIPT=".venv/bin/activate"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$ACTIVATE_SCRIPT"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Setup environment variables
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    echo "Please enter your GitHub Personal Access Token:"
    read -s GITHUB_TOKEN
    
    echo "GITHUB_TOKEN=$GITHUB_TOKEN" > .env
    echo "GITHUB_ENTERPRISE_URL=https://api.github.com" >> .env
    echo "TRANSPORT=stdio" >> .env
    echo "PORT=8050" >> .env
    
    echo ".env file created successfully."
else
    echo ".env file already exists."
fi

# Ask how to run the server
echo ""
echo "How would you like to run the GitHub MCP server?"
echo "1) stdio mode (for direct integration with MCP clients)"
echo "2) SSE mode (for standalone service)"
echo "3) Exit without running"
read -p "Enter your choice (1-3): " CHOICE

case $CHOICE in
    1)
        echo "Running in stdio mode..."
        export $(grep -v '^#' .env | xargs)
        export TRANSPORT=stdio
        python main.py
        ;;
    2)
        echo "Running in SSE mode on port $PORT..."
        export $(grep -v '^#' .env | xargs)
        export TRANSPORT=sse
        python main.py
        ;;
    3)
        echo "Setup complete. Run 'python main.py' to start the server."
        ;;
    *)
        echo "Invalid choice. Setup complete but server not started."
        ;;
esac
