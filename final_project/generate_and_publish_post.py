import boto3
import json
import os
import re
import base64
import random
import tempfile
import datetime
import requests
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
        formatted_post = {
            'title': post.get('post_title', ''),
            'content': re.sub(r'<[^>]+>', '', post.get('post_content', '')),  # Remove HTML tags
            'date': post.get('post_date', ''),
            'categories': [term.get('name', '') for term in post.get('terms', [])],
            'excerpt': re.sub(r'<[^>]+>', '', post.get('post_excerpt', '')) if post.get('post_excerpt') else ""
        }
        formatted_posts.append(formatted_post)
    return formatted_posts
    return formatted_posts

def generate_post_with_bedrock(posts_content, github_activity):
    """Generate a new SEO-optimized post using Amazon Bedrock's Claude model and GitHub activity"""
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION
    )
    
    # Convert datetime objects to strings to make JSON serializable
    posts_json = []
    for post in posts_content:
        post_copy = post.copy()
        if isinstance(post_copy.get('date'), (datetime.date, datetime.datetime)):
            post_copy['date'] = post_copy['date'].strftime('%Y-%m-%d')
        posts_json.append(post_copy)
    
    # Create a prompt for Claude
    prompt = f"""You are a witty, sarcastic tech blogger with a knack for explaining complex topics in an entertaining way.

I'll provide you with some of my recent blog posts so you can understand my writing style and tone.

Recent posts:
{json.dumps(posts_json, indent=2)}

Your recent GitHub activity:
{json.dumps(github_activity, indent=2)}

Based on my writing style and your recent GitHub activity, please generate a new blog post about a tech topic that would interest my readers. The post should:

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
                json_content = json_match.group(1)
                # Manual parsing for backtick-enclosed JSON
                title_match = re.search(r'"title":\s*"([^"]+)"', json_content)
                title = title_match.group(1) if title_match else "Generated Post"
                
                # Extract content (handling nested quotes)
                content_start = json_content.find('"content":') + 11
                content_end = json_content.find('",\n  "tags"')
                if content_end == -1:
                    content_end = json_content.find('",\n  "meta_description"')
                if content_end == -1:
                    content_end = json_content.rfind('",')
                
                post_content = json_content[content_start:content_end].strip('" \n')
                post_content = post_content.replace('\\\"', '"')  # Fix escaped quotes
                
                # Extract tags
                tags_match = re.search(r'"tags":\s*\[(.*?)\]', json_content, re.DOTALL)
                tags = []
                if tags_match:
                    tags_str = tags_match.group(1)
                    tags = [tag.strip(' "') for tag in tags_str.split(',')]
                
                # Extract meta description
                meta_match = re.search(r'"meta_description":\s*"([^"]+)"', json_content)
                meta = meta_match.group(1) if meta_match else ""
                
                post_data = {
                    "title": title,
                    "content": post_content,
                    "tags": tags,
                    "meta_description": meta
                }
            else:
                    # Try to find JSON without code blocks
                json_match = re.search(r'({[\s\S]*})', content)
                if json_match:
                    # Manual parsing as a last resort
                    raw_json = json_match.group(1)
                    # Extract title
                    title_match = re.search(r'"title":\s*"([^"]+)"', raw_json)
                    title = title_match.group(1) if title_match else "Generated Post"
                    
                    # Extract content (this is trickier due to nested quotes)
                    content_start = raw_json.find('"content":') + 11
                    content_end = raw_json.find('",\n  "tags"')
                    if content_end == -1:  # Try another pattern
                        content_end = raw_json.find('",\n  "meta_description"')
                    if content_end == -1:  # One more try
                        content_end = raw_json.rfind('",')
                    
                    post_content = raw_json[content_start:content_end].strip('" \n')
                    post_content = post_content.replace('\\"', '"')  # Fix escaped quotes
                    
                    # Extract tags
                    tags_match = re.search(r'"tags":\s*\[(.*?)\]', raw_json, re.DOTALL)
                    tags = []
                    if tags_match:
                        tags_str = tags_match.group(1)
                        tags = [tag.strip(' "') for tag in tags_str.split(',')]
                    
                    # Extract meta description
                    meta_match = re.search(r'"meta_description":\s*"([^"]+)"', raw_json)
                    meta = meta_match.group(1) if meta_match else ""
                    
                    post_data = {
                        "title": title,
                        "content": post_content,
                        "tags": tags,
                        "meta_description": meta
                    }
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
                if response and isinstance(response, dict) and 'url' in response:
                    # Replace the placeholder with the image HTML
                    img_url = response['url']
                    img_id = response.get('id', '0')
                    img_html = f'<img src="{img_url}" alt="{description}" class="wp-image-{img_id}" />'
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
        
        # Handle tags - ensure they're not None
        tags = post_data.get('tags', [])
        if tags is None:
            tags = []
        
        # Convert post.terms_names to a dictionary with string values only
        post.terms_names = {
            'post_tag': [str(tag) for tag in tags if tag],
            'category': ['AI Generated', 'Technology']  # Default categories
        }
        
        post.post_status = 'publish'
        
        # Handle excerpt - ensure it's not None
        excerpt = post_data.get('meta_description', '')
        if excerpt is None:
            excerpt = ''
        post.excerpt = excerpt
        
        # Set custom fields for SEO - only if meta_description exists and is not None
        meta_desc = post_data.get('meta_description')
        if meta_desc:
            post.custom_fields = [
                {
                    'key': '_yoast_wpseo_metadesc',
                    'value': str(meta_desc)
                }
            ]
        else:
            post.custom_fields = []
        
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
    
    # Get GitHub activity
    github_activity = get_github_activity("felipedebene")
    if not github_activity['starred_repos'] and not github_activity['recent_commits']:
        print("No GitHub activity found")
        # Continue anyway instead of returning
        github_activity = {
            'starred_repos': [{'name': 'placeholder-repo', 'description': 'Placeholder for when GitHub activity is not available'}],
            'recent_commits': [{'repo': 'placeholder-repo', 'message': 'Continue generating content even without GitHub activity'}]
        }
    
    # Generate a new post
    print("Generating new post with Claude 3 Sonnet...")
    post_data = generate_post_with_bedrock(formatted_posts, github_activity)
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
