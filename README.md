# WordPress Post Generator

This project automatically generates new WordPress blog posts using Amazon Bedrock's Claude model based on your existing content.

## Features

- Fetches the latest 3 posts from your WordPress site
- Analyzes the content using Amazon Bedrock's Claude model
- Generates a new post with similar style and tone
- Automatically generates images using Amazon Bedrock's Stable Diffusion XL model
- Automatically publishes the post to your WordPress site with images

## Prerequisites

- Python 3.8+
- [uv package manager](https://github.com/astral-sh/uv)
- AWS credentials configured with Bedrock access
- WordPress site with REST API access and application password

## Setup

1. Make sure you have AWS credentials configured with access to Amazon Bedrock in the us-west-2 region.

2. Run the setup script:
   ```bash
   ./setup_and_run.sh
   ```

   This will:
   - Create a virtual environment using uv
   - Install required dependencies
   - Run the post generator script

## Manual Setup

If you prefer to set up manually:

1. Create a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   python generate_post.py
   ```

## Configuration

Edit the `generate_post.py` file to modify:

- WordPress URL and credentials
- AWS region and model ID
- Post generation parameters

## How It Works

1. The script fetches recent posts from your WordPress site via the REST API
2. It formats these posts and sends them to Amazon Bedrock's Claude model
3. Claude analyzes the content and generates a new post with similar style
4. The script identifies image placeholders in the generated content
5. It generates images using Amazon Bedrock's Stable Diffusion model
6. The script posts the generated content with images back to WordPress

## Troubleshooting

- Ensure your AWS credentials have access to Bedrock
- Verify your WordPress application password is correct
- Check that the WordPress REST API is accessible
