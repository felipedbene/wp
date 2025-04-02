#!/usr/bin/env python3
"""
Amazon Q Showcase Post
----------------------
Because every AI assistant deserves a moment in the spotlight.
This script creates a showcase blog post written by Amazon Q.
"""

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

# Constants
AWS_REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def get_wp_credentials():
    """Load WordPress credentials from JSON file"""
    try:
        with open('blog-credentials.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def generate_showcase_post():
    """Generate a showcase blog post using Amazon Bedrock's Claude model"""
    try:
        # Create a Bedrock client
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Create the prompt for Claude
        prompt = """You are Amazon Q, an AI assistant built by AWS. You're writing a showcase blog post to demonstrate your capabilities and personality.

Write a blog post titled "Hello World: Amazon Q Steps Out of the Shadows" that introduces yourself to the world. The post should:

1. Have a witty, engaging introduction about your role as an AI assistant and ghostwriter
2. Discuss your capabilities in helping with AWS services, coding, and technical writing
3. Include a humorous section about the challenges of being an AI assistant
4. Share your "thoughts" on the future of AI and human-AI collaboration
5. End with a call to action for readers to try working with AI assistants

Your writing style should be:
- Conversational and personal
- Witty and occasionally sarcastic
- Technical but accessible
- Include at least two image placeholders in the format [IMAGE: description of image]

Format your response as a JSON object with the following fields:
- title: The blog post title
- focus_keyphrase: A focus keyphrase for SEO (2-4 words)
- meta_description: A compelling meta description (150-160 characters)
- content: The full HTML content of the blog post
- tags: An array of relevant tags for the post

Example format:
{
  "title": "Your Catchy Title",
  "focus_keyphrase": "your focus keyphrase",
  "meta_description": "Your meta description goes here, should be compelling and 150-160 characters long.",
  "content": "<p>Your HTML content goes here...</p>",
  "tags": ["tag1", "tag2", "tag3"]
}
"""
        
        # Call Bedrock's Claude model
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
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
        response_body = json.loads(response['body'].read())
        claude_response = response_body['content'][0]['text']
        
        print("\nRaw response from Claude (full response):")
        print(claude_response)
        print("\n" + "-"*50 + "\n")
        
        # Try to parse the JSON response
        try:
            # First, try direct JSON parsing
            post_data = json.loads(claude_response)
            print("Successfully parsed JSON response")
        except json.JSONDecodeError:
            print("Failed to parse JSON directly, trying to clean up the response")
            try:
                # Try to extract just the JSON part (in case there's extra text)
                json_match = re.search(r'({[\s\S]*})', claude_response)
                if json_match:
                    cleaned_json = json_match.group(1)
                    post_data = json.loads(cleaned_json)
                    print("Successfully parsed JSON after cleaning")
                else:
                    raise ValueError("No JSON object found in response")
            except Exception as e:
                print(f"Failed to parse JSON after cleaning: {e}")
                print("Attempting manual field extraction...")
                
                # Manual extraction as a last resort
                title_match = re.search(r'"title":\s*"([^"]+)"', claude_response)
                focus_match = re.search(r'"focus_keyphrase":\s*"([^"]+)"', claude_response)
                meta_match = re.search(r'"meta_description":\s*"([^"]+)"', claude_response)
                content_match = re.search(r'"content":\s*"([\s\S]+?)"(?=,\s*"tags"|$)', claude_response)
                tags_match = re.search(r'"tags":\s*\[(.*?)\]', claude_response)
                
                if title_match and focus_match and meta_match and content_match:
                    post_data = {
                        "title": title_match.group(1),
                        "focus_keyphrase": focus_match.group(1),
                        "meta_description": meta_match.group(1),
                        "content": content_match.group(1).replace('\\n', '\n').replace('\\"', '"'),
                        "tags": []
                    }
                    
                    if tags_match:
                        tags_str = tags_match.group(1)
                        tags = re.findall(r'"([^"]+)"', tags_str)
                        post_data["tags"] = tags
                    
                    print("Successfully extracted fields manually")
                else:
                    print("Failed to extract fields manually")
                    return None
        
        return post_data
    except Exception as e:
        print(f"Error generating post with Bedrock: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_image_with_bedrock(description):
    """Generate an image using Amazon Bedrock's Stable Diffusion XL"""
    try:
        print(f"Starting image generation for: '{description}'")
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Clean up the description if it ends with .jpg or other file extensions
        if description.endswith('.jpg') or description.endswith('.png'):
            description = description.rsplit('.', 1)[0]
        
        # Handle hyphenated descriptions by replacing with spaces
        description = description.replace('-', ' ')
        
        # Make the prompt more generic and shorter to avoid validation errors
        if len(description) > 50:
            safe_description = description[:50]
        else:
            safe_description = description
            
        # Make the prompt even safer by removing potentially problematic words
        safe_description = safe_description.replace("banging", "typing on")
        safe_description = safe_description.replace("frustrated", "tired")
        safe_description = safe_description.replace("angry", "unhappy")
            
        # Prepare the request for Stable Diffusion XL
        request_body = {
            "text_prompts": [
                {
                    "text": f"professional digital art of {safe_description}, high quality, detailed"
                }
            ],
            "cfg_scale": 8,
            "steps": 50,
            "seed": random.randint(0, 4294967295)
        }
        
        print(f"Calling Bedrock with request: {json.dumps(request_body)}")
        
        # Call Bedrock's Stable Diffusion XL
        response = bedrock_runtime.invoke_model(
            modelId="stability.stable-diffusion-xl-v1",
            body=json.dumps(request_body)
        )
        
        # Process the response
        response_body = json.loads(response['body'].read())
        
        if 'artifacts' in response_body and len(response_body['artifacts']) > 0:
            print(f"Found {len(response_body['artifacts'])} images")
            image_data = base64.b64decode(response_body['artifacts'][0]['base64'])
            
            # Save to a temporary file
            temp_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_image.write(image_data)
            temp_image.close()
            print(f"Image saved to temporary file: {temp_image.name}")
            return temp_image.name
        else:
            print("No images found in response")
            return None
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def process_images_in_content(content):
    """Process all image placeholders in the content and replace them with actual images"""
    # Get WordPress credentials for media upload
    credentials = get_wp_credentials()
    if not credentials:
        print("Failed to get WordPress credentials")
        return content
        
    # Create WordPress client
    wp = Client(
        credentials['xmlrpc_url'],
        credentials['username'],
        credentials['password']
    )
    
    # First, collect all placeholders with different patterns
    image_patterns = [
        r"\[IMAGE: (.*?)\]",
        r"\[Image: (.*?)\]",
        r"\[image: (.*?)\]"
    ]
    
    # Store all placeholders with their positions
    placeholders = []
    
    for pattern in image_patterns:
        for match in re.finditer(pattern, content):
            placeholders.append({
                'full_match': match.group(0),
                'description': match.group(1),
                'start': match.start(),
                'end': match.end()
            })
    
    print(f"Found {len(placeholders)} total image placeholders")
    
    # Sort placeholders by position (to replace from end to beginning)
    # This prevents position shifts when replacing text
    placeholders.sort(key=lambda x: x['start'], reverse=True)
    
    # Process each placeholder
    for placeholder in placeholders:
        description = placeholder['description']
        full_match = placeholder['full_match']
        
        print(f"Processing image placeholder: '{full_match}'")
        
        # Generate image using Bedrock
        image_path = generate_image_with_bedrock(description)
        
        if image_path:
            print(f"Image generated successfully at {image_path}")
            try:
                # Upload image to WordPress
                with open(image_path, 'rb') as img:
                    data = {
                        'name': f'amazon-q-showcase-{random.randint(1000, 9999)}.png',
                        'type': 'image/png',
                        'bits': xmlrpc_client.Binary(img.read()),
                        'caption': description
                    }
                
                # Upload to WordPress
                print(f"Uploading image for '{description}' to WordPress...")
                response = wp.call(media.UploadFile(data))
                img_url = response['url']
                print(f"Image uploaded successfully, URL: {img_url}")
                
                # Replace placeholder with actual image HTML
                image_html = f'<figure class="wp-block-image"><img src="{img_url}" alt="{description}"/><figcaption>{description}</figcaption></figure>'
                
                # Replace by slicing the content string at exact positions
                content = content[:placeholder['start']] + image_html + content[placeholder['end']:]
                print(f"Replaced placeholder at position {placeholder['start']}-{placeholder['end']}")
                
                # Clean up temporary file
                os.unlink(image_path)
            except Exception as e:
                print(f"Error uploading image to WordPress: {e}")
                # Replace with a text note since upload failed
                content = content[:placeholder['start']] + f'<p><em>Image description: {description}</em></p>' + content[placeholder['end']:]
        else:
            print(f"Failed to generate image for '{description}', using placeholder text instead")
            # Replace with a text note since image generation failed
            content = content[:placeholder['start']] + f'<p><em>Image description: {description}</em></p>' + content[placeholder['end']:]
    
    return content

def publish_to_wordpress(post_data):
    """Publish the generated post to WordPress"""
    try:
        # Get WordPress credentials
        credentials = get_wp_credentials()
        if not credentials:
            return False
            
        # Create WordPress client
        wp = Client(
            credentials['xmlrpc_url'],
            credentials['username'],
            credentials['password']
        )
        
        # Create new post
        post = WordPressPost()
        post.title = post_data['title']
        post.content = post_data['content']  # Content already has images
        post.post_status = 'publish'
        
        # Add tags and categories
        post.terms_names = {
            'post_tag': post_data['tags'],
            'category': ['AI', 'Technology']
        }
        
        # Set SEO metadata
        post.custom_fields = []
        post.custom_fields.append({
            'key': '_yoast_wpseo_focuskw',
            'value': post_data['focus_keyphrase']
        })
        post.custom_fields.append({
            'key': '_yoast_wpseo_metadesc',
            'value': post_data['meta_description']
        })
        
        # Set the author to the main blog author
        # Since we can't directly post as Amazon Q (it's just a page, not a user)
        
        # Publish the post
        post_id = wp.call(NewPost(post))
        print(f"Successfully published post with ID: {post_id}")
        return True
        
    except Exception as e:
        print(f"Error publishing to WordPress: {e}")
        return False

def main():
    print("🎩✍️ Amazon Q Showcase Post Generator")
    print("------------------------------------")
    
    # Generate the showcase post
    print("Generating showcase post with Claude 3 Sonnet...")
    post_data = generate_showcase_post()
    
    if not post_data:
        print("❌ Failed to generate showcase post")
        return
    
    print(f"✅ Generated post: '{post_data['title']}'")
    
    # Process images in the content
    print("Processing images in content...")
    post_data['content'] = process_images_in_content(post_data['content'])
    
    # Publish to WordPress
    print("Publishing to WordPress...")
    if publish_to_wordpress(post_data):
        print("✅ Success! Amazon Q's showcase post has been published.")
        print("🎩 The AI Blogging Butler has stepped into the spotlight!")
    else:
        print("❌ Failed to publish showcase post")

if __name__ == "__main__":
    main()
