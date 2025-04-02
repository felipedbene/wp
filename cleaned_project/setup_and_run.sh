#!/bin/bash

# The AI Blogging Butler setup script
# Because typing commands is hard

echo "🤵 Welcome to The AI Blogging Butler setup! 🤵"
echo "Let's get your automated blogging assistant ready..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv package manager not found! Please install it first:"
    echo "pip install uv"
    exit 1
fi

# Create virtual environment
echo "🔧 Creating virtual environment with uv (because virtualenv is too mainstream)..."
uv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies (pray they're all compatible)..."
uv pip install -r requirements.txt

# Check if credentials file exists
if [ ! -f "blog-credentials.json" ]; then
    echo "⚠️ blog-credentials.json not found!"
    echo "Please create this file with your WordPress credentials:"
    echo '{
  "xmlrpc_url": "https://your-blog.com/xmlrpc.php",
  "username": "your_username",
  "password": "your_application_password"
}'
    exit 1
fi

# Run the script
echo "🚀 Running the AI Blogging Butler (fingers crossed)..."
python generate_and_publish_post.py

echo "✨ Setup complete! Your AI Blogging Butler is ready to serve."
