#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== WordPress Post Generator Setup ===${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv package manager not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create a virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
uv venv

# Activate the virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
uv pip install boto3 requests

# Make the Python script executable
chmod +x generate_post.py

# Run the script
echo -e "${YELLOW}Running the WordPress post generator...${NC}"
python generate_post.py

echo -e "${GREEN}Done!${NC}"
