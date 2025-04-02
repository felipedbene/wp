#!/usr/bin/env python
"""
The AI Blogging Butler - WordPress Post Generator using REST API with Markdown
A project by Felipe de Bene, with assistance from Amazon Q

This script:
1. Fetches recent posts from your WordPress blog via REST API
2. Analyzes them using Amazon Bedrock's Claude 3 Sonnet model
3. Generates a new post in Markdown format with similar style and tone
4. Creates images using Stable Diffusion XL for any image placeholders
5. Publishes the complete post to your WordPress site
"""

import os
import json
import re
import time
import random
import base64
import io
import sys
import markdown
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image
import boto3

# Constants
REGION = "us-west-2"  # AWS region where Bedrock is available
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"  # Using Claude 3 Sonnet model
IMAGE_MODEL_ID = "stability.stable-diffusion-xl-v1"  # Using Stable Diffusion XL

def get_wp_credentials():
    """Load WordPress credentials from JSON file"""
    try:
        # Look for credentials in the current directory and parent directory
        credential_paths = [
            'blog-credentials.json', 
            '../blog-credentials.json',
            'blog-credentials-rest.json',
            '../blog-credentials-rest.json'
        ]
        for path in credential_paths:
            if os.path.exists(path):
                print(f"Found credentials at {path}")
                with open(path, 'r') as f:
                    return json.load(f)
        raise FileNotFoundError("Could not find credentials file")
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def create_wp_client(credentials):
    """Create a WordPress REST API client session with authentication"""
    if not credentials:
        return None
    
    # Extract the site URL from the site_url or legacy xmlrpc_url (for backward compatibility)
    if 'xmlrpc_url' in credentials:
        site_url = credentials['xmlrpc_url'].replace('/xmlrpc.php', '')
    elif 'site_url' in credentials:
        site_url = credentials['site_url']
    else:
        print("Error: No site URL found in credentials")
        return None
    
    # Ensure site_url doesn't end with a slash
    site_url = site_url.rstrip('/')
    
    # Create a session with authentication
    session = requests.Session()
    session.auth = HTTPBasicAuth(credentials['username'], credentials['password'])
    
    # Store the base URL for the WordPress REST API
    api_base_url = f"{site_url}/wp-json/wp/v2"
    
    return {
        'session': session,
        'api_base_url': api_base_url
    }

def get_recent_posts(wp_client, num_posts=5):
    """Fetch recent posts from WordPress via REST API"""
    try:
        response = wp_client['session'].get(
            f"{wp_client['api_base_url']}/posts",
            params={
                'per_page': num_posts,
                'status': 'publish',
                'orderby': 'date',
                'order': 'desc',
                '_embed': 1  # Include embedded info like author, featured media
            }
        )
        response.raise_for_status()
        posts = response.json()
        
        # Format posts for analysis
        formatted_posts = []
        for post in posts:
            # Extract content without HTML tags
            content = re.sub(r'<[^>]+>', '', post['content']['rendered'])
            
            formatted_post = {
                'title': post['title']['rendered'],
                'content': content,
                'excerpt': re.sub(r'<[^>]+>', '', post['excerpt']['rendered']),
                'date': post['date'],
                'link': post['link'],
                'id': post['id']
            }
            
            # Add tags if available
            if 'tags' in post and post['tags']:
                formatted_post['tags'] = post['tags']
                
            formatted_posts.append(formatted_post)
            
        return formatted_posts
    except Exception as e:
        print(f"Error fetching recent posts: {e}")
        return []

def get_all_tags(wp_client):
    """Fetch all tags from WordPress"""
    try:
        all_tags = []
        page = 1
        per_page = 100
        
        while True:
            response = wp_client['session'].get(
                f"{wp_client['api_base_url']}/tags",
                params={
                    'per_page': per_page,
                    'page': page
                }
            )
            response.raise_for_status()
            tags = response.json()
            
            if not tags:
                break
                
            all_tags.extend(tags)
            
            # Check if we've reached the last page
            if len(tags) < per_page:
                break
                
            page += 1
            
        return all_tags
    except Exception as e:
        print(f"Error fetching tags: {e}")
        return []

def create_tag(wp_client, tag_name):
    """Create a new tag in WordPress"""
    try:
        response = wp_client['session'].post(
            f"{wp_client['api_base_url']}/tags",
            json={
                'name': tag_name
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error creating tag '{tag_name}': {e}")
        return None

def get_or_create_tags(wp_client, tag_names):
    """Get or create tags by name and return their IDs"""
    all_tags = get_all_tags(wp_client)
    tag_map = {tag['name'].lower(): tag['id'] for tag in all_tags}
    
    tag_ids = []
    for tag_name in tag_names:
        tag_name_lower = tag_name.lower()
        if tag_name_lower in tag_map:
            tag_ids.append(tag_map[tag_name_lower])
        else:
            new_tag = create_tag(wp_client, tag_name)
            if new_tag:
                tag_ids.append(new_tag['id'])
                
    return tag_ids

def generate_post_with_claude(recent_posts):
    """Generate a new blog post using Claude 3 Sonnet in Markdown format"""
    if not recent_posts:
        print("No recent posts found to analyze style")
        # Generate a post anyway with default style
        recent_posts_text = "No recent posts available for style analysis."
    else:
        # Format recent posts for Claude to analyze
        recent_posts_text = "\n\n".join([
            f"Title: {post['title']}\n\nContent: {post['content']}"
            for post in recent_posts[:3]  # Use up to 3 recent posts
        ])
    
    # Create Bedrock client
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION
    )
    
    # Current date for topical content
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Prepare the prompt for Claude
    prompt = """You are a witty, insightful blog writer with a casual, conversational style and a touch of humor.

Today is """ + current_date + """.

Here are some recent blog posts that show the writing style to emulate:

""" + recent_posts_text + """

Please generate a new blog post in Markdown format that matches this style. The post should:
1. Have an engaging, SEO-friendly title as a level 1 heading (# Title)
2. Include an introduction, 3-5 main sections with subheadings (## Subheading), and a conclusion
3. Be informative but conversational in tone
4. Include 2-3 places where images should be inserted, marked as ![Image: description](image-placeholder)
5. Be 800-1200 words in length

Also provide the following metadata separately:
- Meta description for SEO (150-160 characters)
- 3-5 relevant tags for the post
- A brief excerpt (about 55 words)

Choose a topic that would be interesting to a tech-savvy audience interested in AI, software development, cloud computing, or digital innovation.

Format your response as:

---TITLE---
# Your Title Here

---CONTENT---
Your markdown content here with ![Image: description](image-placeholder) for images

---META---
Meta description: Your meta description here
Tags: tag1, tag2, tag3
Excerpt: Your excerpt here
"""

    try:
        # Call Claude 3 Sonnet
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
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
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        content = response_body.get('content')[0].get('text')
        
        # Parse the response to extract the different sections
        title_match = re.search(r'---TITLE---\s*(.*?)(?=---CONTENT---)', content, re.DOTALL)
        content_match = re.search(r'---CONTENT---\s*(.*?)(?=---META---)', content, re.DOTALL)
        meta_match = re.search(r'---META---\s*(.*)', content, re.DOTALL)
        
        if not title_match or not content_match or not meta_match:
            print("Error parsing Claude's response - couldn't find all sections")
            print(f"Raw response: {content}")
            return None
        
        # Extract and process the data
        title = re.sub(r'^#\s+', '', title_match.group(1).strip())
        markdown_content = content_match.group(1).strip()
        
        # Parse metadata
        meta_text = meta_match.group(1).strip()
        meta_description = re.search(r'Meta description:\s*(.*?)(?=\n|$)', meta_text)
        tags = re.search(r'Tags:\s*(.*?)(?=\n|$)', meta_text)
        excerpt = re.search(r'Excerpt:\s*(.*?)(?=\n|$)', meta_text)
        
        return {
            "title": title,
            "content": markdown_content,
            "meta_description": meta_description.group(1).strip() if meta_description else "",
            "tags": [tag.strip() for tag in tags.group(1).split(',')] if tags else [],
            "excerpt": excerpt.group(1).strip() if excerpt else ""
        }
    except Exception as e:
        print(f"Error generating post with Claude: {e}")
        return None

def extract_image_placeholders(markdown_content):
    """Extract image placeholders from Markdown content"""
    # Match multiple image placeholder formats:
    # 1. ![Image: description](image-placeholder)
    # 2. [IMAGE: description]
    # 3. [image: description]
    patterns = [
        r'!\[Image:\s*(.*?)\]\(image-placeholder\)',  # Markdown format
        r'\[IMAGE:\s*(.*?)\]',                        # [IMAGE: description] format
        r'\[image:\s*(.*?)\]'                         # [image: description] format
    ]
    
    descriptions = []
    for pattern in patterns:
        descriptions.extend(re.findall(pattern, markdown_content))
    
    return descriptions

def generate_image(prompt):
    """Generate an image using Stable Diffusion XL"""
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION
    )
    
    # Keep prompt very short but descriptive
    words = prompt.split()
    short_prompt = " ".join(words[:10]) if len(words) > 10 else prompt
    enhanced_prompt = f"Blog illustration: {short_prompt}"
    
    try:
        print(f"Generating image with Stable Diffusion XL: '{enhanced_prompt}'")
        response = bedrock_runtime.invoke_model(
            modelId=IMAGE_MODEL_ID,
            accept='application/json',
            contentType='application/json',
            body=json.dumps({
                "text_prompts": [
                    {
                        "text": enhanced_prompt,
                        "weight": 1.0
                    }
                ],
                "cfg_scale": 8.0,
                "steps": 50,
                "seed": random.randint(0, 4294967295),
                "width": 512,
                "height": 512
            })
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        
        # Get the base64 encoded image
        base64_image = response_body.get('artifacts')[0].get('base64')
        
        # Convert base64 to image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        return image
            
    except Exception as e:
        print(f"Error generating image with Stable Diffusion XL: {e}")
        # For debugging purposes, print more details about the error
        import traceback
        traceback.print_exc()
        
        # Fallback to a placeholder image
        print("Using placeholder image instead")
        try:
            # Create a simple colored placeholder with text
            img = Image.new('RGB', (800, 450), color=(73, 109, 137))
            from PIL import ImageDraw
            d = ImageDraw.Draw(img)
            d.text((10,10), f"AI Image Placeholder\n\n{prompt}", fill=(255,255,255))
            return img
        except:
            return None

def upload_image_to_wordpress(wp_client, image, filename, alt_text):
    """Upload an image to WordPress via REST API"""
    try:
        # Save image to a temporary file
        temp_file = f"temp_{filename}.jpg"
        image.save(temp_file, "JPEG")
        
        # Upload the image
        with open(temp_file, 'rb') as img:
            files = {'file': (f"{filename}.jpg", img, 'image/jpeg')}
            response = wp_client['session'].post(
                f"{wp_client['api_base_url']}/media",
                files=files,
                data={'alt_text': alt_text}
            )
        
        # Clean up the temporary file
        os.remove(temp_file)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error uploading image: {e}")
        if os.path.exists(f"temp_{filename}.jpg"):
            os.remove(f"temp_{filename}.jpg")
        return None

def replace_image_placeholders(wp_client, markdown_content, image_descriptions):
    """Replace image placeholders with actual WordPress images"""
    updated_content = markdown_content
    
    # Define all the placeholder patterns we need to replace
    placeholder_patterns = [
        lambda desc: f'![Image: {desc}](image-placeholder)',
        lambda desc: f'[IMAGE: {desc}]',
        lambda desc: f'[image: {desc}]'
    ]
    
    for i, description in enumerate(image_descriptions):
        print(f"Processing image {i+1}/{len(image_descriptions)}: {description}")
        
        # Try to generate image up to 2 times
        image = None
        for attempt in range(2):
            print(f"  Attempt {attempt+1}/2 to generate image")
            image = generate_image(description)
            if image:
                print("  Image generated successfully")
                break
            print(f"  Retrying image generation for: {description}")
            time.sleep(1)
        
        if image:
            # Upload image to WordPress
            sanitized_desc = re.sub(r'[^a-zA-Z0-9]', '-', description)[:40]
            filename = f"ai-image-{sanitized_desc}"
            print(f"  Uploading image to WordPress as {filename}")
            uploaded = upload_image_to_wordpress(wp_client, image, filename, description)
            
            if uploaded:
                print(f"  Image uploaded successfully: {uploaded['source_url']}")
                # Create Markdown for the image with figure and caption
                image_md = f'<figure class="wp-block-image size-large">\n'
                image_md += f'<img src="{uploaded["source_url"]}" alt="{description}" />\n'
                image_md += f'<figcaption>{description}</figcaption>\n'
                image_md += '</figure>'
                
                # Replace all possible placeholder formats with the image HTML
                for pattern_func in placeholder_patterns:
                    placeholder = pattern_func(description)
                    updated_content = updated_content.replace(placeholder, image_md)
            else:
                print("  Failed to upload image")
                # If upload failed, replace with a message
                fallback_msg = f'*Image generation failed for: {description}*'
                for pattern_func in placeholder_patterns:
                    placeholder = pattern_func(description)
                    updated_content = updated_content.replace(placeholder, fallback_msg)
        else:
            print("  Failed to generate image")
            # If generation failed, replace with a message
            fallback_messages = [
                f'*AI tried to draw "{description}" but apparently needs more coffee.*',
                f'*Image generation failed for: "{description}". The AI is taking an artistic break.*',
                f'*Our AI artist was feeling uninspired when trying to create: "{description}"*'
            ]
            fallback = random.choice(fallback_messages)
            for pattern_func in placeholder_patterns:
                placeholder = pattern_func(description)
                updated_content = updated_content.replace(placeholder, fallback)
    
    return updated_content

def markdown_to_html(markdown_content):
    """Convert Markdown content to HTML for WordPress"""
    try:
        # Try to use extended markdown features
        html = markdown.markdown(
            markdown_content,
            extensions=['extra', 'nl2br', 'sane_lists'],
            output_format='html5'
        )
        return html
    except ImportError:
        # Fall back to basic markdown if extensions aren't available
        print("Warning: Markdown extensions not available, using basic markdown conversion")
        return markdown.markdown(markdown_content)
    except Exception as e:
        print(f"Error converting markdown to HTML: {e}")
        # Return the original markdown as a fallback
        return f"<pre>{markdown_content}</pre>"

def publish_post_to_wordpress(wp_client, post_data):
    """Publish the generated post to WordPress via REST API"""
    try:
        # Get or create tags
        tag_ids = get_or_create_tags(wp_client, post_data['tags'])
        
        # Extract image placeholders and replace them with actual images
        image_descriptions = extract_image_placeholders(post_data['content'])
        content_with_images = replace_image_placeholders(wp_client, post_data['content'], image_descriptions)
        
        # Convert Markdown to HTML
        html_content = markdown_to_html(content_with_images)
        
        # Prepare the post data
        wp_post_data = {
            'title': post_data['title'],
            'content': html_content,
            'excerpt': post_data['excerpt'],
            'status': 'publish',
            'tags': tag_ids,
            'meta': {
                'description': post_data['meta_description']
            }
        }
        
        # Create the post
        response = wp_client['session'].post(
            f"{wp_client['api_base_url']}/posts",
            json=wp_post_data
        )
        response.raise_for_status()
        
        published_post = response.json()
        print(f"Post published successfully: {published_post['link']}")
        return published_post
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
    
    # Create WordPress client
    wp_client = create_wp_client(credentials)
    if not wp_client:
        print("Failed to create WordPress client")
        return
    
    # Fetch recent posts
    print("Fetching recent posts...")
    recent_posts = get_recent_posts(wp_client)
    if not recent_posts:
        print("No recent posts found")
    else:
        print(f"Found {len(recent_posts)} recent posts")
    
    # Generate new post with Claude
    print("Generating new post with Claude 3 Sonnet...")
    post_data = generate_post_with_claude(recent_posts)
    if not post_data:
        print("Failed to generate post")
        return
    
    print(f"Generated post: {post_data['title']}")
    
    # Publish post to WordPress
    print("Publishing post to WordPress...")
    published_post = publish_post_to_wordpress(wp_client, post_data)
    if published_post:
        print("Post published successfully!")
        print(f"URL: {published_post['link']}")
    else:
        print("Failed to publish post")

if __name__ == "__main__":
    main()
