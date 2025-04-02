# The AI Blogging Butler 🎩✍️

A project by Felipe de Bene, with assistance from Amazon Q

Visit the live blog at: https://blog.debene.dev

Meet Amazon Q: [Hello World: Amazon Q Steps Out of the Shadows](https://blog.debene.dev/hello-world-amazon-q-steps-out-of-the-shadows/)

# WordPress Post Generator: The AI Blogging Butler

Because manually writing blog posts is *so* 2023. This project automatically generates new WordPress blog posts using Amazon Bedrock's Claude 3 Sonnet model, complete with AI-generated images that occasionally look like they were drawn by a caffeinated toddler.

## Features

- Fetches your latest WordPress posts (to understand your writing style, or lack thereof)
- Analyzes content using Amazon Bedrock's Claude 3 Sonnet model (way smarter than your average blogger)
- Generates new posts that sound suspiciously like you wrote them (but probably better)
- Automatically generates images using Stable Diffusion XL (because Titan was being dramatic)
- Includes witty fallback messages when image generation fails (because sometimes AI needs a coffee break)
- Handles multiple image placeholder formats (because consistency is overrated)
- Automatically uploads everything to WordPress (so you can focus on your next coffee)
- Implements retry logic (because even AI has bad days)

## Prerequisites

- Python 3.8+ (because we're not savages)
- [uv package manager](https://github.com/astral-sh/uv) (pip is so yesterday)
- AWS credentials configured with Bedrock access (in us-west-2, because that's where the magic happens)
- WordPress site with XML-RPC API access and application password (if your site doesn't support XML-RPC, welcome to debugging hell)
- A sense of humor (required for reading error messages)

## Setup

1. Make sure you have AWS credentials configured with access to Amazon Bedrock in us-west-2 (other regions are available, but why make life complicated?).

2. Run the setup script (because typing commands is hard):
   ```bash
   ./setup_and_run.sh
   ```

   This will:
   - Create a virtual environment using uv (because virtualenv is too mainstream)
   - Install required dependencies (pray they're all compatible)
   - Run the post generator script (fingers crossed)

### Kubernetes Deployment

For automated posting, deploy to Kubernetes:

1. Build multi-architecture Docker images:
   ```bash
   ./build_multiarch_fixed.sh
   ```

2. Configure your Kubernetes secrets (see `kubernetes/secrets-template.yaml`)

3. Apply the CronJob:
   ```bash
   kubectl apply -f kubernetes/cronjob-actual.yaml
   ```

See the `kubernetes/README.md` file for more details.

## Manual Setup

If you enjoy doing things the hard way:

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
   python generate_and_publish_post.py
   ```

## Configuration

Edit the `blog-credentials.json` file with your WordPress credentials:
```json
{
  "xmlrpc_url": "https://your-blog.com/xmlrpc.php",
  "username": "your_username",
  "password": "your_application_password"
}
```

## How It Works

1. The script fetches recent posts from your WordPress site via XML-RPC (because REST APIs are too easy)
2. It formats these posts and sends them to Claude 3 Sonnet (who probably judges your writing style)
3. Claude generates a new post with similar style (but with better grammar)
4. The script identifies image placeholders in the generated content (formats include [IMAGE: description], because we're fancy)
5. It attempts to generate images using Stable Diffusion XL (up to 2 times, because persistence is key)
6. If image generation fails, you get a witty error message (because why be boring about failure?)
7. Successfully generated images are uploaded to WordPress (assuming your upload directory permissions are correct, good luck with that)
8. Finally, it publishes everything back to WordPress (and crosses its fingers)

## Troubleshooting

- "Access Denied" from Bedrock? Check your AWS credentials and region (and maybe sacrifice a rubber duck)
- WordPress authentication failing? Double-check your application password (and that XML-RPC isn't blocked)
- Images not generating? Try again (and again, and maybe one more time)
- Getting weird error messages? At least they're entertaining
- Everything broken? Have you tried turning it off and on again?

Remember: If all else fails, the script will at least try to make you laugh with its error messages. Because if you're going to fail, fail with style!

## Recent Improvements

- **v1.2.0**: Switched from Amazon Titan Image Generator to Stable Diffusion XL because Titan was being a drama queen 👑
- **v1.1.0**: Added REST API support with Markdown formatting for the modern blogger
- **v1.0.0**: Initial release with all the bells and whistles (and occasional kazoos)

# Created with Amazon Q
This project was developed with assistance from Amazon Q, demonstrating the power of AI-assisted development.

Amazon Q helped with:
- Python code development
- AWS service integration
- Kubernetes deployment
- Documentation
- Troubleshooting
- Author page creation
- Showcase post generation
- Saving developers from the depths of API documentation hell

See [AmazonQ.md](AmazonQ.md) for more details.
