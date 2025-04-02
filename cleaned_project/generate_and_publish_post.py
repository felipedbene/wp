import boto3
import json
import os
import re
import base64
import random
import tempfile
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.compat import xmlrpc_client
import requests

# Constants
AWS_REGION = "us-west-2"  # Explicitly set to us-west-2
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"  # Using Claude 3 Sonnet model

def get_wp_credentials():
    """Load WordPress credentials from JSON file"""
    try:
        # Look for credentials in the current directory and parent directory
        credential_paths = ['blog-credentials.json', '../blog-credentials.json']
        for path in credential_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        raise FileNotFoundError("Could not find blog-credentials.json")
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def get_github_activity(username):
    """Get GitHub activity for a user"""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    
    # Get starred repositories
    starred_url = f'https://api.github.com/users/{username}/starred'
    starred_response = requests.get(starred_url, headers=headers)
    starred_repos = []
    if starred_response.status_code == 200:
        starred_repos = [{'name': repo['name'], 'description': repo.get('description', 'No description')} 
                        for repo in starred_response.json()[:5]]
    
    # Get user's recent commits
    events_url = f'https://api.github.com/users/{username}/events'
    events_response = requests.get(events_url, headers=headers)
    recent_commits = []
    if events_response.status_code == 200:
        for event in events_response.json():
            if event['type'] == 'PushEvent':
                for commit in event['payload']['commits']:
                    recent_commits.append({
                        'repo': event['repo']['name'],
                        'message': commit['message']
                    })
                    if len(recent_commits) >= 5:
                        break
            if len(recent_commits) >= 5:
                break
    
    return {
        'starred_repos': starred_repos,
        'recent_commits': recent_commits
    }

def fetch_recent_posts(wp_client, num_posts=3):
    """Fetch recent posts from WordPress"""
    try:
        recent_posts = wp_client.call(posts.GetPosts({'number': num_posts}))
        return recent_posts
    except Exception as e:
        print(f"Error fetching recent posts: {e}")
        return []

def format_posts_for_analysis(recent_posts):
    """Format recent posts for analysis by Claude"""
    formatted_posts = []
    for post in recent_posts:
        formatted_posts.append({
            'title': post.title,
            'content': re.sub(r'<[^>]+>', '', post.content),  # Remove HTML tags
            'date': post.date.strftime('%Y-%m-%d'),
            'categories': [term.name for term in post.terms],
            'excerpt': re.sub(r'<[^>]+>', '', post.excerpt) if post.excerpt else ""
        })
    return formatted_posts

def generate_post_with_bedrock(posts_content):
    """Generate a new SEO-optimized post using Amazon Bedrock's Claude model"""
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION
    )
    
    # Create a prompt for Claude
    prompt = f"""You are a witty, sarcastic tech blogger with a knack for explaining complex topics in an entertaining way.

I'll provide you with some of my recent blog posts so you can understand my writing style and tone.

Recent posts:
{json.dumps(posts_content, indent=2)}

Based on my writing style, please generate a new blog post about a tech topic that would interest my readers. The post should:

1. Have a catchy, SEO-friendly title
2. Include an engaging introduction
3. Have well-structured sections with subheadings
4. Include at least 2 places for images with the format [IMAGE: description of image]
5. End with a thought-provoking conclusion
6. Include relevant tags (3-5) for the post
7. Include a meta description for SEO purposes

Format your response as a JSON object with the following structure:
{{
  "title": "The title of the post",
  "content": "The full content of the post with image placeholders",
  "tags": ["tag1", "tag2", "tag3"],
  "meta_description": "A compelling meta description for SEO"
}}

Be creative, informative, and maintain my sarcastic, witty tone throughout the post.
"""

    # Call Claude 3 Sonnet
    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
    )
    
    response_body = json.loads(response.get('body').read().decode('utf-8'))
    content = response_body.get('content', [{}])[0].get('text', '')
    
    # Extract JSON from Claude's response
    try:
        # First, try to parse the entire response as JSON
        post_data = json.loads(content)
    except json.JSONDecodeError:
        # If that fails, try to extract JSON from the text
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                post_data = json.loads(json_match.group(1))
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({[\s\S]*})', content)
                if json_match:
                    post_data = json.loads(json_match.group(1))
                else:
                    raise Exception("Could not extract JSON from response")
        except Exception as e:
            print(f"Error extracting JSON: {e}")
            print(f"Raw response: {content}")
            return None
    
    return post_data

def generate_image_with_bedrock(description):
    """Generate an image using Amazon Bedrock's Stable Diffusion XL"""
    try:
        print(f"Starting image generation for: '{description}'")
        
        # Create a Bedrock client
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Prepare the prompt for Stable Diffusion XL
        prompt = f"Professional, high-quality image: {description}. Detailed, vibrant, magazine-quality."
        
        # Call Stable Diffusion XL
        response = bedrock_runtime.invoke_model(
            modelId="stability.stable-diffusion-xl-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "text_prompts": [
                    {
                        "text": prompt,
                        "weight": 1.0
                    },
                    {
                        "text": "blurry, distorted, disfigured, poor quality, low resolution",
                        "weight": -1.0
                    }
                ],
                "cfg_scale": 9,
                "steps": 50,
                "seed": random.randint(0, 4294967295)
            })
        )
        
        # Process the response
        response_body = json.loads(response.get('body').read().decode('utf-8'))
        
        # Get the base64 encoded image
        if 'artifacts' in response_body and len(response_body['artifacts']) > 0:
            image_b64 = response_body['artifacts'][0]['base64']
            
            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_file.write(base64.b64decode(image_b64))
                return temp_file.name
        else:
            print("No image generated in the response")
            return None
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def upload_image_to_wordpress(wp_client, image_path, description):
    """Upload an image to WordPress and return the attachment ID"""
    try:
        # Prepare image data
        with open(image_path, 'rb') as img:
            image_data = img.read()
        
        # Prepare the media item
        filename = os.path.basename(image_path)
        data = {
            'name': f"{description[:50]}.png",
            'type': 'image/png',
            'bits': xmlrpc_client.Binary(image_data),
            'caption': description
        }
        
        # Upload the image
        response = wp_client.call(media.UploadFile(data))
        return response
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

def process_image_placeholders(wp_client, content):
    """Process image placeholders in the content and replace with actual images"""
    # Define patterns for image placeholders
    patterns = [
        r'\[IMAGE:\s*(.*?)\]',  # [IMAGE: description]
        r'\[image:\s*(.*?)\]',  # [image: description]
        r'\{\{IMAGE:\s*(.*?)\}\}',  # {{IMAGE: description}}
        r'\{\{image:\s*(.*?)\}\}'   # {{image: description}}
    ]
    
    # Process each pattern
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for description in matches:
            # Try to generate an image up to 2 times
            image_path = None
            for attempt in range(2):
                image_path = generate_image_with_bedrock(description)
                if image_path:
                    break
                print(f"Retrying image generation for: {description}")
            
            if image_path:
                # Upload the image to WordPress
                response = upload_image_to_wordpress(wp_client, image_path, description)
                if response:
                    # Replace the placeholder with the image HTML
                    img_url = response['url']
                    img_html = f'<img src="{img_url}" alt="{description}" class="wp-image-{response["id"]}" />'
                    content = re.sub(pattern.replace('(.*?)', re.escape(description)), img_html, content, 1)
                    
                    # Clean up the temporary file
                    os.unlink(image_path)
                else:
                    # If upload fails, replace with a message
                    content = re.sub(pattern.replace('(.*?)', re.escape(description)), 
                                    f'<p><em>Image generation failed for: {description}</em></p>', content, 1)
            else:
                # If generation fails, replace with a witty message
                witty_messages = [
                    f"<p><em>The AI tried to draw '{description}' but apparently it skipped art class that day.</em></p>",
                    f"<p><em>Image of '{description}' not available. The AI artist is currently experiencing creative differences with reality.</em></p>",
                    f"<p><em>We asked for an image of '{description}' but the AI was too busy contemplating the meaning of pixels.</em></p>",
                    f"<p><em>Image generation for '{description}' failed. Our AI illustrator is taking an unexpected coffee break.</em></p>"
                ]
                content = re.sub(pattern.replace('(.*?)', re.escape(description)), 
                                random.choice(witty_messages), content, 1)
    
    return content

def publish_post_to_wordpress(wp_client, post_data):
    """Publish the generated post to WordPress"""
    try:
        # Create a new post
        post = WordPressPost()
        post.title = post_data['title']
        post.content = post_data['content']
        post.terms_names = {
            'post_tag': post_data['tags'],
            'category': ['AI Generated', 'Technology']  # Default categories
        }
        post.post_status = 'publish'
        post.excerpt = post_data.get('meta_description', '')
        
        # Set custom fields for SEO
        post.custom_fields = []
        if 'meta_description' in post_data:
            post.custom_fields.append({
                'key': '_yoast_wpseo_metadesc',
                'value': post_data['meta_description']
            })
        
        # Publish the post
        post_id = wp_client.call(NewPost(post))
        return post_id
    except Exception as e:
        print(f"Error publishing post: {e}")
        return None

def main():
    """Main function to generate and publish a post"""
    # Load WordPress credentials
    credentials = get_wp_credentials()
    if not credentials:
        print("Failed to load WordPress credentials")
        return
    
    # Connect to WordPress
    try:
        wp_client = Client(credentials['xmlrpc_url'], credentials['username'], credentials['password'])
    except Exception as e:
        print(f"Error connecting to WordPress: {e}")
        return
    
    # Fetch recent posts
    recent_posts = fetch_recent_posts(wp_client)
    if not recent_posts:
        print("No recent posts found")
        return
    
    # Format posts for analysis
    formatted_posts = format_posts_for_analysis(recent_posts)
    
    # Generate a new post
    print("Generating new post with Claude 3 Sonnet...")
    post_data = generate_post_with_bedrock(formatted_posts)
    if not post_data:
        print("Failed to generate post")
        return
    
    # Process image placeholders
    print("Processing image placeholders...")
    post_data['content'] = process_image_placeholders(wp_client, post_data['content'])
    
    # Publish the post
    print("Publishing post to WordPress...")
    post_id = publish_post_to_wordpress(wp_client, post_data)
    if post_id:
        print(f"Post published successfully with ID: {post_id}")
        print(f"Title: {post_data['title']}")
        print(f"Tags: {', '.join(post_data['tags'])}")
    else:
        print("Failed to publish post")

if __name__ == "__main__":
    main()
