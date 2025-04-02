#!/bin/bash
# Setup and run script for the AI Blogging Butler (REST API with Markdown version)

# Ensure we're in the script's directory
cd "$(dirname "$0")"

# Create virtual environment using uv
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Run the post generator
echo "Running post generator..."
python generate_and_publish_post_rest_md.py

echo "Done!"
