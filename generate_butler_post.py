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

def generate_image_with_bedrock(description):
    """Generate an image using Amazon Bedrock's Stable Diffusion model instead of Titan"""
    for attempt in range(2):  # Try up to 2 times
        try:
            print(f"Starting image generation attempt {attempt + 1} for: '{description}'")
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
            
            # Use Stable Diffusion instead of Titan
            # Prepare the request for Stable Diffusion
            request_body = {
                "text_prompts": [
                    {
                        "text": f"A simple cartoon illustration of {safe_description}, digital art style, clean lines",
                        "weight": 1.0
                    },
                    {
                        "text": "blurry, distorted, low quality, nsfw, violent",
                        "weight": -1.0
                    }
                ],
                "cfg_scale": 7.0,
                "seed": random.randint(0, 4294967295),
                "steps": 30,
                "width": 512,
                "height": 512
            }
            
            print(f"Calling Bedrock with request: {json.dumps(request_body)}")
            
            # Call Bedrock's Stable Diffusion model
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
                if attempt < 1:  # If this isn't the last attempt
                    continue
                return None
        except Exception as e:
            print(f"Error in attempt {attempt + 1} generating image: {str(e)}")
            import traceback
            traceback.print_exc()
            if attempt < 1:  # If this isn't the last attempt
                print("Retrying image generation...")
                continue
            return None
    return None  # Should never reach here, but just in case

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

def generate_butler_post():
    """Generate a blog post about the AI Blogging Butler"""
    try:
        # Read the custom prompt
        with open('butler_prompt.txt', 'r') as f:
            prompt = f.read()
        
        print("Generating blog post about the AI Blogging Butler...")
        
        # Call Claude to generate the post
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Prepare the request for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }
        
        # Call Claude
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Process the response
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        print("\nRaw response from Claude (full response):")
        print(content)
        print("\n" + "-"*50 + "\n")
        
        # Extract the title from the content
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
            # Remove the title from the content
            content = re.sub(r'^#\s+.+?$', '', content, 1, re.MULTILINE)
        else:
            title = "The AI Blogging Butler: Your Automated Content Creator"
        
        # Clean up the content
        content = content.strip()
        
        # Process images in the content
        content = process_images_in_content(content)
        
        # Create a WordPress post
        post = WordPressPost()
        post.title = title
        post.content = content
        post.post_status = 'publish'
        post.terms_names = {
            'post_tag': ['AI', 'blogging', 'automation', 'Claude', 'Stable Diffusion', 'content creation'],
            'category': ['Technology', 'AI']
        }
        
        # Get WordPress credentials
        credentials = get_wp_credentials()
        if not credentials:
            print("Failed to get WordPress credentials")
            return False
        
        # Create WordPress client
        wp = Client(
            credentials['xmlrpc_url'],
            credentials['username'],
            credentials['password']
        )
        
        # Publish the post
        post_id = wp.call(NewPost(post))
        print(f"Successfully published post with ID: {post_id}")
        
        return True
    except Exception as e:
        print(f"Error generating butler post: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    generate_butler_post()
