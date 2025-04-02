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

def update_generate_and_publish_post():
    """Update the generate_and_publish_post.py file with the new image generation function"""
    try:
        # Read the current file
        with open('generate_and_publish_post.py', 'r') as f:
            content = f.read()
        
        # Create a backup
        with open('generate_and_publish_post.py.bak2', 'w') as f:
            f.write(content)
        
        # Replace the image generation function
        pattern = r"def generate_image_with_bedrock\(description\):.*?return None  # Should never reach here, but just in case"
        
        # Get the new function as a string
        with open(__file__, 'r') as f:
            this_content = f.read()
        
        function_pattern = r"def generate_image_with_bedrock\(description\):.*?return None  # Should never reach here, but just in case"
        import re
        function_match = re.search(function_pattern, this_content, re.DOTALL)
        if function_match:
            new_function = function_match.group(0)
            
            # Replace the function in the original file
            updated_content = re.sub(pattern, new_function, content, flags=re.DOTALL)
            
            # Write the updated content
            with open('generate_and_publish_post.py', 'w') as f:
                f.write(updated_content)
            
            print("Successfully updated generate_and_publish_post.py with the new image generation function")
            return True
        else:
            print("Failed to extract the new function")
            return False
    except Exception as e:
        print(f"Error updating file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test the image generation function
    description = "A person working on a computer with colorful code on screen"
    print(f"Testing image generation with description: {description}")
    image_path = generate_image_with_bedrock(description)
    if image_path:
        print(f"Image generated successfully at: {image_path}")
        # Clean up the temporary file
        os.unlink(image_path)
        
        # Update the main script
        update_generate_and_publish_post()
    else:
        print("Failed to generate image")
