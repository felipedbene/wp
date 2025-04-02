#!/bin/bash

# Setup and run script for AI Blogging Butler (REST API version)
# This script creates a virtual environment, installs dependencies, and runs the post generator

echo "🎩 Setting up AI Blogging Butler (REST API version)..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv package manager not found. Please install it first:"
    echo "    curl -sSf https://install.python-poetry.org | python3 -"
    exit 1
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
uv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -r requirements.txt

# Check if blog-credentials.json exists
if [ ! -f blog-credentials.json ]; then
    echo "⚠️ blog-credentials.json not found. Creating template..."
    cp blog-credentials-template-rest.json blog-credentials.json
    echo "⚠️ Please edit blog-credentials.json with your WordPress credentials before continuing."
    exit 1
fi

# Run the post generator
echo "✍️ Generating and publishing post..."
python generate_and_publish_post_rest.py

echo "✅ Done!"
