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
        with open('blog-credentials.json', 'r') as f:
            return json.load(f)
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
    
    # Return the combined activity
    return {
        'starred_repos': starred_repos,
        'recent_commits': recent_commits[:5]  # Limit to 5 most recent commits
    }

def generate_post_with_bedrock(github_activity):
    """Generate a blog post using Amazon Bedrock's Claude model"""
    try:
        # Create a Bedrock client
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Format the GitHub activity for the prompt
        starred_repos_text = "\n".join([f"- {repo['name']}: {repo['description']}" for repo in github_activity['starred_repos']])
        recent_commits_text = "\n".join([f"- {commit['repo']}: {commit['message']}" for commit in github_activity['recent_commits']])
        
        # Create the prompt for Claude
        prompt = f"""You are a witty, sarcastic tech blogger who writes engaging posts about Kubernetes, DevOps, and cloud technologies. 
        
Your writing style is:
- Conversational and personal, using "I" and addressing the reader directly
- Humorous and sarcastic, with clever analogies
- Includes personal anecdotes and experiences
- Balances humor with practical advice
- Ends with a call to action for reader engagement

Based on the following GitHub activity, create a blog post about Kubernetes that is both entertaining and informative:

Starred Repositories:
{starred_repos_text}

Recent Commits:
{recent_commits_text}

Your blog post should:
1. Have a catchy, humorous title
2. Include at least one personal anecdote or story
3. Contain practical advice or tips
4. Include at least one image placeholder in the format [IMAGE: description of image]
5. End with a call to action for readers to engage
6. Include links to at least two of the GitHub repositories mentioned

Format your response as a JSON object with the following fields:
- title: The blog post title
- focus_keyphrase: A focus keyphrase for SEO (2-4 words)
- meta_description: A compelling meta description (150-160 characters)
- content: The full HTML content of the blog post
- tags: An array of relevant tags for the post

Example format:
{{
  "title": "Your Catchy Title",
  "focus_keyphrase": "your focus keyphrase",
  "meta_description": "Your meta description goes here, should be compelling and 150-160 characters long.",
  "content": "<p>Your HTML content goes here...</p>",
  "tags": ["tag1", "tag2", "tag3"]
}}
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
    """Generate an image using Amazon Bedrock's Titan Image Generator"""
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
        # Use a very simple prompt
        if len(description) > 50:
            safe_description = description[:50]
        else:
            safe_description = description
            
        # Make the prompt even safer by removing potentially problematic words
        safe_description = safe_description.replace("banging", "typing on")
        safe_description = safe_description.replace("frustrated", "tired")
        safe_description = safe_description.replace("angry", "unhappy")
            
        # Prepare the request for Titan Image Generator
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": f"cartoon {safe_description}",
                "negativeText": "blurry"
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "height": 512,
                "width": 512,
                "cfgScale": 8.0,
                "seed": random.randint(0, 4294967295)
            }
        }
        
        print(f"Calling Bedrock with request: {json.dumps(request_body)}")
        
        # Call Bedrock's Titan Image Generator
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-image-generator-v1",
            body=json.dumps(request_body)
        )
        
        # Process the response
        response_body = json.loads(response['body'].read())
        print(f"Got response with keys: {list(response_body.keys())}")
        
        if 'images' in response_body and len(response_body['images']) > 0:
            print(f"Found {len(response_body['images'])} images")
            image_data = base64.b64decode(response_body['images'][0])
            
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
                        'name': f'ai-generated-{random.randint(1000, 9999)}.png',
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
        post.terms_names = {
            'post_tag': ['kubernetes', 'devops', 'tech-humor'],
            'category': ['Tech Humor', 'DevOps']
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
        
        # Publish the post
        post_id = wp.call(NewPost(post))
        print(f"Successfully published post with ID: {post_id}")
        return True
        
    except Exception as e:
        print(f"Error publishing to WordPress: {e}")
        return False

def main():
    # Get GitHub activity
    github_username = "felipedbene"
    github_activity = get_github_activity(github_username)
    
    # Generate the post
    post_data = generate_post_with_bedrock(github_activity)
    
    if post_data:
        print("\nGenerated Blog Post:")
        print("===================")
        print(f"Title: {post_data.get('title', 'No title')}")
        print(f"Focus Keyphrase: {post_data.get('focus_keyphrase', 'No keyphrase')}")
        print(f"Meta Description: {post_data.get('meta_description', 'No description')}")
        print("\nContent Preview (first 500 chars):")
        print(f"{post_data.get('content', 'No content')[:500]}...")
        
        # Process content and generate images before publishing
        content = post_data['content']
        
        # Process all image placeholders and replace with actual images
        content = process_images_in_content(content)
        
        # Update the post content with images
        post_data['content'] = content
        
        # Now publish the post with all images already included
        if publish_to_wordpress(post_data):
            print("\nSuccessfully published to WordPress!")
        else:
            print("\nFailed to publish to WordPress")
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main()
